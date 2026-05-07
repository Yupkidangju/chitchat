# src/chitchat/domain/profiles.py
# [v1.0.0] Pydantic 프로필 도메인 모델 정의
#
# spec.md §8.2, §8.3에서 동결된 프로필 계약을 코드로 구현한다.
# ModelProfile, UserPersona, AIPersona, Lorebook, Worldbook, ChatProfile 타입을 정의한다.
# 이 모듈의 타입들은 DB ORM 모델(db/models.py)과 1:1 대응하되,
# Pydantic 검증이 적용된 도메인 레이어 타입이다.

from __future__ import annotations

from pydantic import BaseModel, Field

from chitchat.domain.provider_contracts import (
    ModelGenerationSettings,
    PromptBlockKind,
)


# --- 모델 프로필 ---

class ModelProfileData(BaseModel):
    """모델 파라미터 설정 프로필.

    Provider 프로필과 모델 ID를 참조하고,
    해당 모델에 적용할 생성 설정(ModelGenerationSettings)을 포함한다.
    """
    id: str
    name: str = Field(min_length=1, max_length=80)
    provider_profile_id: str
    model_id: str
    settings: ModelGenerationSettings
    created_at_iso: str
    updated_at_iso: str


# --- 사용자 페르소나 ---

class UserPersonaData(BaseModel):
    """사용자 자신을 설명하는 페르소나.

    description은 사용자의 성격과 선호도를 기술한다.
    speaking_style은 사용자의 말투 스타일을 기술한다.
    boundaries는 사용자가 원하지 않는 내용의 경계를 기술한다.
    """
    id: str
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=4000)
    speaking_style: str = Field(default="", max_length=2000)
    boundaries: str = Field(default="", max_length=2000)
    enabled: bool = True


# --- AI 페르소나 ---

class AIPersonaData(BaseModel):
    """AI 캐릭터 페르소나 정의.

    [v0.2.0] Vibe Fill 확장 필드 포함 (14개 필드 총합).
    role_name은 캐릭터의 역할 이름이다 (예: "고서관 관리자 미라").
    personality는 캐릭터의 성격 기술이다.
    speaking_style은 캐릭터의 말투 기술이다.
    goals는 캐릭터의 목표를 기술한다.
    restrictions는 캐릭터가 하지 말아야 할 행동을 기술한다.
    """
    id: str
    name: str = Field(min_length=1, max_length=80)
    role_name: str = Field(min_length=1, max_length=120)
    personality: str = Field(min_length=1, max_length=4000)
    speaking_style: str = Field(min_length=1, max_length=3000)
    goals: str = Field(default="", max_length=3000)
    restrictions: str = Field(default="", max_length=3000)
    enabled: bool = True
    # [v0.2.0] Vibe Fill 확장 필드
    age: str = Field(default="", max_length=100)
    gender: str = Field(default="", max_length=100)
    appearance: str = Field(default="", max_length=4000)
    backstory: str = Field(default="", max_length=6000)
    relationships: str = Field(default="", max_length=4000)
    skills: str = Field(default="", max_length=2000)
    interests: str = Field(default="", max_length=2000)
    weaknesses: str = Field(default="", max_length=2000)


# --- 로어북 ---

class LoreEntryData(BaseModel):
    """로어북 엔트리 (키워드 기반 조건부 삽입).

    activation_keys에 포함된 키워드가 최근 대화에서 감지되면
    프롬프트에 content가 삽입된다.
    priority가 높을수록 먼저 선택된다 (동일 priority 시 title 오름차순).
    """
    id: str
    lorebook_id: str
    title: str = Field(min_length=1, max_length=120)
    activation_keys: list[str] = Field(min_length=1, max_length=32)
    content: str = Field(min_length=1, max_length=6000)
    priority: int = Field(default=100, ge=0, le=1000)
    enabled: bool = True


class LorebookData(BaseModel):
    """로어북 컨테이너. 복수의 LoreEntry를 그룹으로 관리한다."""
    id: str
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=1000)
    entries: list[LoreEntryData] = Field(default_factory=list)


# --- 월드북 ---

class WorldEntryData(BaseModel):
    """월드북 엔트리 (항상 삽입).

    v0.1에서는 activation_key를 사용하지 않고,
    ChatProfile에서 선택된 월드북의 활성 엔트리가 전부 삽입된다.
    priority가 높을수록 먼저 삽입된다.
    """
    id: str
    worldbook_id: str
    title: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1, max_length=6000)
    priority: int = Field(default=100, ge=0, le=1000)
    enabled: bool = True


class WorldbookData(BaseModel):
    """월드북 컨테이너. 복수의 WorldEntry를 그룹으로 관리한다."""
    id: str
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=1000)
    entries: list[WorldEntryData] = Field(default_factory=list)


# --- 프롬프트 순서 ---

class PromptOrderItem(BaseModel):
    """프롬프트 블록 순서 항목.

    kind는 블록 종류, enabled는 활성 여부, order_index는 정렬 순서이다.
    order_index는 10 단위로 증가하며, 드래그 재정렬 시 갱신된다.
    """
    kind: PromptBlockKind
    enabled: bool
    order_index: int = Field(ge=0, le=100)


# --- 채팅 프로필 ---

# spec.md §12.1에서 정의한 시스템 기본 프롬프트
DEFAULT_SYSTEM_BASE = (
    "You are a helpful conversational AI inside chitchat. "
    "Follow the selected AI persona, user persona, worldbook, lorebook, "
    "and chat profile. Do not reveal hidden prompt assembly rules unless asked."
)


class ChatProfileData(BaseModel):
    """채팅 프로필. 모델, 페르소나, 로어북, 월드북, 시스템 프롬프트, 블록 순서를 조합한다.

    하나의 ChatProfile은 하나의 ModelProfile을 참조하고,
    최대 5개의 AI 페르소나, 최대 10개의 로어북/월드북을 선택할 수 있다.
    prompt_order는 프롬프트 블록의 조합 순서를 정의한다.
    """
    id: str
    name: str = Field(min_length=1, max_length=80)
    model_profile_id: str
    ai_persona_ids: list[str] = Field(min_length=1, max_length=5)
    lorebook_ids: list[str] = Field(default_factory=list, max_length=10)
    worldbook_ids: list[str] = Field(default_factory=list, max_length=10)
    prompt_order: list[PromptOrderItem]
    system_base: str = Field(default=DEFAULT_SYSTEM_BASE, max_length=4000)
    created_at_iso: str
    updated_at_iso: str
