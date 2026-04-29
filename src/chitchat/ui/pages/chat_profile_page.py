# src/chitchat/ui/pages/chat_profile_page.py
# [v0.1.0b0] 채팅 프로필 관리 페이지
#
# ModelProfile 선택 + AI Persona 선택 + Lorebook/Worldbook 선택 + PromptOrder + system_base.
# 첫 사용자 완주 루트의 마지막 퍼즐.
from __future__ import annotations
import json
import logging
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMessageBox, QPushButton,
    QSplitter, QTextEdit, QVBoxLayout, QWidget,
)
from chitchat.services.profile_service import ProfileService
from chitchat.ui.theme import COLORS, SPACING

logger = logging.getLogger(__name__)

# 기본 PromptOrder: spec.md §12.1에서 정의된 표준 순서
_DEFAULT_PROMPT_ORDER = json.dumps([
    {"kind": "system_base", "enabled": True},
    {"kind": "user_persona", "enabled": True},
    {"kind": "ai_persona", "enabled": True},
    {"kind": "worldbook", "enabled": True},
    {"kind": "lorebook", "enabled": True},
    {"kind": "chat_history", "enabled": True},
    {"kind": "current_input", "enabled": True},
], ensure_ascii=False)


class ChatProfilePage(QWidget):
    """채팅 프로필 관리 페이지.

    ModelProfile + AI Persona + Lorebook + Worldbook + PromptOrder + system_base 조합.
    """
    def __init__(self, profile_service: ProfileService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._svc = profile_service
        self._current_id: str | None = None
        self._setup_ui()
        self._load_list()

    def _setup_ui(self) -> None:
        lo = QHBoxLayout(self); lo.setContentsMargins(0, 0, 0, 0); lo.setSpacing(0)
        sp = QSplitter(Qt.Orientation.Horizontal); lo.addWidget(sp)

        # 좌측: 채팅 프로필 목록
        left = QWidget(); ll = QVBoxLayout(left)
        ll.setContentsMargins(SPACING.md, SPACING.md, SPACING.md, SPACING.md)
        ll.addWidget(QLabel("🎯 채팅 프로필 목록"))
        self._list = QListWidget()
        self._list.currentItemChanged.connect(self._on_sel)
        ll.addWidget(self._list)
        blo = QHBoxLayout()
        bn = QPushButton("+ 새 프로필"); bn.setObjectName("primaryButton"); bn.clicked.connect(self._on_new); blo.addWidget(bn)
        bd = QPushButton("삭제"); bd.setObjectName("dangerButton"); bd.clicked.connect(self._on_delete); blo.addWidget(bd)
        ll.addLayout(blo)
        sp.addWidget(left)

        # 우측: 편집 폼
        right = QWidget(); rl = QVBoxLayout(right)
        rl.setContentsMargins(SPACING.lg, SPACING.md, SPACING.lg, SPACING.md)
        rl.addWidget(QLabel("채팅 프로필 설정"))

        # 기본 정보
        fg = QGroupBox("기본 정보"); form = QFormLayout(fg)
        self._name_edit = QLineEdit(); self._name_edit.setPlaceholderText("예: 기본 채팅 프로필")
        form.addRow("프로필 이름:", self._name_edit)

        # ModelProfile 선택 (리스트 위젯, 단일 선택)
        self._mp_list = QListWidget(); self._mp_list.setMaximumHeight(80)
        form.addRow("모델 프로필:", self._mp_list)

        rl.addWidget(fg)

        # 참조 엔티티 선택
        rg = QGroupBox("참조 엔티티 (다중 선택 가능)"); rf = QVBoxLayout(rg)

        # AI Persona (다중 선택)
        rf.addWidget(QLabel("AI 페르소나:"))
        self._ai_list = QListWidget(); self._ai_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self._ai_list.setMaximumHeight(100); rf.addWidget(self._ai_list)

        # Lorebook (다중 선택)
        rf.addWidget(QLabel("로어북:"))
        self._lb_list = QListWidget(); self._lb_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self._lb_list.setMaximumHeight(80); rf.addWidget(self._lb_list)

        # Worldbook (다중 선택)
        rf.addWidget(QLabel("월드북:"))
        self._wb_list = QListWidget(); self._wb_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self._wb_list.setMaximumHeight(80); rf.addWidget(self._wb_list)

        rl.addWidget(rg)

        # System Base 프롬프트
        sg = QGroupBox("시스템 프롬프트"); sl = QVBoxLayout(sg)
        self._system_edit = QTextEdit()
        self._system_edit.setPlaceholderText("시스템 프롬프트를 입력하세요. 예: 당신은 친절한 AI 도우미입니다.")
        self._system_edit.setMaximumHeight(100)
        sl.addWidget(self._system_edit)
        rl.addWidget(sg)

        # 저장 버튼
        alo = QHBoxLayout()
        bs = QPushButton("💾 저장"); bs.setObjectName("primaryButton"); bs.clicked.connect(self._on_save); alo.addWidget(bs)
        rl.addLayout(alo)

        self._status = QLabel(""); self._status.setWordWrap(True); rl.addWidget(self._status)
        rl.addStretch()
        sp.addWidget(right)
        sp.setSizes([260, 640])

    # --- 데이터 로드 ---

    def _load_list(self) -> None:
        self._list.clear()
        for cp in self._svc.get_all_chat_profiles():
            it = QListWidgetItem(cp.name); it.setData(Qt.ItemDataRole.UserRole, cp.id)
            self._list.addItem(it)
        self._load_combos()

    def _load_combos(self) -> None:
        """참조 엔티티 목록을 로드한다."""
        # ModelProfile
        self._mp_list.clear()
        for mp in self._svc.get_all_model_profiles():
            it = QListWidgetItem(mp.name); it.setData(Qt.ItemDataRole.UserRole, mp.id)
            self._mp_list.addItem(it)
        # AI Persona
        self._ai_list.clear()
        for ai in self._svc.get_all_ai_personas():
            it = QListWidgetItem(f"{ai.name} ({ai.role_name})"); it.setData(Qt.ItemDataRole.UserRole, ai.id)
            self._ai_list.addItem(it)
        # Lorebook
        self._lb_list.clear()
        for lb in self._svc.get_all_lorebooks():
            it = QListWidgetItem(lb.name); it.setData(Qt.ItemDataRole.UserRole, lb.id)
            self._lb_list.addItem(it)
        # Worldbook
        self._wb_list.clear()
        for wb in self._svc.get_all_worldbooks():
            it = QListWidgetItem(wb.name); it.setData(Qt.ItemDataRole.UserRole, wb.id)
            self._wb_list.addItem(it)

    def _on_sel(self, cur: QListWidgetItem | None, _: QListWidgetItem | None) -> None:
        if not cur:
            return
        cp = self._svc.get_chat_profile(cur.data(Qt.ItemDataRole.UserRole))
        if not cp:
            return
        self._current_id = cp.id
        self._name_edit.setText(cp.name)
        self._system_edit.setPlainText(cp.system_base)
        # ModelProfile 선택
        for i in range(self._mp_list.count()):
            it = self._mp_list.item(i)
            if it and it.data(Qt.ItemDataRole.UserRole) == cp.model_profile_id:
                self._mp_list.setCurrentItem(it)
                break
        # AI Persona 선택
        ai_ids = set(json.loads(cp.ai_persona_ids_json))
        for i in range(self._ai_list.count()):
            it = self._ai_list.item(i)
            if it:
                it.setSelected(it.data(Qt.ItemDataRole.UserRole) in ai_ids)
        # Lorebook 선택
        lb_ids = set(json.loads(cp.lorebook_ids_json))
        for i in range(self._lb_list.count()):
            it = self._lb_list.item(i)
            if it:
                it.setSelected(it.data(Qt.ItemDataRole.UserRole) in lb_ids)
        # Worldbook 선택
        wb_ids = set(json.loads(cp.worldbook_ids_json))
        for i in range(self._wb_list.count()):
            it = self._wb_list.item(i)
            if it:
                it.setSelected(it.data(Qt.ItemDataRole.UserRole) in wb_ids)
        self._status.setText(f"로드 완료: {cp.name}")

    def _on_new(self) -> None:
        self._current_id = None
        self._name_edit.clear()
        self._system_edit.clear()
        self._mp_list.clearSelection()
        self._ai_list.clearSelection()
        self._lb_list.clearSelection()
        self._wb_list.clearSelection()
        self._status.setText("새 채팅 프로필을 작성하세요.")

    def _on_delete(self) -> None:
        if not self._current_id:
            return
        if QMessageBox.question(self, "확인", "삭제하시겠습니까?") == QMessageBox.StandardButton.Yes:
            self._svc.delete_chat_profile(self._current_id)
            self._current_id = None
            self._load_list()

    def _on_save(self) -> None:
        name = self._name_edit.text().strip()
        system_base = self._system_edit.toPlainText().strip()
        if not name:
            self._status.setText("⚠️ 이름을 입력하세요."); self._status.setStyleSheet(f"color:{COLORS.accent_danger};"); return
        if not system_base:
            self._status.setText("⚠️ 시스템 프롬프트를 입력하세요."); self._status.setStyleSheet(f"color:{COLORS.accent_danger};"); return
        # ModelProfile ID
        mp_item = self._mp_list.currentItem()
        if not mp_item:
            self._status.setText("⚠️ 모델 프로필을 선택하세요."); self._status.setStyleSheet(f"color:{COLORS.accent_danger};"); return
        mp_id = mp_item.data(Qt.ItemDataRole.UserRole)
        # AI Persona IDs
        ai_ids = [self._ai_list.item(i).data(Qt.ItemDataRole.UserRole)
                  for i in range(self._ai_list.count()) if self._ai_list.item(i).isSelected()]
        # Lorebook IDs
        lb_ids = [self._lb_list.item(i).data(Qt.ItemDataRole.UserRole)
                  for i in range(self._lb_list.count()) if self._lb_list.item(i).isSelected()]
        # Worldbook IDs
        wb_ids = [self._wb_list.item(i).data(Qt.ItemDataRole.UserRole)
                  for i in range(self._wb_list.count()) if self._wb_list.item(i).isSelected()]
        try:
            self._svc.save_chat_profile(
                name=name, model_profile_id=mp_id, ai_persona_ids=ai_ids,
                lorebook_ids=lb_ids, worldbook_ids=wb_ids,
                prompt_order_json=_DEFAULT_PROMPT_ORDER, system_base=system_base,
                existing_id=self._current_id,
            )
            self._status.setText(f"✅ '{name}' 저장 완료!"); self._status.setStyleSheet(f"color:{COLORS.accent_success};")
            self._load_list()
        except Exception as e:
            self._status.setText(f"❌ 저장 실패: {e}"); self._status.setStyleSheet(f"color:{COLORS.accent_danger};")
