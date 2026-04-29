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
    ) -> AssembledPrompt:
        """ChatProfile 기반으로 프롬프트를 조립한다.

        Args:
            chat_profile_id: 채팅 프로필 ID.
            user_persona_id: 사용자 페르소나 ID.
            history_messages: [(role, content), ...] 오래된 것부터.
            current_input: 현재 사용자 입력.
            context_budget: 컨텍스트 윈도우 토큰 수.
            max_output_tokens: 최대 출력 토큰 수.

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
        ai_ids = json.loads(cp.ai_persona_ids_json)
        ai_parts: list[str] = []
        for aid in ai_ids:
            ai = self._repos.ai_personas.get_by_id(aid)
            if ai and ai.enabled:
                parts = [f"[{ai.role_name}]", f"성격: {ai.personality}", f"말투: {ai.speaking_style}"]
                if ai.goals: parts.append(f"목표: {ai.goals}")
                if ai.restrictions: parts.append(f"제한: {ai.restrictions}")
                ai_parts.append("\n".join(parts))
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
            for entry in self._repos.lore_entries.get_by_lorebook(lid):
                all_lore_entries.append(LoreEntryData(
                    id=entry.id,
                    lorebook_id=entry.lorebook_id,
                    title=entry.title,
                    activation_keys=json.loads(entry.activation_keys_json),
                    content=entry.content,
                    priority=entry.priority,
                    enabled=bool(entry.enabled),
                ))

        recent_texts = [content for _, content in history_messages[-8:]]
        recent_texts.append(current_input)
        lb_blocks = match_lore_entries(all_lore_entries, recent_texts)

        # 조립
        return assemble_prompt(
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
        )
