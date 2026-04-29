# src/chitchat/app.py
# [v0.1.0b0] 앱 팩토리: 의존성 조립 + MainWindow 구성
#
# 모든 서비스, 레포지토리, UI 페이지를 조립하고 MainWindow를 반환한다.
# 이 팩토리는 main.py에서 호출된다.
from __future__ import annotations
import logging
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget
from chitchat.config.paths import ensure_app_dirs
from chitchat.config.settings import AppSettings
from chitchat.db.engine import create_db_engine, create_session_factory
from chitchat.db.models import Base
from chitchat.db.repositories import RepositoryRegistry
from chitchat.logging_config import setup_logging
from chitchat.providers.registry import ProviderRegistry
from chitchat.secrets.key_store import KeyStore
from chitchat.services.profile_service import ProfileService
from chitchat.services.provider_service import ProviderService
from chitchat.ui.main_window import MainWindow
from chitchat.ui.theme import SPACING, build_global_stylesheet

logger = logging.getLogger(__name__)

def _placeholder(title: str, desc: str) -> QWidget:
    """P4/P5에서 구현될 페이지용 플레이스홀더."""
    w = QWidget()
    lo = QVBoxLayout(w)
    lo.setContentsMargins(SPACING.xl, SPACING.xl, SPACING.xl, SPACING.xl)
    t = QLabel(title); t.setObjectName("sectionTitle"); lo.addWidget(t)
    d = QLabel(desc); d.setObjectName("subtitle"); lo.addWidget(d)
    lo.addStretch()
    return w

def create_app() -> tuple[QApplication, MainWindow]:
    """앱을 생성하고 모든 의존성을 조립한다.

    Returns:
        (QApplication, MainWindow) 튜플.
    """
    # 1. 설정 로딩
    settings = AppSettings()
    ensure_app_dirs(settings.app_data_dir)
    # 2. 로깅 설정
    setup_logging(settings.app_data_dir, settings.log_level)
    logger.info("chitchat v0.1.0b0 시작. app_data=%s", settings.app_data_dir)
    # 3. DB 초기화
    engine = create_db_engine(settings.db_path)
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    repos = RepositoryRegistry(session_factory)
    # 4. 서비스 생성
    key_store = KeyStore()
    provider_registry = ProviderRegistry()
    provider_service = ProviderService(repos, provider_registry, key_store)
    profile_service = ProfileService(repos)
    from chitchat.services.prompt_service import PromptService
    prompt_service = PromptService(repos)
    from chitchat.services.chat_service import ChatService
    chat_service = ChatService(repos, provider_registry, key_store, prompt_service)
    # 5. QApplication + 스타일시트
    app = QApplication.instance()
    if app is None:
        import sys
        app = QApplication(sys.argv)
    app.setStyleSheet(build_global_stylesheet())
    # 6. MainWindow + 페이지 등록
    window = MainWindow()
    # 채팅 페이지
    from chitchat.ui.pages.chat_page import ChatPage
    window.register_page("chat", ChatPage(chat_service))
    # Provider 페이지
    from chitchat.ui.pages.provider_page import ProviderPage
    window.register_page("providers", ProviderPage(provider_service))
    # 모델 프로필
    from chitchat.ui.pages.model_profile_page import ModelProfilePage
    window.register_page("model_profiles", ModelProfilePage(profile_service, provider_service))
    # 사용자 페르소나
    from chitchat.ui.pages.persona_page import AIPersonaPage, UserPersonaPage
    window.register_page("user_personas", UserPersonaPage(profile_service))
    # AI 페르소나
    window.register_page("ai_personas", AIPersonaPage(profile_service))
    # 로어북
    from chitchat.ui.pages.lorebook_page import LorebookPage
    window.register_page("lorebooks", LorebookPage(profile_service))
    # 월드북
    from chitchat.ui.pages.worldbook_page import WorldbookPage
    window.register_page("worldbooks", WorldbookPage(profile_service))
    # 채팅 프로필
    from chitchat.ui.pages.chat_profile_page import ChatProfilePage
    window.register_page("chat_profiles", ChatProfilePage(profile_service))
    # 설정
    window.register_page("settings", _placeholder("⚡ 설정", f"앱 데이터: {settings.app_data_dir}"))
    logger.info("MainWindow 조립 완료. 페이지 %d개 등록.", 9)
    return app, window  # type: ignore[return-value]
