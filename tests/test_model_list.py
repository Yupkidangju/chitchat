# tests/test_model_list.py
# [v0.1.0b0] Provider 모델 목록 조회 테스트 (mock 기반)
#
# 각 Provider의 list_models가 올바른 ModelCapability 리스트를 반환하는지 검증한다.

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from chitchat.domain.provider_contracts import ProviderProfileData
from chitchat.providers.gemini_provider import GeminiProvider


@pytest.fixture
def gemini_profile() -> ProviderProfileData:
    return ProviderProfileData(
        id="prov_gemini_test",
        name="Test Gemini",
        provider_kind="gemini",
    )


@pytest.fixture
def lmstudio_profile() -> ProviderProfileData:
    return ProviderProfileData(
        id="prov_lm_test",
        name="Test LM Studio",
        provider_kind="lm_studio",
        base_url="http://localhost:1234/v1",
    )


class TestGeminiListModels:
    """Gemini list_models mock 테스트."""

    @pytest.mark.asyncio
    async def test_returns_model_capabilities(
        self,
        gemini_profile: ProviderProfileData,
    ) -> None:
        """mock 클라이언트에서 generateContent 모델만 반환하는지 확인한다."""
        provider = GeminiProvider()

        # generateContent를 지원하는 모델과 지원하지 않는 모델
        mock_model_gen = MagicMock()
        mock_model_gen.name = "models/gemini-2.5-flash"
        mock_model_gen.display_name = "Gemini 2.5 Flash"
        mock_model_gen.description = "Fast model"
        mock_model_gen.input_token_limit = 1048576
        mock_model_gen.output_token_limit = 65536
        mock_model_gen.supported_generation_methods = ["generateContent", "countTokens"]

        mock_model_embed = MagicMock()
        mock_model_embed.name = "models/text-embedding-004"
        mock_model_embed.display_name = "Text Embedding"
        mock_model_embed.description = "Embedding model"
        mock_model_embed.input_token_limit = 2048
        mock_model_embed.output_token_limit = None
        mock_model_embed.supported_generation_methods = ["embedContent"]

        mock_client = MagicMock()
        mock_client.models.list.return_value = [mock_model_gen, mock_model_embed]

        with patch.object(provider, "_create_client", return_value=mock_client):
            caps = await provider.list_models(gemini_profile, api_key="fake-key")

        # generateContent만 포함
        assert len(caps) == 1
        assert caps[0].model_id == "gemini-2.5-flash"
        assert caps[0].context_window_tokens == 1048576
        assert caps[0].max_output_tokens == 65536
        assert "temperature" in caps[0].supported_parameters

    @pytest.mark.asyncio
    async def test_no_api_key_raises(
        self,
        gemini_profile: ProviderProfileData,
    ) -> None:
        """API Key 없이 호출하면 ProviderConnectionError가 발생한다."""
        from chitchat.providers.base import ProviderConnectionError

        provider = GeminiProvider()
        with pytest.raises(ProviderConnectionError):
            await provider.list_models(gemini_profile, api_key=None)


class TestLMStudioListModels:
    """LM Studio list_models mock 테스트."""

    @pytest.mark.asyncio
    async def test_lmstudio_token_limits_are_none(
        self,
        lmstudio_profile: ProviderProfileData,
    ) -> None:
        """LM Studio 모델의 token limit이 None인지 확인한다.

        Service 계층에서 기본값 8192/2048을 적용해야 한다.
        capability_mapper를 직접 테스트하여 httpx mock 복잡성을 회피한다.
        """
        from chitchat.providers.capability_mapper import map_lmstudio_model

        raw_models = [
            {"id": "llama-3.1-8b-instruct", "object": "model"},
            {"id": "gemma-2-9b", "object": "model"},
        ]
        caps = [map_lmstudio_model(m) for m in raw_models]

        assert len(caps) == 2
        assert caps[0].model_id == "llama-3.1-8b-instruct"
        assert caps[0].context_window_tokens is None
        assert caps[0].max_output_tokens is None
        assert caps[1].model_id == "gemma-2-9b"


async def _async_return(value):  # type: ignore[no-untyped-def]
    """async context manager mock 유틸리티."""
    return value
