# src/chitchat/db/repositories.py
# [v1.0.0] Repository 패턴 구현 및 RepositoryRegistry
#
# 각 테이블에 대한 CRUD를 Repository 클래스로 캡슐화한다.
# RepositoryRegistry는 모든 Repository 인스턴스를 관리하는 단일 진입점이다.
# Service 계층은 RepositoryRegistry를 통해 데이터에 접근한다.

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from chitchat.db.models import (
    AIPersonaRow,
    Base,
    ChatMessageRow,
    ChatProfileRow,
    ChatSessionRow,
    DynamicStateRow,
    LoreEntryRow,
    LorebookRow,
    ModelCacheRow,
    ModelProfileRow,
    PersonaCardRow,
    ProviderProfileRow,
    UserPersonaRow,
    WorldbookRow,
    WorldEntryRow,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=Base)


class BaseRepository:
    """모든 Repository의 기반 클래스.

    세션 팩토리를 주입받아 CRUD 작업을 수행한다.
    각 메서드는 자체 세션을 열고 닫는다 (단위 작업 패턴).
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def _get_session(self) -> Session:
        """새 세션을 생성한다."""
        return self._session_factory()


class ProviderProfileRepository(BaseRepository):
    """Provider 프로필 Repository."""

    def get_all(self) -> list[ProviderProfileRow]:
        """모든 Provider 프로필을 반환한다."""
        with self._get_session() as session:
            stmt = select(ProviderProfileRow).order_by(ProviderProfileRow.name)
            return list(session.execute(stmt).scalars().all())

    def get_by_id(self, id_: str) -> ProviderProfileRow | None:
        """ID로 Provider 프로필을 조회한다."""
        with self._get_session() as session:
            return session.get(ProviderProfileRow, id_)

    def upsert(self, row: ProviderProfileRow) -> ProviderProfileRow:
        """Provider 프로필을 삽입하거나 업데이트한다."""
        with self._get_session() as session:
            row.updated_at = datetime.now(timezone.utc).isoformat()
            merged = session.merge(row)
            session.commit()
            session.refresh(merged)
            return merged

    def delete_by_id(self, id_: str) -> bool:
        """ID로 Provider 프로필을 삭제한다. 삭제 성공 시 True."""
        with self._get_session() as session:
            row = session.get(ProviderProfileRow, id_)
            if row is None:
                return False
            session.delete(row)
            session.commit()
            return True


class ModelCacheRepository(BaseRepository):
    """모델 캐시 Repository."""

    def get_by_provider(self, provider_profile_id: str) -> list[ModelCacheRow]:
        """특정 Provider의 모든 모델 캐시를 반환한다."""
        with self._get_session() as session:
            stmt = (
                select(ModelCacheRow)
                .where(ModelCacheRow.provider_profile_id == provider_profile_id)
                .order_by(ModelCacheRow.display_name)
            )
            return list(session.execute(stmt).scalars().all())

    def upsert(self, row: ModelCacheRow) -> ModelCacheRow:
        """모델 캐시를 삽입하거나 업데이트한다."""
        with self._get_session() as session:
            merged = session.merge(row)
            session.commit()
            session.refresh(merged)
            return merged

    def delete_by_provider(self, provider_profile_id: str) -> int:
        """특정 Provider의 모든 모델 캐시를 삭제한다. 삭제된 행 수를 반환한다."""
        with self._get_session() as session:
            rows = (
                session.execute(
                    select(ModelCacheRow)
                    .where(ModelCacheRow.provider_profile_id == provider_profile_id)
                )
                .scalars()
                .all()
            )
            count = len(rows)
            for row in rows:
                session.delete(row)
            session.commit()
            return count


class ModelProfileRepository(BaseRepository):
    """모델 프로필 Repository."""

    def get_all(self) -> list[ModelProfileRow]:
        with self._get_session() as session:
            stmt = select(ModelProfileRow).order_by(ModelProfileRow.name)
            return list(session.execute(stmt).scalars().all())

    def get_by_id(self, id_: str) -> ModelProfileRow | None:
        with self._get_session() as session:
            return session.get(ModelProfileRow, id_)

    def upsert(self, row: ModelProfileRow) -> ModelProfileRow:
        with self._get_session() as session:
            row.updated_at = datetime.now(timezone.utc).isoformat()
            merged = session.merge(row)
            session.commit()
            session.refresh(merged)
            return merged

    def delete_by_id(self, id_: str) -> bool:
        with self._get_session() as session:
            row = session.get(ModelProfileRow, id_)
            if row is None:
                return False
            session.delete(row)
            session.commit()
            return True


class UserPersonaRepository(BaseRepository):
    """사용자 페르소나 Repository."""

    def get_all(self) -> list[UserPersonaRow]:
        with self._get_session() as session:
            stmt = select(UserPersonaRow).order_by(UserPersonaRow.name)
            return list(session.execute(stmt).scalars().all())

    def get_by_id(self, id_: str) -> UserPersonaRow | None:
        with self._get_session() as session:
            return session.get(UserPersonaRow, id_)

    def upsert(self, row: UserPersonaRow) -> UserPersonaRow:
        with self._get_session() as session:
            merged = session.merge(row)
            session.commit()
            session.refresh(merged)
            return merged

    def delete_by_id(self, id_: str) -> bool:
        with self._get_session() as session:
            row = session.get(UserPersonaRow, id_)
            if row is None:
                return False
            session.delete(row)
            session.commit()
            return True


class AIPersonaRepository(BaseRepository):
    """AI 페르소나 Repository."""

    def get_all(self) -> list[AIPersonaRow]:
        with self._get_session() as session:
            stmt = select(AIPersonaRow).order_by(AIPersonaRow.name)
            return list(session.execute(stmt).scalars().all())

    def get_by_id(self, id_: str) -> AIPersonaRow | None:
        with self._get_session() as session:
            return session.get(AIPersonaRow, id_)

    def upsert(self, row: AIPersonaRow) -> AIPersonaRow:
        with self._get_session() as session:
            merged = session.merge(row)
            session.commit()
            session.refresh(merged)
            return merged

    def delete_by_id(self, id_: str) -> bool:
        with self._get_session() as session:
            row = session.get(AIPersonaRow, id_)
            if row is None:
                return False
            session.delete(row)
            session.commit()
            return True


class LorebookRepository(BaseRepository):
    """로어북 Repository."""

    def get_all(self) -> list[LorebookRow]:
        with self._get_session() as session:
            stmt = select(LorebookRow).order_by(LorebookRow.name)
            return list(session.execute(stmt).scalars().all())

    def get_by_id(self, id_: str) -> LorebookRow | None:
        with self._get_session() as session:
            return session.get(LorebookRow, id_)

    def upsert(self, row: LorebookRow) -> LorebookRow:
        with self._get_session() as session:
            row.updated_at = datetime.now(timezone.utc).isoformat()
            merged = session.merge(row)
            session.commit()
            session.refresh(merged)
            return merged

    def delete_by_id(self, id_: str) -> bool:
        with self._get_session() as session:
            row = session.get(LorebookRow, id_)
            if row is None:
                return False
            session.delete(row)
            session.commit()
            return True


class LoreEntryRepository(BaseRepository):
    """로어 엔트리 Repository."""

    def get_by_lorebook(self, lorebook_id: str) -> list[LoreEntryRow]:
        with self._get_session() as session:
            stmt = (
                select(LoreEntryRow)
                .where(LoreEntryRow.lorebook_id == lorebook_id)
                .order_by(LoreEntryRow.priority.desc(), LoreEntryRow.title)
            )
            return list(session.execute(stmt).scalars().all())

    def get_by_id(self, id_: str) -> LoreEntryRow | None:
        """ID로 로어 엔트리를 조회한다."""
        with self._get_session() as session:
            return session.get(LoreEntryRow, id_)

    def upsert(self, row: LoreEntryRow) -> LoreEntryRow:
        with self._get_session() as session:
            merged = session.merge(row)
            session.commit()
            session.refresh(merged)
            return merged

    def delete_by_id(self, id_: str) -> bool:
        with self._get_session() as session:
            row = session.get(LoreEntryRow, id_)
            if row is None:
                return False
            session.delete(row)
            session.commit()
            return True


class WorldbookRepository(BaseRepository):
    """월드북 Repository."""

    def get_all(self) -> list[WorldbookRow]:
        with self._get_session() as session:
            stmt = select(WorldbookRow).order_by(WorldbookRow.name)
            return list(session.execute(stmt).scalars().all())

    def get_by_id(self, id_: str) -> WorldbookRow | None:
        with self._get_session() as session:
            return session.get(WorldbookRow, id_)

    def upsert(self, row: WorldbookRow) -> WorldbookRow:
        with self._get_session() as session:
            row.updated_at = datetime.now(timezone.utc).isoformat()
            merged = session.merge(row)
            session.commit()
            session.refresh(merged)
            return merged

    def delete_by_id(self, id_: str) -> bool:
        with self._get_session() as session:
            row = session.get(WorldbookRow, id_)
            if row is None:
                return False
            session.delete(row)
            session.commit()
            return True


class WorldEntryRepository(BaseRepository):
    """월드 엔트리 Repository."""

    def get_by_worldbook(self, worldbook_id: str) -> list[WorldEntryRow]:
        with self._get_session() as session:
            stmt = (
                select(WorldEntryRow)
                .where(WorldEntryRow.worldbook_id == worldbook_id)
                .order_by(WorldEntryRow.priority.desc(), WorldEntryRow.title)
            )
            return list(session.execute(stmt).scalars().all())

    def get_by_id(self, id_: str) -> WorldEntryRow | None:
        """ID로 월드 엔트리를 조회한다."""
        with self._get_session() as session:
            return session.get(WorldEntryRow, id_)

    def upsert(self, row: WorldEntryRow) -> WorldEntryRow:
        with self._get_session() as session:
            merged = session.merge(row)
            session.commit()
            session.refresh(merged)
            return merged

    def delete_by_id(self, id_: str) -> bool:
        with self._get_session() as session:
            row = session.get(WorldEntryRow, id_)
            if row is None:
                return False
            session.delete(row)
            session.commit()
            return True


class ChatProfileRepository(BaseRepository):
    """채팅 프로필 Repository."""

    def get_all(self) -> list[ChatProfileRow]:
        with self._get_session() as session:
            stmt = select(ChatProfileRow).order_by(ChatProfileRow.name)
            return list(session.execute(stmt).scalars().all())

    def get_by_id(self, id_: str) -> ChatProfileRow | None:
        with self._get_session() as session:
            return session.get(ChatProfileRow, id_)

    def upsert(self, row: ChatProfileRow) -> ChatProfileRow:
        with self._get_session() as session:
            row.updated_at = datetime.now(timezone.utc).isoformat()
            merged = session.merge(row)
            session.commit()
            session.refresh(merged)
            return merged

    def delete_by_id(self, id_: str) -> bool:
        with self._get_session() as session:
            row = session.get(ChatProfileRow, id_)
            if row is None:
                return False
            session.delete(row)
            session.commit()
            return True


class ChatSessionRepository(BaseRepository):
    """채팅 세션 Repository."""

    def get_all(self) -> list[ChatSessionRow]:
        with self._get_session() as session:
            stmt = select(ChatSessionRow).order_by(ChatSessionRow.created_at.desc())
            return list(session.execute(stmt).scalars().all())

    def get_by_id(self, id_: str) -> ChatSessionRow | None:
        with self._get_session() as session:
            return session.get(ChatSessionRow, id_)

    def upsert(self, row: ChatSessionRow) -> ChatSessionRow:
        with self._get_session() as session:
            row.updated_at = datetime.now(timezone.utc).isoformat()
            merged = session.merge(row)
            session.commit()
            session.refresh(merged)
            return merged

    def delete_by_id(self, id_: str) -> bool:
        """[v0.1.2] ID로 채팅 세션을 삭제한다."""
        with self._get_session() as session:
            row = session.get(ChatSessionRow, id_)
            if row is None:
                return False
            session.delete(row)
            session.commit()
            return True


class ChatMessageRepository(BaseRepository):
    """채팅 메시지 Repository."""

    def get_by_session(self, session_id: str) -> list[ChatMessageRow]:
        """세션의 모든 메시지를 생성 순서로 반환한다."""
        with self._get_session() as session:
            stmt = (
                select(ChatMessageRow)
                .where(ChatMessageRow.session_id == session_id)
                .order_by(ChatMessageRow.created_at)
            )
            return list(session.execute(stmt).scalars().all())

    def insert(self, row: ChatMessageRow) -> ChatMessageRow:
        """메시지를 삽입한다. 메시지는 수정 불가이므로 insert만 제공한다."""
        with self._get_session() as session:
            session.add(row)
            session.commit()
            session.refresh(row)
            return row

    def delete_by_session(self, session_id: str) -> int:
        """[v0.1.2] 특정 세션의 모든 메시지를 삭제한다. 삭제된 행 수를 반환한다."""
        with self._get_session() as session:
            rows = (
                session.execute(
                    select(ChatMessageRow)
                    .where(ChatMessageRow.session_id == session_id)
                )
                .scalars()
                .all()
            )
            count = len(rows)
            for row in rows:
                session.delete(row)
            session.commit()
            return count


# [v1.0.0] VibeSmith 페르소나 카드 Repository
class PersonaCardRepository(BaseRepository):
    """PersonaCard CRUD Repository.

    9섹션 VibeSmith 페르소나 카드를 관리한다.
    persona_json에 전체 PersonaCard JSON이 저장된다.
    """

    def get_all(self) -> list[PersonaCardRow]:
        """모든 페르소나 카드를 반환한다."""
        with self._get_session() as session:
            stmt = select(PersonaCardRow).order_by(PersonaCardRow.name)
            return list(session.execute(stmt).scalars().all())

    def get_by_id(self, id_: str) -> PersonaCardRow | None:
        """ID로 페르소나 카드를 조회한다."""
        with self._get_session() as session:
            return session.get(PersonaCardRow, id_)

    def upsert(self, row: PersonaCardRow) -> PersonaCardRow:
        """페르소나 카드를 삽입하거나 업데이트한다."""
        with self._get_session() as session:
            row.updated_at = datetime.now(timezone.utc).isoformat()
            merged = session.merge(row)
            session.commit()
            session.refresh(merged)
            return merged

    def delete_by_id(self, id_: str) -> bool:
        """ID로 페르소나 카드를 삭제한다."""
        with self._get_session() as session:
            row = session.get(PersonaCardRow, id_)
            if row is None:
                return False
            session.delete(row)
            session.commit()
            return True


class RepositoryRegistry:
    """모든 Repository 인스턴스를 관리하는 단일 진입점.

    Service 계층은 이 레지스트리를 통해 데이터에 접근한다.
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.providers = ProviderProfileRepository(session_factory)
        self.model_cache = ModelCacheRepository(session_factory)
        self.model_profiles = ModelProfileRepository(session_factory)
        self.user_personas = UserPersonaRepository(session_factory)
        self.ai_personas = AIPersonaRepository(session_factory)
        self.lorebooks = LorebookRepository(session_factory)
        self.lore_entries = LoreEntryRepository(session_factory)
        self.worldbooks = WorldbookRepository(session_factory)
        self.world_entries = WorldEntryRepository(session_factory)
        self.chat_profiles = ChatProfileRepository(session_factory)
        self.chat_sessions = ChatSessionRepository(session_factory)
        self.chat_messages = ChatMessageRepository(session_factory)
        # [v1.0.0] VibeSmith 페르소나 카드
        self.persona_cards = PersonaCardRepository(session_factory)
        # [v1.0.0] 동적 상태 (ZSTD 압축 blob)
        self.dynamic_states = DynamicStateRepository(session_factory)


