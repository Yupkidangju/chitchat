# tests/test_prompt_assembler.py
# [v0.1.0b0] 프롬프트 조립 엔진 테스트
from __future__ import annotations
from chitchat.domain.prompt_assembler import assemble_prompt
from chitchat.domain.prompt_blocks import PromptBlock, estimate_tokens


# 기본 프롬프트 순서 (spec.md §12.1 기본값)
DEFAULT_ORDER: list[tuple[str, bool]] = [
    ("system_base", True),
    ("user_persona", True),
    ("ai_persona", True),
    ("worldbook", True),
    ("lorebook", True),
    ("chat_history", True),
    ("current_input", True),
]


class TestEstimateTokens:
    def test_empty(self) -> None:
        assert estimate_tokens("") == 1

    def test_short(self) -> None:
        assert estimate_tokens("hi") == 1

    def test_typical(self) -> None:
        # 100자 → (100+3)//4 = 25
        assert estimate_tokens("a" * 100) == 25

    def test_korean(self) -> None:
        # 한국어 40자 → (40+3)//4 = 10
        assert estimate_tokens("가" * 40) == 10


class TestBlockAssembly:
    def test_basic_assembly(self) -> None:
        result = assemble_prompt(
            prompt_order=DEFAULT_ORDER,
            system_base="You are helpful",
            user_persona_text="I am user",
            ai_persona_text="I am AI",
            worldbook_blocks=[],
            lorebook_blocks=[],
            history_messages=[],
            current_input="Hello",
            context_budget=8192,
        )
        assert result.total_tokens > 0
        assert len(result.messages) >= 2  # system + user
        assert result.messages[0].role == "system"
        assert result.messages[-1].role == "user"
        assert result.messages[-1].content == "Hello"

    def test_system_message_combines_parts(self) -> None:
        result = assemble_prompt(
            prompt_order=DEFAULT_ORDER,
            system_base="System",
            user_persona_text="User persona",
            ai_persona_text="AI persona",
            worldbook_blocks=[PromptBlock.create("worldbook", "World info")],
            lorebook_blocks=[PromptBlock.create("lorebook", "Lore info")],
            history_messages=[],
            current_input="Hi",
            context_budget=8192,
        )
        system_msg = result.messages[0]
        assert "System" in system_msg.content
        assert "User persona" in system_msg.content
        assert "AI persona" in system_msg.content
        assert "World info" in system_msg.content
        assert "Lore info" in system_msg.content

    def test_disabled_block_excluded(self) -> None:
        order = [
            ("system_base", True),
            ("user_persona", False),  # 비활성
            ("current_input", True),
        ]
        result = assemble_prompt(
            prompt_order=order,
            system_base="System",
            user_persona_text="User",
            ai_persona_text=None,
            worldbook_blocks=[],
            lorebook_blocks=[],
            history_messages=[],
            current_input="Hi",
            context_budget=8192,
        )
        system_msg = result.messages[0]
        assert "User" not in system_msg.content


class TestHistoryTruncation:
    def test_history_included(self) -> None:
        history = [("user", "msg1"), ("assistant", "reply1"), ("user", "msg2"), ("assistant", "reply2")]
        result = assemble_prompt(
            prompt_order=DEFAULT_ORDER,
            system_base="S",
            user_persona_text=None,
            ai_persona_text=None,
            worldbook_blocks=[],
            lorebook_blocks=[],
            history_messages=history,
            current_input="msg3",
            context_budget=100000,
        )
        assert result.history_count == 4
        assert result.truncated_count == 0

    def test_history_truncated_by_budget(self) -> None:
        """예산 부족 시 오래된 메시지부터 잘린다."""
        # 각 메시지가 ~25 토큰 (100자)
        history = [(
            "user" if i % 2 == 0 else "assistant",
            f"{'x' * 100}",
        ) for i in range(20)]
        result = assemble_prompt(
            prompt_order=DEFAULT_ORDER,
            system_base="S",
            user_persona_text=None,
            ai_persona_text=None,
            worldbook_blocks=[],
            lorebook_blocks=[],
            history_messages=history,
            current_input="Hi",
            context_budget=200,  # 매우 작은 예산
        )
        # 일부만 포함되어야 함
        assert result.history_count < 20
        assert result.truncated_count > 0


class TestBudget:
    def test_budget_recorded(self) -> None:
        result = assemble_prompt(
            prompt_order=DEFAULT_ORDER,
            system_base="S",
            user_persona_text=None,
            ai_persona_text=None,
            worldbook_blocks=[],
            lorebook_blocks=[],
            history_messages=[],
            current_input="Hi",
            context_budget=4096,
        )
        assert result.budget_tokens == 4096
