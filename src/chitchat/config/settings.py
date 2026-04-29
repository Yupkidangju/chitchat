# src/chitchat/config/settings.py
# [v0.1.0b0] 앱 설정 관리 (pydantic-settings 기반)
#
# 환경변수와 .env 파일에서 설정을 로딩한다.
# 모든 설정은 AppSettings 인스턴스를 통해 접근한다.

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from chitchat.config.paths import get_app_data_dir, get_db_path


class AppSettings(BaseSettings):
    """앱 전역 설정.

    환경변수 접두사 CHITCHAT_를 사용한다.
    예: CHITCHAT_LOG_LEVEL=DEBUG

    app_data_dir: 앱 데이터 디렉토리 (OS별 자동 결정, 환경변수로 오버라이드 가능)
    log_level: 로깅 레벨 (기본: INFO)
    default_timeout_seconds: Provider 기본 타임아웃 (기본: 60초)
    """
    model_config = SettingsConfigDict(
        env_prefix="CHITCHAT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_data_dir: Path = Field(default_factory=get_app_data_dir)
    log_level: str = Field(default="INFO")
    default_timeout_seconds: int = Field(default=60, ge=5, le=300)

    @property
    def db_path(self) -> Path:
        """SQLite DB 파일 경로를 반환한다."""
        return get_db_path(self.app_data_dir)

    @property
    def db_url(self) -> str:
        """SQLAlchemy용 SQLite URL을 반환한다."""
        return f"sqlite:///{self.db_path}"
