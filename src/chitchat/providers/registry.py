# src/chitchat/providers/registry.py
# [v0.1.0b0] Provider 레지스트리
#
# provider_kind → adapter 인스턴스 매핑을 관리한다.
# 새 Provider 추가 시 이 레지스트리에 등록하면 Service/UI는 수정 불필요.

from __future__ import annotations

import logging

from chitchat.domain.provider_contracts import ProviderKind
from chitchat.providers.gemini_provider import GeminiProvider
from chitchat.providers.lmstudio_provider import LMStudioProvider
from chitchat.providers.openrouter_provider import OpenRouterProvider

logger = logging.getLogger(__name__)

# Provider adapter 타입을 Union으로 정의
ProviderAdapter = GeminiProvider | OpenRouterProvider | LMStudioProvider


class ProviderRegistry:
    """Provider adapter 레지스트리.

    provider_kind 문자열로 적절한 adapter 인스턴스를 반환한다.
    앱 시작 시 한 번 생성되고, Service 계층에서 참조한다.
    """

    def __init__(self) -> None:
        # 각 Provider adapter를 싱글턴으로 생성한다
        self._adapters: dict[ProviderKind, ProviderAdapter] = {
            "gemini": GeminiProvider(),
            "openrouter": OpenRouterProvider(),
            "lm_studio": LMStudioProvider(),
        }
        logger.info(
            "ProviderRegistry 초기화 완료: %s",
            list(self._adapters.keys()),
        )

    def get(self, provider_kind: ProviderKind) -> ProviderAdapter:
        """provider_kind에 해당하는 adapter를 반환한다.

        Args:
            provider_kind: Provider 종류 ("gemini", "openrouter", "lm_studio").

        Returns:
            해당 Provider adapter 인스턴스.

        Raises:
            KeyError: 등록되지 않은 provider_kind일 때.
        """
        adapter = self._adapters.get(provider_kind)
        if adapter is None:
            raise KeyError(f"등록되지 않은 Provider: {provider_kind!r}")
        return adapter

    @property
    def available_kinds(self) -> list[ProviderKind]:
        """등록된 모든 provider_kind를 반환한다."""
        return list(self._adapters.keys())
