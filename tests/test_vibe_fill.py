# tests/test_vibe_fill.py
# [v1.0.0] Vibe Fill 도메인 로직 테스트
#
# [v0.2.0 → v1.0.0 변경사항]
# - VibeFillResult: fields → persona_data (9섹션 JSON)
# - parse_vibe_response: 14필드 → VibeSmith 9섹션 파서
# - Phase 2 (로어북), Phase 3 (월드북) 테스트는 기존 유지

from __future__ import annotations

import json

from chitchat.domain.vibe_fill import (
    LORE_ENTRY_KEYS,
    LORE_FILL_SYSTEM_PROMPT,
    VIBESMITH_SYSTEM_PROMPT,
    WORLD_CATEGORIES,
    WORLD_CATEGORY_CHUNKS,
    WORLD_CATEGORY_MAP,
    WORLD_FILL_SYSTEM_PROMPT,
    LoreFillResult,
    VibeFillResult,
    WorldFillResult,
    build_lore_prompt,
    build_vibe_prompt,
    build_world_prompt,
    get_chunks_for_categories,
    parse_lore_response,
    parse_vibe_response,
    parse_world_response,
)


# ============================================================
# Phase 1: VibeSmith 9섹션 페르소나 테스트 (v1.0.0)
# ============================================================

# 유효한 9섹션 JSON 응답
_VALID_VIBESMITH = json.dumps({
    "generation_summary": {
        "input_vibe": "고서관 관리자",
        "interpretation": "건조한 성격의 고서관 관리자",
        "realism_level": "grounded",
        "core_tension": "지식에 대한 욕구와 고립",
    },
    "fixed_canon": {
        "identity": {
            "name": "미라",
            "age": "24세",
            "gender": "여성",
            "occupation": "고서관 관리자",
        },
        "appearance": {"hair": "은빛 장발"},
        "living": {},
        "skills": {},
    },
    "core_dynamic": {"core_wants": ["지식"]},
    "social_model": {},
    "behavior_rules": {},
    "habits": {},
    "emotional_dynamics": {},
    "memory_policy": {},
    "response_rules": {},
    "coherence_report": {},
}, ensure_ascii=False)


class TestBuildVibePrompt:
    """바이브 프롬프트 조립 테스트."""

    def test_한국어_바이브_변환(self) -> None:
        result = build_vibe_prompt("고서관 관리자인데 건조한 성격")
        assert "고서관 관리자인데 건조한 성격" in result

    def test_빈_바이브_처리(self) -> None:
        result = build_vibe_prompt("")
        assert isinstance(result, str)

    def test_시스템_프롬프트_구조(self) -> None:
        for keyword in ["name", "core_tension", "fixed_canon", "core_dynamic"]:
            assert keyword in VIBESMITH_SYSTEM_PROMPT


class TestParseVibeResponse:
    """VibeSmith 9섹션 JSON 파싱 테스트."""

    def test_순수_JSON_파싱(self) -> None:
        result = parse_vibe_response(_VALID_VIBESMITH)
        assert result.success is True
        assert result.persona_data["fixed_canon"]["identity"]["name"] == "미라"

    def test_마크다운_JSON_블록_파싱(self) -> None:
        wrapped = f"```json\n{_VALID_VIBESMITH}\n```"
        result = parse_vibe_response(wrapped)
        assert result.success is True

    def test_마크다운_json_없이_코드블록(self) -> None:
        wrapped = f"```\n{_VALID_VIBESMITH}\n```"
        result = parse_vibe_response(wrapped)
        assert result.success is True

    def test_앞뒤_텍스트_포함_JSON(self) -> None:
        text = f"캐릭터를 만들었습니다:\n{_VALID_VIBESMITH}\n좋은 캐릭터네요!"
        result = parse_vibe_response(text)
        assert result.success is True

    def test_필수_섹션_누락_시_실패(self) -> None:
        incomplete = json.dumps({"core_dynamic": {}})
        result = parse_vibe_response(incomplete)
        assert result.success is False
        assert "필수 섹션 누락" in result.error

    def test_이름_누락_시_실패(self) -> None:
        no_name = json.dumps({
            "generation_summary": {},
            "fixed_canon": {"identity": {"name": ""}},
        })
        result = parse_vibe_response(no_name)
        assert result.success is False

    def test_잘못된_JSON_실패(self) -> None:
        result = parse_vibe_response("이건 JSON이 아닙니다.")
        assert result.success is False
        assert "JSON 파싱 실패" in result.error

    def test_빈_응답_실패(self) -> None:
        result = parse_vibe_response("")
        assert result.success is False


