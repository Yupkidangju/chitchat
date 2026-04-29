# src/chitchat/ui/pages/persona_page.py
# [v0.1.0b0] UserPersona + AIPersona 관리 페이지
from __future__ import annotations
import logging
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QPushButton, QSplitter, QTextEdit,
    QVBoxLayout, QWidget,
)
from chitchat.services.profile_service import ProfileService
from chitchat.ui.theme import COLORS, SPACING

logger = logging.getLogger(__name__)

class UserPersonaPage(QWidget):
    """사용자 페르소나 관리 페이지."""
    def __init__(self, service: ProfileService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._svc = service
        self._cur_id: str | None = None
        self._setup_ui()
        self._load()

    def _setup_ui(self) -> None:
        lo = QHBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        sp = QSplitter(Qt.Orientation.Horizontal)
        lo.addWidget(sp)
        # 좌측
        lw = QWidget()
        ll = QVBoxLayout(lw)
        ll.setContentsMargins(SPACING.md, SPACING.md, SPACING.md, SPACING.md)
        ll.addWidget(QLabel("사용자 페르소나"))
        self._list = QListWidget()
        self._list.currentItemChanged.connect(self._on_sel)
        ll.addWidget(self._list)
        bl = QHBoxLayout()
        b1 = QPushButton("+ 새 페르소나"); b1.setObjectName("primaryButton"); b1.clicked.connect(self._on_new)
        b2 = QPushButton("삭제"); b2.setObjectName("dangerButton"); b2.clicked.connect(self._on_del)
        bl.addWidget(b1); bl.addWidget(b2)
        ll.addLayout(bl)
        sp.addWidget(lw)
        # 우측
        rw = QWidget()
        rl = QVBoxLayout(rw)
        rl.setContentsMargins(SPACING.lg, SPACING.md, SPACING.lg, SPACING.md)
        g = QGroupBox("편집")
        f = QFormLayout(g)
        self._name = QLineEdit(); f.addRow("이름:", self._name)
        self._desc = QTextEdit(); self._desc.setMaximumHeight(120); f.addRow("설명:", self._desc)
        self._style = QTextEdit(); self._style.setMaximumHeight(80); f.addRow("말투:", self._style)
        self._bound = QTextEdit(); self._bound.setMaximumHeight(80); f.addRow("경계:", self._bound)
        rl.addWidget(g)
        bs = QPushButton("💾 저장"); bs.setObjectName("primaryButton"); bs.clicked.connect(self._on_save)
        rl.addWidget(bs)
        self._st = QLabel(""); self._st.setObjectName("subtitle"); rl.addWidget(self._st)
        rl.addStretch()
        sp.addWidget(rw); sp.setSizes([280, 600])

    def _load(self) -> None:
        self._list.clear()
        for p in self._svc.get_all_user_personas():
            it = QListWidgetItem(p.name); it.setData(Qt.ItemDataRole.UserRole, p.id); self._list.addItem(it)

    def _on_sel(self, c: QListWidgetItem | None, _: QListWidgetItem | None) -> None:
        if not c: return
        p = self._svc.get_user_persona(c.data(Qt.ItemDataRole.UserRole))
        if not p: return
        self._cur_id = p.id; self._name.setText(p.name); self._desc.setPlainText(p.description)
        self._style.setPlainText(p.speaking_style); self._bound.setPlainText(p.boundaries)

    def _on_new(self) -> None:
        self._cur_id = None; self._name.clear(); self._desc.clear(); self._style.clear(); self._bound.clear()

    def _on_save(self) -> None:
        n, d = self._name.text().strip(), self._desc.toPlainText().strip()
        if not n or not d: self._st.setText("⚠️ 이름과 설명 필수"); return
        self._svc.save_user_persona(name=n, description=d, speaking_style=self._style.toPlainText().strip(),
            boundaries=self._bound.toPlainText().strip(), existing_id=self._cur_id)
        self._st.setText(f"✅ '{n}' 저장!"); self._st.setStyleSheet(f"color:{COLORS.accent_success};"); self._load()

    def _on_del(self) -> None:
        if not self._cur_id: return
        if QMessageBox.question(self,"확인","삭제?") == QMessageBox.StandardButton.Yes:
            self._svc.delete_user_persona(self._cur_id); self._on_new(); self._load()


class AIPersonaPage(QWidget):
    """AI 페르소나 관리 페이지."""
    def __init__(self, service: ProfileService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._svc = service
        self._cur_id: str | None = None
        self._setup_ui()
        self._load()

    def _setup_ui(self) -> None:
        lo = QHBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        sp = QSplitter(Qt.Orientation.Horizontal)
        lo.addWidget(sp)
        lw = QWidget()
        ll = QVBoxLayout(lw)
        ll.setContentsMargins(SPACING.md, SPACING.md, SPACING.md, SPACING.md)
        ll.addWidget(QLabel("AI 페르소나"))
        self._list = QListWidget()
        self._list.currentItemChanged.connect(self._on_sel)
        ll.addWidget(self._list)
        bl = QHBoxLayout()
        b1 = QPushButton("+ 새 AI 페르소나"); b1.setObjectName("primaryButton"); b1.clicked.connect(self._on_new)
        b2 = QPushButton("삭제"); b2.setObjectName("dangerButton"); b2.clicked.connect(self._on_del)
        bl.addWidget(b1); bl.addWidget(b2)
        ll.addLayout(bl)
        sp.addWidget(lw)
        rw = QWidget()
        rl = QVBoxLayout(rw)
        rl.setContentsMargins(SPACING.lg, SPACING.md, SPACING.lg, SPACING.md)
        g = QGroupBox("AI 페르소나 편집")
        f = QFormLayout(g)
        self._name = QLineEdit(); f.addRow("이름:", self._name)
        self._role = QLineEdit(); self._role.setPlaceholderText("예: 고서관 관리자 미라"); f.addRow("역할:", self._role)
        self._pers = QTextEdit(); self._pers.setMaximumHeight(100); f.addRow("성격:", self._pers)
        self._style = QTextEdit(); self._style.setMaximumHeight(80); f.addRow("말투:", self._style)
        self._goals = QTextEdit(); self._goals.setMaximumHeight(80); f.addRow("목표:", self._goals)
        self._restr = QTextEdit(); self._restr.setMaximumHeight(80); f.addRow("제한:", self._restr)
        rl.addWidget(g)
        bs = QPushButton("💾 저장"); bs.setObjectName("primaryButton"); bs.clicked.connect(self._on_save)
        rl.addWidget(bs)
        self._st = QLabel(""); self._st.setObjectName("subtitle"); rl.addWidget(self._st)
        rl.addStretch()
        sp.addWidget(rw); sp.setSizes([280, 600])

    def _load(self) -> None:
        self._list.clear()
        for p in self._svc.get_all_ai_personas():
            it = QListWidgetItem(f"{p.name} — {p.role_name}"); it.setData(Qt.ItemDataRole.UserRole, p.id)
            self._list.addItem(it)

    def _on_sel(self, c: QListWidgetItem | None, _: QListWidgetItem | None) -> None:
        if not c: return
        p = self._svc.get_ai_persona(c.data(Qt.ItemDataRole.UserRole))
        if not p: return
        self._cur_id = p.id; self._name.setText(p.name); self._role.setText(p.role_name)
        self._pers.setPlainText(p.personality); self._style.setPlainText(p.speaking_style)
        self._goals.setPlainText(p.goals); self._restr.setPlainText(p.restrictions)

    def _on_new(self) -> None:
        self._cur_id = None
        for w in [self._name, self._role]: w.clear()
        for w in [self._pers, self._style, self._goals, self._restr]: w.clear()

    def _on_save(self) -> None:
        n = self._name.text().strip(); r = self._role.text().strip()
        pe = self._pers.toPlainText().strip(); st = self._style.toPlainText().strip()
        if not all([n, r, pe, st]): self._st.setText("⚠️ 이름, 역할, 성격, 말투 필수"); return
        self._svc.save_ai_persona(name=n, role_name=r, personality=pe, speaking_style=st,
            goals=self._goals.toPlainText().strip(), restrictions=self._restr.toPlainText().strip(),
            existing_id=self._cur_id)
        self._st.setText(f"✅ '{n}' 저장!"); self._st.setStyleSheet(f"color:{COLORS.accent_success};"); self._load()

    def _on_del(self) -> None:
        if not self._cur_id: return
        if QMessageBox.question(self,"확인","삭제?") == QMessageBox.StandardButton.Yes:
            self._svc.delete_ai_persona(self._cur_id); self._on_new(); self._load()
