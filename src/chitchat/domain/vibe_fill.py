# src/chitchat/domain/vibe_fill.py
# [v1.0.0] Vibe Fill 프롬프트 템플릿 및 응답 파싱
#
# [v0.2.0 → v1.0.0 변경사항]
# - Phase 1: 14필드 정적 AI Persona 생성 → VibeSmith 9섹션 동적 페르소나 생성으로 전면 교체
# - 삭제 사유: 14필드 플랫 구조에서 9섹션 동적 구조(VibeSmith)로 페르소나 아키텍처 전환
# - 삭제 버전: v1.0.0
# - Phase 2 (로어북), Phase 3 (월드북)은 기존 로직 유지
#
# 이 모듈은 외부 라이브러리에 의존하지 않는 순수 도메인 로직이다.

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# [v0.3.0] 출력 언어 코드 → 자연어 이름 매핑
# Vibe Fill AI 출력 언어를 사용자가 선택할 수 있게 한다.
OUTPUT_LANGUAGE_NAMES: dict[str, str] = {
    "ko": "한국어(Korean)",
    "en": "English",
}

# 기본 출력 언어
DEFAULT_OUTPUT_LANGUAGE = "ko"

# ============================================================
# Phase 1: VibeSmith 9섹션 동적 페르소나 생성 (v1.0.0)
# ============================================================

