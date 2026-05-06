# src/chitchat/services/chat_service.py
# [v1.0.0] 채팅 스트리밍 서비스
#
# [v0.1.0b0 → v1.0.0 변경사항]
# - DynamicStateEngine 주입: 스트리밍 완료 후 캐릭터 동적 상태 자동 갱신
# - 기억/관계/감정 변화를 ZSTD 압축 blob으로 SQLite에 영속화
# 스트리밍 실행/취소, 세션 상태 전이, 메시지 저장을 관리한다.
from __future__ import annotations
import asyncio
import json
import logging
from collections.abc import Callable
from datetime import datetime, timezone
from chitchat.db.models import ChatMessageRow, ChatProfileRow, ChatSessionRow, UserPersonaRow
from chitchat.db.repositories import RepositoryRegistry
from chitchat.domain.chat_session import InvalidSessionTransitionError, validate_session_transition
from chitchat.domain.ids import new_id
from chitchat.domain.prompt_blocks import AssembledPrompt, estimate_tokens
from chitchat.domain.provider_contracts import (
    ChatCompletionMessage, ChatCompletionRequest, ChatSessionStatus, ModelGenerationSettings,
)
from chitchat.providers.registry import ProviderRegistry
from chitchat.secrets.key_store import KeyStore
from chitchat.services.dynamic_state_engine import DynamicStateEngine
from chitchat.services.prompt_service import PromptService

logger = logging.getLogger(__name__)

# 콜백 타입: delta 텍스트를 UI에 전달
OnChunkCallback = Callable[[str], None]
OnFinishCallback = Callable[[str, dict[str, object] | None], None]  # (full_text, usage)
OnErrorCallback = Callable[[str], None]


