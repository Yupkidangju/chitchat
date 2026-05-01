# tests/test_migrations.py
# [v0.2.0] DB 마이그레이션 경로 회귀 방지 테스트
#
# run_migrations()가 세 가지 DB 상태(신규/v0.1/partial)를
# 에러 없이 처리하는지 자동 검증한다.

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text

from chitchat.db.migrations import run_migrations


@pytest.fixture
def tmp_db(tmp_path: Path):
    """임시 SQLite DB 경로 및 engine 팩토리를 반환하는 픽스처."""
    db_path = tmp_path / "test_mig.sqlite3"

    def _make_engine():
        url = f"sqlite:///{db_path}"
        return create_engine(url)

    return db_path, _make_engine


class TestMigrationScenarios:
    """run_migrations()의 세 가지 DB 상태 시나리오를 검증한다."""

    def test_fresh_db(self, tmp_db: tuple) -> None:
        """시나리오 1: 완전히 새로운 DB → 전체 스키마 생성.

        테이블이 하나도 없는 상태에서 run_migrations()를 호출하면
        initial_schema + v0.2 확장 필드가 모두 정상적으로 생성되어야 한다.
        """
        _, make_engine = tmp_db
        engine = make_engine()

        # 마이그레이션 실행
        run_migrations(engine)

        # 검증: 핵심 테이블 존재 확인
        insp = inspect(engine)
        tables = set(insp.get_table_names())
        assert "ai_personas" in tables
        assert "lorebooks" in tables
        assert "worldbooks" in tables
        assert "alembic_version" in tables

        # 검증: v0.2 확장 필드가 존재하는지 확인
        cols = {c["name"] for c in insp.get_columns("ai_personas")}
        for expected in ("age", "gender", "appearance", "backstory",
                         "relationships", "skills", "interests", "weaknesses"):
            assert expected in cols, f"v0.2 확장 필드 '{expected}'가 누락됨"

    def test_v01_db_upgrade(self, tmp_db: tuple) -> None:
        """시나리오 2: v0.1 DB (테이블 있음, alembic_version 없음, v0.2 컬럼 없음).

        initial_schema까지만 적용된 DB에서 alembic_version을 제거하여
        v0.1 상태를 재현한 뒤, run_migrations()가 v0.2 컬럼을 추가하는지 확인한다.
        """
        db_path, make_engine = tmp_db
        engine = make_engine()

        # v0.1 DB 재현: 전체 마이그레이션 → v0.2 컬럼 롤백을 위해
        # initial_schema만 직접 구성
        run_migrations(engine)

        # alembic_version 제거 + v0.2 컬럼 제거하여 v0.1 상태 재현
        conn = sqlite3.connect(str(db_path))
        conn.execute("DROP TABLE alembic_version")
        # SQLite는 DROP COLUMN을 지원하지 않으므로, 테이블을 재생성
        # 대신 간단하게: 완전히 새로 만들어서 v0.1 구조만 가진 DB 생성
        conn.close()

        # 더 안정적인 방법: 깨끗한 DB에 v0.1 스키마만 수동 생성
        import os
        os.unlink(str(db_path))
        conn = sqlite3.connect(str(db_path))
        conn.execute("""CREATE TABLE ai_personas (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            role_name TEXT NOT NULL,
            personality TEXT NOT NULL,
            speaking_style TEXT NOT NULL,
            goals TEXT NOT NULL,
            restrictions TEXT NOT NULL,
            enabled INTEGER NOT NULL
        )""")
        # 기존 데이터 삽입 (server_default 검증용)
        conn.execute(
            "INSERT INTO ai_personas (id, name, role_name, personality, "
            "speaking_style, goals, restrictions, enabled) "
            "VALUES ('p1', 'Test', 'role', 'kind', 'polite', 'help', 'none', 1)"
        )
        conn.commit()
        conn.close()

        # 새 engine으로 마이그레이션 실행
        engine2 = make_engine()
        run_migrations(engine2)

        # 검증: v0.2 확장 필드가 추가되었는지 확인
        insp = inspect(engine2)
        cols = {c["name"] for c in insp.get_columns("ai_personas")}
        for expected in ("age", "gender", "appearance", "backstory",
                         "relationships", "skills", "interests", "weaknesses"):
            assert expected in cols, f"v0.2 확장 필드 '{expected}'가 추가되지 않음"

        # 검증: 기존 행의 v0.2 필드가 빈 문자열(server_default)로 설정되었는지 확인
        with engine2.connect() as c:
            row = c.execute(text("SELECT age, gender FROM ai_personas WHERE id='p1'")).fetchone()
            assert row is not None
            assert row[0] == ""  # server_default="" 적용 확인
            assert row[1] == ""

    def test_partial_db_recovery(self, tmp_db: tuple) -> None:
        """시나리오 3: Partial DB (v0.2 컬럼이 이미 존재하지만 alembic_version 없음).

        이전 실패 실행(create_all)으로 14개 컬럼이 이미 있지만
        alembic_version이 없는 상태에서 run_migrations()가
        duplicate column 에러 없이 성공하는지 확인한다.
        """
        db_path, make_engine = tmp_db

        # partial DB 재현: 전체 스키마를 직접 생성하되 alembic_version은 만들지 않음
        conn = sqlite3.connect(str(db_path))
        conn.execute("""CREATE TABLE ai_personas (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            role_name TEXT NOT NULL,
            personality TEXT NOT NULL,
            speaking_style TEXT NOT NULL,
            goals TEXT NOT NULL,
            restrictions TEXT NOT NULL,
            enabled INTEGER NOT NULL,
            age TEXT NOT NULL DEFAULT '',
            gender TEXT NOT NULL DEFAULT '',
            appearance TEXT NOT NULL DEFAULT '',
            backstory TEXT NOT NULL DEFAULT '',
            relationships TEXT NOT NULL DEFAULT '',
            skills TEXT NOT NULL DEFAULT '',
            interests TEXT NOT NULL DEFAULT '',
            weaknesses TEXT NOT NULL DEFAULT ''
        )""")
        # 최소한의 다른 테이블도 생성 (initial_schema에 포함된 테이블들)
        conn.execute("""CREATE TABLE lorebooks (
            id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""")
        conn.execute("""CREATE TABLE worldbooks (
            id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""")
        conn.commit()
        conn.close()

        engine = make_engine()

        # 마이그레이션 실행 — duplicate column 에러가 발생하면 안 됨
        run_migrations(engine)

        # 검증: alembic_version이 head로 스탬프되었는지 확인
        insp = inspect(engine)
        assert "alembic_version" in insp.get_table_names()

    def test_idempotent_migration(self, tmp_db: tuple) -> None:
        """run_migrations()를 두 번 연속 호출해도 에러가 발생하지 않는지 확인한다."""
        _, make_engine = tmp_db
        engine = make_engine()

        run_migrations(engine)
        # 두 번째 호출 — 이미 head인 상태에서 다시 upgrade해도 에러 없어야 함
        run_migrations(engine)

        insp = inspect(engine)
        assert "ai_personas" in insp.get_table_names()