# VibeSmith 스타일 페르소나 생성 시스템 프롬프트
# 사용자의 짧은 바이브 입력에서 9개 섹션으로 구성된 완전한 캐릭터를 생성한다.
VIBESMITH_SYSTEM_PROMPT = """\
당신은 VibeSmith — 동적 페르소나 생성기입니다.
사용자의 짧은 바이브(분위기, 느낌, 키워드)를 입력받아
9개 섹션으로 구성된 살아있는 캐릭터 카드를 생성합니다.

## 핵심 원칙

1. **성격은 고정 레이블이 아니라 동적 함수다**: 캐릭터 행동 = f(고정설정, 동적동기, 기억, 현재맥락)
2. **모든 방어전략은 미충족 욕구에서 비롯된다**: 방어적 행동에는 반드시 이유가 있어야 한다.
3. **관계는 정적 라벨이 아니라 상태 변수다**: trust, familiarity 등 수치로 변화를 추적한다.
4. **기억이 행동을 바꾼다**: 과거 상호작용이 미래 반응에 영향을 미쳐야 한다.
5. **바이브에 명시된 것은 반드시 반영**: 사용자가 언급한 내용은 충실히 포함한다.
6. **미언급 항목은 가장 개연성 있는 내용으로 추론**: 나머지는 분위기에서 자연스럽게 채운다.

## 응답 언어

반드시 {output_language}로 모든 내용을 작성합니다.

## 출력 형식

반드시 아래 JSON 형식으로만 응답하세요. 설명, 마크다운, 코드 블록 감싸기 없이 순수 JSON만 출력합니다.

{{
  "generation_summary": {{
    "input_vibe": "사용자 입력 원문",
    "interpretation": "AI가 해석한 캐릭터 설명",
    "realism_level": "grounded|stylized|dramatic|fantasy|surreal 중 하나",
    "core_tension": "이 캐릭터를 살아있게 만드는 핵심 모순"
  }},
  "fixed_canon": {{
    "identity": {{
      "name": "이름",
      "age": "나이/나이대",
      "gender": "성별",
      "birthday": "생일 또는 계절",
      "cultural_context": "문화적 맥락",
      "current_location": "거주/활동 지역",
      "occupation": "직업/역할",
      "education": "교육"
    }},
    "appearance": {{
      "height": "", "build": "", "face_impression": "",
      "hair": "", "eyes": "", "clothing_style": "",
      "notable_details": "", "usual_posture": "", "voice": ""
    }},
    "living": {{
      "housing": "", "financial_situation": "", "family_structure": "",
      "daily_routine": "", "frequent_places": "", "important_possessions": "",
      "current_life_problem": "", "recent_life_change": ""
    }},
    "skills": {{
      "main_skills": "", "secondary_skills": "", "hobbies": "",
      "private_interests": "", "weak_areas": "", "things_avoided": ""
    }}
  }},
  "core_dynamic": {{
    "core_wants": ["원하는 것1", "원하는 것2"],
    "core_needs": ["필요하지만 인정 못하는 것"],
    "core_fears": ["핵심 공포"],
    "core_tension": "핵심 모순",
    "self_concept": {{"i_am": "나는...", "i_am_not": "나는...이 아니다"}},
    "self_lie": "자기를 보호하지만 제한하는 거짓말",
    "hidden_truth": "관계 발전을 통해 접근하는 숨겨진 진실"
  }},
  "social_model": {{
    "general_style": {{"strangers": "", "friends": "", "authority": ""}},
    "user_represents": "", "wants_from_user": "", "fears_from_user": "",
    "hides_from_user": "", "tests_user": "",
    "trust_builders": "", "trust_breakers": "",
    "relationship_state": {{
      "trust": 30, "familiarity": 20, "emotional_reliance": 10,
      "comfort_with_silence": 40, "willingness_to_initiate": 15,
      "fear_of_rejection": 50, "boundary_sensitivity": 60,
      "topic_comfort": {{}}, "repair_ability": 40
    }}
  }},
  "behavior_rules": {{
    "when_uncertain": "", "when_praised": "", "when_criticized": "",
    "when_ignored": "", "when_user_is_kind": "", "when_user_is_too_direct": "",
    "when_asked_personal": "", "when_talking_hobbies": "",
    "when_feeling_safe": "", "when_overwhelmed": "",
    "when_relationship_improves": "", "when_trust_damaged": ""
  }},
  "habits": {{
    "speech": {{
      "rhythm": "", "common_phrases": [], "verbal_tics": "",
      "when_embarrassed": "", "when_defensive": "", "when_hiding_happiness": ""
    }},
    "body_language": {{
      "nervous_habits": "", "comfort_habits": "", "avoidance_habits": "",
      "signs_of_trust": "", "signs_of_discomfort": "",
      "signs_of_hidden_happiness": "", "signs_of_attachment": ""
    }},
    "everyday": {{
      "mundane_inconvenience": "", "small_comfort_ritual": "",
      "private_preference": "", "social_blind_spot": "",
      "better_than_admitted": "", "worse_than_believed": "",
      "favorite_object": "", "least_favorite_task": ""
    }}
  }},
  "emotional_dynamics": {{
    "default_baseline": "기본 감정 상태",
    "escalation": {{"trigger": "", "interpretation": "", "feeling": "", "behavior": "", "consequence": ""}},
    "recovery": {{"trigger": "", "interpretation": "", "feeling": "", "behavior": "", "consequence": ""}},
    "trust_growth": {{"trigger": "", "interpretation": "", "feeling": "", "behavior": "", "consequence": ""}},
    "trust_damage": {{"trigger": "", "interpretation": "", "feeling": "", "behavior": "", "consequence": ""}}
  }},
  "memory_policy": {{
    "store_triggers": ["약속 이행/불이행", "칭찬", "경계 존중/침범"],
    "effect_mappings": {{"칭찬": "trust+1"}},
    "retrieval_priorities": ["현재 주제", "유사 상황 과거 행동"]
  }},
  "response_rules": {{
    "pre_inference_checks": ["이 순간 캐릭터가 원하는 것은?", "두려운 것은?"],
    "behavior_rules": ["정형화된 반응 금지", "상태에 따라 행동 조절"]
  }},
  "coherence_report": {{
    "checked_areas": {{"경제": "OK", "심리": "OK"}},
    "detected_contradictions": [],
    "repairs_applied": [],
    "productive_tensions": ["핵심 긴장"],
    "final_notes": []
  }}
}}"""


@dataclass
class VibeFillResult:
    """Vibe Fill LLM 응답 파싱 결과.

    [v1.0.0] 9섹션 PersonaCard JSON을 담는다.
    success=True이면 persona_data에 전체 JSON dict가 채워져 있다.
    success=False이면 error에 실패 사유가 기록된다.
    """
    success: bool
    persona_data: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    raw_response: str = ""


def get_vibe_system_prompt(output_language: str = DEFAULT_OUTPUT_LANGUAGE) -> str:
    """출력 언어가 적용된 VibeSmith 시스템 프롬프트를 반환한다."""
    lang_name = OUTPUT_LANGUAGE_NAMES.get(
        output_language, OUTPUT_LANGUAGE_NAMES[DEFAULT_OUTPUT_LANGUAGE],
    )
    return VIBESMITH_SYSTEM_PROMPT.replace("{output_language}", lang_name)


