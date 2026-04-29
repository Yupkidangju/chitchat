# src/chitchat/main.py
# [v0.1.0b0] 앱 엔트리포인트
#
# `python -m chitchat.main`으로 실행한다.
# create_app()으로 의존성을 조립하고 Qt 이벤트 루프를 시작한다.
from __future__ import annotations
import sys

def main() -> None:
    """앱을 시작한다."""
    from chitchat.app import create_app
    app, window = create_app()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
