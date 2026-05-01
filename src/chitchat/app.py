# src/chitchat/app.py
# [v0.3.0] 앱 팩토리: 의존성 조립 + MainWindow 구성
#
# 모든 서비스, 레포지토리, UI 페이지를 조립하고 MainWindow를 반환한다.
# [v0.3.0] UserPreferences 로드 및 i18n 초기화를 앱 시작 시 수행한다.
# 이 팩토리는 main.py에서 호출된다.
from __future__ import annotations
import logging
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget
from chitchat.config.paths import ensure_app_dirs
from chitchat.config.settings import AppSettings
from chitchat.config.user_preferences import UserPreferences
from chitchat.db.engine import create_db_engine, create_session_factory
from chitchat.db.repositories import RepositoryRegistry
from chitchat.i18n.translator import Translator
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
    logger.info("chitchat v0.3.0 시작. app_data=%s", settings.app_data_dir)
    # 2.5. [v0.3.0] 사용자 설정 로드 + i18n 초기화
    prefs = UserPreferences.instance()
    prefs.load(settings.app_data_dir)
    translator = Translator.instance()
    translator.set_locale(prefs.ui_locale)
    logger.info("i18n 초기화: locale=%s, vibe_output=%s", prefs.ui_locale, prefs.vibe_output_language)
    # 3. DB 초기화 및 마이그레이션 적용
    engine = create_db_engine(settings.db_path)
    from chitchat.db.migrations import run_migrations
    run_migrations(engine)
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
    # [v0.2.0] Vibe Fill 서비스 생성
    from chitchat.services.vibe_fill_service import VibeFillService
    vibe_fill_service = VibeFillService(repos, provider_registry, key_store)
    # 5. QApplication + 스타일시트
    qapp = QApplication.instance()
    if qapp is None:
        import sys
        qapp = QApplication(sys.argv)
    # [v0.1.4] mypy: QApplication.instance()는 QCoreApplication을 반환하지만,
    # 실제로는 QApplication 인스턴스이므로 assert로 타입 보장
    assert isinstance(qapp, QApplication)
    qapp.setStyleSheet(build_global_stylesheet())
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
    # AI 페르소나 — [v0.2.0] VibeFillService + ProviderService 주입
    window.register_page("ai_personas", AIPersonaPage(
        profile_service,
        vibe_service=vibe_fill_service,
        provider_service=provider_service,
    ))
    # 로어북 — [v0.2.0] VibeFillService + ProviderService 주입
    from chitchat.ui.pages.lorebook_page import LorebookPage
    window.register_page("lorebooks", LorebookPage(
        profile_service,
        vibe_service=vibe_fill_service,
        provider_service=provider_service,
    ))
    # 월드북 — [v0.2.0] VibeFillService + ProviderService 주입
    from chitchat.ui.pages.worldbook_page import WorldbookPage
    window.register_page("worldbooks", WorldbookPage(
        profile_service,
        vibe_service=vibe_fill_service,
        provider_service=provider_service,
    ))
    # 채팅 프로필
    from chitchat.ui.pages.chat_profile_page import ChatProfilePage
    window.register_page("chat_profiles", ChatProfilePage(profile_service))
    # 프롬프트 순서
    from chitchat.ui.pages.prompt_order_page import PromptOrderPage
    window.register_page("prompt_order", PromptOrderPage(profile_service))
    # [v0.3.0] 설정 페이지 — 플레이스홀더 → 실제 SettingsPage 교체
    from chitchat.ui.pages.settings_page import SettingsPage
    window.register_page("settings", SettingsPage(str(settings.app_data_dir)))
    logger.info("MainWindow 조립 완료. 페이지 %d개 등록.", 10)
    return qapp, window

