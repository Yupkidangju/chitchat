# src/chitchat/db/migrations.py
# [v0.2.0] 프로그래밍 방식 Alembic 마이그레이션 실행
#
# 앱 시작 시 자동으로 Alembic 마이그레이션을 적용한다.
# alembic.ini의 URL이 아닌, 런타임에서 결정된 engine을 직접 사용한다.
# create_all() 없이 Alembic만으로 스키마 생성/업그레이드를 일원화한다.

from __future__ import annotations

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# 프로젝트 루트의 alembic 디렉토리 경로
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_ALEMBIC_INI = _PROJECT_ROOT / "alembic.ini"
_ALEMBIC_DIR = _PROJECT_ROOT / "alembic"

# v0.2.0에서 ai_personas에 추가된 확장 필드 목록 (stamp 판별용)
_V020_COLUMNS = {"age", "gender", "appearance", "backstory",
                 "relationships", "skills", "interests", "weaknesses"}


def run_migrations(engine: Engine) -> None:
    """Alembic 마이그레이션을 프로그래밍 방식으로 실행한다.

    앱 시작 시 자동으로 호출되어 DB 스키마를 최신 상태로 유지한다.
    alembic.ini 파일의 sqlalchemy.url을 런타임 engine URL로 오버라이드한다.

    세 가지 DB 상태를 자동 감지하여 처리한다:
      1. 완전히 새로운 DB → upgrade("head")로 전체 스키마 생성
      2. v0.1 DB (테이블 있음, alembic_version 없음, v0.2 컬럼 없음)
         → initial revision으로 stamp 후 upgrade
      3. partial DB (이전 실패 등으로 v0.2 컬럼은 이미 있지만 alembic_version 없음)
         → head로 직접 stamp하여 중복 컬럼 추가 방지

    Args:
        engine: 마이그레이션을 적용할 SQLAlchemy Engine.
    """
    if not _ALEMBIC_INI.exists():
        logger.warning("alembic.ini를 찾을 수 없음: %s. 마이그레이션을 건너뜀.", _ALEMBIC_INI)
        return

    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    alembic_cfg = Config(str(_ALEMBIC_INI))
    alembic_cfg.set_main_option("sqlalchemy.url", str(engine.url))
    alembic_cfg.set_main_option("script_location", str(_ALEMBIC_DIR))

    # alembic_version 테이블이 없는 기존 DB에 대한 호환성 처리
    if "ai_personas" in tables and "alembic_version" not in tables:
        # ai_personas 테이블의 컬럼명을 조회하여 v0.2 확장 필드 존재 여부 판별
        existing_cols = {col["name"] for col in inspector.get_columns("ai_personas")}
        has_v020_cols = _V020_COLUMNS.issubset(existing_cols)

        if has_v020_cols:
            # 이전 실패 실행(create_all + 14개 컬럼) 등으로 v0.2 스키마가 이미 완성된 partial DB
            # → head로 직접 stamp하여 중복 컬럼 추가(duplicate column) 에러를 방지한다.
            logger.info(
                "Partial DB 감지: v0.2 컬럼이 이미 존재하나 alembic_version 없음. "
                "head로 직접 스탬프합니다."
            )
            command.stamp(alembic_cfg, "head")
        else:
            # v0.1 DB: 기본 컬럼만 존재하는 상태
            # → initial revision(792a1c255924)으로 stamp 후 upgrade로 v0.2 컬럼을 추가한다.
            logger.info(
                "기존 v0.1 DB 감지: Alembic 버전 상태를 "
                "초기 스키마(792a1c255924)로 스탬프합니다."
            )
            command.stamp(alembic_cfg, "792a1c255924")

    logger.info("Alembic 마이그레이션 시작: %s", engine.url)
    command.upgrade(alembic_cfg, "head")
    logger.info("Alembic 마이그레이션 완료.")

