# src/chitchat/providers/lmstudio_provider.py
# [v1.0.0] LM Studio Provider adapter
#
# httpx를 사용하여 로컬 LM Studio 서버에 접근한다.
# spec.md §10.3: token limit 미제공 시 기본값 context=8192, output=2048 적용.
# LM Studio는 API Key가 불필요하다 (secret_ref = None).
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
from chitchat.providers.capability_mapper import map_lmstudio_model

logger = logging.getLogger(__name__)

# LM Studio 기본 URL
_DEFAULT_BASE_URL = "http://localhost:1234/v1"


class LMStudioProvider:
    """LM Studio Provider adapter.

    httpx AsyncClient를 사용하여 로컬 LM Studio 서버와 통신한다.
    API Key가 불필요하며, base_url로 서버 주소를 변경할 수 있다.
    """

    provider_kind: ProviderKind = "lm_studio"

    def _get_base_url(self, profile: ProviderProfileData) -> str:
        """Provider 프로필에서 base_url을 결정한다."""
        return profile.base_url or _DEFAULT_BASE_URL

    async def validate_connection(
        self,
        profile: ProviderProfileData,
        api_key: str | None = None,
    ) -> ProviderHealth:
        """LM Studio 서버 연결 상태를 확인한다.

        LM Studio는 API Key가 필요 없으므로 api_key 파라미터는 무시된다.
        """
        checked_at = datetime.now(timezone.utc).isoformat()
        base_url = self._get_base_url(profile)
        start = time.monotonic()

        try:
            async with httpx.AsyncClient(timeout=profile.timeout_seconds) as client:
                resp = await client.get(f"{base_url}/models")
                latency = int((time.monotonic() - start) * 1000)

                if resp.status_code == 200:
                    data = resp.json().get("data", [])
                    return ProviderHealth(
                        ok=True,
                        provider_kind="lm_studio",
                        checked_at_iso=checked_at,
                        message=f"연결 성공. {len(data)}개 모델 로딩됨.",
                        latency_ms=latency,
                    )
                else:
                    return ProviderHealth(
                        ok=False,
                        provider_kind="lm_studio",
                        checked_at_iso=checked_at,
                        message=f"HTTP {resp.status_code}: {resp.text[:200]}",
                        latency_ms=latency,
                    )
        except httpx.ConnectError:
            latency = int((time.monotonic() - start) * 1000)
            return ProviderHealth(
                ok=False,
                provider_kind="lm_studio",
                checked_at_iso=checked_at,
                message=f"LM Studio 서버에 연결할 수 없습니다: {base_url}. "
                        f"LM Studio가 실행 중인지 확인하세요.",
                latency_ms=latency,
            )
        except Exception as e:
            latency = int((time.monotonic() - start) * 1000)
            return ProviderHealth(
                ok=False,
                provider_kind="lm_studio",
                checked_at_iso=checked_at,
                message=f"연결 실패: {e}",
                latency_ms=latency,
            )

    async def list_models(
        self,
        profile: ProviderProfileData,
        api_key: str | None = None,
    ) -> list[ModelCapability]:
        """LM Studio에 로딩된 모델 목록을 조회한다."""
        base_url = self._get_base_url(profile)

        try:
            async with httpx.AsyncClient(timeout=profile.timeout_seconds) as client:
                resp = await client.get(f"{base_url}/models")
                resp.raise_for_status()
                data = resp.json().get("data", [])

            capabilities = [map_lmstudio_model(m) for m in data]
            logger.info("LM Studio 모델 %d개 조회 완료.", len(capabilities))
            return capabilities

        except httpx.ConnectError as e:
            raise ProviderConnectionError(
                f"LM Studio 서버에 연결할 수 없습니다: {base_url}",
                provider_kind="lm_studio",
            ) from e
        except Exception as e:
            raise ProviderApiError(
                f"LM Studio 모델 목록 조회 실패: {e}",
                provider_kind="lm_studio",
            ) from e

    async def get_model_capability(
        self,
        profile: ProviderProfileData,
        model_id: str,
        api_key: str | None = None,
    ) -> ModelCapability:
        """특정 LM Studio 모델의 capability를 반환한다."""
        models = await self.list_models(profile, api_key)
        for cap in models:
            if cap.model_id == model_id:
                return cap
        raise ProviderApiError(
            f"LM Studio에서 모델을 찾을 수 없습니다: {model_id}",
            provider_kind="lm_studio",
        )

    async def stream_chat(
        self,
        profile: ProviderProfileData,
        request: ChatCompletionRequest,
        api_key: str | None = None,
    ) -> AsyncIterator[ChatStreamChunk]:
        """LM Studio 스트리밍 채팅 응답을 반환한다.

        OpenAI-compatible API를 사용한다.
        LM Studio는 API Key가 필요 없으므로 Authorization 헤더를 생략한다.
        """
        base_url = self._get_base_url(profile)

        body: dict[str, object] = {
            "model": request.model_id,
            "messages": [
                {"role": m.role, "content": m.content}
                for m in request.messages
            ],
            "stream": True,
        }

        # 생성 설정 추가
        settings = request.settings
        if settings.temperature is not None:
            body["temperature"] = settings.temperature
        if settings.top_p is not None:
            body["top_p"] = settings.top_p
        if settings.max_output_tokens:
            body["max_tokens"] = settings.max_output_tokens
        if settings.presence_penalty is not None:
            body["presence_penalty"] = settings.presence_penalty
        if settings.frequency_penalty is not None:
            body["frequency_penalty"] = settings.frequency_penalty
        if settings.stop:
            body["stop"] = settings.stop

        try:
            async with httpx.AsyncClient(timeout=profile.timeout_seconds) as client:
                async with client.stream(
                    "POST",
                    f"{base_url}/chat/completions",
                    headers={"Content-Type": "application/json"},
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

        except httpx.ConnectError as e:
            raise ProviderStreamError(
                f"LM Studio 서버에 연결할 수 없습니다: {base_url}",
                provider_kind="lm_studio",
            ) from e
        except Exception as e:
            raise ProviderStreamError(
                f"LM Studio 스트리밍 실패: {e}",
                provider_kind="lm_studio",
            ) from e
