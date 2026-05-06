# tests/test_profile_crud_service.py
# [v0.1.0b0] ProfileService CRUD 통합 테스트
#
# [v1.0.0] 참조 무결성 검증 테스트 추가
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from chitchat.db.models import Base
from chitchat.db.repositories import RepositoryRegistry
from chitchat.services.profile_service import ProfileService


def _make_service() -> ProfileService:
    """in-memory DB로 ProfileService를 생성한다."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    sf = sessionmaker(bind=engine)
    repos = RepositoryRegistry(sf)
    return ProfileService(repos)


class TestUserPersonaCrud:
    def test_create_get_delete(self) -> None:
        svc = _make_service()
        p = svc.save_user_persona(name="테스트유저", description="설명")
        assert p.name == "테스트유저"
        assert svc.get_user_persona(p.id) is not None
        assert svc.delete_user_persona(p.id) is True
        assert svc.get_user_persona(p.id) is None

    def test_update(self) -> None:
        svc = _make_service()
        p = svc.save_user_persona(name="원본", description="원본설명")
        updated = svc.save_user_persona(name="수정됨", description="수정설명", existing_id=p.id)
        assert updated.name == "수정됨"
        assert updated.id == p.id

    def test_list_all(self) -> None:
        svc = _make_service()
        svc.save_user_persona(name="A", description="a")
        svc.save_user_persona(name="B", description="b")
        assert len(svc.get_all_user_personas()) == 2


class TestAIPersonaCrud:
    def test_create_and_get(self) -> None:
        svc = _make_service()
        p = svc.save_ai_persona(name="미라", role_name="관리자", personality="친절", speaking_style="존댓말")
        assert p.role_name == "관리자"
        loaded = svc.get_ai_persona(p.id)
        assert loaded is not None
        assert loaded.personality == "친절"

    def test_delete(self) -> None:
        svc = _make_service()
        p = svc.save_ai_persona(name="X", role_name="R", personality="P", speaking_style="S")
        assert svc.delete_ai_persona(p.id) is True


class TestLorebookCrud:
    def test_book_and_entries(self) -> None:
        svc = _make_service()
        lb = svc.save_lorebook(name="테스트북")
        assert lb.name == "테스트북"
        e1 = svc.save_lore_entry(lb.id, "유물", ["유물", "artifact"], "고대 유물")
        svc.save_lore_entry(lb.id, "마법", ["마법", "magic"], "마법 설명")
        entries = svc.get_lore_entries(lb.id)
        assert len(entries) == 2
        assert svc.delete_lore_entry(e1.id) is True
        assert len(svc.get_lore_entries(lb.id)) == 1

    def test_delete_book(self) -> None:
        svc = _make_service()
        lb = svc.save_lorebook(name="삭제대상")
        assert svc.delete_lorebook(lb.id) is True


class TestWorldbookCrud:
    def test_book_and_entries(self) -> None:
        svc = _make_service()
        wb = svc.save_worldbook(name="판타지세계")
        e = svc.save_world_entry(wb.id, "대륙", "거대한 대륙", priority=50)
        assert e.priority == 50
        assert len(svc.get_world_entries(wb.id)) == 1

    def test_delete_entry(self) -> None:
        svc = _make_service()
        wb = svc.save_worldbook(name="W")
        e = svc.save_world_entry(wb.id, "T", "C")
        assert svc.delete_world_entry(e.id) is True


class TestModelProfileCrud:
    def test_create_and_get(self) -> None:
        svc = _make_service()
        mp = svc.save_model_profile(name="Flash", provider_profile_id="prov_1",
            model_id="gemini-2.5-flash", settings_json='{"temperature": 0.7}')
        assert mp.model_id == "gemini-2.5-flash"
        loaded = svc.get_model_profile(mp.id)
        assert loaded is not None
        assert loaded.settings_json == '{"temperature": 0.7}'


class TestChatProfileCrud:
    def test_create_and_get(self) -> None:
        svc = _make_service()
        cp = svc.save_chat_profile(name="기본프로필", model_profile_id="mp_1",
            ai_persona_ids=["ai_1"], lorebook_ids=["lb_1"], worldbook_ids=[],
            prompt_order_json='[]', system_base="시스템 메시지")
        assert cp.name == "기본프로필"
        loaded = svc.get_chat_profile(cp.id)
        assert loaded is not None

    def test_delete(self) -> None:
        svc = _make_service()
        cp = svc.save_chat_profile(name="X", model_profile_id="mp_1",
            ai_persona_ids=[], lorebook_ids=[], worldbook_ids=[],
            prompt_order_json='[]', system_base="")
        assert svc.delete_chat_profile(cp.id) is True


# --- [v1.0.0] 참조 무결성 검증 테스트 ---


class TestReferentialIntegrity:
    """[v1.0.0] 프로필 삭제 시 연관 참조 무결성 검사 테스트.

    ChatProfile이나 ChatSession에서 참조 중인 엔티티 삭제를 차단하는지 검증한다.
    """

    def _make_full_service(self):
        """ProfileService와 RepositoryRegistry를 함께 반환한다."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        sf = sessionmaker(bind=engine)
        repos = RepositoryRegistry(sf)
        return ProfileService(repos), repos

    def test_delete_ai_persona_blocked_by_chat_profile(self) -> None:
        """AIPersona가 ChatProfile에서 참조 중이면 삭제 차단."""
        svc, _ = self._make_full_service()
        ai = svc.save_ai_persona(name="AI", role_name="R", personality="P", speaking_style="S")
        svc.save_chat_profile(
            name="프로필A", model_profile_id="mp_1",
            ai_persona_ids=[ai.id], lorebook_ids=[], worldbook_ids=[],
            prompt_order_json='[]', system_base="",
        )
        with pytest.raises(ValueError, match="사용 중"):
            svc.delete_ai_persona(ai.id)

    def test_delete_lorebook_blocked_by_chat_profile(self) -> None:
        """Lorebook이 ChatProfile에서 참조 중이면 삭제 차단."""
        svc, _ = self._make_full_service()
        lb = svc.save_lorebook(name="참조대상")
        svc.save_chat_profile(
            name="프로필B", model_profile_id="mp_1",
            ai_persona_ids=[], lorebook_ids=[lb.id], worldbook_ids=[],
            prompt_order_json='[]', system_base="",
        )
        with pytest.raises(ValueError, match="사용 중"):
            svc.delete_lorebook(lb.id)

    def test_delete_worldbook_blocked_by_chat_profile(self) -> None:
        """Worldbook이 ChatProfile에서 참조 중이면 삭제 차단."""
        svc, _ = self._make_full_service()
        wb = svc.save_worldbook(name="참조월드")
        svc.save_chat_profile(
            name="프로필C", model_profile_id="mp_1",
            ai_persona_ids=[], lorebook_ids=[], worldbook_ids=[wb.id],
            prompt_order_json='[]', system_base="",
        )
        with pytest.raises(ValueError, match="사용 중"):
            svc.delete_worldbook(wb.id)

    def test_delete_model_profile_blocked_by_chat_profile(self) -> None:
        """ModelProfile이 ChatProfile에서 참조 중이면 삭제 차단."""
        svc, _ = self._make_full_service()
        mp = svc.save_model_profile(
            name="모델A", provider_profile_id="prov_1",
            model_id="test-model", settings_json='{}',
        )
        svc.save_chat_profile(
            name="프로필D", model_profile_id=mp.id,
            ai_persona_ids=[], lorebook_ids=[], worldbook_ids=[],
            prompt_order_json='[]', system_base="",
        )
        with pytest.raises(ValueError, match="사용 중"):
            svc.delete_model_profile(mp.id)

    def test_delete_chat_profile_blocked_by_session(self) -> None:
        """ChatProfile이 ChatSession에서 참조 중이면 삭제 차단."""
        from chitchat.db.models import ChatSessionRow
        svc, repos = self._make_full_service()
        cp = svc.save_chat_profile(
            name="세션참조", model_profile_id="mp_1",
            ai_persona_ids=[], lorebook_ids=[], worldbook_ids=[],
            prompt_order_json='[]', system_base="",
        )
        # 세션 직접 생성
        session_row = ChatSessionRow(
            id="sess_1", title="테스트세션", status="active",
            chat_profile_id=cp.id, user_persona_id="up_1",
            created_at="2026-01-01T00:00:00Z", updated_at="2026-01-01T00:00:00Z",
        )
        repos.chat_sessions.upsert(session_row)
        with pytest.raises(ValueError, match="사용 중"):
            svc.delete_chat_profile(cp.id)

    def test_delete_user_persona_blocked_by_session(self) -> None:
        """UserPersona가 ChatSession에서 참조 중이면 삭제 차단."""
        from chitchat.db.models import ChatSessionRow
        svc, repos = self._make_full_service()
        up = svc.save_user_persona(name="유저A", description="설명")
        # 세션 직접 생성
        session_row = ChatSessionRow(
            id="sess_2", title="테스트세션2", status="active",
            chat_profile_id="cp_1", user_persona_id=up.id,
            created_at="2026-01-01T00:00:00Z", updated_at="2026-01-01T00:00:00Z",
        )
        repos.chat_sessions.upsert(session_row)
        with pytest.raises(ValueError, match="사용 중"):
            svc.delete_user_persona(up.id)

    def test_delete_unreferenced_entity_succeeds(self) -> None:
        """참조되지 않은 엔티티는 정상 삭제."""
        svc, _ = self._make_full_service()
        ai = svc.save_ai_persona(name="미참조", role_name="R", personality="P", speaking_style="S")
        assert svc.delete_ai_persona(ai.id) is True
        assert svc.get_ai_persona(ai.id) is None


