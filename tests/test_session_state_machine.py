# tests/test_session_state_machine.py
# [v0.1.0b0] 세션 상태 전이 + ChatService 세션 관리 테스트
from __future__ import annotations
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest
from chitchat.db.models import Base
from chitchat.db.repositories import RepositoryRegistry
from chitchat.domain.chat_session import InvalidSessionTransitionError
from chitchat.services.chat_service import ChatService
from chitchat.services.prompt_service import PromptService
from chitchat.providers.registry import ProviderRegistry
from chitchat.secrets.key_store import KeyStore


def _make_chat_service() -> ChatService:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    sf = sessionmaker(bind=engine)
    repos = RepositoryRegistry(sf)
    providers = ProviderRegistry()
    key_store = MagicMock(spec=KeyStore)
    prompt_svc = PromptService(repos)
    return ChatService(repos, providers, key_store, prompt_svc)


class TestSessionCrud:
    def test_create_session(self) -> None:
        svc = _make_chat_service()
        s = svc.create_session("테스트 세션", "cp_1", "up_1")
        assert s.title == "테스트 세션"
        assert s.status == "draft"
        assert s.id.startswith("cs_")

    def test_get_session(self) -> None:
        svc = _make_chat_service()
        s = svc.create_session("세션", "cp_1", "up_1")
        loaded = svc.get_session(s.id)
        assert loaded is not None
        assert loaded.title == "세션"

    def test_get_all_sessions(self) -> None:
        svc = _make_chat_service()
        svc.create_session("A", "cp_1", "up_1")
        svc.create_session("B", "cp_1", "up_1")
        assert len(svc.get_all_sessions()) == 2


class TestMessageCrud:
    def test_save_user_message(self) -> None:
        svc = _make_chat_service()
        s = svc.create_session("세션", "cp_1", "up_1")
        m = svc.save_user_message(s.id, "안녕하세요")
        assert m.role == "user"
        assert m.content == "안녕하세요"
        assert m.token_estimate > 0
        assert m.id.startswith("msg_")

    def test_save_assistant_message(self) -> None:
        svc = _make_chat_service()
        s = svc.create_session("세션", "cp_1", "up_1")
        m = svc.save_assistant_message(s.id, "반갑습니다")
        assert m.role == "assistant"

    def test_messages_ordered(self) -> None:
        svc = _make_chat_service()
        s = svc.create_session("세션", "cp_1", "up_1")
        svc.save_user_message(s.id, "1")
        svc.save_assistant_message(s.id, "2")
        svc.save_user_message(s.id, "3")
        msgs = svc.get_session_messages(s.id)
        assert len(msgs) == 3
        assert msgs[0].content == "1"
        assert msgs[2].content == "3"


class TestStateTransition:
    def test_draft_to_active(self) -> None:
        svc = _make_chat_service()
        s = svc.create_session("세션", "cp_1", "up_1")
        assert s.status == "draft"
        s2 = svc._transition(s, "active")
        assert s2.status == "active"

    def test_active_to_streaming(self) -> None:
        svc = _make_chat_service()
        s = svc.create_session("세션", "cp_1", "up_1")
        s = svc._transition(s, "active")
        s = svc._transition(s, "streaming")
        assert s.status == "streaming"

    def test_streaming_to_stopped(self) -> None:
        svc = _make_chat_service()
        s = svc.create_session("세션", "cp_1", "up_1")
        s = svc._transition(s, "active")
        s = svc._transition(s, "streaming")
        s = svc._transition(s, "stopped")
        assert s.status == "stopped"

    def test_streaming_to_failed(self) -> None:
        svc = _make_chat_service()
        s = svc.create_session("세션", "cp_1", "up_1")
        s = svc._transition(s, "active")
        s = svc._transition(s, "streaming")
        s = svc._transition(s, "failed")
        assert s.status == "failed"

    def test_invalid_transition_raises(self) -> None:
        svc = _make_chat_service()
        s = svc.create_session("세션", "cp_1", "up_1")
        with pytest.raises(InvalidSessionTransitionError):
            svc._transition(s, "streaming")  # draft → streaming 불가

    def test_archived_no_transition(self) -> None:
        svc = _make_chat_service()
        s = svc.create_session("세션", "cp_1", "up_1")
        s = svc._transition(s, "active")
        s = svc._transition(s, "archived")
        with pytest.raises(InvalidSessionTransitionError):
            svc._transition(s, "active")  # archived → active 불가
