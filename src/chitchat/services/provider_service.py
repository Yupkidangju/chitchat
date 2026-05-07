# src/chitchat/services/provider_service.py
# [v1.0.0] Provider 유스케이스 서비스
#
# Provider CRUD, 연결 테스트, 모델 목록 패치, model_cache 갱신을 오케스트레이션한다.
# UI/ViewModel은 이 서비스만 호출하고, 직접 adapter나 repository를 사용하지 않는다.

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from chitchat.db.models import ModelCacheRow, ProviderProfileRow
from chitchat.db.repositories import RepositoryRegistry
from chitchat.domain.ids import new_id
from chitchat.domain.provider_contracts import (
    ModelCapability,
    ProviderHealth,
    ProviderKind,
    ProviderProfileData,
)
from chitchat.providers.registry import ProviderRegistry
from chitchat.secrets.key_store import KeyStore

logger = logging.getLogger(__name__)

# LM Studio 기본 토큰 한도 (spec.md §10.3)
_LMSTUDIO_DEFAULT_CONTEXT = 8192
_LMSTUDIO_DEFAULT_OUTPUT = 2048


class ProviderService:
    """Provider 관련 유스케이스를 처리하는 서비스.

    CRUD, 연결 테스트, 모델 패치, 캐시 갱신을 오케스트레이션한다.
    """

    def __init__(
        self,
        repos: RepositoryRegistry,
        provider_registry: ProviderRegistry,
        key_store: KeyStore,
    ) -> None:
        self._repos = repos
        self._providers = provider_registry
        self._key_store = key_store

    # --- CRUD ---

    def get_all_providers(self) -> list[ProviderProfileRow]:
        """모든 Provider 프로필을 반환한다."""
        return self._repos.providers.get_all()

    def get_provider(self, id_: str) -> ProviderProfileRow | None:
        """ID로 Provider 프로필을 조회한다."""
        return self._repos.providers.get_by_id(id_)

    def save_provider(
        self,
        name: str,
        provider_kind: ProviderKind,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: int = 60,
        existing_id: str | None = None,
    ) -> ProviderProfileRow:
        """Provider 프로필을 저장하고, API Key가 있으면 keyring에 저장한다.

        기존 ID가 주어지면 업데이트, 없으면 새로 생성한다.

        Args:
            name: Provider 이름.
            provider_kind: Provider 종류.
            api_key: API Key (Gemini/OpenRouter). None이면 keyring 저장 생략.
            base_url: 커스텀 base URL (OpenRouter/LM Studio).
            timeout_seconds: 타임아웃 (초).
            existing_id: 기존 Provider ID (업데이트 시).

        Returns:
            저장된 ProviderProfileRow.
        """
        profile_id = existing_id or new_id("prov_")

        # API Key를 keyring에 저장
        secret_ref: str | None = None
        if api_key and provider_kind != "lm_studio":
            secret_ref = self._key_store.set_key(profile_id, provider_kind, api_key)
            logger.info("API Key 저장 완료: %s", profile_id)
        elif existing_id:
            # 업데이트 시 기존 secret_ref 유지
            existing = self._repos.providers.get_by_id(existing_id)
            if existing:
                secret_ref = existing.secret_ref

        row = ProviderProfileRow(
            id=profile_id,
            name=name,
            provider_kind=provider_kind,
            base_url=base_url,
            secret_ref=secret_ref,
            enabled=1,
            timeout_seconds=timeout_seconds,
        )

        saved = self._repos.providers.upsert(row)
        logger.info("Provider 저장 완료: %s (%s)", saved.name, saved.provider_kind)
        return saved

    def delete_provider(self, id_: str) -> bool:
        """[v1.0.0] Provider를 삭제하고, keyring에서 API Key도 삭제한다.

        ModelProfile이 이 Provider를 참조 중이면 삭제를 차단한다.
        """
        provider = self._repos.providers.get_by_id(id_)
        if not provider:
            return False

        # [v1.0.0] ModelProfile 참조 검사
        model_profiles = self._repos.model_profiles.get_all()
        refs = [mp.name for mp in model_profiles if mp.provider_profile_id == id_]
        if refs:
            msg = f"Provider가 {len(refs)}개 모델 프로필에서 사용 중: {', '.join(refs[:3])}"
            raise ValueError(msg)

        # keyring에서 API Key 삭제
        if provider.secret_ref and provider.provider_kind != "lm_studio":
            try:
                self._key_store.delete_key(id_, provider.provider_kind)
            except Exception as e:
                logger.warning("API Key 삭제 실패 (계속 진행): %s", e)

        # 모델 캐시 삭제
        self._repos.model_cache.delete_by_provider(id_)

        # Provider 삭제
        return self._repos.providers.delete_by_id(id_)

    # --- 연결 테스트 ---

    async def test_connection(self, id_: str) -> ProviderHealth:
        """Provider 연결을 테스트한다.

        keyring에서 API Key를 가져와 adapter의 validate_connection을 호출한다.
        """
        provider = self._repos.providers.get_by_id(id_)
        if not provider:
            return ProviderHealth(
                ok=False,
                provider_kind="gemini",  # 기본값
                checked_at_iso=datetime.now(timezone.utc).isoformat(),
                message=f"Provider를 찾을 수 없습니다: {id_}",
            )

        # API Key 조회
        api_key: str | None = None
        if provider.provider_kind != "lm_studio" and provider.secret_ref:
            api_key = self._key_store.get_key(id_, provider.provider_kind)

        profile = _row_to_profile_data(provider)
        adapter = self._providers.get(provider.provider_kind)  # type: ignore[arg-type]
        return await adapter.validate_connection(profile, api_key)

    # --- 모델 패치 ---

    async def fetch_models(self, id_: str) -> list[ModelCapability]:
        """Provider의 모델 목록을 패치하고 캐시에 저장한다.

        기존 캐시를 삭제하고 새로 가져온 모델 목록으로 교체한다.
        LM Studio 모델은 token limit이 None이면 기본값을 적용한다.

        Args:
            id_: Provider 프로필 ID.

        Returns:
            정규화된 ModelCapability 리스트.
        """
        provider = self._repos.providers.get_by_id(id_)
        if not provider:
            raise ValueError(f"Provider를 찾을 수 없습니다: {id_}")

        # API Key 조회
        api_key: str | None = None
        if provider.provider_kind != "lm_studio" and provider.secret_ref:
            api_key = self._key_store.get_key(id_, provider.provider_kind)

        profile = _row_to_profile_data(provider)
        adapter = self._providers.get(provider.provider_kind)  # type: ignore[arg-type]

        # 모델 목록 패치
        capabilities = await adapter.list_models(profile, api_key)

        # LM Studio 기본값 적용 (spec.md §10.3)
        if provider.provider_kind == "lm_studio":
            for cap in capabilities:
                if cap.context_window_tokens is None:
                    cap.context_window_tokens = _LMSTUDIO_DEFAULT_CONTEXT
                if cap.max_output_tokens is None:
                    cap.max_output_tokens = _LMSTUDIO_DEFAULT_OUTPUT

        # 기존 캐시 삭제 후 새 데이터 저장
        self._repos.model_cache.delete_by_provider(id_)

        now = datetime.now(timezone.utc).isoformat()
        for cap in capabilities:
            cache_row = ModelCacheRow(
                id=new_id("mc_"),
                provider_profile_id=id_,
                model_id=cap.model_id,
                display_name=cap.display_name,
                context_window_tokens=cap.context_window_tokens,
                max_output_tokens=cap.max_output_tokens,
                supported_parameters_json=json.dumps(sorted(cap.supported_parameters)),
                supports_streaming=int(cap.supports_streaming),
                supports_system_prompt=int(cap.supports_system_prompt),
                supports_json_mode=int(cap.supports_json_mode),
                raw_json=json.dumps(cap.raw, default=str),
                fetched_at=now,
            )
            self._repos.model_cache.upsert(cache_row)

        logger.info(
            "모델 캐시 갱신 완료: %s (%s), %d개 모델",
            provider.name, provider.provider_kind, len(capabilities),
        )
        return capabilities

    def get_cached_models(self, provider_id: str) -> list[ModelCacheRow]:
        """캐시된 모델 목록을 반환한다."""
        return self._repos.model_cache.get_by_provider(provider_id)


def _row_to_profile_data(row: ProviderProfileRow) -> ProviderProfileData:
    """ORM Row를 Pydantic 도메인 모델로 변환한다."""
    return ProviderProfileData(
        id=row.id,
        name=row.name,
        provider_kind=row.provider_kind,  # type: ignore[arg-type]
        base_url=row.base_url,
        secret_ref=row.secret_ref,
        enabled=bool(row.enabled),
        timeout_seconds=row.timeout_seconds,
    )
