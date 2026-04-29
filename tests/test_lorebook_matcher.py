# tests/test_lorebook_matcher.py
# [v0.1.0b0] 로어북 키워드 매칭 테스트
from __future__ import annotations
from chitchat.domain.lorebook_matcher import match_lore_entries
from chitchat.domain.profiles import LoreEntryData

def _entry(id_: str, title: str, keys: list[str], content: str, priority: int = 100) -> LoreEntryData:
    return LoreEntryData(id=id_, lorebook_id="lb_1", title=title, activation_keys=keys, content=content, priority=priority)


class TestKeywordMatching:
    def test_basic_match(self) -> None:
        entries = [_entry("1", "유물", ["유물", "artifact"], "고대 유물 설명")]
        blocks = match_lore_entries(entries, ["오늘 유물을 발견했다"])
        assert len(blocks) == 1
        assert blocks[0].content == "고대 유물 설명"

    def test_casefold_match(self) -> None:
        """대소문자 무시 매칭."""
        entries = [_entry("1", "Magic", ["magic"], "마법 설명")]
        blocks = match_lore_entries(entries, ["I found MAGIC today"])
        assert len(blocks) == 1

    def test_no_match(self) -> None:
        entries = [_entry("1", "유물", ["유물"], "유물 설명")]
        blocks = match_lore_entries(entries, ["오늘 날씨가 좋다"])
        assert len(blocks) == 0

    def test_disabled_entry_skipped(self) -> None:
        e = _entry("1", "유물", ["유물"], "유물 설명")
        e.enabled = False
        blocks = match_lore_entries([e], ["유물을 발견했다"])
        assert len(blocks) == 0

    def test_empty_messages(self) -> None:
        entries = [_entry("1", "유물", ["유물"], "유물 설명")]
        blocks = match_lore_entries(entries, [])
        assert len(blocks) == 0


class TestPrioritySorting:
    def test_priority_descending(self) -> None:
        entries = [
            _entry("1", "A", ["유물"], "A 내용", priority=50),
            _entry("2", "B", ["유물"], "B 내용", priority=200),
            _entry("3", "C", ["유물"], "C 내용", priority=100),
        ]
        blocks = match_lore_entries(entries, ["유물"])
        assert blocks[0].source_id == "2"  # priority 200
        assert blocks[1].source_id == "3"  # priority 100
        assert blocks[2].source_id == "1"  # priority 50

    def test_same_priority_title_ascending(self) -> None:
        entries = [
            _entry("1", "Zebra", ["유물"], "Z 내용", priority=100),
            _entry("2", "Alpha", ["유물"], "A 내용", priority=100),
        ]
        blocks = match_lore_entries(entries, ["유물"])
        assert blocks[0].source_id == "2"  # Alpha
        assert blocks[1].source_id == "1"  # Zebra


class TestLimits:
    def test_max_entries(self) -> None:
        entries = [_entry(str(i), f"E{i}", ["유물"], f"내용{i}") for i in range(20)]
        blocks = match_lore_entries(entries, ["유물"], max_entries=5)
        assert len(blocks) == 5

    def test_max_tokens(self) -> None:
        # 각 엔트리가 약 100토큰 (400자)
        big_content = "x" * 400
        entries = [_entry(str(i), f"E{i}", ["유물"], big_content) for i in range(20)]
        blocks = match_lore_entries(entries, ["유물"], max_tokens=300)
        # 100토큰 × 3 = 300으로 최대 3개
        assert len(blocks) <= 3

    def test_scan_messages_limit(self) -> None:
        """scan_messages보다 오래된 메시지는 스캔하지 않는다."""
        entries = [_entry("1", "유물", ["유물"], "유물 설명")]
        # 10개 메시지 중 유물은 1번째(인덱스0)에만 있음, scan_messages=3이면 뒤 3개만 스캔
        msgs = ["유물이 있다"] + ["관련없는 대화"] * 9
        blocks = match_lore_entries(entries, msgs, scan_messages=3)
        assert len(blocks) == 0  # 유물은 스캔 범위 밖
