# tests/test_profile_validation.py
# [v0.1.0b0] Pydantic 프로필 모델 경계값 검증 테스트
#
# spec.md §8.2, §8.3에 정의된 필드 제약을 검증한다.
# min_length, max_length, ge, le 등의 경계값을 테스트한다.

from __future__ import annotations

import pytest
from pydantic import ValidationError

from chitchat.domain.ids import new_id
from chitchat.domain.profiles import (
    AIPersonaData,
    LoreEntryData,
    PromptOrderItem,
    UserPersonaData,
)
from chitchat.domain.provider_contracts import (
    ModelGenerationSettings,
    ProviderProfileData,
)


# --- ID 생성 테스트 ---

class TestIdGeneration:
    """ULID 기반 ID 생성 검증."""

    def test_id_has_prefix(self) -> None:
        """생성된 ID가 지정한 prefix로 시작하는지 확인한다."""
        id_ = new_id("cp_")
        assert id_.startswith("cp_")

    def test_id_is_unique(self) -> None:
        """연속 생성된 ID가 모두 고유한지 확인한다."""
        ids = {new_id("test_") for _ in range(100)}
        assert len(ids) == 100

    def test_id_prefix_must_end_with_underscore(self) -> None:
        """prefix가 언더스코어로 끝나지 않으면 ValueError가 발생한다."""
        with pytest.raises(ValueError, match="언더스코어"):
            new_id("bad")


# --- ProviderProfile 테스트 ---

class TestProviderProfileValidation:
    """Provider 프로필 필드 제약 검증."""

    def test_valid_gemini_profile(self) -> None:
        """정상적인 Gemini Provider 프로필 생성."""
        p = ProviderProfileData(
            id="prov_test",
            name="Gemini Main",
            provider_kind="gemini",
            secret_ref="chitchat:prov_test",
        )
        assert p.provider_kind == "gemini"
        assert p.timeout_seconds == 60

    def test_empty_name_rejected(self) -> None:
        """빈 이름은 거부된다."""
        with pytest.raises(ValidationError):
            ProviderProfileData(id="prov_test", name="", provider_kind="gemini")

    def test_name_max_length(self) -> None:
        """이름이 80자를 초과하면 거부된다."""
        with pytest.raises(ValidationError):
            ProviderProfileData(id="prov_test", name="x" * 81, provider_kind="gemini")

    def test_invalid_provider_kind(self) -> None:
        """지원하지 않는 provider_kind는 거부된다."""
        with pytest.raises(ValidationError):
            ProviderProfileData(id="prov_test", name="Bad", provider_kind="unknown")  # type: ignore[arg-type]

    def test_timeout_min(self) -> None:
        """타임아웃이 5초 미만이면 거부된다."""
        with pytest.raises(ValidationError):
            ProviderProfileData(id="p", name="T", provider_kind="gemini", timeout_seconds=4)

    def test_timeout_max(self) -> None:
        """타임아웃이 300초를 초과하면 거부된다."""
        with pytest.raises(ValidationError):
            ProviderProfileData(id="p", name="T", provider_kind="gemini", timeout_seconds=301)


# --- ModelGenerationSettings 테스트 ---

class TestModelGenerationSettings:
    """모델 생성 파라미터 경계값 검증."""

    def test_defaults(self) -> None:
        """기본값이 spec.md §8.2에 정의된 대로인지 확인한다."""
        s = ModelGenerationSettings()
        assert s.temperature is None
        assert s.max_output_tokens == 1024

    def test_temperature_range(self) -> None:
        """temperature 범위 [0.0, 2.0]을 검증한다."""
        s = ModelGenerationSettings(temperature=2.0)
        assert s.temperature == 2.0
        with pytest.raises(ValidationError):
            ModelGenerationSettings(temperature=-0.1)
        with pytest.raises(ValidationError):
            ModelGenerationSettings(temperature=2.1)

    def test_top_p_range(self) -> None:
        """top_p 범위 [0.0, 1.0]을 검증한다."""
        with pytest.raises(ValidationError):
            ModelGenerationSettings(top_p=1.1)

    def test_stop_max_length(self) -> None:
        """stop 시퀀스가 8개를 초과하면 거부된다."""
        with pytest.raises(ValidationError):
            ModelGenerationSettings(stop=["a"] * 9)


# --- UserPersona 테스트 ---

