# src/chitchat/db/migrations.py
# [v1.0.0] 프로그래밍 방식 Alembic 마이그레이션 실행
#
# [v0.2.0 → v1.0.0 변경사항]
# - engine 대신 db_path를 받아서 SQLite 잠금 데드락을 원천 방지
# - inspect를 sqlite3 stdlib으로 대체하여 SQLAlchemy pool과 독립
#
# 앱 시작 시 자동으로 Alembic 마이그레이션을 적용한다.

from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config

logger = logging.getLogger(__name__)

# 프로젝트 루트의 alembic 디렉토리 경로
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_ALEMBIC_INI = _PROJECT_ROOT / "alembic.ini"
_ALEMBIC_DIR = _PROJECT_ROOT / "alembic"

# v0.2.0에서 ai_personas에 추가된 확장 필드 목록 (stamp 판별용)
_V020_COLUMNS = {"age", "gender", "appearance", "backstory",
                 "relationships", "skills", "interests", "weaknesses"}


def run_migrations(db_path: Path) -> None:
    """Alembic 마이그레이션을 프로그래밍 방식으로 실행한다.

    [v1.0.0] SQLAlchemy Engine 대신 db_path를 받아서 SQLite 잠금 데드락을 방지한다.
    inspect는 sqlite3 stdlib으로 수행하여 SQLAlchemy pool과 완전히 독립시킨다.
    """
    if not _ALEMBIC_INI.exists():
        logger.warning("alembic.ini를 찾을 수 없음: %s. 마이그레이션을 건너뜀.", _ALEMBIC_INI)
        return

    # [v1.0.0] 프로그래밍 방식 호출 표시 — env.py에서 fileConfig를 건너뛰게 한다
    os.environ["CHITCHAT_PROGRAMMATIC_ALEMBIC"] = "1"

    url = f"sqlite:///{db_path}"

    # sqlite3로 직접 테이블 정보를 수집한다 (SQLAlchemy pool과 독립)
    needs_stamp = False
    stamp_target = ""
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

        if "ai_personas" in tables and "alembic_version" not in tables:
            cursor.execute("PRAGMA table_info(ai_personas)")
            existing_cols = {row[1] for row in cursor.fetchall()}
            has_v020_cols = _V020_COLUMNS.issubset(existing_cols)
            needs_stamp = True
            stamp_target = "head" if has_v020_cols else "792a1c255924"
    finally:
        conn.close()

    alembic_cfg = Config(str(_ALEMBIC_INI))
    alembic_cfg.set_main_option("sqlalchemy.url", url)
    alembic_cfg.set_main_option("script_location", str(_ALEMBIC_DIR))

    # alembic_version 테이블이 없는 기존 DB에 대한 호환성 처리
    if needs_stamp:
        if stamp_target == "head":
            logger.info(
                "Partial DB 감지: v0.2 컬럼이 이미 존재하나 alembic_version 없음. "
                "head로 직접 스탬프합니다.",
            )
        else:
            logger.info(
                "기존 v0.1 DB 감지: Alembic 버전 상태를 "
                "초기 스키마(%s)로 스탬프합니다.", stamp_target,
            )
        command.stamp(alembic_cfg, stamp_target)

    logger.info("Alembic 마이그레이션 시작: %s", url)
    command.upgrade(alembic_cfg, "head")
    logger.info("Alembic 마이그레이션 완료.")

