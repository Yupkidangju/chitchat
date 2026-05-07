# src/chitchat/main.py
# [v1.0.0] FastAPI 서버 엔트리포인트
#
# [v0.3.0 → v1.0.0 변경사항]
# - PySide6 QApplication 엔트리포인트 제거
# - FastAPI + Uvicorn 서버로 전환
# - 삭제 사유: 데스크톱 앱에서 웹 앱으로 아키텍처 전환
# - 삭제 버전: v1.0.0
# [v1.0.0] PyInstaller 패키징 지원 추가
# - multiprocessing.freeze_support() 호출 (Windows 무한 프로세스 방지)
# - 서버 시작 후 브라우저 자동 오픈

from __future__ import annotations

import multiprocessing
import threading
import webbrowser

import uvicorn


from chitchat.api.app import APP_DATA_DIR, create_app
from chitchat.logging_config import setup_logging

# 로깅 초기화
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
(APP_DATA_DIR / "logs").mkdir(parents=True, exist_ok=True)
setup_logging(APP_DATA_DIR)

# FastAPI 앱 생성
app = create_app()


def _open_browser(port: int) -> None:
    """서버 시작 후 브라우저를 자동으로 열어준다.

    1초 대기 후 브라우저를 열어 Uvicorn 시작 시간을 확보한다.
    """
    import time
    time.sleep(1.0)
    webbrowser.open(f"http://localhost:{port}")


def main() -> None:
    """chitchat 서버를 시작한다.

    기본 포트 8000에서 localhost에 바인딩한다.
    브라우저에서 http://localhost:8000 으로 접속하여 사용한다.
    """
    port = 8000
    print(f"\n  💬 chitchat v1.0.0 — http://localhost:{port}\n")

    # 브라우저 자동 오픈 (별도 스레드로 Uvicorn 시작 차단 방지)
    threading.Thread(target=_open_browser, args=(port,), daemon=True).start()

    uvicorn.run(
        "chitchat.main:app",
        host="127.0.0.1",
        port=port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    # [v1.0.0] PyInstaller 패키징 시 Windows에서 무한 프로세스 생성 방지
    multiprocessing.freeze_support()
    main()
