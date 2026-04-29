# src/chitchat/services/profile_service.py
# [v0.1.0b0] 프로필 CRUD 서비스 (UserPersona, AIPersona, Lorebook, Worldbook, ChatProfile)
#
# UI/ViewModel은 이 서비스만 호출하고, 직접 Repository를 사용하지 않는다.
# 각 엔티티의 CRUD와 Pydantic 검증을 오케스트레이션한다.

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from chitchat.db.models import (
    AIPersonaRow,
    ChatProfileRow,
    LoreEntryRow,
    LorebookRow,
    ModelProfileRow,
    UserPersonaRow,
    WorldbookRow,
    WorldEntryRow,
)
from chitchat.db.repositories import RepositoryRegistry
from chitchat.domain.ids import new_id

logger = logging.getLogger(__name__)


class ProfileService:
    """프로필 CRUD 서비스.

    UserPersona, AIPersona, Lorebook, Worldbook, ChatProfile, ModelProfile의
    CRUD를 오케스트레이션한다.
    """

    def __init__(self, repos: RepositoryRegistry) -> None:
        self._repos = repos

    # --- UserPersona ---

    def get_all_user_personas(self) -> list[UserPersonaRow]:
        return self._repos.user_personas.get_all()

    def get_user_persona(self, id_: str) -> UserPersonaRow | None:
        return self._repos.user_personas.get_by_id(id_)

    def save_user_persona(
        self,
        name: str,
        description: str,
        speaking_style: str = "",
        boundaries: str = "",
        enabled: bool = True,
        existing_id: str | None = None,
    ) -> UserPersonaRow:
        row = UserPersonaRow(
            id=existing_id or new_id("up_"),
            name=name,
            description=description,
            speaking_style=speaking_style,
            boundaries=boundaries,
            enabled=int(enabled),
        )
        saved = self._repos.user_personas.upsert(row)
        logger.info("UserPersona 저장: %s", saved.name)
        return saved

    def delete_user_persona(self, id_: str) -> bool:
        return self._repos.user_personas.delete_by_id(id_)

    # --- AIPersona ---

    def get_all_ai_personas(self) -> list[AIPersonaRow]:
        return self._repos.ai_personas.get_all()

    def get_ai_persona(self, id_: str) -> AIPersonaRow | None:
        return self._repos.ai_personas.get_by_id(id_)

    def save_ai_persona(
        self,
        name: str,
        role_name: str,
        personality: str,
        speaking_style: str,
        goals: str = "",
        restrictions: str = "",
        enabled: bool = True,
        existing_id: str | None = None,
    ) -> AIPersonaRow:
        row = AIPersonaRow(
            id=existing_id or new_id("ai_"),
            name=name,
            role_name=role_name,
            personality=personality,
            speaking_style=speaking_style,
            goals=goals,
            restrictions=restrictions,
            enabled=int(enabled),
        )
        saved = self._repos.ai_personas.upsert(row)
        logger.info("AIPersona 저장: %s", saved.name)
        return saved

    def delete_ai_persona(self, id_: str) -> bool:
        return self._repos.ai_personas.delete_by_id(id_)

    # --- Lorebook ---

    def get_all_lorebooks(self) -> list[LorebookRow]:
        return self._repos.lorebooks.get_all()

    def get_lorebook(self, id_: str) -> LorebookRow | None:
        return self._repos.lorebooks.get_by_id(id_)

    def save_lorebook(
        self,
        name: str,
        description: str = "",
        existing_id: str | None = None,
    ) -> LorebookRow:
        row = LorebookRow(
            id=existing_id or new_id("lb_"),
            name=name,
            description=description,
        )
        saved = self._repos.lorebooks.upsert(row)
        logger.info("Lorebook 저장: %s", saved.name)
        return saved

    def delete_lorebook(self, id_: str) -> bool:
        return self._repos.lorebooks.delete_by_id(id_)

    def get_lore_entries(self, lorebook_id: str) -> list[LoreEntryRow]:
        return self._repos.lore_entries.get_by_lorebook(lorebook_id)

    def save_lore_entry(
        self,
        lorebook_id: str,
        title: str,
        activation_keys: list[str],
        content: str,
        priority: int = 100,
        enabled: bool = True,
        existing_id: str | None = None,
    ) -> LoreEntryRow:
        row = LoreEntryRow(
            id=existing_id or new_id("le_"),
            lorebook_id=lorebook_id,
            title=title,
            activation_keys_json=json.dumps(activation_keys, ensure_ascii=False),
            content=content,
            priority=priority,
            enabled=int(enabled),
        )
        saved = self._repos.lore_entries.upsert(row)
        logger.info("LoreEntry 저장: %s", saved.title)
        return saved

    def delete_lore_entry(self, id_: str) -> bool:
        return self._repos.lore_entries.delete_by_id(id_)

    # --- Worldbook ---

    def get_all_worldbooks(self) -> list[WorldbookRow]:
        return self._repos.worldbooks.get_all()

    def get_worldbook(self, id_: str) -> WorldbookRow | None:
        return self._repos.worldbooks.get_by_id(id_)

    def save_worldbook(
        self,
        name: str,
        description: str = "",
        existing_id: str | None = None,
    ) -> WorldbookRow:
        row = WorldbookRow(
            id=existing_id or new_id("wb_"),
            name=name,
            description=description,
        )
        saved = self._repos.worldbooks.upsert(row)
        logger.info("Worldbook 저장: %s", saved.name)
        return saved

    def delete_worldbook(self, id_: str) -> bool:
        return self._repos.worldbooks.delete_by_id(id_)

    def get_world_entries(self, worldbook_id: str) -> list[WorldEntryRow]:
        return self._repos.world_entries.get_by_worldbook(worldbook_id)

    def save_world_entry(
        self,
        worldbook_id: str,
        title: str,
        content: str,
        priority: int = 100,
        enabled: bool = True,
        existing_id: str | None = None,
    ) -> WorldEntryRow:
        row = WorldEntryRow(
            id=existing_id or new_id("we_"),
            worldbook_id=worldbook_id,
            title=title,
            content=content,
            priority=priority,
            enabled=int(enabled),
        )
        saved = self._repos.world_entries.upsert(row)
        logger.info("WorldEntry 저장: %s", saved.title)
        return saved

    def delete_world_entry(self, id_: str) -> bool:
        return self._repos.world_entries.delete_by_id(id_)

    # --- ModelProfile ---

    def get_all_model_profiles(self) -> list[ModelProfileRow]:
        return self._repos.model_profiles.get_all()

    def get_model_profile(self, id_: str) -> ModelProfileRow | None:
        return self._repos.model_profiles.get_by_id(id_)

    def save_model_profile(
        self,
        name: str,
        provider_profile_id: str,
        model_id: str,
        settings_json: str,
        existing_id: str | None = None,
    ) -> ModelProfileRow:
        now = datetime.now(timezone.utc).isoformat()
        row = ModelProfileRow(
            id=existing_id or new_id("mp_"),
            name=name,
            provider_profile_id=provider_profile_id,
            model_id=model_id,
            settings_json=settings_json,
            created_at=now,
            updated_at=now,
        )
        saved = self._repos.model_profiles.upsert(row)
        logger.info("ModelProfile 저장: %s", saved.name)
        return saved

    def delete_model_profile(self, id_: str) -> bool:
        return self._repos.model_profiles.delete_by_id(id_)

    # --- ChatProfile ---

    def get_all_chat_profiles(self) -> list[ChatProfileRow]:
        return self._repos.chat_profiles.get_all()

    def get_chat_profile(self, id_: str) -> ChatProfileRow | None:
        return self._repos.chat_profiles.get_by_id(id_)

    def save_chat_profile(
        self,
        name: str,
        model_profile_id: str,
        ai_persona_ids: list[str],
        lorebook_ids: list[str],
        worldbook_ids: list[str],
        prompt_order_json: str,
        system_base: str,
        existing_id: str | None = None,
    ) -> ChatProfileRow:
        now = datetime.now(timezone.utc).isoformat()
        row = ChatProfileRow(
            id=existing_id or new_id("cp_"),
            name=name,
            model_profile_id=model_profile_id,
            ai_persona_ids_json=json.dumps(ai_persona_ids),
            lorebook_ids_json=json.dumps(lorebook_ids),
            worldbook_ids_json=json.dumps(worldbook_ids),
            prompt_order_json=prompt_order_json,
            system_base=system_base,
            created_at=now,
            updated_at=now,
        )
        saved = self._repos.chat_profiles.upsert(row)
        logger.info("ChatProfile 저장: %s", saved.name)
        return saved

    def delete_chat_profile(self, id_: str) -> bool:
        return self._repos.chat_profiles.delete_by_id(id_)
