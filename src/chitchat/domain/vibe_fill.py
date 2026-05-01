# src/chitchat/domain/vibe_fill.py
# [v0.2.0] Vibe Fill 프롬프트 템플릿 및 응답 파싱
#
# Phase 1: 바이브 텍스트 → AI Persona 14개 필드 자동 생성
# Phase 2: 바이브 텍스트 (+ 캐릭터 컨텍스트) → 로어 엔트리 복수 건 자동 생성
# Phase 3: 바이브 텍스트 (+ 캐릭터 + 로어북) → 세계관 엔트리 청크 분할 생성
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
# Phase 1: AI Persona Vibe Fill
# ============================================================

# AI 캐릭터 생성 시스템 프롬프트
# 바이브에 명시적으로 언급된 내용은 충실히 반영하고,
# 미언급 항목은 바이브의 분위기에서 가장 개연성 있는 내용을 추론하여 채운다.
VIBE_FILL_SYSTEM_PROMPT = """\
당신은 창작 AI 캐릭터 디자이너입니다.
사용자가 캐릭터의 '바이브'(분위기, 느낌, 핵심 컨셉)를 자유롭게 설명하면,
그 바이브를 바탕으로 14개 필드를 채워 생동감 있고 개연성 있는 캐릭터를 만들어주세요.

## 규칙

1. **바이브 우선**: 사용자가 언급한 내용은 최대한 충실하게 반영합니다.
2. **개연성 추론**: 언급되지 않은 항목은 바이브의 분위기에서 가장 자연스러운 내용으로 추론합니다.
3. **캐릭터 일관성**: 모든 필드가 하나의 인물로서 서로 모순 없이 어울려야 합니다.
4. **구체성**: 추상적이지 않고, 롤플레이에서 즉시 사용할 수 있을 만큼 구체적으로 작성합니다.
5. **말투 필드**: 실제 대사 예시를 1~2개 포함하여 캐릭터의 목소리를 들려줍니다.
6. **응답 언어**: 반드시 {output_language}로 모든 내용을 작성합니다.

## 출력 형식

반드시 아래 JSON 형식으로만 응답하세요. 다른 설명이나 마크다운 없이 순수 JSON만 출력합니다.

```json
{
  "name": "캐릭터 이름",
  "age": "나이 또는 나이대",
  "gender": "성별 또는 정체성",
  "role_name": "세계 내 직업 또는 역할",
  "appearance": "시각적 외모 묘사 (의상, 특징 등 포함)",
  "backstory": "과거 경험과 배경 이야기",
  "personality": "핵심 성격 특성",
  "speaking_style": "대화 패턴, 어투, 말버릇. 대사 예시 1~2개 포함",
  "relationships": "주요 인간관계와 네트워크",
  "skills": "특수 능력, 재능, 전문 분야",
  "interests": "취미, 관심사, 여가 활동",
  "weaknesses": "약점, 두려움, 트라우마",
  "goals": "캐릭터가 추구하는 목표와 행동 방향",
  "restrictions": "캐릭터가 절대 하지 않는 것, 행동 제한"
}
```"""

# 14개 필드 키 목록 (JSON 파싱 검증용)
PERSONA_FIELD_KEYS = [
    "name", "age", "gender", "role_name",
    "appearance", "backstory", "personality", "speaking_style",
    "relationships", "skills", "interests", "weaknesses",
    "goals", "restrictions",
]


@dataclass
class VibeFillResult:
    """Vibe Fill LLM 응답 파싱 결과.

    success=True이면 fields에 14개 필드가 채워져 있다.
    success=False이면 error에 실패 사유가 기록된다.
    """
    success: bool
    fields: dict[str, str] = field(default_factory=dict)
    error: str = ""
    raw_response: str = ""


def get_vibe_system_prompt(output_language: str = DEFAULT_OUTPUT_LANGUAGE) -> str:
    """출력 언어가 적용된 Vibe Fill 시스템 프롬프트를 반환한다.

    Args:
        output_language: 출력 언어 코드 ("ko" 또는 "en").

    Returns:
        출력 언어가 적용된 시스템 프롬프트.
    """
    lang_name = OUTPUT_LANGUAGE_NAMES.get(output_language, OUTPUT_LANGUAGE_NAMES[DEFAULT_OUTPUT_LANGUAGE])
    return VIBE_FILL_SYSTEM_PROMPT.replace("{output_language}", lang_name)


def build_vibe_prompt(vibe_text: str) -> str:
    """바이브 텍스트를 사용자 메시지로 변환한다.

    시스템 프롬프트와 함께 사용되어 LLM에 전송된다.

    Args:
        vibe_text: 사용자가 입력한 캐릭터 바이브 텍스트.

    Returns:
        LLM에 전송할 사용자 메시지.
    """
    return f"아래 바이브를 바탕으로 캐릭터를 만들어주세요:\n\n{vibe_text}"


def _extract_json(raw_text: str) -> str:
    """LLM 응답에서 JSON 문자열을 추출하는 공통 유틸리티.

    1. ```json ... ``` 패턴 우선 추출
    2. 최외곽 { } 또는 [ ] 추출

    Args:
        raw_text: LLM 원문 응답.

    Returns:
        추출된 JSON 문자열.
    """
    json_str = raw_text.strip()

    # ```json ... ``` 패턴 추출
    json_block_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", json_str, re.DOTALL)
    if json_block_match:
        json_str = json_block_match.group(1).strip()

    # 최외곽 { } 추출 (단일 객체)
    if not json_str.startswith("{") and not json_str.startswith("["):
        brace_match = re.search(r"[\{\[].*[\}\]]", json_str, re.DOTALL)
        if brace_match:
            json_str = brace_match.group(0)

    return json_str


def parse_vibe_response(raw_text: str) -> VibeFillResult:
    """LLM 응답에서 14개 필드 JSON을 추출하고 파싱한다.

    JSON 블록(```json ... ```)이 있으면 그 안의 내용을 파싱하고,
    없으면 전체 텍스트를 JSON으로 파싱한다.

    Args:
        raw_text: LLM의 원문 응답.

    Returns:
        VibeFillResult — 성공 시 14개 필드가 채워짐.
    """
    result = VibeFillResult(success=False, raw_response=raw_text)

    json_str = _extract_json(raw_text)

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        result.error = f"JSON 파싱 실패: {e}"
        logger.warning("Vibe Fill JSON 파싱 실패: %s", e)
        return result

    if not isinstance(data, dict):
        result.error = "응답이 JSON 객체가 아닙니다."
        return result

    # 필드 추출 — 존재하지 않는 키는 빈 문자열로 대체
    fields: dict[str, str] = {}
    for key in PERSONA_FIELD_KEYS:
        value = data.get(key, "")
        # 값이 문자열이 아니면 문자열로 변환
        fields[key] = str(value) if value is not None else ""

    # 필수 필드 검증 (name, role_name, personality, speaking_style)
    missing = [k for k in ("name", "role_name", "personality", "speaking_style") if not fields.get(k)]
    if missing:
        result.error = f"필수 필드 누락: {', '.join(missing)}"
        result.fields = fields  # 부분 결과도 전달
        return result

    result.success = True
    result.fields = fields
    logger.info("Vibe Fill 파싱 성공: 캐릭터 '%s'", fields.get("name", "?"))
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

    # 이전 청크 결과 (연쇄 컨텍스트)
    if prev_titles:
        parts.append("[이전 생성 결과 — 아래와 일관성을 유지하세요]")
        for t in prev_titles:
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