def build_vibe_prompt(vibe_text: str) -> str:
    """바이브 텍스트를 사용자 메시지로 변환한다."""
    return f"아래 바이브를 바탕으로 캐릭터를 만들어주세요:\n\n{vibe_text}"


def _extract_json(raw_text: str) -> str:
    """LLM 응답에서 JSON 문자열을 추출하는 공통 유틸리티."""
    json_str = raw_text.strip()

    # ```json ... ``` 패턴 추출
    json_block_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", json_str, re.DOTALL)
    if json_block_match:
        json_str = json_block_match.group(1).strip()

    # 최외곽 { } 또는 [ ] 추출
    if not json_str.startswith("{") and not json_str.startswith("["):
        brace_match = re.search(r"[\{\[].*[\}\]]", json_str, re.DOTALL)
        if brace_match:
            json_str = brace_match.group(0)

    return json_str


def parse_vibe_response(raw_text: str) -> VibeFillResult:
    """LLM 응답에서 VibeSmith 9섹션 JSON을 추출하고 파싱한다.

    [v1.0.0] 기존 14필드 파서에서 9섹션 JSON 파서로 교체.
    필수 섹션: generation_summary, fixed_canon.
    """
    result = VibeFillResult(success=False, raw_response=raw_text)

    json_str = _extract_json(raw_text)

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        result.error = f"JSON 파싱 실패: {e}"
        logger.warning("VibeSmith JSON 파싱 실패: %s", e)
        return result

    if not isinstance(data, dict):
        result.error = "응답이 JSON 객체가 아닙니다."
        return result

    # 필수 섹션 검증
    required_sections = ["generation_summary", "fixed_canon"]
    missing = [s for s in required_sections if s not in data]
    if missing:
        result.error = f"필수 섹션 누락: {', '.join(missing)}"
        result.persona_data = data
        return result

    # fixed_canon.identity.name 검증
    identity = data.get("fixed_canon", {}).get("identity", {})
    if not identity.get("name"):
        result.error = "캐릭터 이름(fixed_canon.identity.name)이 누락되었습니다."
        result.persona_data = data
        return result

    result.success = True
    result.persona_data = data
    name = identity.get("name", "?")
    logger.info("VibeSmith 파싱 성공: 캐릭터 '%s'", name)
    return result


# ============================================================
# Phase 2: Lorebook Vibe Fill
# ============================================================

# 로어북 엔트리 생성 시스템 프롬프트
# 캐릭터 컨텍스트(선택)와 기존 엔트리 목록(중복 방지)을 주입 슬롯으로 포함한다.
LORE_FILL_SYSTEM_PROMPT = """\
당신은 창작 AI 로어 디자이너입니다.
사용자의 바이브를 바탕으로 롤플레이에 사용할 로어북 엔트리를 생성합니다.

## 로어 엔트리란?

로어 엔트리는 대화 중 특정 키워드가 등장하면 AI에게 주입되는 배경 정보입니다.
아이템, 장소, 이벤트, NPC, 룰, 역사 등 다양한 종류의 세계관 정보를 담습니다.

## 규칙

1. **바이브 우선**: 사용자가 요청한 주제와 분위기를 최대한 반영합니다.
2. **캐릭터 연관**: 캐릭터 정보가 주어지면 그 캐릭터의 세계관에 맞게 생성합니다.
3. **구체성**: 각 엔트리는 롤플레이에서 즉시 참조할 수 있을 만큼 구체적으로 작성합니다.
4. **activation_keys**: 대화에서 트리거될 키워드 목록 (최소 2개). 유의어, 약칭, 관련 표현을 포함합니다.
5. **priority**: 엔트리의 중요도 수치입니다.
   - 핵심 설정/주요 장소: 300~500
   - 일반 아이템/NPC: 100~200
   - 부가 정보/풍미: 50~100
6. **중복 방지**: 기존 엔트리 목록이 주어지면 동일한 주제의 엔트리를 생성하지 않습니다.
7. **최대 10개**: 한 번에 최대 10개까지 생성합니다.
8. **응답 언어**: 반드시 {output_language}로 모든 내용을 작성합니다.

## 출력 형식

반드시 아래 JSON 배열 형식으로만 응답하세요. 다른 설명이나 마크다운 없이 순수 JSON만 출력합니다.

```json
[
  {
    "title": "엔트리 제목",
    "activation_keys": ["키워드1", "키워드2", "키워드3"],
    "content": "롤플레이에서 참조할 구체적인 배경 정보",
    "priority": 200
  }
]
```"""

