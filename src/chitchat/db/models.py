# src/chitchat/db/models.py
# [v1.0.0] SQLAlchemy ORM 모델 정의 (12 테이블)
#
# spec.md §9에서 정의된 DB 스키마를 SQLAlchemy ORM 모델로 구현한다.
# 모든 테이블은 TEXT PK(ULID 기반)를 사용하고, 타임스탬프는 ISO 8601 문자열이다.
# JSON 필드는 TEXT 컬럼에 저장하고, 도메인 레이어에서 Pydantic으로 검증한다.

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    Text,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


def _now_iso() -> str:
    """현재 시각을 ISO 8601 형식의 UTC 문자열로 반환한다."""
    return datetime.now(timezone.utc).isoformat()


class Base(DeclarativeBase):
    """모든 ORM 모델의 기반 클래스."""
    pass


# --- Provider 관련 ---

class ProviderProfileRow(Base):
    """Provider 등록 정보 테이블. spec.md §9.1 provider_profiles."""
    __tablename__ = "provider_profiles"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    provider_kind: Mapped[str] = mapped_column(Text, nullable=False)
    base_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    secret_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=_now_iso)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False, default=_now_iso)

    # 관계: 이 Provider에 연결된 모델 캐시
    model_caches: Mapped[list["ModelCacheRow"]] = relationship(
        back_populates="provider_profile", cascade="all, delete-orphan"
    )


class ModelCacheRow(Base):
    """모델 메타데이터 캐시 테이블. spec.md §9.1 model_cache."""
    __tablename__ = "model_cache"
    __table_args__ = (
        Index("ix_model_cache_provider_model", "provider_profile_id", "model_id", unique=True),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    provider_profile_id: Mapped[str] = mapped_column(
        Text, ForeignKey("provider_profiles.id"), nullable=False
    )
    model_id: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    context_window_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    supported_parameters_json: Mapped[str] = mapped_column(Text, nullable=False)
    supports_streaming: Mapped[int] = mapped_column(Integer, nullable=False)
    supports_system_prompt: Mapped[int] = mapped_column(Integer, nullable=False)
    supports_json_mode: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_json: Mapped[str] = mapped_column(Text, nullable=False)
    fetched_at: Mapped[str] = mapped_column(Text, nullable=False, default=_now_iso)

    # 관계
    provider_profile: Mapped["ProviderProfileRow"] = relationship(back_populates="model_caches")


# --- 모델 프로필 ---

class ModelProfileRow(Base):
    """모델 파라미터 설정 프로필 테이블. spec.md §9.1 model_profiles."""
    __tablename__ = "model_profiles"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    provider_profile_id: Mapped[str] = mapped_column(
        Text, ForeignKey("provider_profiles.id"), nullable=False
    )
    model_id: Mapped[str] = mapped_column(Text, nullable=False)
    settings_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=_now_iso)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False, default=_now_iso)


# --- 페르소나 ---

class UserPersonaRow(Base):
    """사용자 페르소나 테이블. spec.md §9.1 user_personas."""
    __tablename__ = "user_personas"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    speaking_style: Mapped[str] = mapped_column(Text, nullable=False, default="")
    boundaries: Mapped[str] = mapped_column(Text, nullable=False, default="")
    enabled: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class AIPersonaRow(Base):
    """AI 캐릭터 페르소나 테이블. spec.md §9.1 ai_personas.

    [v0.2.0] Vibe Fill을 위한 14개 필드 확장.
    기존 6개 필드(name, role_name, personality, speaking_style, goals, restrictions)에
    8개 필드(age, gender, appearance, backstory, relationships, skills, interests, weaknesses)를 추가.
    """
    __tablename__ = "ai_personas"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    role_name: Mapped[str] = mapped_column(Text, nullable=False)
    personality: Mapped[str] = mapped_column(Text, nullable=False)
    speaking_style: Mapped[str] = mapped_column(Text, nullable=False)
    goals: Mapped[str] = mapped_column(Text, nullable=False, default="")
    restrictions: Mapped[str] = mapped_column(Text, nullable=False, default="")
    enabled: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # [v0.2.0] Vibe Fill 확장 필드 — 모두 optional, 하위 호환성 보장
    age: Mapped[str] = mapped_column(Text, nullable=False, default="")
    gender: Mapped[str] = mapped_column(Text, nullable=False, default="")
    appearance: Mapped[str] = mapped_column(Text, nullable=False, default="")
    backstory: Mapped[str] = mapped_column(Text, nullable=False, default="")
    relationships: Mapped[str] = mapped_column(Text, nullable=False, default="")
    skills: Mapped[str] = mapped_column(Text, nullable=False, default="")
    interests: Mapped[str] = mapped_column(Text, nullable=False, default="")
    weaknesses: Mapped[str] = mapped_column(Text, nullable=False, default="")


# --- 로어북 ---

class LorebookRow(Base):
    """로어북 컨테이너 테이블. spec.md §9.1 lorebooks."""
    __tablename__ = "lorebooks"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=_now_iso)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False, default=_now_iso)

    entries: Mapped[list["LoreEntryRow"]] = relationship(
        back_populates="lorebook", cascade="all, delete-orphan"
    )