class TestVibeFillResult:
    """VibeFillResult 데이터클래스 테스트."""

    def test_기본_생성(self) -> None:
        r = VibeFillResult(success=False)
        assert r.success is False
        assert r.persona_data == {}
        assert r.error == ""
        assert r.raw_response == ""

    def test_성공_생성(self) -> None:
        r = VibeFillResult(success=True, persona_data={"fixed_canon": {}})
        assert r.success is True
        assert "fixed_canon" in r.persona_data


# ============================================================
# Phase 2: Lorebook Vibe Fill 테스트 (기존 유지)
# ============================================================

class TestBuildLorePrompt:
    def test_바이브만_입력(self) -> None:
        result = build_lore_prompt("고서관의 유물과 비밀 장소")
        assert "고서관의 유물과 비밀 장소" in result

    def test_캐릭터_시트_포함(self) -> None:
        sheet = "[캐릭터: 미라]\n나이: 24세"
        result = build_lore_prompt("유물 생성", persona_sheet=sheet)
        assert "[캐릭터 참조]" in result

    def test_기존_엔트리_중복방지(self) -> None:
        existing = [("금빛 오라클럼", ["오라클럼", "유물"])]
        result = build_lore_prompt("새 유물 생성", existing_entries=existing)
        assert "기존 엔트리" in result

    def test_시스템_프롬프트_필드_키(self) -> None:
        for key in LORE_ENTRY_KEYS:
            assert f'"{key}"' in LORE_FILL_SYSTEM_PROMPT


class TestParseLoreResponse:
    _VALID = json.dumps([
        {"title": "금빛 오라클럼", "activation_keys": ["오라클럼"], "content": "구체.", "priority": 300},
        {"title": "지하 서고", "activation_keys": ["지하"], "content": "서고.", "priority": 250},
    ], ensure_ascii=False)

    def test_순수_JSON_배열_파싱(self) -> None:
        result = parse_lore_response(self._VALID)
        assert result.success is True
        assert len(result.entries) == 2

    def test_단일_객체_배열_변환(self) -> None:
        single = json.dumps({"title": "깃펜", "activation_keys": ["깃펜"], "content": "설명.", "priority": 200})
        result = parse_lore_response(single)
        assert result.success is True
        assert len(result.entries) == 1

    def test_빈_배열_실패(self) -> None:
        result = parse_lore_response("[]")
        assert result.success is False

    def test_잘못된_JSON_실패(self) -> None:
        result = parse_lore_response("not json")
        assert result.success is False


class TestLoreFillResult:
    def test_기본_생성(self) -> None:
        r = LoreFillResult(success=False)
        assert r.entries == []


# ============================================================
# Phase 3: Worldbook Vibe Fill 테스트 (기존 유지)
# ============================================================

class TestWorldCategories:
    def test_10개_카테고리_존재(self) -> None:
        assert len(WORLD_CATEGORIES) == 10

    def test_카테고리_키_유일성(self) -> None:
        keys = [c.key for c in WORLD_CATEGORIES]
        assert len(keys) == len(set(keys))

    def test_청크_배열_모든_카테고리_포함(self) -> None:
        all_chunk_keys = [k for chunk in WORLD_CATEGORY_CHUNKS for k in chunk]
        all_cat_keys = [c.key for c in WORLD_CATEGORIES]
        assert sorted(all_chunk_keys) == sorted(all_cat_keys)


class TestGetChunksForCategories:
    def test_전체_선택(self) -> None:
        all_keys = [c.key for c in WORLD_CATEGORIES]
        chunks = get_chunks_for_categories(all_keys)
        assert len(chunks) == 4

    def test_빈_선택(self) -> None:
        assert get_chunks_for_categories([]) == []


class TestBuildWorldPrompt:
    _CATS = [WORLD_CATEGORY_MAP["history"], WORLD_CATEGORY_MAP["geography"]]

    def test_바이브만_입력(self) -> None:
        result = build_world_prompt("동양풍 대륙", self._CATS)
        assert "동양풍 대륙" in result

    def test_시스템_프롬프트_필드(self) -> None:
        assert '"title"' in WORLD_FILL_SYSTEM_PROMPT
        assert '"category"' in WORLD_FILL_SYSTEM_PROMPT


class TestParseWorldResponse:
    _VALID = json.dumps([
        {"title": "[역사] 전쟁", "category": "history", "content": "내용.", "priority": 400},
    ], ensure_ascii=False)

    def test_순수_JSON_배열_파싱(self) -> None:
        result = parse_world_response(self._VALID)
        assert result.success is True
        assert len(result.entries) == 1

    def test_빈_배열_실패(self) -> None:
        result = parse_world_response("[]")
        assert result.success is False


class TestWorldFillResult:
    def test_기본_생성(self) -> None:
        r = WorldFillResult(success=False)
        assert r.entries == []
