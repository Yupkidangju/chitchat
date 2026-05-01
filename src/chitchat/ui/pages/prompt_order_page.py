# src/chitchat/ui/pages/prompt_order_page.py
# [v0.1.3] 프롬프트 블록 순서 관리 페이지
#
# spec.md §12.2, designs.md §10.9, DD-05 결정에 따라 구현.
# 사용자가 프롬프트 블록의 순서를 재정렬하고 개별 블록을 활성화/비활성화할 수 있다.
#
# 핵심 규칙 (DD-05):
#   - system_base: 비활성화/삭제 불가, 항상 최상단 고정
#   - current_input: 비활성화/삭제 불가, 항상 최하단 고정
#   - chat_history: 비활성화 가능, 삭제 불가
#   - 나머지 블록: 자유롭게 순서 변경 및 활성화/비활성화 가능
#
# SC-08 성공 기준: PromptOrder 변경 시 최종 프롬프트 순서가 변경됨
from __future__ import annotations

import json
import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from chitchat.services.profile_service import ProfileService
from chitchat.i18n import tr
from chitchat.ui.theme import COLORS, SPACING

logger = logging.getLogger(__name__)


# 블록 종류별 표시 정보 (kind → (이모지, 한국어 이름, 잠금 규칙 설명))
_BLOCK_DISPLAY: dict[str, tuple[str, str, str]] = {
    "system_base": ("📋", tr("prompt_order.system_base"), tr("prompt_order.fixed")),
    "ai_persona": ("🤖", tr("persona.ai_title"), tr("prompt_order.reorder")),
    "worldbook": ("🌍", tr("worldbook.list_title_short"), tr("prompt_order.reorder")),
    "lorebook": ("📖", tr("lorebook.list_title_short"), tr("prompt_order.reorder")),
    "user_persona": ("👤", tr("persona.user_title"), tr("prompt_order.reorder")),
    "chat_history": ("💬", tr("prompt_order.chat_history"), tr("prompt_order.disable_only")),
    "current_input": ("✏️", tr("prompt_order.current_input"), tr("prompt_order.fixed")),
}

# 고정 블록: 순서 이동 불가능한 블록 (최상단/최하단 고정)
_LOCKED_BLOCKS = {"system_base", "current_input"}

# 비활성화 불가 블록
_CANNOT_DISABLE = {"system_base", "current_input"}


