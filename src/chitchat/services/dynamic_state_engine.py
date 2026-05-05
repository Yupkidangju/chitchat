# src/chitchat/services/dynamic_state_engine.py
# [v1.0.0] 동적 상태 갱신 엔진
#
# 매 AI 응답 후 실행되어 캐릭터의 동적 상태를 갱신한다.
# AI에게 현재 대화 + 기존 상태를 제공하고, 상태 변경 판단을 요청한다.
# 변경된 상태는 ZSTD 압축 후 SQLite에 저장된다.
#
# 동적 갱신 대상:
# - 관계 상태 변수 (trust, familiarity, emotional_reliance 등 9개)
# - 기억 형성 (MemoryEntry)
# - 감정 상태 갱신
# - 내러티브 이벤트 기록

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import zstandard as zstd

from chitchat.domain.dynamic_state import (
    DynamicCharacterState,
    MemoryEntry,
    NarrativeEvent,
)
from chitchat.domain.ids import new_id
from chitchat.domain.vibesmith_persona import RelationshipState

logger = logging.getLogger(__name__)

# ZSTD 압축 레벨 (1~22, 기본 3 — 속도와 압축률 균형)
_ZSTD_COMPRESSION_LEVEL = 3

# 기억 저장 트리거 키워드 (AI 분석 전 사전 필터링용)
_MEMORY_TRIGGER_TYPES = [
    "promise_kept",       # 약속 이행
    "promise_broken",     # 약속 불이행
    "praise",             # 칭찬
    "boundary_respect",   # 경계 존중
    "boundary_violation", # 경계 침범
    "vulnerability",      # 취약한 면 드러냄
    "initiation",         # 먼저 다가감
    "conflict_repair",    # 갈등 회복
    "shared_experience",  # 공동 경험
]


