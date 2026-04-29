# src/chitchat/domain/chat_session.py
# [v0.1.0b0] 채팅 세션 및 메시지 도메인 타입 + 상태 전이 검증
#
# spec.md §8.4에서 동결된 채팅 계약과 §13.2 상태 머신을 구현한다.
# 상태 전이 검증 함수는 잘못된 전이를 사전에 차단한다.

from __future__ import annotations

from pydantic import BaseModel, Field

from chitchat.domain.provider_contracts import ChatSessionStatus, Role


class ChatSessionData(BaseModel):
    """채팅 세션 데이터.

    chat_profile_id와 user_persona_id를 참조하여 프롬프트를 조립한다.
    status는 spec.md §13.2 상태 머신에 따라 전이한다.
    """
    id: str
    title: str = Field(min_length=1, max_length=120)
    chat_profile_id: str
    user_persona_id: str
    status: ChatSessionStatus
    created_at_iso: str
    updated_at_iso: str


class ChatMessageData(BaseModel):
    """채팅 메시지 데이터.

    prompt_snapshot_json은 assistant 메시지에만 저장되며,
    해당 응답 생성 시 사용된 프롬프트 조합 스냅샷(JSON 문자열)이다.
    token_estimate는 estimate_tokens() 함수로 계산한 근사 토큰 수이다.
    """
    id: str
    session_id: str
    role: Role
    content: str = Field(min_length=1)
    prompt_snapshot_json: str | None = None
    created_at_iso: str
    token_estimate: int


# --- 상태 전이 규칙 ---
# spec.md §13.2에서 정의된 유효한 전이 맵
# 키: 현재 상태, 값: 전이 가능한 다음 상태 집합

_VALID_TRANSITIONS: dict[ChatSessionStatus, set[ChatSessionStatus]] = {
    "draft": {"active"},
    "active": {"streaming", "archived"},
    "streaming": {"active", "stopped", "failed"},
    "stopped": {"active"},
    "failed": {"active"},
    "archived": set(),  # archived에서는 다른 상태로 전이할 수 없다
}


def validate_session_transition(
    current: ChatSessionStatus,
    target: ChatSessionStatus,
) -> bool:
    """현재 상태에서 목표 상태로의 전이가 유효한지 검증한다.

    Args:
        current: 현재 세션 상태.
        target: 전이하려는 목표 상태.

    Returns:
        전이가 유효하면 True, 아니면 False.
    """
    return target in _VALID_TRANSITIONS.get(current, set())


class InvalidSessionTransitionError(Exception):
    """유효하지 않은 세션 상태 전이 시 발생하는 예외."""

    def __init__(self, current: ChatSessionStatus, target: ChatSessionStatus) -> None:
        self.current = current
        self.target = target
        super().__init__(
            f"유효하지 않은 세션 상태 전이: {current!r} → {target!r}. "
            f"허용 전이: {_VALID_TRANSITIONS.get(current, set())}"
        )