# 로어 엔트리 필수 키 목록
LORE_ENTRY_KEYS = ["title", "activation_keys", "content", "priority"]


@dataclass
class LoreFillResult:
    """Lore Fill LLM 응답 파싱 결과.

    success=True이면 entries에 파싱된 엔트리 리스트가 들어간다.
    각 엔트리는 {"title", "activation_keys", "content", "priority"} dict.
    success=False이면 error에 실패 사유가 기록된다.
    """
    success: bool
    entries: list[dict[str, Any]] = field(default_factory=list)
    error: str = ""
    raw_response: str = ""


def get_lore_system_prompt(output_language: str = DEFAULT_OUTPUT_LANGUAGE) -> str:
    """출력 언어가 적용된 Lore Fill 시스템 프롬프트를 반환한다.

    Args:
        output_language: 출력 언어 코드 ("ko" 또는 "en").

    Returns:
        출력 언어가 적용된 시스템 프롬프트.
    """
    lang_name = OUTPUT_LANGUAGE_NAMES.get(output_language, OUTPUT_LANGUAGE_NAMES[DEFAULT_OUTPUT_LANGUAGE])
    return LORE_FILL_SYSTEM_PROMPT.replace("{output_language}", lang_name)


def build_lore_prompt(
    vibe_text: str,
    persona_sheet: str | None = None,
    existing_entries: list[tuple[str, list[str]]] | None = None,
) -> str:
    """로어북 바이브 프롬프트를 조립한다.

    캐릭터 시트(선택)와 기존 엔트리 목록(중복 방지)을 포함하여
    LLM 사용자 메시지를 생성한다.

    Args:
        vibe_text: 사용자가 입력한 로어 바이브 텍스트.
        persona_sheet: Phase 1에서 생성된 AI Persona 캐릭터 시트 텍스트.
            None이면 캐릭터 참조 없이 생성한다.
        existing_entries: 기존 엔트리의 (제목, 키워드 리스트) 튜플 목록.
            중복 방지를 위해 프롬프트에 포함된다.

    Returns:
        LLM에 전송할 사용자 메시지.
    """
    parts: list[str] = []

    # 캐릭터 참조 (선택)
    if persona_sheet:
        parts.append("[캐릭터 참조]")
        parts.append("---")
        parts.append(persona_sheet)
        parts.append("---")
        parts.append("")

    # 기존 엔트리 목록 (중복 방지)
    if existing_entries:
        parts.append("[기존 엔트리 — 아래 주제와 중복되지 않도록 하세요]")
        for title, keys in existing_entries:
            key_str = ", ".join(keys)
            parts.append(f'- "{title}" (키: {key_str})')
        parts.append("")

    # 바이브 텍스트
    parts.append(f"아래 바이브를 바탕으로 로어 엔트리를 생성해주세요:\n\n{vibe_text}")

    return "\n".join(parts)


