# src/chitchat/services/prompt_service.py
# [v0.1.0b0] 프롬프트 조립 오케스트레이션 서비스
#
# ChatProfile에서 참조된 엔티티들을 로드하고,
# prompt_assembler + lorebook_matcher를 호출하여 AssembledPrompt를 생성한다.
from __future__ import annotations
import json
import logging
from chitchat.db.repositories import RepositoryRegistry
from chitchat.domain.lorebook_matcher import match_lore_entries
from chitchat.domain.profiles import LoreEntryData
from chitchat.domain.prompt_assembler import assemble_prompt
from chitchat.domain.prompt_blocks import AssembledPrompt, PromptBlock

logger = logging.getLogger(__name__)


class PromptService:
    """프롬프트 조립 오케스트레이션."""

    def __init__(self, repos: RepositoryRegistry) -> None:
        self._repos = repos

    def build_prompt(
        self,
        chat_profile_id: str,
        user_persona_id: str,
        history_messages: list[tuple[str, str]],
        current_input: str,
        context_budget: int,
        max_output_tokens: int = 2048,
        history_message_ids: list[str] | None = None,
    ) -> AssembledPrompt:
        """ChatProfile 기반으로 프롬프트를 조립한다.

        Args:
            chat_profile_id: 채팅 프로필 ID.
            user_persona_id: 사용자 페르소나 ID.
            history_messages: [(role, content), ...] 오래된 것부터.
            current_input: 현재 사용자 입력.
            context_budget: 컨텍스트 윈도우 토큰 수.
            max_output_tokens: 최대 출력 토큰 수.
            history_message_ids: 히스토리 메시지 ID 리스트 (history_messages와 동일 순서).
                전달 시 잘린 메시지의 ID를 AssembledPrompt.truncated_history_message_ids에 기록한다.

        Returns:
            조립 완료된 AssembledPrompt.
        """
        # ChatProfile 로드
        cp = self._repos.chat_profiles.get_by_id(chat_profile_id)
        if not cp:
            raise ValueError(f"ChatProfile을 찾을 수 없습니다: {chat_profile_id}")

        # prompt_order 파싱
        raw_order = json.loads(cp.prompt_order_json)
        prompt_order: list[tuple[str, bool]] = [
            (item["kind"], item["enabled"]) for item in raw_order
        ]

        # UserPersona 텍스트
        up_text: str | None = None
        up = self._repos.user_personas.get_by_id(user_persona_id)
        if up and up.enabled:
            parts = [up.description]
            if up.speaking_style:
                parts.append(f"말투: {up.speaking_style}")
            if up.boundaries:
                parts.append(f"경계: {up.boundaries}")
            up_text = "\n".join(parts)

        # AIPersona 텍스트 (모든 활성 AI 페르소나 결합)
        # [v0.2.0] 14개 필드 구조화된 캐릭터 시트로 조립
        ai_ids = json.loads(cp.ai_persona_ids_json)
        ai_parts: list[str] = []
        for aid in ai_ids:
            ai = self._repos.ai_personas.get_by_id(aid)
            if ai and ai.enabled:
                # 캐릭터 헤더
                header = f"[캐릭터: {ai.name}]"
                lines = [header]
                # 기본 정보 라인 (나이/성별/직업을 한 줄로 결합)
                basic_parts: list[str] = []
                if getattr(ai, "age", ""):
                    basic_parts.append(f"나이: {ai.age}")
                if getattr(ai, "gender", ""):
                    basic_parts.append(f"성별: {ai.gender}")
                basic_parts.append(f"역할: {ai.role_name}")
                lines.append(" / ".join(basic_parts))
                # 확장 필드 (비어 있으면 생략)
                _ext_fields = [
                    ("외모", getattr(ai, "appearance", "")),
                    ("성격", ai.personality),
                    ("말투", ai.speaking_style),
                    ("배경", getattr(ai, "backstory", "")),
                    ("인간관계", getattr(ai, "relationships", "")),
                    ("특기", getattr(ai, "skills", "")),
                    ("취미", getattr(ai, "interests", "")),
                    ("약점", getattr(ai, "weaknesses", "")),
                    ("목표", ai.goals),
                    ("제한", ai.restrictions),
                ]
                for label, value in _ext_fields:
                    if value:
                        lines.append(f"{label}: {value}")
                ai_parts.append("\n".join(lines))
        ai_text = "\n\n".join(ai_parts) if ai_parts else None

        # Worldbook 블록
        wb_ids = json.loads(cp.worldbook_ids_json)
        wb_blocks: list[PromptBlock] = []
        for wid in wb_ids:
            for entry in self._repos.world_entries.get_by_worldbook(wid):
                if entry.enabled:
                    wb_blocks.append(PromptBlock.create("worldbook", entry.content, source_id=entry.id))
        # DB에서 이미 priority desc, title asc 정렬되어 반환됨 (WorldEntryRepository)

        # Lorebook 매칭
        lb_ids = json.loads(cp.lorebook_ids_json)
        all_lore_entries: list[LoreEntryData] = []
        for lid in lb_ids:
            # [v0.1.4] mypy 타입 추론 혼선 방지: WorldEntryRow와 다른 변수명 사용
            for lore_entry in self._repos.lore_entries.get_by_lorebook(lid):
                all_lore_entries.append(LoreEntryData(
                    id=lore_entry.id,
                    lorebook_id=lore_entry.lorebook_id,
                    title=lore_entry.title,
                    activation_keys=json.loads(lore_entry.activation_keys_json),
                    content=lore_entry.content,
                    priority=lore_entry.priority,
                    enabled=bool(lore_entry.enabled),
                ))

        recent_texts = [content for _, content in history_messages[-8:]]
        recent_texts.append(current_input)
        lb_blocks = match_lore_entries(all_lore_entries, recent_texts)

        # 조립
        assembled = assemble_prompt(
            prompt_order=prompt_order,  # type: ignore[arg-type]
            system_base=cp.system_base,
            user_persona_text=up_text,
            ai_persona_text=ai_text,
            worldbook_blocks=wb_blocks,
            lorebook_blocks=lb_blocks,
            history_messages=history_messages,
            current_input=current_input,
            context_budget=context_budget,
            max_output_tokens=max_output_tokens,
            history_message_ids=history_message_ids,
        )

        # [v0.1.4] spec §12.6: matched_lore_entry_ids를 lorebook 블록의 source_id에서 수집
        assembled.matched_lore_entry_ids = [
            b.source_id for b in assembled.blocks
            if b.kind == "lorebook" and b.source_id
        ]

        return assembled