class ChatService:
    """채팅 스트리밍 서비스.

    세션 생성, 메시지 저장, 스트리밍 실행/취소를 관리한다.
    [v1.0.0] DynamicStateEngine을 통해 매 턴 후 캐릭터 상태를 갱신한다.
    """
    def __init__(
        self,
        repos: RepositoryRegistry,
        providers: ProviderRegistry,
        key_store: KeyStore,
        prompt_service: PromptService,
        dynamic_state_engine: DynamicStateEngine | None = None,
    ) -> None:
        self._repos = repos
        self._providers = providers
        self._key_store = key_store
        self._prompt_svc = prompt_service
        self._dse = dynamic_state_engine
        self._current_task: asyncio.Task | None = None  # type: ignore[type-arg]

    # --- 세션 관리 ---

    def create_session(self, title: str, chat_profile_id: str, user_persona_id: str) -> ChatSessionRow:
        """새 채팅 세션을 생성한다."""
        now = datetime.now(timezone.utc).isoformat()
        row = ChatSessionRow(
            id=new_id("cs_"), title=title, chat_profile_id=chat_profile_id,
            user_persona_id=user_persona_id, status="draft",
            created_at=now, updated_at=now,
        )
        return self._repos.chat_sessions.upsert(row)

    def get_session(self, id_: str) -> ChatSessionRow | None:
        return self._repos.chat_sessions.get_by_id(id_)

    def get_all_sessions(self) -> list[ChatSessionRow]:
        return self._repos.chat_sessions.get_all()

    def get_session_messages(self, session_id: str) -> list[ChatMessageRow]:
        return self._repos.chat_messages.get_by_session(session_id)

    def get_available_chat_profiles(self) -> list[ChatProfileRow]:
        """사용 가능한 채팅 프로필 목록을 반환한다."""
        return self._repos.chat_profiles.get_all()

    def get_available_user_personas(self) -> list[UserPersonaRow]:
        """사용 가능한 사용자 페르소나 목록을 반환한다."""
        return self._repos.user_personas.get_all()

    def delete_session(self, session_id: str) -> bool:
        """[v0.1.2] 채팅 세션과 관련 메시지를 삭제한다.

        세션 삭제 시 해당 세션의 모든 메시지도 함께 삭제된다.
        """
        self._repos.chat_messages.delete_by_session(session_id)
        return self._repos.chat_sessions.delete_by_id(session_id)


    def _transition(self, session: ChatSessionRow, target: ChatSessionStatus) -> ChatSessionRow:
        """세션 상태를 전이한다."""
        current = session.status
        if not validate_session_transition(current, target):  # type: ignore[arg-type]
            raise InvalidSessionTransitionError(current, target)  # type: ignore[arg-type]
        session.status = target
        session.updated_at = datetime.now(timezone.utc).isoformat()
        return self._repos.chat_sessions.upsert(session)

    # --- 메시지 저장 ---

    def save_user_message(self, session_id: str, content: str) -> ChatMessageRow:
        """사용자 메시지를 저장한다."""
        now = datetime.now(timezone.utc).isoformat()
        row = ChatMessageRow(
            id=new_id("msg_"), session_id=session_id, role="user",
            content=content, token_estimate=estimate_tokens(content),
            created_at=now,
        )
        return self._repos.chat_messages.insert(row)

    def save_assistant_message(
        self, session_id: str, content: str,
        prompt_snapshot: AssembledPrompt | None = None,
        usage: dict[str, object] | None = None,
    ) -> ChatMessageRow:
        """[v0.1.3] 어시스턴트 메시지를 저장한다.

        prompt_snapshot이 전달되면 spec §12.6 규격의 PromptSnapshot을 생성한다.
        포함 필드: chat_profile_id, user_persona_id, model_profile_id,
        prompt_order, blocks, matched_lore_entry_ids,
        truncated_history_message_ids, total_token_estimate, created_at_iso
        """
        now = datetime.now(timezone.utc).isoformat()
        snapshot_json: str | None = None
        if prompt_snapshot:
            # [v0.1.3] 세션에서 프로필 정보를 조회하여 spec §12.6 필드를 채운다
            chat_profile_id = ""
            user_persona_id = ""
            model_profile_id = ""
            session = self._repos.chat_sessions.get_by_id(session_id)
            if session:
                chat_profile_id = session.chat_profile_id
                user_persona_id = session.user_persona_id
                cp = self._repos.chat_profiles.get_by_id(session.chat_profile_id)
                if cp:
                    model_profile_id = cp.model_profile_id

            # 로어북 매칭 ID: assembled에서 수집된 ID 사용
            matched_lore_ids = prompt_snapshot.matched_lore_entry_ids

            # 프롬프트 순서: 블록 종류 목록
            prompt_order = [
                {"kind": b.kind, "token_estimate": b.token_estimate}
                for b in prompt_snapshot.blocks
            ]

            snapshot_json = json.dumps({
                "chat_profile_id": chat_profile_id,
                "user_persona_id": user_persona_id,
                "model_profile_id": model_profile_id,
                "prompt_order": prompt_order,
                "blocks": [
                    {"kind": b.kind, "token_estimate": b.token_estimate, "source_id": b.source_id}
                    for b in prompt_snapshot.blocks
                ],
                "matched_lore_entry_ids": matched_lore_ids,
                # [v0.1.4] spec §12.6: 잘린 히스토리 메시지 ID를 assembled에서 수집
                "truncated_history_message_ids": prompt_snapshot.truncated_history_message_ids,
                "total_token_estimate": prompt_snapshot.total_tokens,
                "budget_tokens": prompt_snapshot.budget_tokens,
                "history_count": prompt_snapshot.history_count,
                "truncated_count": prompt_snapshot.truncated_count,
                "usage": usage,
                "created_at_iso": now,
            }, ensure_ascii=False)
        row = ChatMessageRow(
            id=new_id("msg_"), session_id=session_id, role="assistant",
            content=content, prompt_snapshot_json=snapshot_json,
            token_estimate=estimate_tokens(content), created_at=now,
        )
        return self._repos.chat_messages.insert(row)

    # --- 스트리밍 ---

    async def start_stream(
        self,
        session_id: str,
        on_chunk: OnChunkCallback,
        on_finish: OnFinishCallback,
        on_error: OnErrorCallback,
    ) -> None:
        """스트리밍을 시작한다.

        1. 세션을 active → streaming으로 전이한다.
        2. 프롬프트를 조립한다.
        3. Provider의 stream_chat()을 호출하여 chunk를 수신한다.
        4. 완료 시 streaming → active로 전이하고 메시지를 저장한다.
        """
        session = self._repos.chat_sessions.get_by_id(session_id)
        if not session:
            on_error(f"세션을 찾을 수 없습니다: {session_id}")
            return

        # draft → active 전이 (첫 메시지 시)
        if session.status == "draft":
            session = self._transition(session, "active")

        # active → streaming 전이
        session = self._transition(session, "streaming")

        try:
            # ChatProfile 로드
            cp = self._repos.chat_profiles.get_by_id(session.chat_profile_id)
            if not cp:
                raise ValueError("ChatProfile을 찾을 수 없습니다")

            # ModelProfile 로드
            mp = self._repos.model_profiles.get_by_id(cp.model_profile_id)
            if not mp:
                raise ValueError("ModelProfile을 찾을 수 없습니다")

            # Provider 로드
            prov = self._repos.providers.get_by_id(mp.provider_profile_id)
            if not prov:
                raise ValueError("Provider를 찾을 수 없습니다")

            # API Key 조회
            api_key: str | None = None
            if prov.provider_kind != "lm_studio" and prov.secret_ref:
                api_key = self._key_store.get_key(prov.id, prov.provider_kind)

            # 히스토리 로드
            msgs = self._repos.chat_messages.get_by_session(session_id)
            history = [(m.role, m.content) for m in msgs]
            # [v0.1.4] 잘린 메시지 ID 추적을 위해 ID 리스트 추출
            history_ids = [m.id for m in msgs]

            # 프롬프트 조립
            settings = json.loads(mp.settings_json)
            context_budget = settings.get("context_window_tokens", 8192)
            max_output = settings.get("max_output_tokens", 2048)

            assembled = self._prompt_svc.build_prompt(
                chat_profile_id=session.chat_profile_id,
                user_persona_id=session.user_persona_id,
                history_messages=history[:-1],  # 현재 입력 제외
                current_input=history[-1][1] if history else "",
                context_budget=context_budget,
                max_output_tokens=max_output,
                history_message_ids=history_ids[:-1] if len(history_ids) > 1 else None,
            )

            messages = [ChatCompletionMessage(role=m.role, content=m.content) for m in assembled.messages]
            gen_settings = ModelGenerationSettings(**{k: v for k, v in settings.items()
                if k in ModelGenerationSettings.model_fields})
            request = ChatCompletionRequest(
                provider_profile_id=prov.id,
                model_id=mp.model_id, messages=messages, settings=gen_settings,
            )

            # Provider 프로필 데이터
            from chitchat.domain.provider_contracts import ProviderProfileData
            profile_data = ProviderProfileData(
                id=prov.id, name=prov.name, provider_kind=prov.provider_kind,  # type: ignore[arg-type]
                base_url=prov.base_url, secret_ref=prov.secret_ref,
                timeout_seconds=prov.timeout_seconds,
            )

            # 스트리밍 실행
            adapter = self._providers.get(prov.provider_kind)  # type: ignore[arg-type]
            full_text = ""
            last_usage: dict[str, object] | None = None

            async for chunk in adapter.stream_chat(profile_data, request, api_key):
                full_text += chunk.delta
                on_chunk(chunk.delta)
                if chunk.usage:
                    last_usage = chunk.usage
                if chunk.finish_reason:
                    break

            # 어시스턴트 메시지 저장
            self.save_assistant_message(session_id, full_text, assembled, last_usage)

            # [v1.0.0] 동적 상태 갱신 — 비차단, 실패 시 스트리밍 결과에 영향 없음
            await self._update_dynamic_state(session_id, full_text)

            # streaming → active 전이
            session = self._repos.chat_sessions.get_by_id(session_id)
            if session:
                self._transition(session, "active")

            on_finish(full_text, last_usage)

        except asyncio.CancelledError:
            # 사용자가 취소함 → streaming → stopped
            session = self._repos.chat_sessions.get_by_id(session_id)
            if session:
                self._transition(session, "stopped")
            on_error("스트리밍이 취소되었습니다.")
        except Exception as e:
            # 에러 발생 → streaming → failed
            logger.error("스트리밍 실패: %s", e)
            session = self._repos.chat_sessions.get_by_id(session_id)
            if session and session.status == "streaming":
                self._transition(session, "failed")
            on_error(str(e))

    # [v0.1.0b0 Remediation] run_stream(), stop_stream() 삭제
    # 삭제 사유: threading 기반 스트리밍은 ui/async_bridge.py의 AsyncSignalBridge로 대체.
    # 삭제 버전: v0.1.0b0 정합성 감사 Remediation

    # --- 동적 상태 갱신 ---

    async def _update_dynamic_state(self, session_id: str, assistant_text: str) -> None:
        """스트리밍 완료 후 캐릭터 동적 상태를 갱신한다.

        [v1.0.0] 2단계 분석:
        1. AI 판단 기반 분석 (Provider 사용 가능 시)
        2. 키워드 폴백 (AI 분석 실패 또는 Provider 없을 시)

        실패 시 로그만 남기고 채팅 흐름에 영향을 주지 않는다.
        """
        if not self._dse:
            return

        try:
            from chitchat.db.models import DynamicStateRow

            # 세션에서 캐릭터 ID 추출
            session = self._repos.chat_sessions.get_by_id(session_id)
            if not session:
                return

            # ChatProfile에서 AI Persona ID를 가져옴
            cp = self._repos.chat_profiles.get_by_id(session.chat_profile_id)
            if not cp:
                return

            character_id = cp.ai_persona_id
            if not character_id:
                logger.debug("AI 페르소나 미설정 — 동적 상태 갱신 생략")
                return

            # 기존 동적 상태 로드 또는 생성
            ds_row = self._repos.dynamic_states.get_by_character_session(
                character_id, session_id,
            )

            if ds_row:
                state = self._dse.decompress_state(ds_row.state_blob)
            else:
                state = self._dse.create_initial_state(character_id, session_id)

            # 턴 카운트 증가
            self._dse.increment_turn(state)

            # AI 판단 기반 분석 시도 → 실패 시 키워드 폴백
            ai_success = await self._try_ai_analysis(
                session, cp, state, session_id, assistant_text,
            )
            if not ai_success:
                self._keyword_fallback_analysis(state, assistant_text)

            # ZSTD 압축 후 DB 저장
            blob = self._dse.compress_state(state)
            if ds_row:
                ds_row.state_blob = blob
                ds_row.version = state.version
                ds_row.turn_count = state.turn_count
                self._repos.dynamic_states.upsert(ds_row)
            else:
                new_row = DynamicStateRow(
                    id=new_id("ds_"),
                    character_id=character_id,
                    session_id=session_id,
                    state_blob=blob,
                    version=state.version,
                    turn_count=state.turn_count,
                )
                self._repos.dynamic_states.upsert(new_row)

            logger.info(
                "동적 상태 갱신 완료: 캐릭터=%s, 세션=%s, 턴=%d, AI분석=%s",
                character_id, session_id, state.turn_count,
                "성공" if ai_success else "폴백",
            )

        except Exception:
            # 동적 상태 갱신 실패는 채팅에 영향을 주지 않는다
            logger.exception("동적 상태 갱신 실패 (비차단)")

    async def _try_ai_analysis(
        self,
        session: "ChatSessionRow",  # noqa: F821
        cp: "ChatProfileRow",  # noqa: F821
        state: "DynamicCharacterState",  # noqa: F821
        session_id: str,
        assistant_text: str,
    ) -> bool:
        """AI Provider를 사용하여 대화를 분석하고 동적 상태를 갱신한다.

        [v1.0.0] 성공 시 True, 실패 시 False를 반환하여 키워드 폴백을 결정한다.
        """
        try:
            # ModelProfile → Provider 체인 로드
            mp = self._repos.model_profiles.get_by_id(cp.model_profile_id)
            if not mp:
                return False

            prov = self._repos.providers.get_by_id(mp.provider_profile_id)
            if not prov:
                return False

            # API Key 조회
            api_key: str | None = None
            if prov.provider_kind != "lm_studio" and prov.secret_ref:
                api_key = self._key_store.get_key(prov.id, prov.provider_kind)

            # AI Persona 이름 가져오기
            persona = self._repos.ai_personas.get_by_id(cp.ai_persona_id)
            character_name = persona.name if persona else "캐릭터"

            # 최근 대화 히스토리 로드
            msgs = self._repos.chat_messages.get_by_session(session_id)
            recent_messages = [(m.role, m.content) for m in msgs[-10:]]

            # 분석 프롬프트 생성
            analysis_prompt = self._dse.build_analysis_prompt(
                state, character_name, recent_messages,
            )

            # 분석용 Provider 호출 (비스트리밍)
            from chitchat.domain.provider_contracts import (
                ChatCompletionMessage,
                ChatCompletionRequest,
                ModelGenerationSettings,
                ProviderProfileData,
            )

            request = ChatCompletionRequest(
                provider_profile_id=prov.id,
                model_id=mp.model_id,
                messages=[
                    ChatCompletionMessage(role="system", content=analysis_prompt),
                    ChatCompletionMessage(
                        role="user",
                        content="위 대화를 분석하고 JSON으로 응답하세요.",
                    ),
                ],
                settings=ModelGenerationSettings(
                    temperature=0.3,  # 분석이므로 낮은 온도
                    max_output_tokens=500,
                ),
            )

            profile_data = ProviderProfileData(
                id=prov.id,
                name=prov.name,
                provider_kind=prov.provider_kind,  # type: ignore[arg-type]
                base_url=prov.base_url,
                secret_ref=prov.secret_ref,
                timeout_seconds=prov.timeout_seconds,
            )

            # 스트리밍으로 수집 (비스트리밍 API가 없으므로)
            adapter = self._providers.get(prov.provider_kind)  # type: ignore[arg-type]
            response_text = ""
            async for chunk in adapter.stream_chat(profile_data, request, api_key):
                response_text += chunk.delta
                if chunk.finish_reason:
                    break

            if not response_text.strip():
                logger.warning("AI 분석 응답이 비어 있음")
                return False

            # JSON 파싱 + 적용
            analysis = self._dse.parse_analysis_response(response_text)
            if not analysis:
                return False

            self._dse.apply_analysis(state, analysis)
            logger.info("AI 기반 동적 상태 분석 성공")
            return True

        except Exception:
            logger.debug("AI 분석 실패 — 키워드 폴백으로 전환", exc_info=True)
            return False

    def _keyword_fallback_analysis(
        self,
        state: "DynamicCharacterState",  # noqa: F821
        text: str,
    ) -> None:
        """AI 분석 실패 시 키워드 기반으로 동적 상태를 갱신한다.

        [v1.0.0] AI 판단 기반 분석의 폴백 메커니즘.
        7개 한국어 키워드를 매칭하여 기억 형성 + 관계 변수 조정.
        """
        if not self._dse:
            return

        # 키워드 → 트리거 매핑
        keyword_triggers = {
            "약속": ("promise_kept", {"trust": 3}),
            "고마워": ("praise", {"trust": 2, "familiarity": 1}),
            "감사": ("praise", {"trust": 2, "familiarity": 1}),
            "미안": ("conflict_repair", {"repair_ability": 2}),
            "비밀": ("vulnerability", {"emotional_reliance": 3, "fear_of_rejection": -2}),
            "처음으로": ("shared_experience", {"familiarity": 3, "willingness_to_initiate": 2}),
            "함께": ("shared_experience", {"familiarity": 2}),
        }

        triggered = False
        for keyword, (trigger, changes) in keyword_triggers.items():
            if keyword in text:
                self._dse.add_memory(
                    state, trigger, f"대화에서 '{keyword}' 관련 상호작용 감지",
                    emotional_impact=", ".join(f"{k}{v:+d}" for k, v in changes.items()),
                )
                self._dse.update_relationship(state, changes)
                logger.debug("키워드 폴백 트리거: %s → %s", keyword, trigger)
                triggered = True

        if not triggered:
            logger.debug("키워드 폴백: 트리거 없음")

