# src/chitchat/services/vibe_fill_service.py
# [v1.0.0] Vibe Fill 서비스 — 바이브 텍스트를 구조화된 AI Persona로 변환
#
# Provider의 LLM을 호출하여 14개 필드를 JSON으로 생성한 뒤,
# 도메인 로직(vibe_fill.py)으로 파싱하여 결과를 반환한다.
# [v0.3.0] UserPreferences의 vibe_output_language 설정에 따라 출력 언어를 동적 적용한다.
# UI 계층은 이 서비스를 통해 Vibe Fill 기능을 사용한다.

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any, cast

from chitchat.config.user_preferences import UserPreferences
from chitchat.db.repositories import RepositoryRegistry
from chitchat.domain.provider_contracts import (
    ChatCompletionMessage,
    ChatCompletionRequest,
    ModelGenerationSettings,
    ProviderKind,
    ProviderProfileData,
)
from chitchat.domain.vibe_fill import (
    WORLD_CATEGORY_MAP,
    LoreFillResult,
    VibeFillResult,
    WorldFillResult,
    build_lore_prompt,
    build_vibe_prompt,
    build_world_prompt,
    get_chunks_for_categories,
    get_lore_system_prompt,
    get_vibe_system_prompt,
    get_world_system_prompt,
    parse_lore_response,
    parse_vibe_response,
    parse_world_response,
)
from chitchat.providers.registry import ProviderRegistry
from chitchat.secrets.key_store import KeyStore

logger = logging.getLogger(__name__)


