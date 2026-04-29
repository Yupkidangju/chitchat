# src/chitchat/services/chat_service.py
# [v0.1.0b0] 채팅 스트리밍 서비스
#
# 스트리밍 실행/취소, 세션 상태 전이, 메시지 저장을 관리한다.
# asyncio Task로 Provider의 stream_chat()을 호출하고,
# 매 chunk마다 콜백을 호출하여 UI에 전달한다.
from __future__ import annotations
import asyncio
import json
import logging
from collections.abc import Callable
from datetime import datetime, timezone
from chitchat.db.models import ChatMessageRow, ChatSessionRow
from chitchat.db.repositories import RepositoryRegistry
from chitchat.domain.chat_session import InvalidSessionTransitionError, validate_session_transition
from chitchat.domain.ids import new_id
from chitchat.domain.prompt_blocks import AssembledPrompt, estimate_tokens
from chitchat.domain.provider_contracts import (
    ChatCompletionMessage, ChatCompletionRequest, ChatSessionStatus, ModelGenerationSettings,
)
from chitchat.providers.registry import ProviderRegistry
from chitchat.secrets.key_store import KeyStore
from chitchat.services.prompt_service import PromptService

logger = logging.getLogger(__name__)

# 콜백 타입: delta 텍스트를 UI에 전달
OnChunkCallback = Callable[[str], None]
OnFinishCallback = Callable[[str, dict | None], None]  # (full_text, usage)
OnErrorCallback = Callable[[str], None]


class ChatService:
    """채팅 스트리밍 서비스.

    세션 생성, 메시지 저장, 스트리밍 실행/취소를 관리한다.
    """
    def __init__(
        self,
        repos: RepositoryRegistry,
        providers: ProviderRegistry,
        key_store: KeyStore,
        prompt_service: PromptService,
    ) -> None:
        self._repos = repos
        self._providers = providers
        self._key_store = key_store
        self._prompt_svc = prompt_service
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

    def get_available_chat_profiles(self) -> list:
        """사용 가능한 채팅 프로필 목록을 반환한다."""
        return self._repos.chat_profiles.get_all()

    def get_available_user_personas(self) -> list:
        """사용 가능한 사용자 페르소나 목록을 반환한다."""
        return self._repos.user_personas.get_all()

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
        usage: dict | None = None,
    ) -> ChatMessageRow:
        """어시스턴트 메시지를 저장한다."""
        now = datetime.now(timezone.utc).isoformat()
        snapshot_json: str | None = None
        if prompt_snapshot:
            snapshot_json = json.dumps({
                "total_tokens": prompt_snapshot.total_tokens,
                "history_count": prompt_snapshot.history_count,
                "truncated_count": prompt_snapshot.truncated_count,
                "budget_tokens": prompt_snapshot.budget_tokens,
                "block_kinds": [b.kind for b in prompt_snapshot.blocks],
                "usage": usage,
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
            last_usage: dict | None = None

            async for chunk in adapter.stream_chat(profile_data, request, api_key):
                full_text += chunk.delta
                on_chunk(chunk.delta)
                if chunk.usage:
                    last_usage = chunk.usage
                if chunk.finish_reason:
                    break

            # 어시스턴트 메시지 저장
            self.save_assistant_message(session_id, full_text, assembled, last_usage)

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
    #   Service 계층에 threading 로직이 있으면 UI/Service 분리 원칙 위반.
    #   start_stream()은 async def이므로 UI에서 AsyncSignalBridge를 통해 호출한다.
    # 삭제 버전: v0.1.0b0 정합성 감사 Remediation

