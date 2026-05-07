# src/chitchat/providers/base.py
# [v1.0.0] Provider 공통 기반: Protocol re-export, 에러 타입
#
# 모든 Provider adapter가 공유하는 에러 타입과 Protocol을 정의한다.
# Service 계층은 이 모듈의 타입만 참조하고 구체 adapter에 의존하지 않는다.

from __future__ import annotations

# ChatProvider Protocol을 이 모듈에서 re-export한다.
# Service/ViewModel은 providers.base.ChatProvider로 접근한다.
from chitchat.domain.provider_contracts import (  # noqa: F401
    ChatCompletionRequest,
    ChatProvider,
    ChatStreamChunk,
    ModelCapability,
    ProviderHealth,
    ProviderProfileData,
)


class ProviderError(Exception):
    """Provider 통신 중 발생하는 기반 에러.

    모든 Provider 관련 에러는 이 클래스를 상속한다.
    """

    def __init__(self, message: str, provider_kind: str | None = None) -> None:
        self.provider_kind = provider_kind
        super().__init__(message)


class ProviderConnectionError(ProviderError):
    """Provider 연결 실패 시 발생하는 에러.

    네트워크 장애, 인증 실패, 타임아웃 등을 포함한다.
    """
    pass


class ProviderApiError(ProviderError):
    """Provider API 호출 중 발생하는 에러.

    HTTP 4xx/5xx 응답, JSON 파싱 실패 등을 포함한다.
    status_code가 있으면 HTTP 상태 코드이다.
    """

    def __init__(
        self,
        message: str,
        provider_kind: str | None = None,
        status_code: int | None = None,
    ) -> None:
        self.status_code = status_code
        super().__init__(message, provider_kind)


class ProviderStreamError(ProviderError):
    """스트리밍 응답 처리 중 발생하는 에러.

    SSE 파싱 실패, 스트림 중단 등을 포함한다.
    """
    pass
