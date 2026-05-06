# src/chitchat/main.py
# [v1.0.0] FastAPI 서버 엔트리포인트
#
# [v0.3.0 → v1.0.0 변경사항]
# - PySide6 QApplication 엔트리포인트 제거
# - FastAPI + Uvicorn 서버로 전환
# - 삭제 사유: 데스크톱 앱에서 웹 앱으로 아키텍처 전환
# - 삭제 버전: v1.0.0

from __future__ import annotations

import uvicorn


from chitchat.api.app import APP_DATA_DIR, create_app
from chitchat.logging_config import setup_logging

# 로깅 초기화
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
(APP_DATA_DIR / "logs").mkdir(parents=True, exist_ok=True)
setup_logging(APP_DATA_DIR)

# FastAPI 앱 생성
app = create_app()


def main() -> None:
    """chitchat 서버를 시작한다.

    기본 포트 8000에서 localhost에 바인딩한다.
    브라우저에서 http://localhost:8000 으로 접속하여 사용한다.
    """
    uvicorn.run(
        "chitchat.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