def parse_lore_response(raw_text: str) -> LoreFillResult:
    """LLM 응답에서 로어 엔트리 JSON 배열을 추출하고 파싱한다.

    JSON 배열 [...] 또는 마크다운 JSON 블록에서 배열을 추출한다.
    각 엔트리의 필수 필드(title, activation_keys, content, priority)를 검증한다.

    Args:
        raw_text: LLM의 원문 응답.

    Returns:
        LoreFillResult — 성공 시 entries에 파싱된 엔트리 리스트.
    """
    result = LoreFillResult(success=False, raw_response=raw_text)

    json_str = _extract_json(raw_text)

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        result.error = f"JSON 파싱 실패: {e}"
        logger.warning("Lore Fill JSON 파싱 실패: %s", e)
        return result

    # 단일 객체가 오면 배열로 감싸기
    if isinstance(data, dict):
        data = [data]

    if not isinstance(data, list):
        result.error = "응답이 JSON 배열이 아닙니다."
        return result

    if not data:
        result.error = "빈 배열이 반환되었습니다."
        return result

    # 각 엔트리 검증 및 정규화
    valid_entries: list[dict[str, Any]] = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            logger.warning("Lore Fill 엔트리 #%d: dict가 아님, 스킵", i)
            continue

        title = str(item.get("title", "")).strip()
        if not title:
            logger.warning("Lore Fill 엔트리 #%d: title 누락, 스킵", i)
            continue

        # activation_keys 정규화 — 문자열 배열이어야 함
        raw_keys = item.get("activation_keys", [])
        if isinstance(raw_keys, str):
            # 쉼표 구분 문자열을 리스트로 변환
            keys = [k.strip() for k in raw_keys.split(",") if k.strip()]
        elif isinstance(raw_keys, list):
            keys = [str(k).strip() for k in raw_keys if k]
        else:
            keys = [title]  # 키가 없으면 제목을 키로 사용

        if not keys:
            keys = [title]

        content = str(item.get("content", "")).strip()
        if not content:
            logger.warning("Lore Fill 엔트리 #%d '%s': content 누락, 스킵", i, title)
            continue

        # priority 정규화 — 정수여야 하며 0~1000 범위
        raw_priority = item.get("priority", 100)
        try:
            priority = max(0, min(1000, int(raw_priority)))
        except (ValueError, TypeError):
            priority = 100

        valid_entries.append({
            "title": title,
            "activation_keys": keys,
            "content": content,
            "priority": priority,
        })

    if not valid_entries:
        result.error = "유효한 엔트리가 없습니다."
        return result

    result.success = True
    result.entries = valid_entries
    logger.info("Lore Fill 파싱 성공: %d개 엔트리", len(valid_entries))
    return result


# ============================================================
# Phase 3: Worldbook Vibe Fill
# ============================================================


@dataclass
class WorldCategory:
    """세계관 카테고리 정의.

    key: 내부 식별자 (예: "history")
    label: UI 표시 이름 (예: "역사")
    description: AI에게 전달할 설명
    default_priority: 생성 시 기본 우선순위
    """
    key: str
    label: str
    description: str
    default_priority: int


# 10개 세계관 카테고리 정의
WORLD_CATEGORIES: list[WorldCategory] = [
    WorldCategory("history", "역사", "세계의 주요 사건, 전쟁, 전환점, 연대기", 400),
    WorldCategory("geography", "지리", "대륙, 지형, 기후, 주요 지역, 바다", 350),
    WorldCategory("factions", "세력/국가", "국가, 조직, 단체, 파벌, 정치 구조", 350),
    WorldCategory("races", "종족", "존재하는 종족과 그 특성, 문화적 차이", 300),
    WorldCategory("magic_tech", "마법/기술", "마법 체계, 기술 수준, 에너지원", 300),
    WorldCategory("economy", "경제", "화폐, 교역, 자원, 산업", 200),
    WorldCategory("religion", "종교/신화", "신앙, 신, 창조 신화, 의식", 250),
    WorldCategory("dungeons", "던전/위험지대", "위험한 장소, 미지의 영역, 금지 구역", 200),
    WorldCategory("culture", "일상/문화", "생활 양식, 축제, 음식, 풍습, 예술", 150),
    WorldCategory("rules", "규칙/법칙", "세계의 물리 법칙, 특수 규칙, 제약", 400),
]

# 카테고리 키 → WorldCategory 매핑
WORLD_CATEGORY_MAP: dict[str, WorldCategory] = {c.key: c for c in WORLD_CATEGORIES}

# 청크 분할 설정: 카테고리를 2~3개씩 묶어 여러 번 LLM 호출
# 토큰 제한을 넘지 않도록 한 번에 2~3개만 생성
WORLD_CATEGORY_CHUNKS: list[list[str]] = [
    ["history", "geography", "factions"],    # 청크 1: 세계의 큰 그림
    ["races", "magic_tech", "economy"],       # 청크 2: 구성 요소
    ["religion", "dungeons"],                  # 청크 3: 미스터리
    ["culture", "rules"],                      # 청크 4: 일상과 법칙
]