class LoreEntryRow(Base):
    """로어 엔트리 테이블. spec.md §9.1 lore_entries."""
    __tablename__ = "lore_entries"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    lorebook_id: Mapped[str] = mapped_column(
        Text, ForeignKey("lorebooks.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    activation_keys_json: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    enabled: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    lorebook: Mapped["LorebookRow"] = relationship(back_populates="entries")


# --- 월드북 ---

class WorldbookRow(Base):
    """월드북 컨테이너 테이블. spec.md §9.1 worldbooks."""
    __tablename__ = "worldbooks"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=_now_iso)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False, default=_now_iso)

    entries: Mapped[list["WorldEntryRow"]] = relationship(
        back_populates="worldbook", cascade="all, delete-orphan"
    )


class WorldEntryRow(Base):
    """월드 엔트리 테이블. spec.md §9.1 world_entries."""
    __tablename__ = "world_entries"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    worldbook_id: Mapped[str] = mapped_column(
        Text, ForeignKey("worldbooks.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    enabled: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    worldbook: Mapped["WorldbookRow"] = relationship(back_populates="entries")


# --- 채팅 프로필 ---

class ChatProfileRow(Base):
    """채팅 프로필 테이블. spec.md §9.1 chat_profiles."""
    __tablename__ = "chat_profiles"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    model_profile_id: Mapped[str] = mapped_column(
        Text, ForeignKey("model_profiles.id"), nullable=False
    )
    ai_persona_ids_json: Mapped[str] = mapped_column(Text, nullable=False)
    lorebook_ids_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    worldbook_ids_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    prompt_order_json: Mapped[str] = mapped_column(Text, nullable=False)
    system_base: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=_now_iso)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False, default=_now_iso)


# --- 채팅 세션 ---

class ChatSessionRow(Base):
    """채팅 세션 테이블. spec.md §9.1 chat_sessions."""
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    chat_profile_id: Mapped[str] = mapped_column(
        Text, ForeignKey("chat_profiles.id"), nullable=False
    )
    user_persona_id: Mapped[str] = mapped_column(
        Text, ForeignKey("user_personas.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, default="draft")
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=_now_iso)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False, default=_now_iso)

    messages: Mapped[list["ChatMessageRow"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class ChatMessageRow(Base):
    """채팅 메시지 테이블. spec.md §9.1 chat_messages."""
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    session_id: Mapped[str] = mapped_column(
        Text, ForeignKey("chat_sessions.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_snapshot_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_estimate: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=_now_iso)

    session: Mapped["ChatSessionRow"] = relationship(back_populates="messages")


# ============================================================
# [v1.0.0] VibeSmith 동적 페르소나 + 동적 상태 테이블
# ============================================================

class PersonaCardRow(Base):
    """VibeSmith 9섹션 페르소나 카드 테이블.

    원본 MD 문서의 메타데이터 + 전체 JSON을 저장한다.
    persona_json에는 PersonaCard 전체가 JSON 문자열로 저장된다.
    원본 MD 문서는 파일시스템(data/personas/)에 별도 저장된다.
    """
    __tablename__ = "persona_cards"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    age: Mapped[str] = mapped_column(Text, nullable=False, default="")
    gender: Mapped[str] = mapped_column(Text, nullable=False, default="")
    occupation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    realism_level: Mapped[str] = mapped_column(Text, nullable=False, default="grounded")
    core_tension: Mapped[str] = mapped_column(Text, nullable=False, default="")
    persona_json: Mapped[str] = mapped_column(Text, nullable=False)
    md_file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=_now_iso)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False, default=_now_iso)

    # 역참조: 이 페르소나의 동적 상태들
    dynamic_states: Mapped[list["DynamicStateRow"]] = relationship(
        back_populates="persona_card", cascade="all, delete-orphan",
    )


class DynamicStateRow(Base):
    """캐릭터 동적 상태 테이블 (ZSTD 압축 JSON blob).

    하나의 PersonaCard + 하나의 ChatSession에 연결된다.
    state_blob에는 DynamicCharacterState 전체가 ZSTD 압축된 바이너리로 저장된다.
    """
    __tablename__ = "dynamic_states"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    character_id: Mapped[str] = mapped_column(
        Text, ForeignKey("persona_cards.id"), nullable=False,
    )
    session_id: Mapped[str] = mapped_column(
        Text, ForeignKey("chat_sessions.id"), nullable=False,
    )
    state_blob: Mapped[bytes] = mapped_column(nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    turn_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False, default=_now_iso)

    # 관계
    persona_card: Mapped["PersonaCardRow"] = relationship(back_populates="dynamic_states")

    __table_args__ = (
        Index("ix_dynamic_states_session", "session_id"),
        Index("ix_dynamic_states_character", "character_id"),
    )


class MemoryRow(Base):
    """기억 테이블.

    DynamicStateRow와 연결되어 캐릭터가 대화에서 형성한 기억을 개별 레코드로 저장한다.
    state_blob 내의 memories 리스트와 동기화된다 (검색/쿼리 최적화용).
    """
    __tablename__ = "memories"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    dynamic_state_id: Mapped[str] = mapped_column(
        Text, ForeignKey("dynamic_states.id"), nullable=False,
    )
    trigger_type: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    emotional_impact: Mapped[str] = mapped_column(Text, nullable=False, default="")
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=_now_iso)

    __table_args__ = (
        Index("ix_memories_state", "dynamic_state_id"),
        Index("ix_memories_trigger", "trigger_type"),
    )

