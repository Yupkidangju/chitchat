# tests/test_provider_capability_mapper.py
# [v0.1.0b0] Provider별 capability 매핑 테스트
#
# Gemini, OpenRouter, LM Studio의 raw 샘플 데이터를
# ModelCapability로 정규화한 결과를 검증한다.
# spec.md §10.1~§10.3, §14 실데이터 샘플 기반.

from __future__ import annotations

from chitchat.providers.capability_mapper import (
    map_gemini_model,
    map_lmstudio_model,
    map_model_capability,
    map_openrouter_model,
)


class TestGeminiMapper:
    """Gemini raw → ModelCapability 변환 검증. spec.md §10.1, §14.1."""

    def test_gemini_flash_sample(self) -> None:
        """spec.md §14.1 Gemini Flash 샘플 데이터 매핑."""
        raw = {
            "name": "models/gemini-2.5-flash-preview-05-20",
            "display_name": "Gemini 2.5 Flash Preview 05-20",
            "description": "A fast model",
            "input_token_limit": 1048576,
            "output_token_limit": 65536,
            "supported_generation_methods": ["generateContent", "countTokens"],
        }
        cap = map_gemini_model(raw)

        assert cap.provider_kind == "gemini"
        assert cap.model_id == "gemini-2.5-flash-preview-05-20"
        assert cap.display_name == "Gemini 2.5 Flash Preview 05-20"
        assert cap.context_window_tokens == 1048576
        assert cap.max_output_tokens == 65536
        assert cap.supports_streaming is True
        assert cap.supports_system_prompt is True
        assert cap.supports_json_mode is True
        # Gemini는 모든 8종 파라미터를 지원한다
        assert "temperature" in cap.supported_parameters
        assert "top_k" in cap.supported_parameters
        assert "seed" in cap.supported_parameters
        assert len(cap.supported_parameters) == 8

    def test_gemini_model_id_prefix_stripped(self) -> None:
        """models/ 접두사가 제거되는지 확인한다."""
        raw = {
            "name": "models/gemini-pro",
            "supported_generation_methods": ["generateContent"],
        }
        cap = map_gemini_model(raw)
        assert cap.model_id == "gemini-pro"

    def test_gemini_no_generate_content(self) -> None:
        """generateContent 미지원 모델의 json_mode가 False인지 확인한다."""
        raw = {
            "name": "models/embedding-model",
            "supported_generation_methods": ["embedContent"],
        }
        cap = map_gemini_model(raw)
        assert cap.supports_json_mode is False


class TestOpenRouterMapper:
    """OpenRouter raw → ModelCapability 변환 검증. spec.md §10.2, §14.2."""

    def test_openrouter_claude_sample(self) -> None:
        """spec.md §14.2 OpenRouter 샘플 데이터 매핑."""
        raw = {
            "id": "anthropic/claude-sonnet-4",
            "name": "Anthropic: Claude Sonnet 4",
            "context_length": 200000,
            "top_provider": {
                "max_completion_tokens": 16000,
            },
            "supported_parameters": [
                "temperature", "top_p", "top_k", "max_tokens",
                "presence_penalty", "frequency_penalty", "stop",
            ],
        }
        cap = map_openrouter_model(raw)

        assert cap.provider_kind == "openrouter"
        assert cap.model_id == "anthropic/claude-sonnet-4"
        assert cap.display_name == "Anthropic: Claude Sonnet 4"
        assert cap.context_window_tokens == 200000
        assert cap.max_output_tokens == 16000
        assert "temperature" in cap.supported_parameters
        assert "top_k" in cap.supported_parameters
        # max_tokens → max_output_tokens로 매핑
        assert "max_output_tokens" in cap.supported_parameters
        assert "seed" not in cap.supported_parameters

    def test_openrouter_no_top_provider(self) -> None:
        """top_provider가 없을 때 max_output_tokens가 None인지 확인한다."""
        raw = {
            "id": "test/model",
            "name": "Test Model",
            "context_length": 4096,
            "supported_parameters": ["temperature"],
        }
        cap = map_openrouter_model(raw)
        assert cap.max_output_tokens is None

    def test_openrouter_empty_supported_parameters(self) -> None:
        """supported_parameters가 빈 배열일 때 빈 집합이 되는지 확인한다."""
        raw = {
            "id": "test/model",
            "name": "Test",
            "supported_parameters": [],
        }
        cap = map_openrouter_model(raw)
        assert cap.supported_parameters == set()


class TestLMStudioMapper:
    """LM Studio raw → ModelCapability 변환 검증. spec.md §10.3, §14.3."""

    def test_lmstudio_sample(self) -> None:
        """spec.md §14.3 LM Studio 샘플 데이터 매핑."""
        raw = {
            "id": "llama-3.1-8b-instruct",
            "object": "model",
            "owned_by": "lmstudio-community",
        }
        cap = map_lmstudio_model(raw)

        assert cap.provider_kind == "lm_studio"
        assert cap.model_id == "llama-3.1-8b-instruct"
        assert cap.display_name == "llama-3.1-8b-instruct"
        # LM Studio는 token limit을 제공하지 않음 → None
        assert cap.context_window_tokens is None
        assert cap.max_output_tokens is None
        assert cap.supports_streaming is True
        assert cap.supports_json_mode is False
        # LM Studio 기본 6종 파라미터
        assert "temperature" in cap.supported_parameters
        assert "top_p" in cap.supported_parameters
        assert "max_output_tokens" in cap.supported_parameters
        # top_k, seed는 LM Studio에서 미지원
        assert "top_k" not in cap.supported_parameters
        assert "seed" not in cap.supported_parameters


class TestUnifiedMapper:
    """통합 매퍼 함수 검증."""

    def test_dispatch_gemini(self) -> None:
        """gemini provider_kind로 올바른 매퍼가 호출되는지 확인한다."""
        cap = map_model_capability("gemini", {
            "name": "models/test",
            "supported_generation_methods": ["generateContent"],
        })
        assert cap.provider_kind == "gemini"

    def test_dispatch_openrouter(self) -> None:
        """openrouter provider_kind 디스패치 확인."""
        cap = map_model_capability("openrouter", {
            "id": "test/model",
            "supported_parameters": [],
        })
        assert cap.provider_kind == "openrouter"

    def test_dispatch_lm_studio(self) -> None:
        """lm_studio provider_kind 디스패치 확인."""
        cap = map_model_capability("lm_studio", {"id": "test"})
        assert cap.provider_kind == "lm_studio"
