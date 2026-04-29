# src/chitchat/logging_config.py
# [v0.1.0b0] 로깅 설정 모듈
#
# 앱 전역 로깅을 설정한다.
# 콘솔과 파일 핸들러를 동시에 사용한다.
# 로그 파일은 앱 데이터 디렉토리의 logs/chitchat.log에 저장된다.

from __future__ import annotations

import logging
import sys
from pathlib import Path

from chitchat.config.paths import get_log_path


def setup_logging(app_data_dir: Path, level: str = "INFO") -> None:
    """앱 로깅을 설정한다.

    콘솔 핸들러(stderr)와 파일 핸들러를 동시에 등록한다.
    파일 핸들러는 UTF-8 인코딩을 강제한다.

    Args:
        app_data_dir: 앱 데이터 디렉토리 경로. logs/ 하위에 로그 파일을 생성한다.
        level: 로깅 레벨 문자열 (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    log_path = get_log_path(app_data_dir)
    log_level = getattr(logging, level.upper(), logging.INFO)

    # 포맷터 설정
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)-5.5s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 기존 핸들러 제거 (중복 방지)
    root_logger.handlers.clear()

    # 콘솔 핸들러 (stderr)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 파일 핸들러 (UTF-8 강제)
    file_handler = logging.FileHandler(
        log_path,
        encoding="utf-8",
        mode="a",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # 외부 라이브러리 로그 레벨 억제
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
