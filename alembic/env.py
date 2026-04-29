# alembic/env.py
# [v0.1.0b0] Alembic 환경 설정 파일
# SQLAlchemy ORM 모델의 MetaData를 참조하여 자동 마이그레이션을 생성한다.
# 런타임에서는 migrations.py가 이 파일을 호출하여 마이그레이션을 실행한다.

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Alembic Config 객체. alembic.ini의 값에 접근한다.
config = context.config

# 로깅 설정
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ORM 모델의 MetaData를 target_metadata로 설정한다.
# Alembic autogenerate가 이 메타데이터를 참조하여 마이그레이션을 생성한다.
from chitchat.db.models import Base  # noqa: E402
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """오프라인 모드: SQL 스크립트만 생성하고 DB에 직접 연결하지 않는다."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """온라인 모드: DB에 연결하여 마이그레이션을 직접 실행한다."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
