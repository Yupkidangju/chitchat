# src/chitchat/db/migrations.py
# [v0.1.0b0] 프로그래밍 방식 Alembic 마이그레이션 실행
#
# 앱 시작 시 자동으로 Alembic 마이그레이션을 적용한다.
# alembic.ini의 URL이 아닌, 런타임에서 결정된 engine을 직접 사용한다.

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


def run_migrations(engine: Engine) -> None:
    """Alembic 마이그레이션을 프로그래밍 방식으로 실행한다.

    앱 시작 시 자동으로 호출되어 DB 스키마를 최신 상태로 유지한다.
    alembic.ini 파일의 sqlalchemy.url을 런타임 engine URL로 오버라이드한다.

    Args:
        engine: 마이그레이션을 적용할 SQLAlchemy Engine.
    """
    if not _ALEMBIC_INI.exists():
        logger.warning("alembic.ini를 찾을 수 없음: %s. 마이그레이션을 건너뜀.", _ALEMBIC_INI)
        return

    alembic_cfg = Config(str(_ALEMBIC_INI))
    alembic_cfg.set_main_option("sqlalchemy.url", str(engine.url))
    alembic_cfg.set_main_option("script_location", str(_ALEMBIC_DIR))

    logger.info("Alembic 마이그레이션 시작: %s", engine.url)
    command.upgrade(alembic_cfg, "head")
    logger.info("Alembic 마이그레이션 완료.")
