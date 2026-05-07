# src/chitchat/providers/openrouter_provider.py
# [v1.0.0] OpenRouter Provider adapter
#
# httpx를 사용하여 OpenRouter API에 접근한다.
# spec.md §10.2: context_length → context_window_tokens
# ChatProvider Protocol의 4개 메서드를 구현한다.

from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncIterator
from datetime import datetime, timezone

import httpx

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
from chitchat.providers.capability_mapper import map_openrouter_model

logger = logging.getLogger(__name__)

# OpenRouter 기본 URL
_DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterProvider:
    """OpenRouter Provider adapter.

    httpx AsyncClient를 사용하여 OpenRouter API와 통신한다.
    base_url을 오버라이드할 수 있다.
    """

    provider_kind: ProviderKind = "openrouter"

    def _get_base_url(self, profile: ProviderProfileData) -> str:
        """Provider 프로필에서 base_url을 결정한다."""
        return profile.base_url or _DEFAULT_BASE_URL

    def _get_headers(self, api_key: str) -> dict[str, str]:
        """API 요청 헤더를 생성한다."""
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/chitchat-app",
            "X-Title": "chitchat",
        }

    async def validate_connection(
        self,
        profile: ProviderProfileData,
        api_key: str | None = None,
    ) -> ProviderHealth:
        """OpenRouter API 연결 상태를 확인한다."""
        checked_at = datetime.now(timezone.utc).isoformat()
        if not api_key:
            return ProviderHealth(
                ok=False,
                provider_kind="openrouter",
                checked_at_iso=checked_at,
                message="API Key가 제공되지 않았습니다.",
            )

        base_url = self._get_base_url(profile)
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=profile.timeout_seconds) as client:
                resp = await client.get(
                    f"{base_url}/models",
                    headers=self._get_headers(api_key),
                )
                latency = int((time.monotonic() - start) * 1000)

                if resp.status_code == 200:
                    data = resp.json().get("data", [])
                    return ProviderHealth(
                        ok=True,
                        provider_kind="openrouter",
                        checked_at_iso=checked_at,
                        message=f"연결 성공. {len(data)}개 모델 감지.",
                        latency_ms=latency,
                    )
                else:
                    return ProviderHealth(
                        ok=False,
                        provider_kind="openrouter",
                        checked_at_iso=checked_at,
                        message=f"HTTP {resp.status_code}: {resp.text[:200]}",
                        latency_ms=latency,
                    )
        except Exception as e:
            latency = int((time.monotonic() - start) * 1000)
            return ProviderHealth(
                ok=False,
                provider_kind="openrouter",
                checked_at_iso=checked_at,
                message=f"연결 실패: {e}",
                latency_ms=latency,
            )

    async def list_models(
        self,
        profile: ProviderProfileData,
        api_key: str | None = None,
    ) -> list[ModelCapability]:
        """OpenRouter 모델 목록을 조회한다."""
        if not api_key:
            raise ProviderConnectionError("API Key가 필요합니다.", provider_kind="openrouter")

        base_url = self._get_base_url(profile)
        try:
            async with httpx.AsyncClient(timeout=profile.timeout_seconds) as client:
                resp = await client.get(
                    f"{base_url}/models",
                    headers=self._get_headers(api_key),
                )
                resp.raise_for_status()
                data = resp.json().get("data", [])

            capabilities = [map_openrouter_model(m) for m in data]
            logger.info("OpenRouter 모델 %d개 조회 완료.", len(capabilities))
            return capabilities

        except httpx.HTTPStatusError as e:
            raise ProviderApiError(
                f"OpenRouter 모델 목록 조회 실패: HTTP {e.response.status_code}",
                provider_kind="openrouter",
                status_code=e.response.status_code,
            ) from e
        except Exception as e:
            raise ProviderApiError(
                f"OpenRouter 모델 목록 조회 실패: {e}",
                provider_kind="openrouter",
            ) from e

    async def get_model_capability(
        self,
        profile: ProviderProfileData,
        model_id: str,
        api_key: str | None = None,
    ) -> ModelCapability:
        """특정 OpenRouter 모델의 capability를 반환한다."""
        # OpenRouter는 개별 모델 조회 API가 없으므로 전체 목록에서 필터링한다
        models = await self.list_models(profile, api_key)
        for cap in models:
            if cap.model_id == model_id:
                return cap
        raise ProviderApiError(
            f"OpenRouter에서 모델을 찾을 수 없습니다: {model_id}",
            provider_kind="openrouter",
        )

    async def stream_chat(
        self,
        profile: ProviderProfileData,
        request: ChatCompletionRequest,
        api_key: str | None = None,
    ) -> AsyncIterator[ChatStreamChunk]:
        """OpenRouter 스트리밍 채팅 응답을 반환한다."""
        if not api_key:
            raise ProviderConnectionError("API Key가 필요합니다.", provider_kind="openrouter")

        base_url = self._get_base_url(profile)
        headers = self._get_headers(api_key)

        # OpenAI-compatible 요청 body 구성
        body: dict[str, object] = {
            "model": request.model_id,
            "messages": [
                {"role": m.role, "content": m.content}
                for m in request.messages
            ],
            "stream": True,
        }

        # 생성 설정 추가 (None이 아닌 값만)
        settings = request.settings
        if settings.temperature is not None:
            body["temperature"] = settings.temperature
        if settings.top_p is not None:
            body["top_p"] = settings.top_p
        if settings.top_k is not None:
            body["top_k"] = settings.top_k
        if settings.max_output_tokens:
            body["max_tokens"] = settings.max_output_tokens
        if settings.presence_penalty is not None:
            body["presence_penalty"] = settings.presence_penalty
        if settings.frequency_penalty is not None:
            body["frequency_penalty"] = settings.frequency_penalty
        if settings.seed is not None:
            body["seed"] = settings.seed
        if settings.stop:
            body["stop"] = settings.stop

        try:
            async with httpx.AsyncClient(timeout=profile.timeout_seconds) as client:
                async with client.stream(
                    "POST",
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=body,
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data_str = line[len("data: "):]
                        if data_str.strip() == "[DONE]":
                            break

                        try:
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        choices = data.get("choices", [])
                        if not choices:
                            continue

                        choice = choices[0]
                        delta = choice.get("delta", {})
                        content = delta.get("content", "")
                        finish_reason = choice.get("finish_reason")
                        usage = data.get("usage")

                        yield ChatStreamChunk(
                            delta=content or "",
                            finish_reason=finish_reason,
                            usage=usage,
                            raw=data,
                        )

        except httpx.HTTPStatusError as e:
            raise ProviderStreamError(
                f"OpenRouter 스트리밍 실패: HTTP {e.response.status_code}",
                provider_kind="openrouter",
            ) from e
        except Exception as e:
            raise ProviderStreamError(
                f"OpenRouter 스트리밍 실패: {e}",
                provider_kind="openrouter",
            ) from e
