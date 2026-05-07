# src/chitchat/api/app.py
# [v1.0.0] FastAPI 앱 인스턴스 및 라이프사이클
#
# PySide6 QApplication을 대체하는 FastAPI 서버 진입점.
# CORS 설정, 라이프사이클 이벤트, 라우터 등록, 정적 파일 서빙을 담당한다.

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
import typing
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from chitchat.config.user_preferences import UserPreferences
from chitchat.config.settings import AppSettings
from chitchat.config.paths import ensure_app_dirs
from chitchat.db.engine import create_db_engine, create_session_factory
from chitchat.db.migrations import run_migrations
from chitchat.i18n.translator import Translator

logger = logging.getLogger(__name__)

# [v1.1.1] 앱 데이터 디렉토리 — AppSettings에서 OS별 경로를 가져온다.
# spec.md §3.3: Linux → ${XDG_DATA_HOME}/chitchat/, Windows → %APPDATA%/chitchat/
_settings = AppSettings()
APP_DATA_DIR = _settings.app_data_dir

# [v1.1.1] 기존 경로 호환 — ~/.chitchat에서 마이그레이션
_LEGACY_DATA_DIR = Path.home() / ".chitchat"


def _migrate_legacy_data(new_dir: Path) -> None:
    """기존 ~/.chitchat/chitchat.db가 존재하면 새 경로로 복사한다.

    [v1.1.1] 경로 전환 시 데이터 유실을 방지한다.
    기존 파일명(chitchat.db)을 새 파일명(chitchat.sqlite3)으로 매핑한다.
    새 경로에 이미 DB가 존재하면 마이그레이션을 건너뛴다.
    """
    import shutil
    legacy_db = _LEGACY_DATA_DIR / "chitchat.db"
    new_db = _settings.db_path  # chitchat.sqlite3

    if legacy_db.exists() and not new_db.exists():
        new_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(legacy_db, new_db)
        logger.info(
            "기존 DB 마이그레이션 완료: %s → %s",
            legacy_db, new_db,
        )
        # 설정 파일도 복사
        legacy_settings = _LEGACY_DATA_DIR / "settings.json"
        new_settings = new_dir / "settings.json"
        if legacy_settings.exists() and not new_settings.exists():
            shutil.copy2(legacy_settings, new_settings)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """FastAPI 라이프사이클 관리.

    시작 시 DB 엔진 생성, 마이그레이션, 서비스 레지스트리 초기화를 수행한다.
    종료 시 DB 커넥션을 정리한다.
    """
    # [v1.1.1] 앱 데이터 디렉토리 보장 + 기존 경로 마이그레이션
    ensure_app_dirs(APP_DATA_DIR)
    _migrate_legacy_data(APP_DATA_DIR)

    # DB 마이그레이션 후 엔진 생성
    # [v1.0.0] run_migrations는 SQLite 잠금 데드락 방지를 위해 db_path를 직접 받는다.
    # 마이그레이션 완료 후 engine과 session_factory를 생성한다.
    db_path = _settings.db_path
    run_migrations(db_path)
    engine = create_db_engine(db_path)
    session_factory = create_session_factory(engine)

    # 사용자 설정 로드 및 i18n 초기화
    prefs = UserPreferences.instance()
    prefs.load(APP_DATA_DIR)
    translator = Translator.instance()
    translator.set_locale(prefs.ui_locale)

    # [v1.0.0] 서비스 레지스트리 초기화
    from chitchat.db.repositories import RepositoryRegistry
    from chitchat.providers.registry import ProviderRegistry
    from chitchat.secrets.key_store import KeyStore
    from chitchat.services.chat_service import ChatService
    from chitchat.services.dynamic_state_engine import DynamicStateEngine
    from chitchat.services.prompt_service import PromptService
    from chitchat.services.provider_service import ProviderService
    from chitchat.services.vibe_fill_service import VibeFillService
    from chitchat.services.profile_service import ProfileService

    repos = RepositoryRegistry(session_factory)
    key_store = KeyStore()
    provider_registry = ProviderRegistry()
    provider_service = ProviderService(repos, provider_registry, key_store)
    prompt_service = PromptService(repos)
    dynamic_state_engine = DynamicStateEngine()
    # [v1.0.0] ChatService에 DynamicStateEngine을 주입하여 스트리밍 후 자동 갱신
    chat_service = ChatService(
        repos, provider_registry, key_store, prompt_service, dynamic_state_engine,
    )
    vibe_fill_service = VibeFillService(repos, provider_registry, key_store)
    profile_service = ProfileService(repos)

    # 앱 상태에 공유 객체 저장 (라우터에서 접근)
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.app_data_dir = APP_DATA_DIR
    app.state.user_preferences = prefs
    app.state.repos = repos
    app.state.provider_service = provider_service
    app.state.chat_service = chat_service
    app.state.vibe_fill_service = vibe_fill_service
    app.state.dynamic_state_engine = dynamic_state_engine
    app.state.profile_service = profile_service

    logger.info("chitchat v1.0.0 서버 시작 — DB: %s", db_path)

    yield

    # 종료 정리
    engine.dispose()
    logger.info("chitchat 서버 종료")


def create_app() -> FastAPI:
    """FastAPI 앱 인스턴스를 생성하고 라우터를 등록한다."""
    app = FastAPI(
        title="chitchat",
        version="1.0.0",
        description="VibeSmith-powered dynamic persona AI roleplay chat platform",
        lifespan=lifespan,
    )

    # CORS 설정 (로컬 개발용)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # [v1.1.1] 개발 환경에서 정적 파일 캐시 방지 미들웨어
    # 브라우저가 오래된 JS/CSS를 캐시하여 변경이 반영되지 않는 문제를 방지한다.
    import sys
    if not getattr(sys, "frozen", False):
        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.requests import Request
        from starlette.responses import Response

        class NoCacheMiddleware(BaseHTTPMiddleware):
            """정적 파일(JS/CSS)에 Cache-Control: no-store 헤더를 추가한다."""
            async def dispatch(
                self, request: Request, call_next: typing.Callable[..., typing.Awaitable[Response]]
            ) -> Response:
                response: Response = await call_next(request)
                path = request.url.path
                if path.endswith(('.js', '.css', '.html')):
                    response.headers["Cache-Control"] = "no-store, must-revalidate"
                return response

        app.add_middleware(NoCacheMiddleware)

    # API 라우터 등록
    from chitchat.api.routes import (  # noqa: E402
        chat,
        health,
        personas,
        profiles,
        providers,
        settings,
    )

    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(providers.router, prefix="/api", tags=["providers"])
    app.include_router(personas.router, prefix="/api", tags=["personas"])
    app.include_router(profiles.router, prefix="/api", tags=["profiles"])
    app.include_router(chat.router, prefix="/api", tags=["chat"])
    app.include_router(settings.router, prefix="/api", tags=["settings"])

    # 프론트엔드 정적 파일 서빙
    # [v1.0.0] PyInstaller 번들 환경에서는 sys._MEIPASS 기준으로 frontend를 찾는다.
    import sys
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # PyInstaller 번들 환경 — _MEIPASS/frontend 경로 사용
        frontend_dir = Path(sys._MEIPASS) / "frontend"
    else:
        # 개발 환경 — 프로젝트 루트/frontend 경로 사용
        frontend_dir = Path(__file__).parent.parent.parent.parent / "frontend"
    if frontend_dir.exists():
        app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
        logger.info("프론트엔드 정적 파일 마운트: %s", frontend_dir)

    return app
