# src/chitchat/domain/dynamic_state.py
# [v1.0.0] 캐릭터 동적 상태 도메인 모델
#
# 대화 진행에 따라 변화하는 캐릭터의 런타임 상태를 정의한다.
# 이 데이터는 SQLite에 ZSTD 압축 JSON blob으로 저장된다.
# 원본 PersonaCard(MD 문서)와 분리되어 독립적으로 갱신된다.
#
# 핵심 동적 요소:
# - 관계 상태 변수 (trust, familiarity, emotional_reliance 등 9개)
# - 기억 저장소 (MemoryEntry 리스트)
# - 감정 상태 (현재 감정, 활성 방어전략)
# - 이벤트 로그 (NarrativeEvent 리스트)

from __future__ import annotations

from pydantic import BaseModel, Field

from chitchat.domain.vibesmith_persona import RelationshipState


class MemoryEntry(BaseModel):
    """캐릭터가 대화에서 형성한 기억.

    매 턴 종료 후 DynamicStateEngine이 기억 저장 트리거를 감지하면
    이 엔트리가 생성되어 동적 상태에 추가된다.
    """
    id: str = Field(description="기억 고유 ID (ULID)")
    trigger_type: str = Field(
        description="기억 형성 트리거 유형 (promise_kept, praise, boundary_violation 등)",
    )
    content: str = Field(
        max_length=2000,
        description="기억 내용 요약",
    )
    emotional_impact: str = Field(
        default="",
        max_length=500,
        description="감정 영향 (예: 'trust+5, fear_of_rejection-3')",
    )
    turn_number: int = Field(
        ge=0,
        description="기억이 형성된 대화 턴 번호",
    )
    created_at_iso: str = Field(description="생성 시각 ISO 8601")


class NarrativeEvent(BaseModel):
    """내러티브 이벤트 — 캐릭터의 사회적 위치/상황 변화를 기록한다.

    예: "카페 아르바이트에서 사용자와 공동 작업을 시작함",
        "진로 이야기에서 처음으로 솔직하게 고민을 나눔"
    """
    id: str = Field(description="이벤트 고유 ID (ULID)")
    event_type: str = Field(
        description="이벤트 유형 (social_change, conflict, resolution, milestone)",
    )
    description: str = Field(
        max_length=1000,
        description="이벤트 설명",
    )
    impact_summary: str = Field(
        default="",
        max_length=500,
        description="이벤트가 캐릭터에게 미친 영향 요약",
    )
    turn_number: int = Field(ge=0, description="이벤트 발생 턴 번호")
    created_at_iso: str = Field(description="생성 시각 ISO 8601")


class DynamicCharacterState(BaseModel):
    """캐릭터의 런타임 동적 상태.

    하나의 PersonaCard(캐릭터)와 하나의 ChatSession(세션)에 연결된다.
    대화 진행에 따라 AI가 판단하여 이 상태를 갱신한다.
    SQLite dynamic_states 테이블에 ZSTD 압축 JSON blob으로 저장된다.
    """
    # 식별자
    character_id: str = Field(description="연결된 PersonaCard ID")
    session_id: str = Field(description="연결된 ChatSession ID")

    # 관계 상태 변수 (VibeSmith §3 RelationshipState에서 초기화)
    relationship_state: RelationshipState = Field(
        default_factory=RelationshipState,
        description="현재 관계 상태 변수 (9개)",
    )

    # 기억 저장소
    memories: list[MemoryEntry] = Field(
        default_factory=list,
        description="형성된 기억 목록 (시간순)",
    )

    # 감정 상태
    current_emotional_state: str = Field(
        default="neutral",
        max_length=500,
        description="현재 감정 상태 요약",
    )
    active_defense_strategy: str = Field(
        default="",
        max_length=500,
        description="현재 활성화된 방어 전략",
    )

    # 이벤트 로그
    events: list[NarrativeEvent] = Field(
        default_factory=list,
        description="내러티브 이벤트 로그 (시간순)",
    )

    # 메타데이터
    version: int = Field(default=1, description="상태 버전 (낙관적 잠금용)")
    turn_count: int = Field(default=0, ge=0, description="누적 대화 턴 수")
    updated_at_iso: str = Field(default="", description="마지막 갱신 시각")
