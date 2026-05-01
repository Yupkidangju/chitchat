# src/chitchat/ui/widgets/entity_picker_dialog.py
# [v0.1.1] 참조 엔티티 선택 다이얼로그
#
# 채팅 프로필 페이지에서 AI 페르소나 / 로어북 / 월드북을 선택할 때
# 모달 다이얼로그 형태로 열리는 공용 선택 위젯이다.
# 기존에 선택된 항목은 체크 상태로 표시되며,
# 검색 필터로 목록이 많아도 쉽게 찾을 수 있다.
#
# 사용 방법:
#   dialog = EntityPickerDialog("AI 페르소나 선택", items, selected_ids, max_count=5)
#   if dialog.exec():
#       selected = dialog.get_selected_ids()

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from chitchat.i18n import tr
from chitchat.ui.theme import COLORS, SPACING


class EntityPickerDialog(QDialog):
    """참조 엔티티 선택 모달 다이얼로그.

    items: [(id, display_name), ...] 형태의 전체 후보 목록
    selected_ids: 이미 선택된 ID 집합
    max_count: 최대 선택 가능 개수 (0이면 무제한)
    """

    def __init__(
        self,
        title: str,
        items: list[tuple[str, str]],
        selected_ids: set[str],
        max_count: int = 0,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(420, 380)
        self.setModal(True)

        self._items = items  # (id, display_name) 원본 목록
        self._max_count = max_count
        self._checkboxes: list[tuple[str, QCheckBox]] = []

        self._setup_ui(selected_ids)

    def _setup_ui(self, selected_ids: set[str]) -> None:
        """다이얼로그 UI를 구성한다."""
        root = QVBoxLayout(self)
        root.setContentsMargins(SPACING.md, SPACING.md, SPACING.md, SPACING.md)
        root.setSpacing(SPACING.sm)

        # 제목 + 최대 선택 안내
        header = QHBoxLayout()
        title_label = QLabel(self.windowTitle())
        title_label.setObjectName("sectionTitle")
        header.addWidget(title_label)
        header.addStretch()
        if self._max_count > 0:
            limit_label = QLabel(tr("common.max_select", max=self._max_count))
            limit_label.setObjectName("subtitle")
            header.addWidget(limit_label)
        root.addLayout(header)

        # 검색 필터
        self._search = QLineEdit()
        self._search.setPlaceholderText(tr("common.search"))
        self._search.textChanged.connect(self._on_filter)
        root.addWidget(self._search)

        # 스크롤 가능한 체크박스 목록
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(SPACING.sm, SPACING.sm, SPACING.sm, SPACING.sm)
        self._list_layout.setSpacing(SPACING.xs)

        # 항목이 없을 때 안내 문구
        if not self._items:
            empty_label = QLabel(tr("common.no_items"))
            empty_label.setObjectName("subtitle")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._list_layout.addWidget(empty_label)
        else:
            for item_id, display_name in self._items:
                cb = QCheckBox(display_name)
                cb.setChecked(item_id in selected_ids)
                # 최대 개수 제한 시 체크 상태 변경 감시
                if self._max_count > 0:
                    cb.stateChanged.connect(self._on_check_changed)
                self._checkboxes.append((item_id, cb))
                self._list_layout.addWidget(cb)

        self._list_layout.addStretch()
        scroll.setWidget(self._list_container)
        root.addWidget(scroll)

        # 선택 현황 레이블
        self._count_label = QLabel("")
        self._count_label.setObjectName("subtitle")
        root.addWidget(self._count_label)
        self._update_count_label()

        # 확인 / 취소 버튼
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_cancel = QPushButton(tr("common.cancel"))
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_ok = QPushButton(tr("common.confirm"))
        btn_ok.setObjectName("primaryButton")
        btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(btn_ok)
        root.addLayout(btn_layout)

    # --- 이벤트 핸들러 ---

    def _on_filter(self, text: str) -> None:
        """검색 텍스트에 따라 체크박스 항목을 필터링한다."""
        keyword = text.strip().lower()
        for _, cb in self._checkboxes:
            # 검색어가 체크박스 라벨에 포함되면 표시
            cb.setVisible(keyword in cb.text().lower() if keyword else True)

    def _on_check_changed(self) -> None:
        """체크 상태가 변경될 때 최대 개수를 초과하면 비활성화한다."""
        self._update_count_label()
        checked_count = sum(1 for _, cb in self._checkboxes if cb.isChecked())
        if self._max_count > 0 and checked_count >= self._max_count:
            # 체크되지 않은 항목들을 비활성화
            for _, cb in self._checkboxes:
                if not cb.isChecked():
                    cb.setEnabled(False)
        else:
            # 모든 항목 활성화
            for _, cb in self._checkboxes:
                cb.setEnabled(True)

    def _update_count_label(self) -> None:
        """현재 선택 개수를 표시한다."""
        checked = sum(1 for _, cb in self._checkboxes if cb.isChecked())
        if self._max_count > 0:
            self._count_label.setText(tr("common.select_count", checked=checked, max=self._max_count))
            if checked >= self._max_count:
                self._count_label.setStyleSheet(f"color: {COLORS.accent_warning};")
            else:
                self._count_label.setStyleSheet(f"color: {COLORS.text_secondary};")
        else:
            self._count_label.setText(tr("common.select_count_no_max", checked=checked))

    # --- 공개 API ---

    def get_selected_ids(self) -> list[str]:
        """사용자가 확인을 누른 후 선택된 ID 목록을 반환한다."""
        return [item_id for item_id, cb in self._checkboxes if cb.isChecked()]