class TestProviderReferentialIntegrity:
    """[v1.0.0] Provider 삭제 시 ModelProfile 참조 검사 테스트."""

    def test_delete_provider_blocked_by_model_profile(self) -> None:
        """ModelProfile이 Provider를 참조 중이면 삭제 차단."""
        from unittest.mock import MagicMock
        from chitchat.services.provider_service import ProviderService

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        sf = sessionmaker(bind=engine)
        repos = RepositoryRegistry(sf)

        # mock key_store과 provider_registry
        mock_key_store = MagicMock()
        mock_registry = MagicMock()
        prov_svc = ProviderService(repos, mock_registry, mock_key_store)
        prof_svc = ProfileService(repos)

        # Provider 생성
        prov = prov_svc.save_provider(
            name="테스트Gemini", provider_kind="gemini",
            api_key=None, timeout_seconds=30,
        )

        # ModelProfile이 Provider를 참조
        prof_svc.save_model_profile(
            name="Flash모델", provider_profile_id=prov.id,
            model_id="test-model", settings_json='{}',
        )

        # 삭제 시도 → 차단
        with pytest.raises(ValueError, match="사용 중"):
            prov_svc.delete_provider(prov.id)

    def test_delete_unreferenced_provider_succeeds(self) -> None:
        """참조되지 않은 Provider는 정상 삭제."""
        from unittest.mock import MagicMock
        from chitchat.services.provider_service import ProviderService

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        sf = sessionmaker(bind=engine)
        repos = RepositoryRegistry(sf)

        mock_key_store = MagicMock()
        mock_registry = MagicMock()
        prov_svc = ProviderService(repos, mock_registry, mock_key_store)

        prov = prov_svc.save_provider(
            name="삭제대상", provider_kind="lm_studio",
            timeout_seconds=30,
        )

        assert prov_svc.delete_provider(prov.id) is True
        assert prov_svc.get_provider(prov.id) is None
