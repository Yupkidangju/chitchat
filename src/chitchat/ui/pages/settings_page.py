# src/chitchat/ui/pages/settings_page.py
# [v0.3.0] 설정 페이지
#
# 좌측 사이드바 "⚡ 설정" 메뉴에서 표시되는 설정 페이지.
# UI 언어, Vibe Fill AI 출력 언어 등의 사용자 설정을 관리한다.
# 설정 변경 시 즉시 settings.json에 저장된다.

from __future__ import annotations

import logging

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from chitchat.config.user_preferences import UserPreferences
from chitchat.i18n import tr
from chitchat.i18n.translator import LOCALE_DISPLAY_NAMES, SUPPORTED_LOCALES
from chitchat.ui.theme import COLORS, SPACING

logger = logging.getLogger(__name__)


class SettingsPage(QWidget):
    """앱 설정 페이지.

    UI 언어, Vibe Fill 출력 언어, 앱 정보를 표시하고 설정을 관리한다.
    설정 변경 시 즉시 settings.json에 저장된다.
    """

    def __init__(
        self,
        app_data_dir_str: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._app_data_dir_str = app_data_dir_str
        self._prefs = UserPreferences.instance()
        self._setup_ui()

    def _setup_ui(self) -> None:
        """UI를 구성한다."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING.xl, SPACING.xl, SPACING.xl, SPACING.xl)
        layout.setSpacing(SPACING.lg)

        # 페이지 타이틀
        title = QLabel(tr("settings.title"))
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        # === 일반 설정 ===
        general_group = QGroupBox(tr("settings.general"))
        general_form = QFormLayout(general_group)

        # UI 언어 드롭다운
        self._locale_combo = QComboBox()
        for locale_code in SUPPORTED_LOCALES:
            display_name = LOCALE_DISPLAY_NAMES.get(locale_code, locale_code)
            self._locale_combo.addItem(display_name, locale_code)

        # 현재 로케일 선택
        current_locale = self._prefs.ui_locale
        idx = SUPPORTED_LOCALES.index(current_locale) if current_locale in SUPPORTED_LOCALES else 0
        self._locale_combo.setCurrentIndex(idx)
        self._locale_combo.currentIndexChanged.connect(self._on_locale_changed)
        general_form.addRow(tr("settings.ui_language"), self._locale_combo)

        # 재시작 안내 레이블 (초기에는 숨김)
        self._restart_label = QLabel(tr("settings.restart_required"))
        self._restart_label.setStyleSheet(f"color: {COLORS.accent_warning}; font-style: italic;")
        self._restart_label.setWordWrap(True)
        self._restart_label.setVisible(False)
        general_form.addRow("", self._restart_label)

        layout.addWidget(general_group)

        # === Vibe Fill 설정 ===
        vibe_group = QGroupBox(tr("settings.vibe_section"))
        vibe_form = QFormLayout(vibe_group)

        # AI 출력 언어 드롭다운
        self._vibe_lang_combo = QComboBox()
        self._vibe_lang_combo.addItem(tr("settings.vibe_output_ko"), "ko")
        self._vibe_lang_combo.addItem(tr("settings.vibe_output_en"), "en")

        # 현재 선택
        current_vibe_lang = self._prefs.vibe_output_language
        vibe_idx = 0 if current_vibe_lang == "ko" else 1
        self._vibe_lang_combo.setCurrentIndex(vibe_idx)
        self._vibe_lang_combo.currentIndexChanged.connect(self._on_vibe_lang_changed)
        vibe_form.addRow(tr("settings.vibe_output_lang"), self._vibe_lang_combo)

        layout.addWidget(vibe_group)

        # === 앱 정보 ===
        info_group = QGroupBox(tr("settings.app_info"))
        info_form = QFormLayout(info_group)

        version_label = QLabel("v0.3.0")
        info_form.addRow(tr("settings.version"), version_label)

        data_path_label = QLabel(self._app_data_dir_str)
        data_path_label.setWordWrap(True)
        data_path_label.setTextInteractionFlags(
            data_path_label.textInteractionFlags()
            | data_path_label.textInteractionFlags().TextSelectableByMouse
        )
        info_form.addRow(tr("settings.data_path"), data_path_label)

        layout.addWidget(info_group)

        # 상태 레이블
        self._status_label = QLabel("")
        self._status_label.setObjectName("subtitle")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        layout.addStretch()

    def _on_locale_changed(self, _index: int) -> None:
        """UI 언어 변경 시 설정을 저장하고 재시작 안내를 표시한다."""
        locale_code = self._locale_combo.currentData()
        if locale_code and locale_code != self._prefs.ui_locale:
            self._prefs.ui_locale = locale_code
            self._prefs.save()
            self._restart_label.setVisible(True)
            self._status_label.setText(tr("settings.saved"))
            self._status_label.setStyleSheet(f"color: {COLORS.accent_success};")
            logger.info("UI 로케일 변경: %s (재시작 필요)", locale_code)

    def _on_vibe_lang_changed(self, _index: int) -> None:
        """Vibe Fill 출력 언어 변경 시 설정을 즉시 저장한다."""
        lang_code = self._vibe_lang_combo.currentData()
        if lang_code and lang_code != self._prefs.vibe_output_language:
            self._prefs.vibe_output_language = lang_code
            self._prefs.save()
            self._status_label.setText(tr("settings.saved"))
            self._status_label.setStyleSheet(f"color: {COLORS.accent_success};")
            logger.info("Vibe Fill 출력 언어 변경: %s", lang_code)
