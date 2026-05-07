# src/chitchat/providers/gemini_provider.py
# [v1.0.0] Gemini Provider adapter
#
# google-genai SDK를 사용하여 Gemini API에 접근한다.
# spec.md §10.1: input_token_limit → context_window_tokens, output_token_limit → max_output_tokens
# ChatProvider Protocol의 4개 메서드를 구현한다.

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

from google import genai
from google.genai import types as genai_types

from chitchat.domain.provider_contracts import (
    ChatCompletionRequest,
    ChatStreamChunk,
    ModelCapability,
    ProviderHealth,
    ProviderKind,
    ProviderProfileData,
)
from chitchat.providers.base import (
    ProviderApiError,
    ProviderConnectionError,
    ProviderStreamError,
)
from chitchat.providers.capability_mapper import map_gemini_model

logger = logging.getLogger(__name__)


class GeminiProvider:
    """Google Gemini Provider adapter.

    google-genai SDK를 사용하여 Gemini API와 통신한다.
    api_key는 KeyStore에서 런타임에 주입된다.
    """

    provider_kind: ProviderKind = "gemini"

    def _create_client(self, api_key: str) -> genai.Client:
        """API Key로 google-genai 클라이언트를 생성한다."""
        return genai.Client(api_key=api_key)

    async def validate_connection(
        self,
        profile: ProviderProfileData,
        api_key: str | None = None,
    ) -> ProviderHealth:
        """Gemini API 연결 상태를 확인한다.

        models.list()를 호출하여 연결을 검증한다.
        """
        checked_at = datetime.now(timezone.utc).isoformat()
        if not api_key:
            return ProviderHealth(
                ok=False,
                provider_kind="gemini",
                checked_at_iso=checked_at,
                message="API Key가 제공되지 않았습니다.",
            )

        start = time.monotonic()
        try:
            client = self._create_client(api_key)
            # 모델 목록을 1개만 가져와서 연결을 확인한다
            models = list(client.models.list())
            latency = int((time.monotonic() - start) * 1000)
            return ProviderHealth(
                ok=True,
                provider_kind="gemini",
                checked_at_iso=checked_at,
                message=f"연결 성공. {len(models)}개 모델 감지.",
                latency_ms=latency,
            )
        except Exception as e:
            latency = int((time.monotonic() - start) * 1000)
            return ProviderHealth(
                ok=False,
                provider_kind="gemini",
                checked_at_iso=checked_at,
                message=f"연결 실패: {e}",
                latency_ms=latency,
            )

    async def list_models(
        self,
        profile: ProviderProfileData,
        api_key: str | None = None,
    ) -> list[ModelCapability]:
        """Gemini 모델 목록을 조회하여 ModelCapability 리스트로 반환한다."""
        if not api_key:
            raise ProviderConnectionError("API Key가 필요합니다.", provider_kind="gemini")

        try:
            client = self._create_client(api_key)
            raw_models = list(client.models.list())

            capabilities: list[ModelCapability] = []
            for model in raw_models:
                # Model 객체를 딕셔너리로 변환
                raw_dict = _model_to_dict(model)
                # generateContent를 지원하는 모델만 포함
                methods = raw_dict.get("supported_generation_methods", [])
                if "generateContent" in methods:
                    cap = map_gemini_model(raw_dict)
                    capabilities.append(cap)

            logger.info("Gemini 모델 %d개 조회 완료.", len(capabilities))
            return capabilities

        except Exception as e:
            raise ProviderApiError(
                f"Gemini 모델 목록 조회 실패: {e}",
                provider_kind="gemini",
            ) from e

    async def get_model_capability(
        self,
        profile: ProviderProfileData,
        model_id: str,
        api_key: str | None = None,
    ) -> ModelCapability:
        """특정 Gemini 모델의 capability를 반환한다."""
        if not api_key:
            raise ProviderConnectionError("API Key가 필요합니다.", provider_kind="gemini")

        try:
            client = self._create_client(api_key)
            model = client.models.get(model=f"models/{model_id}")
            raw_dict = _model_to_dict(model)
            return map_gemini_model(raw_dict)
        except Exception as e:
            raise ProviderApiError(
                f"Gemini 모델 정보 조회 실패 ({model_id}): {e}",
                provider_kind="gemini",
            ) from e

    async def stream_chat(
        self,
        profile: ProviderProfileData,
        request: ChatCompletionRequest,
        api_key: str | None = None,
    ) -> AsyncIterator[ChatStreamChunk]:
        """Gemini 스트리밍 채팅 응답을 반환한다."""
        if not api_key:
            raise ProviderConnectionError("API Key가 필요합니다.", provider_kind="gemini")

        try:
            client = self._create_client(api_key)

            # 메시지를 Gemini 형식으로 변환
            # system 메시지는 system_instruction으로, 나머지는 contents로 분리
            system_instruction: str | None = None
            contents: list[genai_types.Content] = []

            for msg in request.messages:
                if msg.role == "system":
                    # 마지막 system 메시지를 system_instruction으로 사용
                    system_instruction = msg.content
                else:
                    role = "user" if msg.role == "user" else "model"
                    contents.append(
                        genai_types.Content(
                            role=role,
                            parts=[genai_types.Part(text=msg.content)],
                        )
                    )

            # 생성 설정 구성
            gen_config = genai_types.GenerateContentConfig(
                temperature=request.settings.temperature,
                top_p=request.settings.top_p,
                top_k=request.settings.top_k,
                max_output_tokens=request.settings.max_output_tokens,
                presence_penalty=request.settings.presence_penalty,
                frequency_penalty=request.settings.frequency_penalty,
                seed=request.settings.seed,
                stop_sequences=request.settings.stop or None,
                system_instruction=system_instruction,
            )

            # 스트리밍 응답 생성
            response_stream = client.models.generate_content_stream(
                model=request.model_id,
                contents=contents,
                config=gen_config,
            )

            for chunk in response_stream:
                text = ""
                if chunk.text:
                    text = chunk.text

                finish_reason = None
                if chunk.candidates and chunk.candidates[0].finish_reason:
                    finish_reason = str(chunk.candidates[0].finish_reason)

                usage = None
                if chunk.usage_metadata:
                    usage = {
                        "prompt_tokens": chunk.usage_metadata.prompt_token_count,
                        "completion_tokens": chunk.usage_metadata.candidates_token_count,
                        "total_tokens": chunk.usage_metadata.total_token_count,
                    }

                yield ChatStreamChunk(
                    delta=text,
                    finish_reason=finish_reason,
                    usage=usage,
                )

        except Exception as e:
            raise ProviderStreamError(
                f"Gemini 스트리밍 실패: {e}",
                provider_kind="gemini",
            ) from e


def _model_to_dict(model: Any) -> dict[str, Any]:
    """google-genai Model 객체를 딕셔너리로 변환한다.

    SDK 버전에 따라 속성명이 다를 수 있으므로, 안전하게 getattr로 접근한다.
    """
    return {
        "name": getattr(model, "name", ""),
        "display_name": getattr(model, "display_name", ""),
        "description": getattr(model, "description", ""),
        "input_token_limit": getattr(model, "input_token_limit", None),
        "output_token_limit": getattr(model, "output_token_limit", None),
        "supported_generation_methods": getattr(model, "supported_generation_methods", []),
    }
