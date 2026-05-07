# src/chitchat/domain/provider_contracts.py
# [v1.0.0] Provider 통신 계약 타입 정의
#
# spec.md §8.1에서 동결된 Provider 경계 계약을 코드로 구현한다.
# ChatProvider Protocol과 요청/응답 타입, 모델 capability 타입을 정의한다.
# 이 모듈은 외부 라이브러리(httpx, google-genai 등)에 의존하지 않는다.

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Literal, Protocol

from pydantic import BaseModel, Field


# --- 열거 타입 ---
# spec.md §7.2에서 정의된 Literal 타입

ProviderKind = Literal["gemini", "openrouter", "lm_studio"]
"""지원하는 Provider 종류. spec.md §1에서 Gemini, OpenRouter, LM Studio로 고정."""

Role = Literal["system", "user", "assistant"]
"""채팅 메시지 역할. system/user/assistant 3종만 허용."""

ChatSessionStatus = Literal["draft", "active", "streaming", "stopped", "failed", "archived"]
"""채팅 세션 상태. spec.md §13.2 상태 머신에 따라 전이한다."""

PromptBlockKind = Literal[
    "system_base",
    "ai_persona",
    "worldbook",
    "lorebook",
    "user_persona",
    "chat_history",
    "current_input",
]
"""프롬프트 블록 종류. spec.md §12.2 기본 순서에 7종이 정의되어 있다."""

ParameterName = Literal[
    "temperature",
    "top_p",
    "top_k",
    "max_output_tokens",
    "presence_penalty",
    "frequency_penalty",
    "seed",
    "stop",
]
"""모델 생성 파라미터 이름. spec.md §11.1에서 정의된 8종."""


# --- Provider 프로필 ---

class ProviderProfileData(BaseModel):
    """Provider 등록 정보. DB에 저장되는 Provider 프로필 데이터.

    secret_ref는 keyring의 참조 키이며, 실제 API Key는 이 모델에 포함되지 않는다.
    base_url은 OpenRouter/LM Studio에서 사용하고, Gemini는 None이다.
    """
    id: str
    name: str = Field(min_length=1, max_length=80)
    provider_kind: ProviderKind
    base_url: str | None = None
    secret_ref: str | None = None
    enabled: bool = True
    timeout_seconds: int = Field(default=60, ge=5, le=300)


class ProviderHealth(BaseModel):
    """Provider 연결 테스트 결과.

    validate_connection()의 반환 타입이다.
    ok가 False이면 message에 실패 사유가 포함된다.
    latency_ms는 연결 테스트 응답 시간(밀리초)이다.
    """
    ok: bool
    provider_kind: ProviderKind
    checked_at_iso: str
    message: str
    latency_ms: int | None = None


# --- 모델 capability ---

class ModelCapability(BaseModel):
    """모델의 능력치 정보. Provider별 raw 응답을 정규화한 결과.

    supported_parameters는 이 모델이 지원하는 파라미터 집합이다.
    UI는 이 집합에 포함되지 않은 파라미터 컨트롤을 숨겨야 한다.
    context_window_tokens가 None이면 LM Studio 등에서 알 수 없는 경우이며,
    기본값 8192를 적용한다.
    """
    provider_kind: ProviderKind
    model_id: str
    display_name: str
    context_window_tokens: int | None = Field(default=None, ge=1)
    max_output_tokens: int | None = Field(default=None, ge=1)
    supported_parameters: set[ParameterName]
    supports_streaming: bool
    supports_system_prompt: bool
    supports_json_mode: bool
    raw: dict  # type: ignore[type-arg]  # Provider별 원본 메타데이터 보존용


# --- 모델 생성 설정 ---

class ModelGenerationSettings(BaseModel):
    """모델 생성 파라미터 설정값.

    ModelProfile에 저장되며, ChatCompletionRequest에도 포함된다.
    각 파라미터가 None이면 Provider 기본값을 사용한다.
    max_output_tokens만 기본값 1024가 있다.
    """
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    top_k: int | None = Field(default=None, ge=1, le=500)
    max_output_tokens: int = Field(default=1024, ge=1)
    presence_penalty: float | None = Field(default=None, ge=-2.0, le=2.0)
    frequency_penalty: float | None = Field(default=None, ge=-2.0, le=2.0)
    seed: int | None = None
    stop: list[str] = Field(default_factory=list, max_length=8)


# --- 채팅 요청/응답 ---

class ChatCompletionMessage(BaseModel):
    """채팅 메시지 단일 항목. role과 content로 구성된다."""
    role: Role
    content: str = Field(min_length=1)


class ChatCompletionRequest(BaseModel):
    """Provider에 보내는 채팅 완성 요청.

    stream=True이면 Provider는 AsyncIterator[ChatStreamChunk]를 반환한다.
    messages는 prompt_assembler가 조합한 최종 메시지 목록이다.
    """
    provider_profile_id: str
    model_id: str
    settings: ModelGenerationSettings
    messages: list[ChatCompletionMessage]
    stream: bool = True


class ChatStreamChunk(BaseModel):
    """스트리밍 응답의 단일 청크.

    delta는 이번 청크에서 추가된 텍스트 조각이다.
    finish_reason이 None이 아니면 스트림이 종료된 것이다.
    usage는 마지막 청크에서만 포함될 수 있다.
    """
    delta: str
    finish_reason: str | None = None
    usage: dict | None = None  # type: ignore[type-arg]
    raw: dict | None = None  # type: ignore[type-arg]


# --- Provider Protocol ---

class ChatProvider(Protocol):
    """Provider adapter가 구현해야 하는 프로토콜.

    spec.md §4 D-06에서 동결된 경계 계약이다.
    모든 Provider adapter는 이 Protocol의 4개 메서드를 구현한다.
    UI/Service 계층은 이 Protocol만 참조하고, 구체 구현에 의존하지 않는다.
    """
    provider_kind: ProviderKind

    async def validate_connection(self, profile: ProviderProfileData, api_key: str | None = None) -> ProviderHealth:
        """Provider 연결 상태를 확인한다."""
        ...

    async def list_models(self, profile: ProviderProfileData, api_key: str | None = None) -> list[ModelCapability]:
        """사용 가능한 모델 목록을 반환한다."""
        ...

    async def get_model_capability(
        self,
        profile: ProviderProfileData,
        model_id: str,
        api_key: str | None = None,
    ) -> ModelCapability:
        """특정 모델의 capability를 반환한다."""
        ...

    async def stream_chat(
        self,
        profile: ProviderProfileData,
        request: ChatCompletionRequest,
        api_key: str | None = None,
    ) -> AsyncIterator[ChatStreamChunk]:
        """스트리밍 채팅 응답을 반환한다. 각 청크는 ChatStreamChunk이다."""
        ...
