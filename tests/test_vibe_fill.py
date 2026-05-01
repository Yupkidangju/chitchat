# tests/test_vibe_fill.py
# [v0.2.0] Vibe Fill 도메인 로직 테스트
#
# Phase 1: 프롬프트 조립, JSON 파싱, 에러 핸들링, 필드 검증을 테스트한다.
# Phase 2: 로어북 프롬프트 조립, JSON 배열 파싱, 엔트리 검증을 테스트한다.
# Phase 3: 세계관 프롬프트 조립, 청크 분할, 카테고리 파싱을 테스트한다.
# Provider LLM 호출은 mock 처리하며, 도메인 로직(vibe_fill.py)을 중점 검증한다.

from __future__ import annotations

import json

from chitchat.domain.vibe_fill import (
    LORE_ENTRY_KEYS,
    LORE_FILL_SYSTEM_PROMPT,
    PERSONA_FIELD_KEYS,
    VIBE_FILL_SYSTEM_PROMPT,
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


class TestBuildVibePrompt:
    """바이브 프롬프트 조립 테스트."""

    def test_한국어_바이브_변환(self) -> None:
        """한국어 바이브 텍스트가 사용자 메시지로 변환된다."""
        result = build_vibe_prompt("고서관 관리자인데 건조한 성격")
        assert "고서관 관리자인데 건조한 성격" in result
        assert "바이브" in result

    def test_빈_바이브_처리(self) -> None:
        """빈 바이브도 프롬프트로 변환된다 (서비스 레벨에서 검증)."""
        result = build_vibe_prompt("")
        assert isinstance(result, str)

    def test_시스템_프롬프트_구조(self) -> None:
        """시스템 프롬프트에 14개 필드가 모두 포함되어 있다."""
        for key in PERSONA_FIELD_KEYS:
            assert f'"{key}"' in VIBE_FILL_SYSTEM_PROMPT, f"시스템 프롬프트에 '{key}' 누락"


class TestParseVibeResponse:
    """Vibe Fill JSON 응답 파싱 테스트."""

    # 정상 JSON 응답 (14개 필드)
    _VALID_RESPONSE = json.dumps({
        "name": "미라",
        "age": "24세",
        "gender": "여성",
        "role_name": "고서관 관리자",
        "appearance": "은빛 장발, 프레임 안경",
        "backstory": "어린 시절 고서관에서 자란 고아",
        "personality": "호기심 많고 친절하지만 엄격",
        "speaking_style": "존대하지만 건조한 말투",
        "relationships": "고양이 '먼지'와 동거",
        "skills": "고대 문자 해독",
        "interests": "차 수집, 고서 복원",
        "weaknesses": "어둠을 무서워함",
        "goals": "방문자 안내, 비밀 수호",
        "restrictions": "고서관 밖 세계에 무관심",
    }, ensure_ascii=False)

    def test_순수_JSON_파싱(self) -> None:
        """순수 JSON 응답이 올바르게 파싱된다."""
        result = parse_vibe_response(self._VALID_RESPONSE)
        assert result.success is True
        assert result.fields["name"] == "미라"
        assert result.fields["age"] == "24세"
        assert result.fields["personality"] == "호기심 많고 친절하지만 엄격"

    def test_마크다운_JSON_블록_파싱(self) -> None:
        """```json ... ``` 블록이 올바르게 파싱된다."""
        wrapped = f"```json\n{self._VALID_RESPONSE}\n```"
        result = parse_vibe_response(wrapped)
        assert result.success is True
        assert result.fields["name"] == "미라"

    def test_마크다운_json_없이_코드블록(self) -> None:
        """``` ... ``` 블록도 파싱된다."""
        wrapped = f"```\n{self._VALID_RESPONSE}\n```"
        result = parse_vibe_response(wrapped)
        assert result.success is True
        assert result.fields["name"] == "미라"

    def test_앞뒤_텍스트_포함_JSON(self) -> None:
        """앞뒤에 설명 텍스트가 포함된 JSON도 추출된다."""
        text = f"캐릭터를 만들었습니다:\n{self._VALID_RESPONSE}\n좋은 캐릭터네요!"
        result = parse_vibe_response(text)
        assert result.success is True
        assert result.fields["role_name"] == "고서관 관리자"

    def test_필수_필드_누락_시_실패(self) -> None:
        """name, role_name, personality, speaking_style 중 하나라도 빠지면 실패."""
        incomplete = json.dumps({
            "name": "미라",
            "role_name": "",  # 빈 문자열
            "personality": "밝은 성격",
            "speaking_style": "반말",
        })
        result = parse_vibe_response(incomplete)
        assert result.success is False
        assert "필수 필드 누락" in result.error

    def test_잘못된_JSON_실패(self) -> None:
        """파싱 불가능한 텍스트는 실패."""
        result = parse_vibe_response("이건 JSON이 아닙니다.")
        assert result.success is False
        assert "JSON 파싱 실패" in result.error

    def test_빈_응답_실패(self) -> None:
        """빈 응답은 실패."""
        result = parse_vibe_response("")
        assert result.success is False

    def test_누락_필드_빈_문자열_보충(self) -> None:
        """JSON에 누락된 필드는 빈 문자열로 채워진다."""
        minimal = json.dumps({
            "name": "카이",
            "role_name": "정보 브로커",
            "personality": "냉소적",
            "speaking_style": "반말",
        })
        result = parse_vibe_response(minimal)
        assert result.success is True
        assert result.fields["age"] == ""
        assert result.fields["weaknesses"] == ""

    def test_14개_필드_키_완전성(self) -> None:
        """성공 시 14개 필드 키가 모두 존재한다."""
        result = parse_vibe_response(self._VALID_RESPONSE)
        assert result.success is True
        for key in PERSONA_FIELD_KEYS:
            assert key in result.fields, f"결과에 '{key}' 키 누락"

    def test_숫자_값_문자열_변환(self) -> None:
        """숫자 값은 문자열로 변환된다."""
        data = json.dumps({
            "name": "테스트",
            "age": 25,  # 숫자
            "role_name": "전사",
            "personality": "용감함",
            "speaking_style": "거친 말투",
        })
        result = parse_vibe_response(data)
        assert result.success is True
        assert result.fields["age"] == "25"

    def test_None_값_빈_문자열_변환(self) -> None:
        """None 값은 빈 문자열로 변환된다."""
        data = json.dumps({
            "name": "테스트",
            "age": None,
            "role_name": "마법사",
            "personality": "차분함",
            "speaking_style": "존댓말",
        })
        result = parse_vibe_response(data)
        assert result.success is True
        assert result.fields["age"] == ""


class TestVibeFillResult:
    """VibeFillResult 데이터클래스 테스트."""

    def test_기본_생성(self) -> None:
        """기본 생성 시 success=False, 빈 fields."""
        r = VibeFillResult(success=False)
        assert r.success is False
        assert r.fields == {}
        assert r.error == ""
        assert r.raw_response == ""

    def test_성공_생성(self) -> None:
        """성공 시 fields가 채워진다."""
        r = VibeFillResult(success=True, fields={"name": "미라"})
        assert r.success is True
        assert r.fields["name"] == "미라"


# ============================================================
# Phase 2: Lorebook Vibe Fill 테스트
# ============================================================


class TestBuildLorePrompt:
    """로어북 바이브 프롬프트 조립 테스트."""

    def test_바이브만_입력(self) -> None:
        """바이브 텍스트만 입력하면 간결한 프롬프트가 생성된다."""
        result = build_lore_prompt("고서관의 유물과 비밀 장소")
        assert "고서관의 유물과 비밀 장소" in result
        assert "로어 엔트리" in result

    def test_캐릭터_시트_포함(self) -> None:
        """캐릭터 시트가 프롬프트에 포함된다."""
        sheet = "[캐릭터: 미라]\n나이: 24세 / 성별: 여성 / 역할: 고서관 관리자"
        result = build_lore_prompt("유물 생성", persona_sheet=sheet)
        assert "[캐릭터 참조]" in result
        assert "미라" in result

    def test_기존_엔트리_중복방지(self) -> None:
        """기존 엔트리 목록이 프롬프트에 포함된다."""
        existing = [
            ("금빛 오라클럼", ["오라클럼", "유물"]),
            ("지하 서고", ["지하", "서고"]),
        ]
        result = build_lore_prompt("새 유물 생성", existing_entries=existing)
        assert "기존 엔트리" in result
        assert "금빛 오라클럼" in result
        assert "지하 서고" in result

    def test_캐릭터_없이_기존_엔트리(self) -> None:
        """캐릭터 없이 기존 엔트리만 있는 경우."""
        existing = [("무언가", ["키1"])]
        result = build_lore_prompt("새 로어", existing_entries=existing)
        assert "[캐릭터 참조]" not in result
        assert "기존 엔트리" in result

    def test_모두_포함(self) -> None:
        """캐릭터 + 기존 엔트리 + 바이브 모두 포함."""
        result = build_lore_prompt(
            "축제와 특산물",
            persona_sheet="[캐릭터: 미라]",
            existing_entries=[("특산물A", ["키A"])],
        )
        assert "[캐릭터 참조]" in result
        assert "기존 엔트리" in result
        assert "축제와 특산물" in result

    def test_시스템_프롬프트_필드_키(self) -> None:
        """로어 시스템 프롬프트에 4개 필드 키가 모두 포함되어 있다."""
        for key in LORE_ENTRY_KEYS:
            assert f'"{key}"' in LORE_FILL_SYSTEM_PROMPT, f"시스템 프롬프트에 '{key}' 누락"


class TestParseLoreResponse:
    """Lore Fill JSON 배열 응답 파싱 테스트."""

    _VALID_RESPONSE = json.dumps([
        {
            "title": "금빛 기억의 오라클럼",
            "activation_keys": ["오라클럼", "유물", "금빛 구체"],
            "content": "고서관 최심부에 보관된 반투명 금빛 구체.",
            "priority": 300,
        },
        {
            "title": "잠긴 지하 서고",
            "activation_keys": ["지하 서고", "금지된 구역"],
            "content": "고서관 지하 3층에 봉인된 서고.",
            "priority": 250,
        },
    ], ensure_ascii=False)

    def test_순수_JSON_배열_파싱(self) -> None:
        """순수 JSON 배열이 올바르게 파싱된다."""
        result = parse_lore_response(self._VALID_RESPONSE)
        assert result.success is True
        assert len(result.entries) == 2
        assert result.entries[0]["title"] == "금빛 기억의 오라클럼"
        assert result.entries[1]["priority"] == 250

    def test_마크다운_JSON_블록(self) -> None:
        """```json ... ``` 블록 파싱."""
        wrapped = f"```json\n{self._VALID_RESPONSE}\n```"
        result = parse_lore_response(wrapped)
        assert result.success is True
        assert len(result.entries) == 2

    def test_앞뒤_텍스트_포함(self) -> None:
        """앞뒤 설명 텍스트가 있어도 JSON 배열을 추출한다."""
        text = f"엔트리를 만들었습니다:\n{self._VALID_RESPONSE}\n즐거운 게임!"
        result = parse_lore_response(text)
        assert result.success is True

    def test_단일_객체_배열_변환(self) -> None:
        """단일 JSON 객체는 배열로 감싸서 처리한다."""
        single = json.dumps({
            "title": "마법의 깃펜",
            "activation_keys": ["깃펜", "마법 도구"],
            "content": "쓰는 대로 실현되는 깃펜.",
            "priority": 200,
        }, ensure_ascii=False)
        result = parse_lore_response(single)
        assert result.success is True
        assert len(result.entries) == 1
        assert result.entries[0]["title"] == "마법의 깃펜"

    def test_title_누락_엔트리_스킵(self) -> None:
        """title이 없는 엔트리는 스킵된다."""
        data = json.dumps([
            {"title": "유효", "activation_keys": ["키"], "content": "내용", "priority": 100},
            {"activation_keys": ["키2"], "content": "내용2", "priority": 50},
        ])
        result = parse_lore_response(data)
        assert result.success is True
        assert len(result.entries) == 1

    def test_content_누락_엔트리_스킵(self) -> None:
        """content가 없는 엔트리는 스킵된다."""
        data = json.dumps([
            {"title": "유효", "activation_keys": ["키"], "content": "내용", "priority": 100},
            {"title": "빈내용", "activation_keys": ["키2"], "content": "", "priority": 50},
        ])
        result = parse_lore_response(data)
        assert result.success is True
        assert len(result.entries) == 1

    def test_키_문자열_리스트_변환(self) -> None:
        """activation_keys가 쉼표 문자열이면 리스트로 변환."""
        data = json.dumps([{
            "title": "테스트",
            "activation_keys": "키1, 키2, 키3",
            "content": "내용",
            "priority": 100,
        }])
        result = parse_lore_response(data)
        assert result.success is True
        assert result.entries[0]["activation_keys"] == ["키1", "키2", "키3"]

    def test_키_누락시_제목_사용(self) -> None:
        """activation_keys가 없으면 title을 키로 사용."""
        data = json.dumps([{
            "title": "특별한 아이템",
            "content": "아이템 설명",
            "priority": 100,
        }])
        result = parse_lore_response(data)
        assert result.success is True
        assert result.entries[0]["activation_keys"] == ["특별한 아이템"]

    def test_priority_범위_클램핑(self) -> None:
        """priority가 0~1000 범위를 넘으면 클램핑된다."""
        data = json.dumps([
            {"title": "높음", "activation_keys": ["키"], "content": "내용", "priority": 9999},
            {"title": "음수", "activation_keys": ["키"], "content": "내용", "priority": -50},
        ])
        result = parse_lore_response(data)
        assert result.success is True
        assert result.entries[0]["priority"] == 1000
        assert result.entries[1]["priority"] == 0

    def test_priority_비숫자_기본값(self) -> None:
        """priority가 숫자가 아니면 100이 기본값."""
        data = json.dumps([{
            "title": "테스트",
            "activation_keys": ["키"],
            "content": "내용",
            "priority": "높음",
        }])
        result = parse_lore_response(data)
        assert result.success is True
        assert result.entries[0]["priority"] == 100

    def test_잘못된_JSON_실패(self) -> None:
        """파싱 불가능한 텍스트는 실패."""
        result = parse_lore_response("이건 JSON이 아닙니다.")
        assert result.success is False
        assert "JSON 파싱 실패" in result.error

    def test_빈_배열_실패(self) -> None:
        """빈 배열은 실패."""
        result = parse_lore_response("[]")
        assert result.success is False
        assert "빈 배열" in result.error

    def test_빈_응답_실패(self) -> None:
        """빈 응답은 실패."""
        result = parse_lore_response("")
        assert result.success is False

    def test_모든_엔트리_무효시_실패(self) -> None:
        """모든 엔트리가 무효하면 실패."""
        data = json.dumps([
            {"activation_keys": ["키"], "content": "내용"},  # title 누락
            {"title": "제목", "activation_keys": ["키"]},  # content 누락
        ])
        result = parse_lore_response(data)
        assert result.success is False
        assert "유효한 엔트리" in result.error


class TestLoreFillResult:
    """LoreFillResult 데이터클래스 테스트."""

    def test_기본_생성(self) -> None:
        """기본 생성 시 success=False, 빈 entries."""
        r = LoreFillResult(success=False)
        assert r.success is False
        assert r.entries == []
        assert r.error == ""

    def test_성공_생성(self) -> None:
        """성공 시 entries가 채워진다."""
        r = LoreFillResult(
            success=True,
            entries=[{"title": "테스트", "activation_keys": ["키"], "content": "내용", "priority": 100}],
        )
        assert r.success is True
        assert len(r.entries) == 1


# ============================================================
# Phase 3: Worldbook Vibe Fill 테스트
# ============================================================


class TestWorldCategories:
    """세계관 카테고리 정의 테스트."""

    def test_10개_카테고리_존재(self) -> None:
        """정확히 10개 카테고리가 정의되어 있다."""
        assert len(WORLD_CATEGORIES) == 10

    def test_카테고리_키_유일성(self) -> None:
        """모든 카테고리 키가 고유하다."""
        keys = [c.key for c in WORLD_CATEGORIES]
        assert len(keys) == len(set(keys))

    def test_카테고리_맵_일치(self) -> None:
        """WORLD_CATEGORY_MAP이 WORLD_CATEGORIES와 일치한다."""
        assert len(WORLD_CATEGORY_MAP) == len(WORLD_CATEGORIES)
        for cat in WORLD_CATEGORIES:
            assert cat.key in WORLD_CATEGORY_MAP

    def test_청크_배열_모든_카테고리_포함(self) -> None:
        """청크 배열이 모든 10개 카테고리를 포함한다."""
        all_chunk_keys = [k for chunk in WORLD_CATEGORY_CHUNKS for k in chunk]
        all_cat_keys = [c.key for c in WORLD_CATEGORIES]
        assert sorted(all_chunk_keys) == sorted(all_cat_keys)


class TestGetChunksForCategories:
    """청크 분할 로직 테스트."""

    def test_전체_선택(self) -> None:
        """모든 카테고리 선택 시 4개 청크."""
        all_keys = [c.key for c in WORLD_CATEGORIES]
        chunks = get_chunks_for_categories(all_keys)
        assert len(chunks) == 4

    def test_부분_선택(self) -> None:
        """일부 카테고리만 선택."""
        chunks = get_chunks_for_categories(["history", "races"])
        assert len(chunks) == 2
        assert chunks[0] == ["history"]
        assert chunks[1] == ["races"]

    def test_빈_선택(self) -> None:
        """아무것도 선택하지 않으면 빈 리스트."""
        chunks = get_chunks_for_categories([])
        assert chunks == []

    def test_없는_키_무시(self) -> None:
        """존재하지 않는 키는 무시된다."""
        chunks = get_chunks_for_categories(["history", "nonexistent"])
        assert len(chunks) == 1
        assert chunks[0] == ["history"]


class TestBuildWorldPrompt:
    """세계관 바이브 프롬프트 조립 테스트."""

    _CATS = [WORLD_CATEGORY_MAP["history"], WORLD_CATEGORY_MAP["geography"]]

    def test_바이브만_입력(self) -> None:
        """바이브 + 카테고리만 입력."""
        result = build_world_prompt("동양풍 대륙", self._CATS)
        assert "동양풍 대륙" in result
        assert "역사" in result
        assert "지리" in result

    def test_캐릭터_포함(self) -> None:
        """캐릭터 시트가 프롬프트에 포함된다."""
        result = build_world_prompt("바이브", self._CATS, persona_sheet="[캐릭터: 미라]")
        assert "[캐릭터 참조]" in result
        assert "미라" in result

    def test_로어북_참조(self) -> None:
        """로어북 요약이 프롬프트에 포함된다."""
        result = build_world_prompt(
            "바이브", self._CATS,
            lore_summaries=["오라클럼 (키: 유물)", "지하 서고 (키: 지하)"],
        )
        assert "[로어북 참조]" in result
        assert "오라클럼" in result

    def test_연쇄_컨텍스트(self) -> None:
        """이전 청크 제목이 프롬프트에 포함된다."""
        result = build_world_prompt(
            "바이브", self._CATS,
            prev_titles=["[역사] 대붕괴 전쟁", "[지리] 운해 대륙"],
        )
        assert "이전 생성 결과" in result
        assert "대붕괴 전쟁" in result

    def test_모두_포함(self) -> None:
        """캐릭터 + 로어북 + 연쇄 + 바이브 모두 포함."""
        result = build_world_prompt(
            "세계관", self._CATS,
            persona_sheet="캐릭터", lore_summaries=["로어"],
            prev_titles=["이전"],
        )
        assert "[캐릭터 참조]" in result
        assert "[로어북 참조]" in result
        assert "이전 생성 결과" in result

    def test_시스템_프롬프트_필드(self) -> None:
        """시스템 프롬프트에 핵심 키워드가 포함되어 있다."""
        assert '"title"' in WORLD_FILL_SYSTEM_PROMPT
        assert '"category"' in WORLD_FILL_SYSTEM_PROMPT
        assert '"content"' in WORLD_FILL_SYSTEM_PROMPT
        assert '"priority"' in WORLD_FILL_SYSTEM_PROMPT


class TestParseWorldResponse:
    """세계관 JSON 배열 응답 파싱 테스트."""

    _VALID_RESPONSE = json.dumps([
        {
            "title": "[역사] 대붕괴 전쟁",
            "category": "history",
            "content": "300년 전 대륙 전체를 뒤흔든 마법 전쟁.",
            "priority": 400,
        },
        {
            "title": "[지리] 운해 대륙",
            "category": "geography",
            "content": "구름 위에 떠 있는 신비로운 대륙.",
            "priority": 350,
        },
    ], ensure_ascii=False)

    def test_순수_JSON_배열_파싱(self) -> None:
        """JSON 배열이 올바르게 파싱된다."""
        result = parse_world_response(self._VALID_RESPONSE)
        assert result.success is True
        assert len(result.entries) == 2
        assert result.entries[0]["title"] == "[역사] 대붕괴 전쟁"
        assert result.entries[0]["category"] == "history"

    def test_카테고리_없으면_제목에서_추출(self) -> None:
        """category 필드가 없으면 title의 [카테고리] 접두사에서 추출."""
        data = json.dumps([{
            "title": "[마법/기술] 에테르 마나",
            "content": "마법의 근원 에너지.",
            "priority": 300,
        }], ensure_ascii=False)
        result = parse_world_response(data)
        assert result.success is True
        assert result.entries[0]["category"] == "magic_tech"

    def test_알_수_없는_카테고리(self) -> None:
        """category가 유효하지 않으면 빈 문자열."""
        data = json.dumps([{
            "title": "특이한 엔트리",
            "category": "unknown_cat",
            "content": "내용",
            "priority": 100,
        }])
        result = parse_world_response(data)
        assert result.success is True
        assert result.entries[0]["category"] == ""

    def test_단일_객체_배열_변환(self) -> None:
        """단일 객체는 배열로 감싸서 처리."""
        single = json.dumps({
            "title": "[역사] 테스트",
            "category": "history",
            "content": "내용",
            "priority": 400,
        })
        result = parse_world_response(single)
        assert result.success is True
        assert len(result.entries) == 1

    def test_빈_배열_실패(self) -> None:
        """빈 배열은 실패."""
        result = parse_world_response("[]")
        assert result.success is False

    def test_잘못된_JSON_실패(self) -> None:
        """파싱 불가능한 텍스트는 실패."""
        result = parse_world_response("이건 JSON이 아닙니다.")
        assert result.success is False

    def test_priority_기본값_카테고리(self) -> None:
        """priority가 잘못되면 카테고리 기본값 사용."""
        data = json.dumps([{
            "title": "[역사] 테스트",
            "category": "history",
            "content": "내용",
            "priority": "높음",
        }])
        result = parse_world_response(data)
        assert result.success is True
        assert result.entries[0]["priority"] == 400  # history 기본값


class TestWorldFillResult:
    """WorldFillResult 데이터클래스 테스트."""

    def test_기본_생성(self) -> None:
        """기본 생성 시 success=False, 빈 entries."""
        r = WorldFillResult(success=False)
        assert r.success is False
        assert r.entries == []

    def test_성공_생성(self) -> None:
        """성공 시 entries가 채워진다."""
        r = WorldFillResult(
            success=True,
            entries=[{"title": "[역사] 테스트", "category": "history", "content": "내용", "priority": 400}],
        )
        assert r.success is True
        assert len(r.entries) == 1
