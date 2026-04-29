# src/chitchat/db/engine.py
# [v0.1.0b0] SQLAlchemy 엔진 팩토리
#
# SQLite 연결을 위한 SQLAlchemy 엔진과 세션 팩토리를 생성한다.
# spec.md §4 D-03에서 SQLite + SQLAlchemy 2.0 ORM으로 동결.

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def create_db_engine(db_path: Path) -> Engine:
    """SQLite 엔진을 생성한다.

    WAL 모드와 foreign key 강제를 활성화한다.
    echo=False로 SQL 쿼리 로깅을 비활성화한다 (필요 시 환경변수로 제어).

    Args:
        db_path: SQLite 데이터베이스 파일 경로.

    Returns:
        설정된 SQLAlchemy Engine 인스턴스.
    """
    url = f"sqlite:///{db_path}"
    engine = create_engine(
        url,
        echo=False,
        pool_pre_ping=True,
        # SQLite는 NullPool이 기본이므로 별도 설정 불필요
    )

    # SQLite에서 foreign key 제약조건을 강제한다.
    # SQLite는 기본적으로 FK를 무시하므로, 매 연결 시 PRAGMA를 실행해야 한다.
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_conn, _connection_record):  # type: ignore[no-untyped-def]
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """세션 팩토리를 생성한다.

    Args:
        engine: SQLAlchemy Engine 인스턴스.

    Returns:
        Session을 생성하는 sessionmaker 인스턴스.
    """
    return sessionmaker(bind=engine, expire_on_commit=False)