class DynamicStateEngine:
    """캐릭터 동적 상태 갱신 엔진.

    매 AI 응답 후 호출되어 대화 분석 → 상태 갱신 → 기억 형성 → 영속화를 수행한다.
    """

    def __init__(self) -> None:
        self._compressor = zstd.ZstdCompressor(level=_ZSTD_COMPRESSION_LEVEL)
        self._decompressor = zstd.ZstdDecompressor()

    def create_initial_state(
        self,
        character_id: str,
        session_id: str,
        initial_relationship: RelationshipState | None = None,
    ) -> DynamicCharacterState:
        """새 세션의 초기 동적 상태를 생성한다.

        PersonaCard의 기본 RelationshipState를 복사하여 초기화한다.
        """
        now = datetime.now(timezone.utc).isoformat()
        return DynamicCharacterState(
            character_id=character_id,
            session_id=session_id,
            relationship_state=initial_relationship or RelationshipState(),
            memories=[],
            current_emotional_state="neutral",
            active_defense_strategy="",
            events=[],
            version=1,
            turn_count=0,
            updated_at_iso=now,
        )

    def add_memory(
        self,
        state: DynamicCharacterState,
        trigger_type: str,
        content: str,
        emotional_impact: str = "",
    ) -> MemoryEntry:
        """동적 상태에 새 기억을 추가한다.

        Args:
            state: 현재 동적 상태.
            trigger_type: 기억 형성 트리거 유형.
            content: 기억 내용 요약.
            emotional_impact: 감정 영향 (예: 'trust+5').

        Returns:
            생성된 MemoryEntry.
        """
        now = datetime.now(timezone.utc).isoformat()
        memory = MemoryEntry(
            id=new_id("mem_"),
            trigger_type=trigger_type,
            content=content,
            emotional_impact=emotional_impact,
            turn_number=state.turn_count,
            created_at_iso=now,
        )
        state.memories.append(memory)
        logger.info(
            "기억 형성: 캐릭터=%s, 트리거=%s, 턴=%d",
            state.character_id, trigger_type, state.turn_count,
        )
        return memory

    def add_event(
        self,
        state: DynamicCharacterState,
        event_type: str,
        description: str,
        impact_summary: str = "",
    ) -> NarrativeEvent:
        """동적 상태에 내러티브 이벤트를 추가한다."""
        now = datetime.now(timezone.utc).isoformat()
        event = NarrativeEvent(
            id=new_id("evt_"),
            event_type=event_type,
            description=description,
            impact_summary=impact_summary,
            turn_number=state.turn_count,
            created_at_iso=now,
        )
        state.events.append(event)
        logger.info(
            "이벤트 기록: 캐릭터=%s, 유형=%s",
            state.character_id, event_type,
        )
        return event

    def update_relationship(
        self,
        state: DynamicCharacterState,
        changes: dict[str, int],
    ) -> None:
        """관계 상태 변수를 갱신한다.

        Args:
            state: 현재 동적 상태.
            changes: 변경할 변수와 증감값 (예: {'trust': 5, 'fear_of_rejection': -3}).
        """
        rs = state.relationship_state
        for key, delta in changes.items():
            if key == "topic_comfort":
                continue  # 딕셔너리 타입은 별도 처리
            if hasattr(rs, key):
                current = getattr(rs, key)
                if isinstance(current, int):
                    new_val = max(0, min(100, current + delta))
                    setattr(rs, key, new_val)
                    logger.debug("관계 변수 갱신: %s %d → %d", key, current, new_val)

    def increment_turn(self, state: DynamicCharacterState) -> None:
        """턴 카운트를 증가시키고 갱신 시각을 기록한다."""
        state.turn_count += 1
        state.updated_at_iso = datetime.now(timezone.utc).isoformat()
        state.version += 1

    # --- ZSTD 직렬화 ---

    def compress_state(self, state: DynamicCharacterState) -> bytes:
        """동적 상태를 ZSTD 압축 JSON blob으로 직렬화한다."""
        json_bytes = state.model_dump_json().encode("utf-8")
        compressed = self._compressor.compress(json_bytes)
        ratio = len(json_bytes) / max(len(compressed), 1)
        logger.debug(
            "상태 압축: %d bytes → %d bytes (%.1fx)",
            len(json_bytes), len(compressed), ratio,
        )
        return compressed

    def decompress_state(self, blob: bytes) -> DynamicCharacterState:
        """ZSTD 압축 JSON blob에서 동적 상태를 복원한다."""
        json_bytes = self._decompressor.decompress(blob)
        data = json.loads(json_bytes.decode("utf-8"))
        return DynamicCharacterState.model_validate(data)

    def build_dynamic_prompt_block(
        self,
        state: DynamicCharacterState,
        character_name: str,
    ) -> str:
        """프롬프트 조립용 동적 상태 블록을 생성한다.

        이 블록은 PromptAssembler v2에서 AI persona 텍스트에 주입된다.

        Args:
            state: 현재 동적 상태.
            character_name: 캐릭터 이름.

        Returns:
            프롬프트에 삽입할 동적 상태 텍스트.
        """
        rs = state.relationship_state
        lines = [
            f"[{character_name} — 현재 동적 상태]",
            f"신뢰: {rs.trust}/100",
            f"친밀도: {rs.familiarity}/100",
            f"감정 의존도: {rs.emotional_reliance}/100",
            f"침묵 편안함: {rs.comfort_with_silence}/100",
            f"먼저 다가가려는 의지: {rs.willingness_to_initiate}/100",
            f"거절 공포: {rs.fear_of_rejection}/100",
            f"경계 민감도: {rs.boundary_sensitivity}/100",
            f"갈등 회복력: {rs.repair_ability}/100",
        ]

        # 주제별 편안함
        if rs.topic_comfort:
            tc_str = ", ".join(f"{k}: {v}/100" for k, v in rs.topic_comfort.items())
            lines.append(f"주제별 편안함: {tc_str}")

        # 현재 감정
        lines.append(f"현재 감정: {state.current_emotional_state}")
        if state.active_defense_strategy:
            lines.append(f"활성 방어전략: {state.active_defense_strategy}")

        # 최근 기억 (최대 5개)
        recent_memories = state.memories[-5:] if state.memories else []
        if recent_memories:
            lines.append("최근 기억:")
            for mem in recent_memories:
                lines.append(f"  - [{mem.trigger_type}] {mem.content}")

        # 최근 이벤트 (최대 3개)
        recent_events = state.events[-3:] if state.events else []
        if recent_events:
            lines.append("최근 이벤트:")
            for evt in recent_events:
                lines.append(f"  - [{evt.event_type}] {evt.description}")

        return "\n".join(lines)
