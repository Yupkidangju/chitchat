# tests/test_profile_crud_service.py
# [v0.1.0b0] ProfileService CRUD 통합 테스트
#
# in-memory SQLite에서 ProfileService의 7종 엔티티 CRUD를 검증한다.
from __future__ import annotations
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
