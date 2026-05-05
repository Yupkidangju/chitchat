# src/chitchat/domain/prompt_assembler.py
# [v1.0.0] 프롬프트 조립 엔진 v2
#
# [v0.1.0b0 → v1.0.0 변경사항]
# - dynamic_state_text 파라미터 추가: 동적 상태 블록을 ai_persona 뒤에 주입
# - DynamicStateEngine.build_dynamic_prompt_block()의 출력을 받아 프롬프트에 반영
#
# spec.md §12.1~§12.3 알고리즘을 구현한다:
# 1. PromptOrderItem 순서대로 활성 블록을 수집한다.
# 2. system_base, user_persona, ai_persona, dynamic_state, worldbook 블록을 고정 삽입한다.
# 3. lorebook 블록은 match_lore_entries()에서 매칭된 것만 삽입한다.
# 4. chat_history 블록은 남은 예산으로 최신 메시지부터 삽입한다.
# 5. current_input 블록은 사용자의 현재 입력을 삽입한다.
from __future__ import annotations
import logging
from chitchat.domain.prompt_blocks import (
    AssembledPrompt, MessageSlot, PromptBlock, estimate_tokens,
)
from chitchat.domain.provider_contracts import PromptBlockKind

logger = logging.getLogger(__name__)


def assemble_prompt(
    prompt_order: list[tuple[PromptBlockKind, bool]],
    system_base: str,
    user_persona_text: str | None,
    ai_persona_text: str | None,
    worldbook_blocks: list[PromptBlock],
    lorebook_blocks: list[PromptBlock],
    history_messages: list[tuple[str, str]],
    current_input: str,
    context_budget: int,
    max_output_tokens: int = 2048,
    history_message_ids: list[str] | None = None,
    # [v1.0.0] 동적 상태 블록 — DynamicStateEngine.build_dynamic_prompt_block() 출력
    dynamic_state_text: str | None = None,
) -> AssembledPrompt:
    """프롬프트를 조립한다.

    [v1.0.0] dynamic_state_text가 주어지면 ai_persona 블록 뒤에 동적 상태를 주입한다.
    이를 통해 캐릭터의 현재 관계/기억/감정 상태가 프롬프트에 실시간 반영된다.

    Args:
        prompt_order: (PromptBlockKind, enabled) 튜플 리스트 (order_index 정렬됨).
        system_base: 시스템 기본 프롬프트.
        user_persona_text: 사용자 페르소나 텍스트 (없으면 None).
        ai_persona_text: AI 페르소나 텍스트 (없으면 None).
        worldbook_blocks: 월드북 블록 리스트.
        lorebook_blocks: 로어북 매칭 결과 블록 리스트.
        history_messages: 히스토리 메시지 리스트 [(role, content), ...] (오래된 것부터).
        current_input: 현재 사용자 입력.
        context_budget: 컨텍스트 윈도우 토큰 수.
        max_output_tokens: 최대 출력 토큰 수 (예산에서 차감).
        history_message_ids: 히스토리 메시지 ID 리스트.
        dynamic_state_text: 동적 상태 블록 텍스트 (v1.0.0 신규).

    Returns:
        조립 완료된 AssembledPrompt.
    """
    result = AssembledPrompt(budget_tokens=context_budget)

    # 출력 토큰을 예산에서 차감
    available = context_budget - max_output_tokens
    if available <= 0:
        available = context_budget // 2

    # 고정 블록을 먼저 수집 (히스토리 제외)
    fixed_blocks: list[PromptBlock] = []
    include_history = False

    for kind, enabled in prompt_order:
        if not enabled:
            continue
        if kind == "system_base":
            fixed_blocks.append(PromptBlock.create("system_base", system_base))
        elif kind == "user_persona" and user_persona_text:
            fixed_blocks.append(PromptBlock.create("user_persona", user_persona_text))
        elif kind == "ai_persona" and ai_persona_text:
            fixed_blocks.append(PromptBlock.create("ai_persona", ai_persona_text))
            # [v1.0.0] 동적 상태 블록을 ai_persona 뒤에 주입
            if dynamic_state_text:
                fixed_blocks.append(PromptBlock.create("ai_persona", dynamic_state_text))
        elif kind == "worldbook":
            fixed_blocks.extend(worldbook_blocks)
        elif kind == "lorebook":
            fixed_blocks.extend(lorebook_blocks)
        elif kind == "chat_history":
            include_history = True
        elif kind == "current_input":
            fixed_blocks.append(PromptBlock.create("current_input", current_input))

    # 고정 블록 토큰 합산
    fixed_tokens = sum(b.token_estimate for b in fixed_blocks)

    # 히스토리에 남은 예산 계산
    history_budget = available - fixed_tokens
    history_blocks: list[PromptBlock] = []
    truncated = 0
    # [v0.1.4] 잘린 메시지 인덱스 추적 (spec §12.6 truncated_history_message_ids)
    # history_budget <= 0 경로에서도 UnboundLocalError 방지를 위해 상위 스코프에서 초기화
    included_indices: set[int] = set()

    if include_history and history_budget > 0:
        # 최신 메시지부터 역순으로 삽입 (spec.md §12.3)
        budget_left = history_budget
        for idx in range(len(history_messages) - 1, -1, -1):
            role, content = history_messages[idx]
            tokens = estimate_tokens(content)
            if budget_left - tokens < 0:
                truncated += 1
                continue
            history_blocks.insert(0, PromptBlock(
                kind="chat_history", content=content, token_estimate=tokens,
            ))
            included_indices.add(idx)
            budget_left -= tokens
        truncated = len(history_messages) - len(history_blocks)
    elif include_history and history_messages:
        # [v0.1.4] 예산 소진으로 히스토리 전체가 잘린 경우 — truncated_count 정합성 보장
        truncated = len(history_messages)

    # 최종 블록 리스트 조립: prompt_order 순서를 따른다
    all_blocks: list[PromptBlock] = []
    for kind, enabled in prompt_order:
        if not enabled:
            continue
        if kind == "chat_history":
            all_blocks.extend(history_blocks)
        elif kind == "lorebook":
            all_blocks.extend(lorebook_blocks)
        elif kind == "worldbook":
            all_blocks.extend(worldbook_blocks)
        else:
            # 해당 kind의 고정 블록을 찾아 삽입
            for fb in fixed_blocks:
                if fb.kind == kind:
                    all_blocks.append(fb)

    # 메시지 배열 생성: system 블록들은 system role로 결합, history/input은 원래 역할
    system_parts: list[str] = []
    messages: list[MessageSlot] = []

    # 히스토리 블록 → 원본 메시지 인덱스 매핑 (content 동일성 대신 인덱스 기반)
    history_index = 0
    history_block_roles: dict[int, str] = {}
    for idx, hb in enumerate(history_blocks):
        # history_blocks는 history_messages의 부분 집합이며 순서 보존됨
        while history_index < len(history_messages):
            role, content = history_messages[history_index]
            history_index += 1
            if content == hb.content:
                history_block_roles[idx] = role
                break

    hb_counter = 0
    for block in all_blocks:
        if block.kind in ("system_base", "user_persona", "ai_persona", "worldbook", "lorebook"):
            system_parts.append(block.content)
        elif block.kind == "chat_history":
            role = history_block_roles.get(hb_counter, "user")
            messages.append(MessageSlot(role=role, content=block.content))  # type: ignore[arg-type]
            hb_counter += 1
        elif block.kind == "current_input":
            # system parts를 먼저 system 메시지로 추가
            if system_parts:
                messages.insert(0, MessageSlot(role="system", content="\n\n".join(system_parts)))
                system_parts = []
            messages.append(MessageSlot(role="user", content=block.content))

    # system_parts가 남아 있으면 맨 앞에 추가
    if system_parts:
        messages.insert(0, MessageSlot(role="system", content="\n\n".join(system_parts)))

    result.blocks = all_blocks
    result.messages = messages
    result.total_tokens = sum(b.token_estimate for b in all_blocks)
    result.history_count = len(history_blocks)
    result.truncated_count = truncated

    # [v0.1.4] spec §12.6: 잘린 히스토리 메시지 ID 수집
    if history_message_ids and include_history:
        result.truncated_history_message_ids = [
            history_message_ids[i] for i in range(len(history_messages))
            if i not in included_indices
        ]
    # included_indices가 정의되지 않은 경우 (히스토리 비활성) 빈 리스트 유지

    logger.info(
        "프롬프트 조립 완료: %d 블록, %d 토큰, 히스토리 %d/%d",
        len(all_blocks), result.total_tokens, result.history_count,
        result.history_count + truncated,
    )
    return result
