# src/chitchat/domain/ids.py
# [v1.0.0] ULID 기반 정렬 가능 ID 생성 모듈
#
# 모든 엔티티 ID는 prefix + ULID 형태로 생성한다.
# ULID는 시간 순 정렬이 가능하므로 DB 인덱싱에 유리하다.
# prefix는 반드시 언더스코어로 끝나야 한다: "cp_", "prov_", "le_" 등
#
# 의존: python-ulid (pyproject.toml에 명시)

from __future__ import annotations

from ulid import ULID


def new_id(prefix: str) -> str:
    """prefix + 소문자 ULID로 정렬 가능한 고유 ID를 생성한다.

    Args:
        prefix: 엔티티 종류를 나타내는 접두사. 반드시 언더스코어로 끝나야 한다.
                예: "cp_", "prov_", "le_", "cs_"

    Returns:
        "cp_01j5..." 형태의 정렬 가능한 고유 ID 문자열.

    Raises:
        ValueError: prefix가 언더스코어로 끝나지 않을 때.
    """
    if not prefix.endswith("_"):
        raise ValueError(f"ID prefix는 반드시 언더스코어('_')로 끝나야 한다: {prefix!r}")
    return f"{prefix}{str(ULID()).lower()}"