class DynamicStateRepository:
    """DynamicStateRow CRUD — ZSTD 압축 blob 기반 동적 상태 영속화.

    character_id + session_id 조합으로 고유한 상태를 관리한다.
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sf = session_factory

    def _get_session(self) -> Session:
        return self._sf()

    def get_by_session(self, session_id: str) -> DynamicStateRow | None:
        """세션 ID로 동적 상태를 조회한다."""
        with self._get_session() as session:
            stmt = select(DynamicStateRow).where(
                DynamicStateRow.session_id == session_id,
            )
            return session.execute(stmt).scalars().first()

    def get_by_character_session(
        self, character_id: str, session_id: str,
    ) -> DynamicStateRow | None:
        """캐릭터 + 세션 조합으로 동적 상태를 조회한다."""
        with self._get_session() as session:
            stmt = select(DynamicStateRow).where(
                DynamicStateRow.character_id == character_id,
                DynamicStateRow.session_id == session_id,
            )
            return session.execute(stmt).scalars().first()

    def upsert(self, row: DynamicStateRow) -> DynamicStateRow:
        """동적 상태를 삽입하거나 업데이트한다."""
        with self._get_session() as session:
            row.updated_at = datetime.now(timezone.utc).isoformat()
            merged = session.merge(row)
            session.commit()
            session.refresh(merged)
            return merged

    def delete_by_id(self, id_: str) -> bool:
        """ID로 동적 상태를 삭제한다."""
        with self._get_session() as session:
            row = session.get(DynamicStateRow, id_)
            if row is None:
                return False
            session.delete(row)
            session.commit()
            return True
