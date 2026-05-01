# src/chitchat/ui/main_window.py
# [v0.3.0] 메인 윈도우 + QStackedWidget 페이지 라우팅
#
# designs.md §3에서 정의된 레이아웃을 구현한다.
# 좌측: NavigationSidebar (220px 고정)
# 우측: QStackedWidget (페이지 영역)
# 사이드바의 page_changed Signal에 따라 페이지를 전환한다.

from __future__ import annotations

import logging

from PySide6.QtCore import QSize
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from chitchat.i18n import tr
from chitchat.ui.navigation import NavigationSidebar
from chitchat.ui.theme import COLORS, SPACING

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """앱 메인 윈도우.

    좌측 사이드바 + 우측 페이지 영역으로 구성된다.
    register_page()로 페이지를 등록하고, 사이드바 클릭으로 전환한다.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("chitchat")
        self.setMinimumSize(QSize(1024, 640))
        self.resize(QSize(1280, 800))

        # 페이지 매핑: page_id → QStackedWidget index
        self._page_map: dict[str, int] = {}

        self._setup_ui()
        logger.info("MainWindow 초기화 완료.")

    def _setup_ui(self) -> None:
        """UI를 구성한다."""
        # 중앙 위젯
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 사이드바
        self._sidebar = NavigationSidebar()
        self._sidebar.page_changed.connect(self._on_page_changed)
        main_layout.addWidget(self._sidebar)

        # 페이지 스택
        self._stack = QStackedWidget()
        self._stack.setStyleSheet(f"""
            QStackedWidget {{
                background-color: {COLORS.bg_primary};
            }}
        """)
        main_layout.addWidget(self._stack, stretch=1)

        # 상태바
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        status_bar.showMessage(tr("app.status_ready"))

    def register_page(self, page_id: str, widget: QWidget) -> None:
        """페이지를 등록한다.

        Args:
            page_id: 네비게이션 항목의 page_id와 일치해야 한다.
            widget: 표시할 페이지 위젯.
        """
        index = self._stack.addWidget(widget)
        self._page_map[page_id] = index
        logger.debug("페이지 등록: %s (index=%d)", page_id, index)

    def _on_page_changed(self, page_id: str) -> None:
        """사이드바 선택 변경 시 페이지를 전환한다."""
        index = self._page_map.get(page_id)
        if index is not None:
            self._stack.setCurrentIndex(index)
            logger.debug("페이지 전환: %s", page_id)
        else:
            logger.warning("등록되지 않은 페이지: %s", page_id)


def _create_placeholder_page(title: str, description: str) -> QWidget:
    """아직 구현되지 않은 페이지용 플레이스홀더를 생성한다."""
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(SPACING.xl, SPACING.xl, SPACING.xl, SPACING.xl)
    layout.setSpacing(SPACING.md)

    title_label = QLabel(title)
    title_label.setObjectName("sectionTitle")

    desc_label = QLabel(description)
    desc_label.setObjectName("subtitle")

    layout.addWidget(title_label)
    layout.addWidget(desc_label)
    layout.addStretch()

    return page
