# src/chitchat/config/paths.py
# [v1.0.0] OS별 앱 데이터 경로 결정 및 디렉토리 생성
#
# spec.md §3.3에서 정의된 런타임 저장 경로를 구현한다.
# Windows: %APPDATA%/chitchat/
# macOS: ~/Library/Application Support/chitchat/
# Linux: ${XDG_DATA_HOME:-~/.local/share}/chitchat/
#
# ensure_app_dirs()는 앱 최초 실행 시 필요한 하위 디렉토리를 생성한다.

from __future__ import annotations

import os
import sys
from pathlib import Path

# 앱 이름. 디렉토리명으로 사용된다.
APP_NAME = "chitchat"


def get_app_data_dir() -> Path:
    """OS에 따라 앱 데이터 디렉토리 경로를 반환한다.

    Windows: %APPDATA%/chitchat/
    macOS:   ~/Library/Application Support/chitchat/
    Linux:   ${XDG_DATA_HOME:-~/.local/share}/chitchat/

    Returns:
        앱 데이터 디렉토리의 Path 객체.
    """
    if sys.platform == "win32":
        # Windows: %APPDATA% 환경변수 사용
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        # macOS: ~/Library/Application Support/
        base = Path.home() / "Library" / "Application Support"
    else:
        # Linux 및 기타: XDG_DATA_HOME 또는 ~/.local/share/
        xdg = os.environ.get("XDG_DATA_HOME")
        base = Path(xdg) if xdg else Path.home() / ".local" / "share"

    return base / APP_NAME


def ensure_app_dirs(app_data_dir: Path) -> None:
    """앱 데이터 디렉토리와 하위 폴더를 생성한다.

    생성되는 디렉토리:
    - {app_data_dir}/          (루트)
    - {app_data_dir}/logs/     (로그 파일)
    - {app_data_dir}/exports/  (내보내기 파일)
    - {app_data_dir}/backups/  (백업 파일)

    이미 존재하는 디렉토리는 건너뛴다.

    Args:
        app_data_dir: 앱 데이터 루트 디렉토리 경로.
    """
    subdirs = ["logs", "exports", "backups"]
    app_data_dir.mkdir(parents=True, exist_ok=True)
    for subdir in subdirs:
        (app_data_dir / subdir).mkdir(exist_ok=True)


def get_db_path(app_data_dir: Path) -> Path:
    """SQLite 데이터베이스 파일 경로를 반환한다.

    Args:
        app_data_dir: 앱 데이터 루트 디렉토리 경로.

    Returns:
        chitchat.sqlite3 파일의 전체 경로.
    """
    return app_data_dir / "chitchat.sqlite3"


def get_log_path(app_data_dir: Path) -> Path:
    """로그 파일 경로를 반환한다.

    Args:
        app_data_dir: 앱 데이터 루트 디렉토리 경로.

    Returns:
        chitchat.log 파일의 전체 경로.
    """
    return app_data_dir / "logs" / "chitchat.log"
