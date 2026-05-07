# src/chitchat/providers/capability_mapper.py
# [v1.0.0] Provider별 raw 응답 → ModelCapability 정규화
#
# 각 Provider의 모델 메타데이터 raw 응답을 통일된 ModelCapability로 변환한다.
# spec.md §10.1~§10.3의 매핑 규칙을 구현한다.
#
# Gemini: google-genai SDK의 Model 객체
# OpenRouter: GET /api/v1/models 응답의 data 항목
# LM Studio: GET /v1/models 응답의 data 항목

from __future__ import annotations

import logging
from typing import Any

from chitchat.domain.provider_contracts import (
    ModelCapability,
    ParameterName,
    ProviderKind,
)

logger = logging.getLogger(__name__)

# --- Gemini 매핑 (spec.md §10.1) ---
# Gemini는 모든 기본 파라미터를 지원한다.
_GEMINI_DEFAULT_PARAMS: set[ParameterName] = {
    "temperature",
    "top_p",
    "top_k",
    "max_output_tokens",
    "presence_penalty",
    "frequency_penalty",
    "seed",
    "stop",
}


def map_gemini_model(raw: dict[str, Any]) -> ModelCapability:
    """Gemini raw 모델 메타데이터를 ModelCapability로 변환한다.

    google-genai SDK의 Model 객체를 dict로 변환한 것을 입력받는다.
    input_token_limit → context_window_tokens
    output_token_limit → max_output_tokens

    Args:
        raw: Gemini 모델 메타데이터 딕셔너리.

    Returns:
        정규화된 ModelCapability.
    """
    # Gemini 모델 이름에서 "models/" 접두사를 제거한다
    model_id = raw.get("name", "")
    if model_id.startswith("models/"):
        model_id = model_id[len("models/"):]

    display_name = raw.get("display_name", model_id)

    return ModelCapability(
        provider_kind="gemini",
        model_id=model_id,
        display_name=display_name,
        context_window_tokens=raw.get("input_token_limit"),
        max_output_tokens=raw.get("output_token_limit"),
        supported_parameters=_GEMINI_DEFAULT_PARAMS.copy(),
        supports_streaming=True,
        supports_system_prompt=True,
        supports_json_mode="generateContent" in raw.get("supported_generation_methods", []),
        raw=raw,
    )


# --- OpenRouter 매핑 (spec.md §10.2) ---

# OpenRouter의 supported_parameters → ParameterName 매핑
_OPENROUTER_PARAM_MAP: dict[str, ParameterName] = {
    "temperature": "temperature",
    "top_p": "top_p",
    "top_k": "top_k",
    "max_tokens": "max_output_tokens",
    "presence_penalty": "presence_penalty",
    "frequency_penalty": "frequency_penalty",
    "seed": "seed",
    "stop": "stop",
}


def map_openrouter_model(raw: dict[str, Any]) -> ModelCapability:
    """OpenRouter raw 모델 메타데이터를 ModelCapability로 변환한다.

    GET /api/v1/models 응답의 data 배열 각 항목을 입력받는다.
    context_length → context_window_tokens
    top_provider.max_completion_tokens → max_output_tokens
    supported_parameters → ParameterName 집합으로 변환

    Args:
        raw: OpenRouter 모델 메타데이터 딕셔너리.

    Returns:
        정규화된 ModelCapability.
    """
    model_id = raw.get("id", "")
    display_name = raw.get("name", model_id)

    # supported_parameters에서 ParameterName 집합 추출
    raw_params = raw.get("supported_parameters", [])
    supported: set[ParameterName] = set()
    for p in raw_params:
        if p in _OPENROUTER_PARAM_MAP:
            supported.add(_OPENROUTER_PARAM_MAP[p])

    # top_provider에서 max_completion_tokens 추출
    top_provider = raw.get("top_provider", {}) or {}
    max_output = top_provider.get("max_completion_tokens")

    return ModelCapability(
        provider_kind="openrouter",
        model_id=model_id,
        display_name=display_name,
        context_window_tokens=raw.get("context_length"),
        max_output_tokens=max_output,
        supported_parameters=supported,
        supports_streaming=True,
        supports_system_prompt=True,
        supports_json_mode=True,
        raw=raw,
    )


# --- LM Studio 매핑 (spec.md §10.3) ---

# LM Studio는 OpenAI-compatible이므로 기본 파라미터를 가정한다.
# token limit은 API에서 제공하지 않으므로 None (기본값 8192/2048 적용).
_LMSTUDIO_DEFAULT_PARAMS: set[ParameterName] = {
    "temperature",
    "top_p",
    "max_output_tokens",
    "presence_penalty",
    "frequency_penalty",
    "stop",
}


def map_lmstudio_model(raw: dict[str, Any]) -> ModelCapability:
    """LM Studio raw 모델 메타데이터를 ModelCapability로 변환한다.

    GET /v1/models 응답의 data 배열 각 항목을 입력받는다.
    LM Studio는 token limit 정보를 제공하지 않으므로 None을 설정한다.
    spec.md §10.3: 기본값 context_window_tokens=8192, max_output_tokens=2048.

    Args:
        raw: LM Studio 모델 메타데이터 딕셔너리.

    Returns:
        정규화된 ModelCapability.
    """
    model_id = raw.get("id", "")

    return ModelCapability(
        provider_kind="lm_studio",
        model_id=model_id,
        display_name=model_id,
        # LM Studio는 token limit을 제공하지 않음 → None
        # Service 계층에서 기본값 8192/2048을 적용한다.
        context_window_tokens=None,
        max_output_tokens=None,
        supported_parameters=_LMSTUDIO_DEFAULT_PARAMS.copy(),
        supports_streaming=True,
        supports_system_prompt=True,
        supports_json_mode=False,
        raw=raw,
    )


# --- 통합 매퍼 ---

def map_model_capability(
    provider_kind: ProviderKind,
    raw: dict[str, Any],
) -> ModelCapability:
    """Provider 종류에 따라 적절한 매퍼를 선택하여 ModelCapability를 반환한다.

    Args:
        provider_kind: Provider 종류.
        raw: Provider별 raw 모델 메타데이터.

    Returns:
        정규화된 ModelCapability.

    Raises:
        ValueError: 알 수 없는 provider_kind일 때.
    """
    if provider_kind == "gemini":
        return map_gemini_model(raw)
    elif provider_kind == "openrouter":
        return map_openrouter_model(raw)
    elif provider_kind == "lm_studio":
        return map_lmstudio_model(raw)
    else:
        raise ValueError(f"알 수 없는 provider_kind: {provider_kind!r}")
