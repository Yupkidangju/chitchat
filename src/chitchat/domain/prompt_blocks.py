# src/chitchat/domain/prompt_blocks.py
# [v0.1.0b0] 프롬프트 블록 타입 정의
#
# spec.md §12.1~§12.3에서 정의된 프롬프트 블록 구조를 구현한다.
# PromptBlock: 단일 블록 (종류, 내용, 토큰 추정치)
# AssembledPrompt: 조립 완료된 프롬프트 (블록 리스트, 토큰 합산, 메시지 배열)
from __future__ import annotations
from dataclasses import dataclass, field
from chitchat.domain.provider_contracts import PromptBlockKind, Role


def estimate_tokens(text: str) -> int:
    """텍스트의 토큰 수를 근사 추정한다.

    spec.md §12.3: max(1, (len(text) + 3) // 4)
    영어 기준 ~4글자/토큰, 한국어는 더 많으므로 보수적 추정이다.
    """
    return max(1, (len(text) + 3) // 4)


@dataclass
class PromptBlock:
    """프롬프트 블록 단위.

    kind: 블록 종류 (system_base, user_persona, ai_persona, worldbook 등)
    content: 블록의 실제 텍스트 내용
    token_estimate: estimate_tokens()로 계산한 토큰 추정치
    source_id: 원본 엔티티 ID (로어/월드 엔트리 등)
    """
    kind: PromptBlockKind
    content: str
    token_estimate: int
    source_id: str | None = None

    @staticmethod
    def create(kind: PromptBlockKind, content: str, source_id: str | None = None) -> PromptBlock:
        """블록을 생성하고 토큰을 자동 추정한다."""
        return PromptBlock(kind=kind, content=content, token_estimate=estimate_tokens(content), source_id=source_id)


@dataclass
class MessageSlot:
    """최종 메시지 배열의 한 슬롯.

    role: 메시지 역할 (system, user, assistant)
    content: 메시지 내용
    """
    role: Role
    content: str


@dataclass
class AssembledPrompt:
    """조립 완료된 프롬프트.

    blocks: 삽입된 블록 리스트 (순서 보존)
    messages: 최종 메시지 배열 (Provider에 전달)
    total_tokens: 블록 토큰 합산
    history_count: 포함된 히스토리 메시지 수
    truncated_count: 잘린 히스토리 메시지 수
    budget_tokens: 컨텍스트 예산 총 토큰
    """
    blocks: list[PromptBlock] = field(default_factory=list)
    messages: list[MessageSlot] = field(default_factory=list)
    total_tokens: int = 0
    history_count: int = 0
    truncated_count: int = 0
    budget_tokens: int = 0