class TestUserPersonaValidation:
    """사용자 페르소나 필드 제약 검증."""

    def test_valid_persona(self) -> None:
        """정상적인 사용자 페르소나 생성."""
        u = UserPersonaData(
            id="up_test",
            name="테스트 사용자",
            description="테스트용 설명",
        )
        assert u.enabled is True

    def test_empty_description_rejected(self) -> None:
        """빈 설명은 거부된다."""
        with pytest.raises(ValidationError):
            UserPersonaData(id="up_test", name="T", description="")

    def test_description_max_length(self) -> None:
        """설명이 4000자를 초과하면 거부된다."""
        with pytest.raises(ValidationError):
            UserPersonaData(id="up_test", name="T", description="x" * 4001)


# --- AIPersona 테스트 ---

class TestAIPersonaValidation:
    """AI 페르소나 필드 제약 검증."""

    def test_valid_ai_persona(self) -> None:
        """정상적인 AI 페르소나 생성."""
        a = AIPersonaData(
            id="ai_test",
            name="미라",
            role_name="고서관 관리자 미라",
            personality="신비롭고 지적인",
            speaking_style="~해요체 사용",
        )
        assert a.enabled is True

    def test_empty_role_name_rejected(self) -> None:
        """빈 역할 이름은 거부된다."""
        with pytest.raises(ValidationError):
            AIPersonaData(
                id="ai_test", name="T", role_name="",
                personality="p", speaking_style="s",
            )


# --- LoreEntry 테스트 ---

class TestLoreEntryValidation:
    """로어 엔트리 필드 제약 검증."""

    def test_valid_entry(self) -> None:
        """정상적인 로어 엔트리 생성."""
        e = LoreEntryData(
            id="le_test",
            lorebook_id="lb_test",
            title="고대 유물",
            activation_keys=["유물", "artifact"],
            content="고대 유물에 대한 설명...",
        )
        assert e.priority == 100
        assert e.enabled is True

    def test_empty_activation_keys_rejected(self) -> None:
        """빈 activation_keys는 거부된다."""
        with pytest.raises(ValidationError):
            LoreEntryData(
                id="le_test", lorebook_id="lb_test",
                title="T", activation_keys=[], content="C",
            )

    def test_priority_range(self) -> None:
        """priority 범위 [0, 1000]을 검증한다."""
        e = LoreEntryData(
            id="le_test", lorebook_id="lb_test",
            title="T", activation_keys=["k"], content="C",
            priority=1000,
        )
        assert e.priority == 1000
        with pytest.raises(ValidationError):
            LoreEntryData(
                id="le_test", lorebook_id="lb_test",
                title="T", activation_keys=["k"], content="C",
                priority=1001,
            )


# --- PromptOrderItem 테스트 ---

class TestPromptOrderItemValidation:
    """프롬프트 순서 항목 검증."""

    def test_valid_item(self) -> None:
        """정상적인 순서 항목 생성."""
        item = PromptOrderItem(kind="system_base", enabled=True, order_index=10)
        assert item.kind == "system_base"

    def test_invalid_kind_rejected(self) -> None:
        """유효하지 않은 kind는 거부된다."""
        with pytest.raises(ValidationError):
            PromptOrderItem(kind="invalid_block", enabled=True, order_index=10)  # type: ignore[arg-type]

    def test_order_index_range(self) -> None:
        """order_index 범위 [0, 100]을 검증한다."""
        with pytest.raises(ValidationError):
            PromptOrderItem(kind="system_base", enabled=True, order_index=101)


# --- ChatSessionData 상태 전이 테스트 ---

class TestChatSessionTransition:
    """채팅 세션 상태 전이 규칙 검증. spec.md §13.2."""

    @pytest.mark.parametrize(
        "current,target,expected",
        [
            ("draft", "active", True),
            ("active", "streaming", True),
            ("active", "archived", True),
            ("streaming", "active", True),
            ("streaming", "stopped", True),
            ("streaming", "failed", True),
            ("stopped", "active", True),
            ("failed", "active", True),
            # 유효하지 않은 전이
            ("draft", "streaming", False),
            ("draft", "archived", False),
            ("active", "draft", False),
            ("archived", "active", False),
            ("archived", "draft", False),
        ],
    )
    def test_transitions(self, current: str, target: str, expected: bool) -> None:
        """상태 전이 매트릭스 검증."""
        from chitchat.domain.chat_session import validate_session_transition
        assert validate_session_transition(current, target) == expected  # type: ignore[arg-type]