class PromptOrderPage(QWidget):
    """프롬프트 블록 순서 관리 페이지.

    [v0.1.3] 사용자가 7종 프롬프트 블록의 순서를 재정렬하고,
    개별 블록을 활성화/비활성화하여 최종 프롬프트 조립에 반영한다.
    ChatProfile별로 다른 PromptOrder를 설정할 수 있다.
    """

    def __init__(self, profile_service: ProfileService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._psvc = profile_service
        self._current_profile_id: str | None = None
        # 현재 편집 중인 순서 데이터 (UI 상태)
        self._order_data: list[dict[str, object]] = []
        self._setup_ui()
        self._load_profiles()

    def _setup_ui(self) -> None:
        lo = QHBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(0)
        sp = QSplitter(Qt.Orientation.Horizontal)
        lo.addWidget(sp)

        # ━━━ 좌측: 채팅 프로필 선택 ━━━
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(SPACING.md, SPACING.md, SPACING.md, SPACING.md)
        ll.addWidget(QLabel(tr("prompt_order.profile_select")))
        ll.addWidget(QLabel(tr("prompt_order.profile_hint")))
        self._profile_list = QListWidget()
        self._profile_list.currentItemChanged.connect(self._on_profile_sel)
        ll.addWidget(self._profile_list)
        sp.addWidget(left)

        # ━━━ 중앙: 프롬프트 블록 순서 편집 ━━━
        center = QWidget()
        cl = QVBoxLayout(center)
        cl.setContentsMargins(SPACING.lg, SPACING.md, SPACING.lg, SPACING.md)
        cl.addWidget(QLabel(tr("prompt_order.title")))

        # 블록 리스트
        self._block_list = QListWidget()
        self._block_list.setDragDropMode(QListWidget.DragDropMode.NoDragDrop)
        cl.addWidget(self._block_list)

        # 이동 버튼
        btn_row = QHBoxLayout()
        self._btn_up = QPushButton(tr("prompt_order.move_up"))
        self._btn_up.setObjectName("primaryButton")
        self._btn_up.clicked.connect(self._move_up)
        btn_row.addWidget(self._btn_up)

        self._btn_down = QPushButton(tr("prompt_order.move_down"))
        self._btn_down.setObjectName("primaryButton")
        self._btn_down.clicked.connect(self._move_down)
        btn_row.addWidget(self._btn_down)

        self._btn_reset = QPushButton(tr("prompt_order.reset"))
        self._btn_reset.clicked.connect(self._reset_default)
        btn_row.addWidget(self._btn_reset)
        cl.addLayout(btn_row)

        # 활성화/비활성화 체크박스 영역
        toggle_group = QGroupBox(tr("prompt_order.toggle_group"))
        self._toggle_layout = QVBoxLayout(toggle_group)
        cl.addWidget(toggle_group)

        # 저장 버튼
        save_row = QHBoxLayout()
        self._btn_save = QPushButton(tr("prompt_order.save"))
        self._btn_save.setObjectName("primaryButton")
        self._btn_save.clicked.connect(self._on_save)
        save_row.addWidget(self._btn_save)
        cl.addLayout(save_row)

        self._status = QLabel("")
        self._status.setWordWrap(True)
        cl.addWidget(self._status)
        cl.addStretch()
        sp.addWidget(center)

        # ━━━ 우측: 미리보기 ━━━
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(SPACING.md, SPACING.md, SPACING.md, SPACING.md)
        rl.addWidget(QLabel(tr("prompt_order.preview_title")))
        rl.addWidget(QLabel(tr("prompt_order.preview_hint")))
        self._preview = QTextEdit()
        self._preview.setReadOnly(True)
        rl.addWidget(self._preview)

        # 규칙 안내
        rules_group = QGroupBox(tr("prompt_order.rules_title"))
        rules_layout = QVBoxLayout(rules_group)
        for kind, (emoji, name, rule) in _BLOCK_DISPLAY.items():
            lbl = QLabel(f"  {emoji} {name}: {rule}")
            lbl.setWordWrap(True)
            if kind in _LOCKED_BLOCKS:
                lbl.setStyleSheet(f"color:{COLORS.accent_warning};")
            rules_layout.addWidget(lbl)
        rl.addWidget(rules_group)
        rl.addStretch()
        sp.addWidget(right)
        sp.setSizes([220, 400, 280])

    # ━━━ 데이터 로드 ━━━

    def _load_profiles(self) -> None:
        """채팅 프로필 목록을 갱신한다."""
        self._profile_list.clear()
        for cp in self._psvc.get_all_chat_profiles():
            it = QListWidgetItem(f"🎯 {cp.name}")
            it.setData(Qt.ItemDataRole.UserRole, cp.id)
            self._profile_list.addItem(it)

    def _on_profile_sel(self, cur: QListWidgetItem | None, _: QListWidgetItem | None) -> None:
        """채팅 프로필 선택 시 해당 프로필의 PromptOrder를 로드한다."""
        if not cur:
            return
        pid = cur.data(Qt.ItemDataRole.UserRole)
        self._current_profile_id = pid
        cp = self._psvc.get_chat_profile(pid)
        if not cp:
            return
        # PromptOrder JSON 파싱
        try:
            self._order_data = json.loads(cp.prompt_order_json)
        except (json.JSONDecodeError, TypeError):
            # 파싱 실패 시 기본값 사용
            self._order_data = _default_order()
        self._refresh_ui()

    # ━━━ UI 갱신 ━━━

    def _refresh_ui(self) -> None:
        """블록 리스트, 토글 체크박스, 미리보기를 모두 갱신한다."""
        # 블록 리스트 갱신
        self._block_list.blockSignals(True)
        self._block_list.clear()
        for i, block in enumerate(self._order_data):
            kind = str(block.get("kind", ""))
            enabled = bool(block.get("enabled", True))
            emoji, name, _ = _BLOCK_DISPLAY.get(kind, ("❓", kind, ""))
            status = "✅" if enabled else "⬜"
            locked = "🔒" if kind in _LOCKED_BLOCKS else ""
            text = f"{i + 1}. {status} {emoji} {name} {locked}"
            it = QListWidgetItem(text)
            it.setData(Qt.ItemDataRole.UserRole, i)
            # 잠긴 블록은 선택 불가 아닌 시각적 구분만
            if kind in _LOCKED_BLOCKS:
                it.setForeground(Qt.GlobalColor.gray)
            self._block_list.addItem(it)
        self._block_list.blockSignals(False)

        # 토글 체크박스 갱신
        _clear_layout(self._toggle_layout)
        for i, block in enumerate(self._order_data):
            kind = str(block.get("kind", ""))
            enabled = bool(block.get("enabled", True))
            emoji, name, _ = _BLOCK_DISPLAY.get(kind, ("❓", kind, ""))
            cb = QCheckBox(f"{emoji} {name}")
            cb.setChecked(enabled)
            # 비활성화 불가 블록은 체크박스도 비활성화
            if kind in _CANNOT_DISABLE:
                cb.setEnabled(False)
            # 체크 변경 시 데이터 반영
            cb.stateChanged.connect(lambda state, idx=i: self._on_toggle(idx, state))
            self._toggle_layout.addWidget(cb)

        # 미리보기 갱신
        self._update_preview()

    def _update_preview(self) -> None:
        """활성화된 블록만 순서대로 미리보기에 표시한다."""
        lines = []
        step = 1
        for block in self._order_data:
            kind = str(block.get("kind", ""))
            enabled = bool(block.get("enabled", True))
            emoji, name, _ = _BLOCK_DISPLAY.get(kind, ("❓", kind, ""))
            if enabled:
                lines.append(f"  {step}. {emoji} {name} ({kind})")
                step += 1
            else:
                lines.append(f"  ⬜ {emoji} {name} ({kind}) — {tr('prompt_order.disabled')}")
        self._preview.setPlainText(tr("prompt_order.assembly_header") + "\n" + "\n".join(lines))

    # ━━━ 블록 이동 ━━━

    def _move_up(self) -> None:
        """선택된 블록을 위로 이동한다. 잠긴 블록은 이동 불가."""
        cur = self._block_list.currentRow()
        if cur <= 0:
            return
        kind = str(self._order_data[cur].get("kind", ""))
        kind_above = str(self._order_data[cur - 1].get("kind", ""))
        # 잠긴 블록이면 이동 불가
        if kind in _LOCKED_BLOCKS or kind_above in _LOCKED_BLOCKS:
            self._status.setText(tr("prompt_order.fixed_block"))
            self._status.setStyleSheet(f"color:{COLORS.accent_warning};")
            return
        # 교환
        self._order_data[cur], self._order_data[cur - 1] = self._order_data[cur - 1], self._order_data[cur]
        self._refresh_ui()
        self._block_list.setCurrentRow(cur - 1)
        self._status.setText(tr("prompt_order.moved_up"))
        self._status.setStyleSheet(f"color:{COLORS.text_primary};")

    def _move_down(self) -> None:
        """선택된 블록을 아래로 이동한다. 잠긴 블록은 이동 불가."""
        cur = self._block_list.currentRow()
        if cur < 0 or cur >= len(self._order_data) - 1:
            return
        kind = str(self._order_data[cur].get("kind", ""))
        kind_below = str(self._order_data[cur + 1].get("kind", ""))
        # 잠긴 블록이면 이동 불가
        if kind in _LOCKED_BLOCKS or kind_below in _LOCKED_BLOCKS:
            self._status.setText(tr("prompt_order.fixed_block"))
            self._status.setStyleSheet(f"color:{COLORS.accent_warning};")
            return
        # 교환
        self._order_data[cur], self._order_data[cur + 1] = self._order_data[cur + 1], self._order_data[cur]
        self._refresh_ui()
        self._block_list.setCurrentRow(cur + 1)
        self._status.setText(tr("prompt_order.moved_down"))
        self._status.setStyleSheet(f"color:{COLORS.text_primary};")

    def _on_toggle(self, idx: int, state: int) -> None:
        """블록의 활성화 상태를 변경한다."""
        if 0 <= idx < len(self._order_data):
            self._order_data[idx]["enabled"] = state == Qt.CheckState.Checked.value
            self._update_preview()

    def _reset_default(self) -> None:
        """기본 프롬프트 순서로 복원한다."""
        result = QMessageBox.question(
            self, tr("prompt_order.reset_title"), tr("prompt_order.reset_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if result == QMessageBox.StandardButton.Yes:
            self._order_data = _default_order()
            self._refresh_ui()
            self._status.setText(tr("prompt_order.reset_done"))
            self._status.setStyleSheet(f"color:{COLORS.accent_success};")

    # ━━━ 저장 ━━━

    def _on_save(self) -> None:
        """현재 순서를 ChatProfile의 prompt_order_json에 저장한다."""
        if not self._current_profile_id:
            self._status.setText(tr("prompt_order.select_profile_first"))
            self._status.setStyleSheet(f"color:{COLORS.accent_danger};")
            return
        cp = self._psvc.get_chat_profile(self._current_profile_id)
        if not cp:
            return
        # order_index를 10 간격으로 갱신하여 저장
        for i, block in enumerate(self._order_data):
            block["order_index"] = i * 10
        order_json = json.dumps(self._order_data, ensure_ascii=False)
        try:
            self._psvc.update_chat_profile_prompt_order(self._current_profile_id, order_json)
            self._status.setText(tr("prompt_order.saved"))
            self._status.setStyleSheet(f"color:{COLORS.accent_success};")
        except Exception as e:
            self._status.setText(tr("common.save_failed", e=e))
            self._status.setStyleSheet(f"color:{COLORS.accent_danger};")


# ━━━ 유틸리티 ━━━

def _default_order() -> list[dict[str, object]]:
    """spec.md §12.2에 정의된 기본 프롬프트 순서를 반환한다."""
    return [
        {"kind": "system_base", "enabled": True, "order_index": 0},
        {"kind": "ai_persona", "enabled": True, "order_index": 10},
        {"kind": "worldbook", "enabled": True, "order_index": 20},
        {"kind": "lorebook", "enabled": True, "order_index": 30},
        {"kind": "user_persona", "enabled": True, "order_index": 40},
        {"kind": "chat_history", "enabled": True, "order_index": 50},
        {"kind": "current_input", "enabled": True, "order_index": 60},
    ]


def _clear_layout(layout: QVBoxLayout) -> None:
    """QLayout의 모든 위젯을 제거한다."""
    while layout.count():
        child = layout.takeAt(0)
        w = child.widget() if child else None
        if w:
            w.deleteLater()
