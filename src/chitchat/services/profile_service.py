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
        """[v1.0.0] UserPersona를 삭제한다.

        채팅 세션이 이 UserPersona를 참조 중이면 삭제를 차단한다.
        """
        # 채팅 세션 참조 검사
        sessions = self._repos.chat_sessions.get_all()
        refs = [s.title for s in sessions if s.user_persona_id == id_]
        if refs:
            msg = f"UserPersona가 {len(refs)}개 세션에서 사용 중: {', '.join(refs[:3])}"
            raise ValueError(msg)
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
        # [v0.2.0] Vibe Fill 확장 필드
        age: str = "",
        gender: str = "",
        appearance: str = "",
        backstory: str = "",
        relationships: str = "",
        skills: str = "",
        interests: str = "",
        weaknesses: str = "",
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
            # [v0.2.0] 확장 필드
            age=age,
            gender=gender,
            appearance=appearance,
            backstory=backstory,
            relationships=relationships,
            skills=skills,
            interests=interests,
            weaknesses=weaknesses,
        )
        saved = self._repos.ai_personas.upsert(row)
        logger.info("AIPersona 저장: %s", saved.name)
        return saved

    def delete_ai_persona(self, id_: str) -> bool:
        """[v1.0.0] AIPersona를 삭제한다.

        ChatProfile이 이 AIPersona를 참조 중이면 삭제를 차단한다.
        """
        # ChatProfile 참조 검사
        profiles = self._repos.chat_profiles.get_all()
        refs = [cp.name for cp in profiles if id_ in json.loads(cp.ai_persona_ids_json)]
        if refs:
            msg = f"AIPersona가 {len(refs)}개 채팅 프로필에서 사용 중: {', '.join(refs[:3])}"
            raise ValueError(msg)
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
        """[v1.0.0] Lorebook을 삭제한다.

        ChatProfile이 이 Lorebook을 참조 중이면 삭제를 차단한다.
        삭제 시 하위 LoreEntry도 함께 삭제된다.
        """
        # ChatProfile 참조 검사
        profiles = self._repos.chat_profiles.get_all()
        refs = [cp.name for cp in profiles if id_ in json.loads(cp.lorebook_ids_json)]
        if refs:
            msg = f"Lorebook이 {len(refs)}개 채팅 프로필에서 사용 중: {', '.join(refs[:3])}"
            raise ValueError(msg)
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
        """[v1.0.0] Worldbook을 삭제한다.

        ChatProfile이 이 Worldbook을 참조 중이면 삭제를 차단한다.
        """
        # ChatProfile 참조 검사
        profiles = self._repos.chat_profiles.get_all()
        refs = [cp.name for cp in profiles if id_ in json.loads(cp.worldbook_ids_json)]
        if refs:
            msg = f"Worldbook이 {len(refs)}개 채팅 프로필에서 사용 중: {', '.join(refs[:3])}"
            raise ValueError(msg)
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
        """[v1.0.0] ModelProfile을 삭제한다.

        ChatProfile이 이 ModelProfile을 참조 중이면 삭제를 차단한다.
        """
        # ChatProfile 참조 검사
        profiles = self._repos.chat_profiles.get_all()
        refs = [cp.name for cp in profiles if cp.model_profile_id == id_]
        if refs:
            msg = f"ModelProfile이 {len(refs)}개 채팅 프로필에서 사용 중: {', '.join(refs[:3])}"
            raise ValueError(msg)
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
        """[v1.0.0] ChatProfile을 삭제한다.

        채팅 세션이 이 ChatProfile을 참조 중이면 삭제를 차단한다.
        """
        # 채팅 세션 참조 검사
        sessions = self._repos.chat_sessions.get_all()
        refs = [s.title for s in sessions if s.chat_profile_id == id_]
        if refs:
            msg = f"ChatProfile이 {len(refs)}개 세션에서 사용 중: {', '.join(refs[:3])}"
            raise ValueError(msg)
        return self._repos.chat_profiles.delete_by_id(id_)

    def update_chat_profile_prompt_order(self, profile_id: str, prompt_order_json: str) -> ChatProfileRow:
        """[v0.1.3] ChatProfile의 prompt_order_json만 갱신한다.

        PromptOrderPage에서 순서 변경 시 호출된다.
        기존 프로필의 다른 필드는 유지하고 prompt_order_json만 교체한다.
        """
        cp = self._repos.chat_profiles.get_by_id(profile_id)
        if not cp:
            msg = f"ChatProfile을 찾을 수 없습니다: {profile_id}"
            raise ValueError(msg)
        cp.prompt_order_json = prompt_order_json
        saved = self._repos.chat_profiles.upsert(cp)
        logger.info("ChatProfile 프롬프트 순서 갱신: %s", saved.name)
        return saved
