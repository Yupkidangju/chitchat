# src/chitchat/domain/lorebook_matcher.py
# [v0.1.0b0] 로어북 키워드 매칭 엔진
#
# spec.md §12.4 알고리즘을 구현한다:
# 1. 최근 N개 메시지에서 텍스트를 결합한다.
# 2. 각 LoreEntry의 activation_keys를 casefold하여 'in' 연산자로 매칭한다.
# 3. priority 내림차순 → title 오름차순으로 정렬한다.
# 4. 최대 max_entries개 (기본 12) 선택, 총 토큰 합이 max_tokens (기본 3000)을 초과하면 중단.
from __future__ import annotations
import logging
from chitchat.domain.prompt_blocks import PromptBlock, estimate_tokens
from chitchat.domain.profiles import LoreEntryData

logger = logging.getLogger(__name__)

# spec.md §12.4 기본값
_DEFAULT_MAX_ENTRIES = 12
_DEFAULT_MAX_TOKENS = 3000
_DEFAULT_SCAN_MESSAGES = 8


def match_lore_entries(
    entries: list[LoreEntryData],
    recent_messages: list[str],
    max_entries: int = _DEFAULT_MAX_ENTRIES,
    max_tokens: int = _DEFAULT_MAX_TOKENS,
    scan_messages: int = _DEFAULT_SCAN_MESSAGES,
) -> list[PromptBlock]:
    """최근 메시지에서 로어북 키워드를 매칭하여 PromptBlock 리스트를 반환한다.

    알고리즘 (spec.md §12.4):
    1. recent_messages에서 마지막 scan_messages개를 결합하여 검색 텍스트를 만든다.
    2. 각 활성 엔트리의 activation_keys를 casefold하여 검색 텍스트에 포함되는지 확인한다.
    3. 매칭된 엔트리를 priority 내림차순 → title 오름차순으로 정렬한다.
    4. 최대 max_entries개까지 선택하되, 누적 토큰이 max_tokens를 초과하면 중단한다.

    Args:
        entries: 전체 LoreEntry 리스트 (활성/비활성 포함).
        recent_messages: 최근 메시지 텍스트 리스트 (오래된 것부터).
        max_entries: 최대 선택 엔트리 수.
        max_tokens: 최대 누적 토큰 수.
        scan_messages: 스캔할 최근 메시지 수.

    Returns:
        매칭된 PromptBlock 리스트.
    """
    # 1. 검색 텍스트 생성: 마지막 scan_messages개 결합 후 casefold
    scan_texts = recent_messages[-scan_messages:]
    search_text = " ".join(scan_texts).casefold()

    if not search_text.strip():
        return []

    # 2. 활성 엔트리 중 키워드 매칭
    matched: list[LoreEntryData] = []
    for entry in entries:
        if not entry.enabled:
            continue
        # activation_keys 중 하나라도 검색 텍스트에 포함되면 매칭
        for key in entry.activation_keys:
            if key.casefold() in search_text:
                matched.append(entry)
                break

    # 3. priority 내림차순 → title 오름차순 정렬
    matched.sort(key=lambda e: (-e.priority, e.title))

    # 4. max_entries, max_tokens 제한 적용
    result: list[PromptBlock] = []
    total_tokens = 0
    for entry in matched:
        if len(result) >= max_entries:
            break
        tokens = estimate_tokens(entry.content)
        if total_tokens + tokens > max_tokens:
            break
        result.append(PromptBlock.create(
            kind="lorebook",
            content=entry.content,
            source_id=entry.id,
        ))
        total_tokens += tokens

    logger.debug("로어북 매칭: %d/%d 엔트리, %d 토큰", len(result), len(matched), total_tokens)
    return result
