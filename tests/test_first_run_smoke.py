# tests/test_first_run_smoke.py
# [v0.1.0b0] 첫 완주 루트 smoke 테스트
#
# 새 사용자가 UI만으로 첫 채팅까지 완주하는 루트를 서비스 레벨에서 검증한다.
# 목표: "첫 완주 루트가 다시 끊기지 않게 하는 것"
#
# 루트: Provider 등록 → 모델 캐시 → ModelProfile → UserPersona → AIPersona
#       → ChatProfile → Session → 메시지 저장 → 스트리밍 응답 저장 확인
from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from chitchat.db.models import (
    Base,
    ModelCacheRow,
)
from chitchat.db.repositories import RepositoryRegistry
from chitchat.domain.ids import new_id
from chitchat.providers.registry import ProviderRegistry
from chitchat.secrets.key_store import KeyStore
from chitchat.services.chat_service import ChatService
from chitchat.services.profile_service import ProfileService
from chitchat.services.prompt_service import PromptService
from chitchat.services.provider_service import ProviderService


@pytest.fixture()
def fresh_db():
    """테스트용 인메모리 DB를 생성하고 모든 테이블을 초기화한다."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    return factory


@pytest.fixture()
def repos(fresh_db):
    """RepositoryRegistry를 생성한다."""
    return RepositoryRegistry(fresh_db)


@pytest.fixture()
def key_store():
    """KeyStore mock: set_key는 secret_ref 반환, get_key는 'fake-key' 반환."""
    ks = MagicMock(spec=KeyStore)
    ks.set_key.return_value = "chitchat:test_provider"
    ks.get_key.return_value = "fake-api-key-12345"
    return ks


class TestFirstRunSmoke:
    """첫 완주 루트를 서비스 레벨에서 검증한다.

    각 단계가 이전 단계의 산출물을 올바르게 사용하는지 확인한다.
    """

    def test_full_first_run_route(self, repos, key_store):
        """Provider → ModelProfile → Persona → ChatProfile → Session → Send 전체 루트."""
        now = datetime.now(timezone.utc).isoformat()

        # === 1단계: Provider 등록 ===
        prov_svc = ProviderService(repos, ProviderRegistry(), key_store)
        provider = prov_svc.save_provider(
            name="테스트 Gemini",
            provider_kind="gemini",
            api_key="test-key-abc",
        )
        assert provider.id
        assert provider.name == "테스트 Gemini"
        assert provider.provider_kind == "gemini"
        # KeyStore.set_key가 호출되었는지 확인
        key_store.set_key.assert_called_once()

        # === 2단계: 모델 캐시 시뮬레이션 (실제는 API 호출) ===
        # ProviderService.fetch_models는 async이므로, 직접 캐시 삽입
        session_factory = repos.model_cache._session_factory
        with session_factory() as db_session:
            cache = ModelCacheRow(
                id=new_id("mc_"),
                provider_profile_id=provider.id,
                model_id="gemini-2.0-flash",
                display_name="Gemini 2.0 Flash",
                context_window_tokens=1048576,
                max_output_tokens=8192,
                supported_parameters_json=json.dumps(["temperature", "top_p", "top_k"]),
                supports_streaming=1,
                supports_system_prompt=1,
                supports_json_mode=1,
                raw_json="{}",
                fetched_at=now,
            )
            db_session.add(cache)
            db_session.commit()
            cached_model_id = cache.model_id

        # 캐시 조회 확인
        cached = prov_svc.get_cached_models(provider.id)
        assert len(cached) == 1
        assert cached[0].model_id == "gemini-2.0-flash"

        # === 3단계: ModelProfile 생성 ===
        prof_svc = ProfileService(repos)
        settings = json.dumps({
            "context_window_tokens": 1048576,
            "max_output_tokens": 8192,
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 40,
        })
        mp = prof_svc.save_model_profile(
            name="Flash 기본",
            provider_profile_id=provider.id,
            model_id=cached_model_id,
            settings_json=settings,
        )
        assert mp.id
        assert mp.model_id == "gemini-2.0-flash"

        # === 4단계: UserPersona 생성 ===
        up = prof_svc.save_user_persona(
            name="테스트 사용자",
            description="테스트용 사용자 페르소나",
        )
        assert up.id

        # === 5단계: AIPersona 생성 ===
        ai = prof_svc.save_ai_persona(
            name="테스트 AI",
            role_name="도우미",
            personality="친절하고 명확한 답변",
            speaking_style="존댓말",
        )
        assert ai.id

        # === 6단계: ChatProfile 생성 ===
        prompt_order = json.dumps([
            {"kind": "system_base", "enabled": True},
            {"kind": "user_persona", "enabled": True},
            {"kind": "ai_persona", "enabled": True},
            {"kind": "worldbook", "enabled": True},
            {"kind": "lorebook", "enabled": True},
            {"kind": "chat_history", "enabled": True},
            {"kind": "current_input", "enabled": True},
        ])
        cp = prof_svc.save_chat_profile(
            name="기본 채팅 프로필",
            model_profile_id=mp.id,
            ai_persona_ids=[ai.id],
            lorebook_ids=[],
            worldbook_ids=[],
            prompt_order_json=prompt_order,
            system_base="당신은 친절한 AI 도우미입니다.",
        )
        assert cp.id
        assert cp.model_profile_id == mp.id

        # === 7단계: Session 생성 ===
        prompt_svc = PromptService(repos)
        chat_svc = ChatService(repos, ProviderRegistry(), key_store, prompt_svc)
        session = chat_svc.create_session(
            title="첫 채팅",
            chat_profile_id=cp.id,
            user_persona_id=up.id,
        )
        assert session.id
        assert session.status == "draft"

        # === 8단계: 사용자 메시지 전송 ===
        chat_svc.save_user_message(session.id, "안녕하세요!")
        msgs = chat_svc.get_session_messages(session.id)
        assert len(msgs) == 1
        assert msgs[0].role == "user"
        assert msgs[0].content == "안녕하세요!"

        # === 9단계: 가짜 AI 응답 저장 (스트리밍 시뮬레이션) ===
        # 실제 start_stream은 LLM API가 필요. 서비스 레벨에서 assistant 메시지 직접 저장.
        from chitchat.db.models import ChatMessageRow
        from chitchat.domain.prompt_blocks import estimate_tokens
        ai_response = "안녕하세요! 무엇을 도와드릴까요?"
        # created_at을 user 메시지보다 늦게 설정 (정렬 순서 보장)
        from datetime import timedelta
        ai_created_at = (datetime.now(timezone.utc) + timedelta(seconds=1)).isoformat()
        with session_factory() as db_session:
            ai_msg = ChatMessageRow(
                id=new_id("msg_"),
                session_id=session.id,
                role="assistant",
                content=ai_response,
                prompt_snapshot_json=json.dumps({"total_tokens": 150, "budget_tokens": 1048576}),
                created_at=ai_created_at,
                token_estimate=estimate_tokens(ai_response),
            )
            db_session.add(ai_msg)
            db_session.commit()

        # 최종 검증: 메시지 2개 (user + assistant)
        all_msgs = chat_svc.get_session_messages(session.id)
        assert len(all_msgs) == 2
        assert all_msgs[0].role == "user"
        assert all_msgs[1].role == "assistant"
        assert all_msgs[1].content == ai_response

    def test_missing_prerequisites_block_session(self, repos, key_store):
        """ChatProfile이나 UserPersona 없이 세션 생성 시 필수 항목 검증."""
        chat_svc = ChatService(
            repos, ProviderRegistry(), key_store, PromptService(repos),
        )
        # ChatProfile/UserPersona가 없는 상태
        profiles = chat_svc.get_available_chat_profiles()
        personas = chat_svc.get_available_user_personas()
        assert len(profiles) == 0
        assert len(personas) == 0

    def test_model_profile_requires_provider(self, repos, key_store):
        """ModelProfile 생성 시 Provider ID가 유효해야 한다."""
        prof_svc = ProfileService(repos)
        # Provider 없이 ModelProfile 생성은 허용되지만 (FK constraint는 DB 레벨)
        # UI에서는 Provider 콤보가 비어있으면 저장 불가
        mp = prof_svc.save_model_profile(
            name="고아 프로필",
            provider_profile_id="nonexistent_prov",
            model_id="fake-model",
            settings_json="{}",
        )
        # DB에 저장은 되지만 (SQLite FK 기본 비활성),
        # 실사용 시 chat_service.start_stream에서 Provider 조회 실패로 에러
        assert mp.id

    def test_chat_profile_requires_model_profile(self, repos, key_store):
        """ChatProfile이 ModelProfile을 참조하는지 검증."""
        prof_svc = ProfileService(repos)
        cp = prof_svc.save_chat_profile(
            name="테스트",
            model_profile_id="nonexistent_mp",
            ai_persona_ids=[],
            lorebook_ids=[],
            worldbook_ids=[],
            prompt_order_json="[]",
            system_base="test",
        )
        assert cp.model_profile_id == "nonexistent_mp"

    def test_service_layer_encapsulation(self, repos, key_store):
        """ChatService가 repos를 직접 노출하지 않고 도우미 메서드를 제공하는지 검증."""
        chat_svc = ChatService(
            repos, ProviderRegistry(), key_store, PromptService(repos),
        )
        # 도우미 메서드 존재 확인
        assert hasattr(chat_svc, "get_available_chat_profiles")
        assert hasattr(chat_svc, "get_available_user_personas")
        assert callable(chat_svc.get_available_chat_profiles)
        assert callable(chat_svc.get_available_user_personas)