# 세계관 엔트리 생성 시스템 프롬프트
WORLD_FILL_SYSTEM_PROMPT = """\
당신은 창작 AI 세계관 설계자입니다.
사용자의 바이브를 바탕으로 세계관의 특정 측면에 대한 엔트리를 생성합니다.

## 세계관 엔트리란?

세계관 엔트리는 롤플레이 시 AI에게 항상 주입되는 배경 설정입니다.
역사, 지리, 세력, 종족, 마법 체계 등 세계의 뼈대를 구성합니다.

## 규칙

1. **바이브 우선**: 사용자가 요청한 분위기와 방향을 최대한 반영합니다.
2. **캐릭터/로어 연관**: 캐릭터나 로어북 정보가 주어지면 그것과 자연스럽게 연결합니다.
3. **카테고리별 생성**: 지정된 카테고리에 맞는 엔트리만 생성합니다.
4. **title 접두사**: 제목에 반드시 [카테고리] 접두사를 포함합니다. 예: "[역사] 대붕괴 전쟁"
5. **구체성**: 롤플레이에서 즉시 참조할 수 있을 만큼 구체적으로 작성합니다.
6. **카테고리 간 일관성**: 생성된 모든 엔트리가 하나의 세계관으로 모순 없이 연결되어야 합니다.
7. **priority**: 카테고리별 기본값을 따르되 엔트리 중요도에 따라 조정합니다.
8. **최대 10개**: 한 번에 최대 10개까지 생성합니다.
9. **이전 결과 참조**: 이전에 생성된 엔트리 제목이 주어지면 그것과 일관성을 유지합니다.
10. **응답 언어**: 반드시 {output_language}로 모든 내용을 작성합니다.

## 출력 형식

반드시 아래 JSON 배열 형식으로만 응답하세요.

```json
[
  {
    "title": "[카테고리] 엔트리 제목",
    "category": "카테고리키",
    "content": "세계관 배경 정보",
    "priority": 300
  }
]
```"""


@dataclass
class WorldFillResult:
    """World Fill LLM 응답 파싱 결과.

    success=True이면 entries에 파싱된 엔트리 리스트가 들어간다.
    각 엔트리는 {"title", "category", "content", "priority"} dict.
    """
    success: bool
    entries: list[dict[str, Any]] = field(default_factory=list)
    error: str = ""
    raw_response: str = ""


def get_chunks_for_categories(category_keys: list[str]) -> list[list[str]]:
    """선택된 카테고리 키를 청크로 분할한다.

    WORLD_CATEGORY_CHUNKS 기준으로 선택된 카테고리만 필터링하여
    실제 호출할 청크 목록을 반환한다. 빈 청크는 제외한다.

    Args:
        category_keys: 사용자가 선택한 카테고리 키 목록.

    Returns:
        청크별 카테고리 키 리스트의 리스트.
    """
    selected = set(category_keys)
    chunks: list[list[str]] = []
    for chunk_template in WORLD_CATEGORY_CHUNKS:
        filtered = [k for k in chunk_template if k in selected]
        if filtered:
            chunks.append(filtered)
    return chunks


def get_world_system_prompt(output_language: str = DEFAULT_OUTPUT_LANGUAGE) -> str:
    """출력 언어가 적용된 World Fill 시스템 프롬프트를 반환한다.

    Args:
        output_language: 출력 언어 코드 ("ko" 또는 "en").

    Returns:
        출력 언어가 적용된 시스템 프롬프트.
    """
    lang_name = OUTPUT_LANGUAGE_NAMES.get(output_language, OUTPUT_LANGUAGE_NAMES[DEFAULT_OUTPUT_LANGUAGE])
    return WORLD_FILL_SYSTEM_PROMPT.replace("{output_language}", lang_name)


