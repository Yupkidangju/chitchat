# src/chitchat/ui/navigation.py
# [v0.1.0b0] 사이드바 네비게이션 위젯
#
# designs.md §3.1에서 정의된 사이드바를 구현한다.
# 9개 네비게이션 항목: 5개 설정 + 1개 채팅 + 3개 데이터 관리.
# 현재 선택된 항목은 accent_primary 배경으로 강조된다.

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from chitchat.ui.theme import COLORS, SPACING, TYPOGRAPHY


# 네비게이션 항목 정의 (순서, ID, 표시 이름, 아이콘 이모지)
NAV_ITEMS: list[tuple[str, str, str]] = [
    ("chat", "💬 채팅", "chat"),
    ("providers", "🔌 Provider", "providers"),
    ("model_profiles", "⚙️ 모델 프로필", "model_profiles"),
    ("user_personas", "👤 사용자 페르소나", "user_personas"),
    ("ai_personas", "🤖 AI 페르소나", "ai_personas"),
    ("lorebooks", "📖 로어북", "lorebooks"),
    ("worldbooks", "🌍 월드북", "worldbooks"),
    ("chat_profiles", "🎯 채팅 프로필", "chat_profiles"),
    ("settings", "⚡ 설정", "settings"),
]


class NavigationSidebar(QWidget):
    """사이드바 네비게이션 위젯.

    9개 항목을 표시하고, 클릭 시 page_changed Signal을 emit한다.
    """

    # 페이지 변경 시그널: page_id (str) 전달
    page_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("navigationSidebar")
        self.setFixedWidth(220)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """UI를 구성한다."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 앱 타이틀
        title = QLabel("chitchat")
        title.setObjectName("appTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"""
            QLabel {{
                font-size: {TYPOGRAPHY.font_size_xxl}px;
                font-weight: {TYPOGRAPHY.font_weight_bold};
                color: {COLORS.accent_primary};
                padding: {SPACING.lg}px;
                background-color: {COLORS.bg_secondary};
                border-bottom: 2px solid {COLORS.border};
                border-right: 2px solid {COLORS.border};
            }}
        """)
        layout.addWidget(title)

        # 네비게이션 리스트
        self._list = QListWidget()
        self._list.setObjectName("navList")
        self._list.setFrameShape(QListWidget.Shape.NoFrame)
        self._list.setStyleSheet(f"""
            QListWidget {{
                background-color: {COLORS.bg_secondary};
                border: none;
                border-right: 2px solid {COLORS.border};
                outline: none;
            }}
            QListWidget::item {{
                padding: {SPACING.md}px {SPACING.lg}px;
                border-bottom: 1px solid {COLORS.bg_primary};
                font-size: {TYPOGRAPHY.font_size_md}px;
                color: {COLORS.text_primary};
            }}
            QListWidget::item:selected {{
                background-color: {COLORS.accent_primary};
                color: {COLORS.bg_secondary};
                font-weight: {TYPOGRAPHY.font_weight_bold};
            }}
            QListWidget::item:hover:!selected {{
                background-color: {COLORS.bg_tertiary};
            }}
        """)

        for page_id, display_name, _ in NAV_ITEMS:
            item = QListWidgetItem(display_name)
            item.setData(Qt.ItemDataRole.UserRole, page_id)
            self._list.addItem(item)

        self._list.currentItemChanged.connect(self._on_item_changed)
        layout.addWidget(self._list, stretch=1)

        # 기본 선택: 첫 번째 항목 (채팅)
        self._list.setCurrentRow(0)

    def _on_item_changed(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        """네비게이션 항목 변경 시 Signal을 emit한다."""
        if current:
            page_id = current.data(Qt.ItemDataRole.UserRole)
            self.page_changed.emit(page_id)

    def select_page(self, page_id: str) -> None:
        """프로그래밍 방식으로 페이지를 선택한다."""
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == page_id:
                self._list.setCurrentRow(i)
                break
