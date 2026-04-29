# tests/test_repository_crud.py
# [v0.1.0b0] Repository CRUD 테스트
#
# 각 테이블의 insert/get/update/delete를 SQLite in-memory DB에서 검증한다.
# 실제 DB 파일 없이 테스트가 가능하도록 세션 팩토리를 fixture로 제공한다.

from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from chitchat.db.models import (
    AIPersonaRow,
    Base,
    ChatMessageRow,
    ChatSessionRow,
    LoreEntryRow,
    LorebookRow,
    ModelCacheRow,
    ModelProfileRow,
    ProviderProfileRow,
    UserPersonaRow,
    WorldEntryRow,
    WorldbookRow,
    ChatProfileRow,
)
from chitchat.db.repositories import RepositoryRegistry
from chitchat.domain.ids import new_id


@pytest.fixture
def repos() -> RepositoryRegistry:
    """in-memory SQLite에서 테스트용 RepositoryRegistry를 생성한다."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return RepositoryRegistry(factory)


class TestProviderProfileCrud:
    """Provider 프로필 CRUD 검증."""

    def test_insert_and_get(self, repos: RepositoryRegistry) -> None:
        """삽입 후 조회가 되는지 확인한다."""
        row = ProviderProfileRow(
            id=new_id("prov_"),
            name="Gemini Main",
            provider_kind="gemini",
            secret_ref="chitchat:prov_test",
        )
        saved = repos.providers.upsert(row)
        fetched = repos.providers.get_by_id(saved.id)
        assert fetched is not None
        assert fetched.name == "Gemini Main"
        assert fetched.provider_kind == "gemini"

    def test_update(self, repos: RepositoryRegistry) -> None:
        """업데이트가 반영되는지 확인한다."""
        row = ProviderProfileRow(
            id=new_id("prov_"),
            name="Before",
            provider_kind="openrouter",
        )
        saved = repos.providers.upsert(row)
        saved.name = "After"
        repos.providers.upsert(saved)
        fetched = repos.providers.get_by_id(saved.id)
        assert fetched is not None
        assert fetched.name == "After"

    def test_delete(self, repos: RepositoryRegistry) -> None:
        """삭제가 되는지 확인한다."""
        row = ProviderProfileRow(
            id=new_id("prov_"),
            name="To Delete",
            provider_kind="lm_studio",
        )
        saved = repos.providers.upsert(row)
        assert repos.providers.delete_by_id(saved.id) is True
        assert repos.providers.get_by_id(saved.id) is None

    def test_delete_nonexistent_returns_false(self, repos: RepositoryRegistry) -> None:
        """존재하지 않는 ID 삭제 시 False를 반환한다."""
        assert repos.providers.delete_by_id("prov_nonexist") is False

    def test_get_all(self, repos: RepositoryRegistry) -> None:
        """get_all이 이름순으로 정렬된 목록을 반환하는지 확인한다."""
        for name in ["Zebra", "Alpha", "Middle"]:
            repos.providers.upsert(ProviderProfileRow(
                id=new_id("prov_"),
                name=name,
                provider_kind="gemini",
            ))
        all_rows = repos.providers.get_all()
        names = [r.name for r in all_rows]
        assert names == ["Alpha", "Middle", "Zebra"]


class TestUserPersonaCrud:
    """사용자 페르소나 CRUD 검증."""

    def test_insert_and_get(self, repos: RepositoryRegistry) -> None:
        row = UserPersonaRow(
            id=new_id("up_"),
            name="테스트 사용자",
            description="테스트 설명",
        )
        saved = repos.user_personas.upsert(row)
        fetched = repos.user_personas.get_by_id(saved.id)
        assert fetched is not None
        assert fetched.name == "테스트 사용자"

    def test_delete(self, repos: RepositoryRegistry) -> None:
        row = UserPersonaRow(
            id=new_id("up_"),
            name="삭제 대상",
            description="설명",
        )
        saved = repos.user_personas.upsert(row)
        assert repos.user_personas.delete_by_id(saved.id) is True
        assert repos.user_personas.get_by_id(saved.id) is None


class TestAIPersonaCrud:
    """AI 페르소나 CRUD 검증."""

    def test_insert_and_get(self, repos: RepositoryRegistry) -> None:
        row = AIPersonaRow(
            id=new_id("ai_"),
            name="미라",
            role_name="고서관 관리자 미라",
            personality="신비롭고 지적인",
            speaking_style="~해요체",
        )
        saved = repos.ai_personas.upsert(row)
        fetched = repos.ai_personas.get_by_id(saved.id)
        assert fetched is not None
        assert fetched.role_name == "고서관 관리자 미라"


class TestLorebookCrud:
    """로어북 CRUD 검증."""

    def test_lorebook_with_entries(self, repos: RepositoryRegistry) -> None:
        """로어북과 엔트리가 함께 저장되는지 확인한다."""
        lb = LorebookRow(
            id=new_id("lb_"),
            name="테스트 로어북",
        )
        repos.lorebooks.upsert(lb)

        entry = LoreEntryRow(
            id=new_id("le_"),
            lorebook_id=lb.id,
            title="고대 유물",
            activation_keys_json=json.dumps(["유물", "artifact"]),
            content="고대 유물에 대한 설명...",
        )
        repos.lore_entries.upsert(entry)

        entries = repos.lore_entries.get_by_lorebook(lb.id)
        assert len(entries) == 1
        assert entries[0].title == "고대 유물"


class TestWorldbookCrud:
    """월드북 CRUD 검증."""

    def test_worldbook_with_entries(self, repos: RepositoryRegistry) -> None:
        wb = WorldbookRow(
            id=new_id("wb_"),
            name="판타지 세계",
        )
        repos.worldbooks.upsert(wb)

        entry = WorldEntryRow(
            id=new_id("we_"),
            worldbook_id=wb.id,
            title="마법 체계",
            content="이 세계의 마법은...",
        )
        repos.world_entries.upsert(entry)

        entries = repos.world_entries.get_by_worldbook(wb.id)
        assert len(entries) == 1
        assert entries[0].title == "마법 체계"


class TestModelCacheCrud:
    """모델 캐시 CRUD 검증."""

    def test_insert_and_get_by_provider(self, repos: RepositoryRegistry) -> None:
        """Provider별 모델 캐시 조회를 확인한다."""
        prov = ProviderProfileRow(
            id=new_id("prov_"),
            name="Test Provider",
            provider_kind="gemini",
        )
        repos.providers.upsert(prov)

        cache = ModelCacheRow(
            id=new_id("mc_"),
            provider_profile_id=prov.id,
            model_id="gemini-2.5-flash",
            display_name="Gemini 2.5 Flash",
            context_window_tokens=1048576,
            max_output_tokens=65536,
            supported_parameters_json=json.dumps(["temperature", "top_p", "top_k"]),
            supports_streaming=1,
            supports_system_prompt=1,
            supports_json_mode=1,
            raw_json="{}",
        )
        repos.model_cache.upsert(cache)

        caches = repos.model_cache.get_by_provider(prov.id)
        assert len(caches) == 1
        assert caches[0].model_id == "gemini-2.5-flash"


class TestChatMessageCrud:
    """채팅 메시지 CRUD 검증."""

    def test_messages_ordered_by_creation(self, repos: RepositoryRegistry) -> None:
        """메시지가 생성 순서로 반환되는지 확인한다."""
        # 사전 조건: Provider → ModelProfile → ChatProfile → UserPersona → Session
        prov = ProviderProfileRow(
            id=new_id("prov_"), name="P", provider_kind="gemini",
        )
        repos.providers.upsert(prov)

        mp = ModelProfileRow(
            id=new_id("mp_"), name="MP", provider_profile_id=prov.id,
            model_id="m1", settings_json="{}",
        )
        repos.model_profiles.upsert(mp)

        up = UserPersonaRow(
            id=new_id("up_"), name="UP", description="D",
        )
        repos.user_personas.upsert(up)

        cp = ChatProfileRow(
            id=new_id("cp_"), name="CP", model_profile_id=mp.id,
            ai_persona_ids_json='["ai_1"]',
            prompt_order_json='[]',
            system_base="system",
        )
        repos.chat_profiles.upsert(cp)

        session = ChatSessionRow(
            id=new_id("cs_"), title="Test Session",
            chat_profile_id=cp.id, user_persona_id=up.id,
            status="active",
        )
        repos.chat_sessions.upsert(session)

        # 메시지 삽입
        for i, (role, content) in enumerate([
            ("user", "안녕하세요"),
            ("assistant", "안녕하세요! 도와드릴까요?"),
            ("user", "날씨 알려줘"),
        ]):
            msg = ChatMessageRow(
                id=new_id("cm_"),
                session_id=session.id,
                role=role,
                content=content,
                token_estimate=len(content) // 4,
            )
            repos.chat_messages.insert(msg)

        messages = repos.chat_messages.get_by_session(session.id)
        assert len(messages) == 3
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"
        assert messages[2].content == "날씨 알려줘"