class VibeFillService:
    """바이브 텍스트를 구조화된 AI Persona 필드로 변환하는 서비스.

    Provider의 LLM을 호출하여 14개 필드를 JSON으로 생성한 뒤,
    VibeFillResult로 변환하여 반환한다.

    사용 흐름:
    1. UI에서 바이브 텍스트 + Provider/Model 선택
    2. generate_persona() 호출
    3. LLM 스트리밍 응답 수집
    4. JSON 파싱 → VibeFillResult 반환
    """

    def __init__(
        self,
        repos: RepositoryRegistry,
        providers: ProviderRegistry,
        key_store: KeyStore,
    ) -> None:
        self._repos = repos
        self._providers = providers
        self._key_store = key_store

    async def generate_persona(
        self,
        vibe_text: str,
        provider_profile_id: str,
        model_id: str,
    ) -> VibeFillResult:
        """바이브 텍스트에서 AI Persona 14개 필드를 생성한다.

        Provider의 LLM을 호출하여 스트리밍 응답을 수집한 뒤,
        JSON으로 파싱하여 VibeFillResult를 반환한다.

        Args:
            vibe_text: 사용자가 입력한 캐릭터 바이브 텍스트.
            provider_profile_id: 사용할 Provider 프로필 ID.
            model_id: 사용할 모델 ID.

        Returns:
            VibeFillResult — success=True이면 fields에 14개 필드가 채워짐.
        """
        # Provider 프로필 로드
        prov = self._repos.providers.get_by_id(provider_profile_id)
        if not prov:
            return VibeFillResult(
                success=False,
                error=f"Provider를 찾을 수 없습니다: {provider_profile_id}",
            )

        # API Key 로드 — KeyStore는 (provider_profile_id, provider_kind)를 받는다
        api_key: str | None = None
        if prov.secret_ref:
            api_key = self._key_store.get_key(provider_profile_id, prov.provider_kind)
            if not api_key:
                return VibeFillResult(
                    success=False,
                    error="API Key가 설정되지 않았습니다.",
                )

        # [v0.3.0] 사용자 설정의 vibe_output_language로 출력 언어 적용
        output_lang = UserPreferences.instance().vibe_output_language

        # 메시지 조립
        messages = [
            ChatCompletionMessage(role="system", content=get_vibe_system_prompt(output_lang)),
            ChatCompletionMessage(role="user", content=build_vibe_prompt(vibe_text)),
        ]

        # 생성 설정: 낮은 temperature로 안정적인 JSON 생성
        settings = ModelGenerationSettings(
            temperature=0.7,
            max_output_tokens=2048,
        )

        request = ChatCompletionRequest(
            provider_profile_id=provider_profile_id,
            model_id=model_id,
            settings=settings,
            messages=messages,
            stream=True,
        )

        # Provider adapter로 스트리밍 호출 → 전체 응답 수집
        # DB의 provider_kind는 str이지만, 레지스트리는 Literal 타입을 요구
        kind = cast(ProviderKind, prov.provider_kind)
        try:
            adapter = self._providers.get(kind)
            profile_data = ProviderProfileData(
                id=prov.id,
                name=prov.name,
                provider_kind=kind,
                base_url=prov.base_url,
                secret_ref=prov.secret_ref,
                enabled=bool(prov.enabled),
                timeout_seconds=prov.timeout_seconds,
            )

            full_text = ""
            async for chunk in adapter.stream_chat(profile_data, request, api_key):
                full_text += chunk.delta

            logger.info(
                "Vibe Fill LLM 응답 수신 완료: %d 글자, provider=%s, model=%s",
                len(full_text), prov.provider_kind, model_id,
            )

        except Exception as e:
            logger.exception("Vibe Fill LLM 호출 실패")
            return VibeFillResult(
                success=False,
                error=f"LLM 호출 실패: {e}",
            )

        # JSON 파싱
        return parse_vibe_response(full_text)

    # ============================================================
    # Phase 2: Lorebook Vibe Fill
    # ============================================================

    def _build_persona_sheet(self, persona_ids: list[str]) -> str | None:
        """AI Persona ID 목록에서 캐릭터 시트 텍스트를 조립한다.

        Phase 1의 14개 필드를 구조화된 캐릭터 시트로 변환한다.
        persona_ids가 비어 있으면 None을 반환한다.

        Args:
            persona_ids: AI Persona ID 목록.

        Returns:
            캐릭터 시트 텍스트 또는 None.
        """
        if not persona_ids:
            return None

        sheets: list[str] = []
        for pid in persona_ids:
            ai = self._repos.ai_personas.get_by_id(pid)
            if not ai or not ai.enabled:
                continue
            lines = [f"[캐릭터: {ai.name}]"]
            basic_parts: list[str] = []
            if getattr(ai, "age", ""):
                basic_parts.append(f"나이: {ai.age}")
            if getattr(ai, "gender", ""):
                basic_parts.append(f"성별: {ai.gender}")
            basic_parts.append(f"역할: {ai.role_name}")
            lines.append(" / ".join(basic_parts))
            _ext = [
                ("외모", getattr(ai, "appearance", "")),
                ("성격", ai.personality),
                ("말투", ai.speaking_style),
                ("배경", getattr(ai, "backstory", "")),
                ("인간관계", getattr(ai, "relationships", "")),
                ("특기", getattr(ai, "skills", "")),
                ("취미", getattr(ai, "interests", "")),
                ("약점", getattr(ai, "weaknesses", "")),
                ("목표", ai.goals),
                ("제한", ai.restrictions),
            ]
            for label, value in _ext:
                if value:
                    lines.append(f"{label}: {value}")
            sheets.append("\n".join(lines))

        return "\n\n".join(sheets) if sheets else None

    async def generate_lore_entries(
        self,
        vibe_text: str,
        lorebook_id: str,
        provider_profile_id: str,
        model_id: str,
        persona_ids: list[str] | None = None,
    ) -> LoreFillResult:
        """바이브 텍스트에서 로어 엔트리를 복수 건 생성한다.

        1. persona_ids가 있으면 AI Persona 캐릭터 시트를 조립하여 컨텍스트로 주입
        2. 해당 lorebook의 기존 엔트리 제목/키워드를 주입하여 중복 방지
        3. LLM 호출 → JSON 배열 파싱
        4. LoreFillResult로 반환 (DB 저장은 UI에서 별도 수행)

        Args:
            vibe_text: 사용자가 입력한 로어 바이브 텍스트.
            lorebook_id: 대상 로어북 ID.
            provider_profile_id: 사용할 Provider 프로필 ID.
            model_id: 사용할 모델 ID.
            persona_ids: 컨텍스트로 주입할 AI Persona ID 목록 (선택).

        Returns:
            LoreFillResult — success=True이면 entries에 파싱된 엔트리 리스트.
        """
        # 캐릭터 시트 조립 (선택)
        persona_sheet = self._build_persona_sheet(persona_ids or [])

        # 기존 엔트리 목록 로드 (중복 방지)
        existing_rows = self._repos.lore_entries.get_by_lorebook(lorebook_id)
        existing_entries: list[tuple[str, list[str]]] = []
        for row in existing_rows:
            keys = json.loads(row.activation_keys_json)
            existing_entries.append((row.title, keys))

        # 사용자 메시지 조립
        user_msg = build_lore_prompt(vibe_text, persona_sheet, existing_entries or None)

        # Provider 프로필 로드
        prov = self._repos.providers.get_by_id(provider_profile_id)
        if not prov:
            return LoreFillResult(
                success=False,
                error=f"Provider를 찾을 수 없습니다: {provider_profile_id}",
            )

        # API Key 로드
        api_key: str | None = None
        if prov.secret_ref:
            api_key = self._key_store.get_key(provider_profile_id, prov.provider_kind)
            if not api_key:
                return LoreFillResult(
                    success=False,
                    error="API Key가 설정되지 않았습니다.",
                )

        # [v0.3.0] 사용자 설정의 vibe_output_language로 출력 언어 적용
        output_lang = UserPreferences.instance().vibe_output_language

        # 메시지 조립
        messages = [
            ChatCompletionMessage(role="system", content=get_lore_system_prompt(output_lang)),
            ChatCompletionMessage(role="user", content=user_msg),
        ]

        # 생성 설정: 로어 엔트리는 배열이므로 충분한 토큰 허용
        settings = ModelGenerationSettings(
            temperature=0.7,
            max_output_tokens=4096,
        )

        request = ChatCompletionRequest(
            provider_profile_id=provider_profile_id,
            model_id=model_id,
            settings=settings,
            messages=messages,
            stream=True,
        )

        # Provider adapter로 스트리밍 호출
        kind = cast(ProviderKind, prov.provider_kind)
        try:
            adapter = self._providers.get(kind)
            profile_data = ProviderProfileData(
                id=prov.id,
                name=prov.name,
                provider_kind=kind,
                base_url=prov.base_url,
                secret_ref=prov.secret_ref,
                enabled=bool(prov.enabled),
                timeout_seconds=prov.timeout_seconds,
            )

            full_text = ""
            async for chunk in adapter.stream_chat(profile_data, request, api_key):
                full_text += chunk.delta

            logger.info(
                "Lore Fill LLM 응답 수신 완료: %d 글자, provider=%s, model=%s",
                len(full_text), prov.provider_kind, model_id,
            )

        except Exception as e:
            logger.exception("Lore Fill LLM 호출 실패")
            return LoreFillResult(
                success=False,
                error=f"LLM 호출 실패: {e}",
            )

        # JSON 배열 파싱
        return parse_lore_response(full_text)

    # ============================================================
    # Phase 3: Worldbook Vibe Fill
    # ============================================================

    def _build_lore_summaries(self, lorebook_ids: list[str]) -> list[str]:
        """Lorebook 엔트리의 제목+키워드를 요약 문자열로 조립한다.

        세계관 프롬프트에서 로어북 참조용으로 사용된다.
        토큰 절약을 위해 제목과 키워드만 포함한다.

        Args:
            lorebook_ids: 참조할 Lorebook ID 목록.

        Returns:
            "제목 (키: 키워드1, 키워드2)" 형식의 요약 문자열 리스트.
        """
        summaries: list[str] = []
        for lb_id in lorebook_ids:
            rows = self._repos.lore_entries.get_by_lorebook(lb_id)
            for row in rows:
                keys = json.loads(row.activation_keys_json)
                key_str = ", ".join(keys)
                summaries.append(f"{row.title} (키: {key_str})")
        return summaries

    async def generate_world_entries(
        self,
        vibe_text: str,
        worldbook_id: str,
        provider_profile_id: str,
        model_id: str,
        category_keys: list[str],
        persona_ids: list[str] | None = None,
        lorebook_ids: list[str] | None = None,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> WorldFillResult:
        """카테고리를 청크로 나눠 여러 번 LLM 호출하여 세계관 엔트리를 생성한다.

        1. 선택된 카테고리를 WORLD_CATEGORY_CHUNKS 기준으로 분할
        2. 각 청크마다 LLM 호출 (이전 청크 제목을 연쇄 컨텍스트로 주입)
        3. 전체 결과를 병합하여 WorldFillResult로 반환
        4. progress_callback으로 UI에 진행률 실시간 전달

        Args:
            vibe_text: 사용자가 입력한 세계관 바이브 텍스트.
            worldbook_id: 대상 월드북 ID.
            provider_profile_id: 사용할 Provider 프로필 ID.
            model_id: 사용할 모델 ID.
            category_keys: 생성할 카테고리 키 목록.
            persona_ids: 컨텍스트로 주입할 AI Persona ID 목록 (선택).
            lorebook_ids: 컨텍스트로 주입할 Lorebook ID 목록 (선택).
            progress_callback: 진행률 콜백 (current_chunk, total_chunks, status_text).

        Returns:
            WorldFillResult — success=True이면 entries에 전체 파싱된 엔트리 리스트.
        """
        # 청크 분할
        chunks = get_chunks_for_categories(category_keys)
        if not chunks:
            return WorldFillResult(success=False, error="선택된 카테고리가 없습니다.")

        total_chunks = len(chunks)

        # 캐릭터 시트 조립 (선택)
        persona_sheet = self._build_persona_sheet(persona_ids or [])

        # 로어북 요약 조립 (선택)
        lore_summaries = self._build_lore_summaries(lorebook_ids or []) if lorebook_ids else None

        # Provider 프로필 로드
        prov = self._repos.providers.get_by_id(provider_profile_id)
        if not prov:
            return WorldFillResult(
                success=False,
                error=f"Provider를 찾을 수 없습니다: {provider_profile_id}",
            )

        # API Key 로드
        api_key: str | None = None
        if prov.secret_ref:
            api_key = self._key_store.get_key(provider_profile_id, prov.provider_kind)
            if not api_key:
                return WorldFillResult(
                    success=False,
                    error="API Key가 설정되지 않았습니다.",
                )

        # Provider adapter 준비
        kind = cast(ProviderKind, prov.provider_kind)
        adapter = self._providers.get(kind)
        profile_data = ProviderProfileData(
            id=prov.id,
            name=prov.name,
            provider_kind=kind,
            base_url=prov.base_url,
            secret_ref=prov.secret_ref,
            enabled=bool(prov.enabled),
            timeout_seconds=prov.timeout_seconds,
        )

        # 생성 설정
        settings = ModelGenerationSettings(
            temperature=0.7,
            max_output_tokens=4096,
        )

        # 연쇄 생성: 청크별 LLM 호출
        all_entries: list[dict[str, Any]] = []
        prev_titles: list[str] = []
        raw_responses: list[str] = []

        for chunk_idx, chunk_keys in enumerate(chunks):
            # 이번 청크의 카테고리 객체 목록
            cats = [WORLD_CATEGORY_MAP[k] for k in chunk_keys if k in WORLD_CATEGORY_MAP]
            if not cats:
                continue

            # 진행률 콜백
            cat_labels = ", ".join(c.label for c in cats)
            if progress_callback:
                progress_callback(
                    chunk_idx + 1, total_chunks,
                    f"{cat_labels} 생성 중...",
                )

            # 사용자 메시지 조립 (이전 청크 제목을 연쇄 컨텍스트로 포함)
            user_msg = build_world_prompt(
                vibe_text, cats, persona_sheet,
                lore_summaries, prev_titles or None,
            )

            # [v0.3.0] 사용자 설정의 vibe_output_language로 출력 언어 적용
            output_lang = UserPreferences.instance().vibe_output_language

            messages = [
                ChatCompletionMessage(role="system", content=get_world_system_prompt(output_lang)),
                ChatCompletionMessage(role="user", content=user_msg),
            ]

            request = ChatCompletionRequest(
                provider_profile_id=provider_profile_id,
                model_id=model_id,
                settings=settings,
                messages=messages,
                stream=True,
            )

            # LLM 스트리밍 호출
            try:
                full_text = ""
                async for chunk in adapter.stream_chat(profile_data, request, api_key):
                    full_text += chunk.delta

                logger.info(
                    "World Fill 청크 %d/%d 완료: %d 글자, 카테고리=%s",
                    chunk_idx + 1, total_chunks, len(full_text), cat_labels,
                )
                raw_responses.append(full_text)

            except Exception as e:
                logger.exception("World Fill 청크 %d LLM 호출 실패", chunk_idx + 1)
                # 부분 실패 — 이전 청크 결과는 유지하고 에러 기록
                if all_entries:
                    return WorldFillResult(
                        success=True,
                        entries=all_entries,
                        error=f"청크 {chunk_idx + 1}/{total_chunks} 실패: {e} (이전 {len(all_entries)}개는 유지)",
                        raw_response="\n---\n".join(raw_responses),
                    )
                return WorldFillResult(
                    success=False,
                    error=f"LLM 호출 실패 (청크 {chunk_idx + 1}): {e}",
                )

            # 청크 결과 파싱
            chunk_result = parse_world_response(full_text)
            if chunk_result.success:
                all_entries.extend(chunk_result.entries)
                # 연쇄 컨텍스트: 이번 청크 제목을 다음 청크에 전달
                prev_titles.extend(e["title"] for e in chunk_result.entries)
            else:
                logger.warning(
                    "World Fill 청크 %d 파싱 실패: %s", chunk_idx + 1, chunk_result.error,
                )

        if not all_entries:
            return WorldFillResult(
                success=False,
                error="모든 청크에서 유효한 엔트리를 생성하지 못했습니다.",
                raw_response="\n---\n".join(raw_responses),
            )

        # 진행률 완료 콜백
        if progress_callback:
            progress_callback(total_chunks, total_chunks, "완료!")

        return WorldFillResult(
            success=True,
            entries=all_entries,
            raw_response="\n---\n".join(raw_responses),
        )