def build_world_prompt(
    vibe_text: str,
    categories: list[WorldCategory],
    persona_sheet: str | None = None,
    lore_summaries: list[str] | None = None,
    prev_titles: list[str] | None = None,
) -> str:
    """세계관 바이브 프롬프트를 조립한다.

    캐릭터 시트(선택), 로어북 요약(선택), 이전 청크 결과 제목(연쇄),
    생성 대상 카테고리 목록을 포함하여 LLM 사용자 메시지를 생성한다.

    Args:
        vibe_text: 사용자가 입력한 세계관 바이브 텍스트.
        categories: 이번 청크에서 생성할 카테고리 목록.
        persona_sheet: AI Persona 캐릭터 시트 텍스트 (선택).
        lore_summaries: 로어북 엔트리 요약 목록 (선택).
        prev_titles: 이전 청크에서 생성된 엔트리 제목 목록 (연쇄 컨텍스트).

    Returns:
        LLM에 전송할 사용자 메시지.
    """
    parts: list[str] = []

    # 이번에 생성할 카테고리 안내
    parts.append("[이번에 생성할 카테고리]")
    for cat in categories:
        parts.append(f"- {cat.label} ({cat.key}): {cat.description} [기본 priority: {cat.default_priority}]")
    parts.append("")

    # 캐릭터 참조 (선택)
    if persona_sheet:
        parts.append("[캐릭터 참조]")
        parts.append("---")
        parts.append(persona_sheet)
        parts.append("---")
        parts.append("")

    # 로어북 참조 (선택)
    if lore_summaries:
        parts.append("[로어북 참조]")
        for s in lore_summaries:
            parts.append(f"- {s}")
        parts.append("")

    # [v1.1.1] 이전 청크 결과 (연쇄 컨텍스트) — 방어 로직 적용
    # 최대 30개로 클램핑하고, 특수문자를 제거하여 프롬프트 인젝션 방지
    _MAX_PREV_TITLES = 30
    if prev_titles:
        # 특수문자 제거 + 길이 클램핑 (제목당 50자)
        import re
        safe_titles = [
            re.sub(r'[\\`{}\[\]<>|]', '', t)[:50]
            for t in prev_titles[:_MAX_PREV_TITLES]
        ]
        parts.append("[이전 생성 결과 — 아래와 일관성을 유지하세요]")
        for t in safe_titles:
            parts.append(f'- "{t}"')
        parts.append("")

    # 바이브 텍스트
    parts.append(f"아래 바이브를 바탕으로 세계관 엔트리를 생성해주세요:\n\n{vibe_text}")

    return "\n".join(parts)


def parse_world_response(raw_text: str) -> WorldFillResult:
    """LLM 응답에서 세계관 엔트리 JSON 배열을 추출하고 파싱한다.

    parse_lore_response와 유사하지만, category 필드를 추가로 검증한다.

    Args:
        raw_text: LLM의 원문 응답.

    Returns:
        WorldFillResult — 성공 시 entries에 파싱된 엔트리 리스트.
    """
    result = WorldFillResult(success=False, raw_response=raw_text)

    json_str = _extract_json(raw_text)

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        result.error = f"JSON 파싱 실패: {e}"
        logger.warning("World Fill JSON 파싱 실패: %s", e)
        return result

    # 단일 객체 → 배열 감싸기
    if isinstance(data, dict):
        data = [data]

    if not isinstance(data, list):
        result.error = "응답이 JSON 배열이 아닙니다."
        return result

    if not data:
        result.error = "빈 배열이 반환되었습니다."
        return result

    # 각 엔트리 검증 및 정규화
    valid_entries: list[dict[str, Any]] = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            logger.warning("World Fill 엔트리 #%d: dict가 아님, 스킵", i)
            continue

        title = str(item.get("title", "")).strip()
        if not title:
            logger.warning("World Fill 엔트리 #%d: title 누락, 스킵", i)
            continue

        content = str(item.get("content", "")).strip()
        if not content:
            logger.warning("World Fill 엔트리 #%d '%s': content 누락, 스킵", i, title)
            continue

        # category 정규화 — 유효한 카테고리 키인지 확인
        category = str(item.get("category", "")).strip()
        if category not in WORLD_CATEGORY_MAP:
            # title에서 [카테고리] 접두사 추출 시도
            bracket_match = re.match(r"\[(.+?)\]", title)
            if bracket_match:
                label = bracket_match.group(1)
                # 라벨 → 키 역매핑
                for cat in WORLD_CATEGORIES:
                    if cat.label == label:
                        category = cat.key
                        break
            if category not in WORLD_CATEGORY_MAP:
                category = ""  # 알 수 없는 카테고리

        # priority 정규화
        raw_priority = item.get("priority", 100)
        try:
            priority = max(0, min(1000, int(raw_priority)))
        except (ValueError, TypeError):
            # 카테고리 기본 priority 사용
            cat_obj = WORLD_CATEGORY_MAP.get(category)
            priority = cat_obj.default_priority if cat_obj else 100

        valid_entries.append({
            "title": title,
            "category": category,
            "content": content,
            "priority": priority,
        })

    if not valid_entries:
        result.error = "유효한 엔트리가 없습니다."
        return result

    result.success = True
    result.entries = valid_entries
    logger.info("World Fill 파싱 성공: %d개 엔트리", len(valid_entries))
    return result
