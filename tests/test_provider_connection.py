# tests/test_provider_connection.py
# [v0.1.0b0] Provider 연결 테스트 (mock 기반)
#
# 실제 API를 호출하지 않고, mock으로 validate_connection의 동작을 검증한다.
# 성공/실패 양쪽 시나리오를 테스트한다.

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from chitchat.domain.provider_contracts import ProviderProfileData
from chitchat.providers.gemini_provider import GeminiProvider
from chitchat.providers.lmstudio_provider import LMStudioProvider
from chitchat.providers.openrouter_provider import OpenRouterProvider


@pytest.fixture
def gemini_profile() -> ProviderProfileData:
    """테스트용 Gemini 프로필."""
    return ProviderProfileData(
        id="prov_gemini_test",
        name="Test Gemini",
        provider_kind="gemini",
        secret_ref="chitchat:prov_gemini_test",
    )


@pytest.fixture
def openrouter_profile() -> ProviderProfileData:
    """테스트용 OpenRouter 프로필."""
    return ProviderProfileData(
        id="prov_or_test",
        name="Test OpenRouter",
        provider_kind="openrouter",
        secret_ref="chitchat:prov_or_test",
    )


@pytest.fixture
def lmstudio_profile() -> ProviderProfileData:
    """테스트용 LM Studio 프로필."""
    return ProviderProfileData(
        id="prov_lm_test",
        name="Test LM Studio",
        provider_kind="lm_studio",
        base_url="http://localhost:1234/v1",
    )


class TestGeminiConnection:
    """Gemini 연결 테스트."""

    @pytest.mark.asyncio
    async def test_no_api_key_returns_failure(
        self,
        gemini_profile: ProviderProfileData,
    ) -> None:
        """API Key 없이 연결 시 실패를 반환한다."""
        provider = GeminiProvider()
        health = await provider.validate_connection(gemini_profile, api_key=None)
        assert health.ok is False
        assert "API Key" in health.message

    @pytest.mark.asyncio
    async def test_success_with_mock_client(
        self,
        gemini_profile: ProviderProfileData,
    ) -> None:
        """mock 클라이언트로 연결 성공 시나리오."""
        provider = GeminiProvider()
        mock_client = MagicMock()
        mock_client.models.list.return_value = [MagicMock(), MagicMock()]

        with patch.object(provider, "_create_client", return_value=mock_client):
            health = await provider.validate_connection(gemini_profile, api_key="fake-key")

        assert health.ok is True
        assert "2개 모델" in health.message
        assert health.latency_ms is not None

    @pytest.mark.asyncio
    async def test_failure_with_exception(
        self,
        gemini_profile: ProviderProfileData,
    ) -> None:
        """연결 실패 시 ok=False를 반환한다."""
        provider = GeminiProvider()
        mock_client = MagicMock()
        mock_client.models.list.side_effect = Exception("Network error")

        with patch.object(provider, "_create_client", return_value=mock_client):
            health = await provider.validate_connection(gemini_profile, api_key="fake-key")

        assert health.ok is False
        assert "Network error" in health.message


class TestOpenRouterConnection:
    """OpenRouter 연결 테스트."""

    @pytest.mark.asyncio
    async def test_no_api_key_returns_failure(
        self,
        openrouter_profile: ProviderProfileData,
    ) -> None:
        """API Key 없이 연결 시 실패를 반환한다."""
        provider = OpenRouterProvider()
        health = await provider.validate_connection(openrouter_profile, api_key=None)
        assert health.ok is False
        assert "API Key" in health.message


class TestLMStudioConnection:
    """LM Studio 연결 테스트."""

    @pytest.mark.asyncio
    async def test_no_api_key_still_works(
        self,
        lmstudio_profile: ProviderProfileData,
    ) -> None:
        """LM Studio는 API Key 없이도 연결을 시도한다 (서버 미실행 시 실패)."""
        provider = LMStudioProvider()
        health = await provider.validate_connection(lmstudio_profile, api_key=None)
        # 로컬 서버가 실행 중이 아니므로 실패한다
        assert health.ok is False
        assert health.provider_kind == "lm_studio"
