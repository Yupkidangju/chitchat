# src/chitchat/ui/pages/worldbook_page.py
# [v0.1.0b0] 월드북 관리 페이지
from __future__ import annotations
import logging
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QPushButton, QSpinBox, QSplitter,
    QTextEdit, QVBoxLayout, QWidget,
)
from chitchat.services.profile_service import ProfileService
from chitchat.ui.theme import COLORS, SPACING

logger = logging.getLogger(__name__)

class WorldbookPage(QWidget):
    """월드북 + 엔트리 관리 페이지."""
    def __init__(self, service: ProfileService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._svc = service
        self._cur_wb: str | None = None
        self._cur_we: str | None = None
        self._setup_ui()
        self._load_books()

    def _setup_ui(self) -> None:
        lo = QHBoxLayout(self); lo.setContentsMargins(0,0,0,0)
        sp = QSplitter(Qt.Orientation.Horizontal); lo.addWidget(sp)
        # 좌측
        lw = QWidget(); ll = QVBoxLayout(lw)
        ll.setContentsMargins(SPACING.md, SPACING.md, SPACING.md, SPACING.md)
        ll.addWidget(QLabel("🌍 월드북"))
        self._book_list = QListWidget()
        self._book_list.currentItemChanged.connect(self._on_book_sel)
        ll.addWidget(self._book_list)
        bl = QHBoxLayout()
        b1 = QPushButton("+ 새 월드북"); b1.setObjectName("primaryButton"); b1.clicked.connect(self._on_new_book)
        b2 = QPushButton("삭제"); b2.setObjectName("dangerButton"); b2.clicked.connect(self._on_del_book)
        bl.addWidget(b1); bl.addWidget(b2); ll.addLayout(bl)
        g1 = QGroupBox("월드북 정보"); f1 = QFormLayout(g1)
        self._bk_name = QLineEdit(); f1.addRow("이름:", self._bk_name)
        self._bk_desc = QLineEdit(); f1.addRow("설명:", self._bk_desc)
        ll.addWidget(g1)
        bs1 = QPushButton("💾 월드북 저장"); bs1.clicked.connect(self._on_save_book); ll.addWidget(bs1)
        sp.addWidget(lw)
        # 중앙
        mw = QWidget(); ml = QVBoxLayout(mw)
        ml.setContentsMargins(SPACING.md, SPACING.md, SPACING.md, SPACING.md)
        ml.addWidget(QLabel("엔트리 목록"))
        self._entry_list = QListWidget()
        self._entry_list.currentItemChanged.connect(self._on_entry_sel)
        ml.addWidget(self._entry_list)
        el = QHBoxLayout()
        e1 = QPushButton("+ 엔트리"); e1.setObjectName("primaryButton"); e1.clicked.connect(self._on_new_entry)
        e2 = QPushButton("삭제"); e2.setObjectName("dangerButton"); e2.clicked.connect(self._on_del_entry)
        el.addWidget(e1); el.addWidget(e2); ml.addLayout(el)
        sp.addWidget(mw)
        # 우측
        rw = QWidget(); rl = QVBoxLayout(rw)
        rl.setContentsMargins(SPACING.lg, SPACING.md, SPACING.lg, SPACING.md)
        g2 = QGroupBox("엔트리 편집"); f2 = QFormLayout(g2)
        self._e_title = QLineEdit(); f2.addRow("제목:", self._e_title)
        self._e_content = QTextEdit(); self._e_content.setMaximumHeight(150); f2.addRow("내용:", self._e_content)
        self._e_pri = QSpinBox(); self._e_pri.setRange(0,1000); self._e_pri.setValue(100)
        f2.addRow("우선순위:", self._e_pri)
        rl.addWidget(g2)
        bs2 = QPushButton("💾 엔트리 저장"); bs2.setObjectName("primaryButton"); bs2.clicked.connect(self._on_save_entry)
        rl.addWidget(bs2)
        self._st = QLabel(""); self._st.setObjectName("subtitle"); rl.addWidget(self._st)
        rl.addStretch(); sp.addWidget(rw); sp.setSizes([250, 250, 400])

    def _load_books(self) -> None:
        self._book_list.clear()
        for b in self._svc.get_all_worldbooks():
            it = QListWidgetItem(b.name); it.setData(Qt.ItemDataRole.UserRole, b.id); self._book_list.addItem(it)

    def _on_book_sel(self, c: QListWidgetItem | None, _: QListWidgetItem | None) -> None:
        if not c: return
        b = self._svc.get_worldbook(c.data(Qt.ItemDataRole.UserRole))
        if not b: return
        self._cur_wb = b.id; self._bk_name.setText(b.name); self._bk_desc.setText(b.description)
        self._load_entries()

    def _load_entries(self) -> None:
        self._entry_list.clear(); self._cur_we = None
        if not self._cur_wb: return
        for e in self._svc.get_world_entries(self._cur_wb):
            it = QListWidgetItem(f"[{e.priority}] {e.title}"); it.setData(Qt.ItemDataRole.UserRole, e.id)
            self._entry_list.addItem(it)

    def _on_entry_sel(self, c: QListWidgetItem | None, _: QListWidgetItem | None) -> None:
        if not c: return
        entries = self._svc.get_world_entries(self._cur_wb or "")
        eid = c.data(Qt.ItemDataRole.UserRole)
        for e in entries:
            if e.id == eid:
                self._cur_we = e.id; self._e_title.setText(e.title)
                self._e_content.setPlainText(e.content); self._e_pri.setValue(e.priority); break

    def _on_new_book(self) -> None:
        self._cur_wb = None; self._bk_name.clear(); self._bk_desc.clear(); self._entry_list.clear()

    def _on_save_book(self) -> None:
        n = self._bk_name.text().strip()
        if not n: self._st.setText("⚠️ 이름 필수"); return
        self._svc.save_worldbook(name=n, description=self._bk_desc.text().strip(), existing_id=self._cur_wb)
        self._st.setText(f"✅ '{n}' 저장!"); self._st.setStyleSheet(f"color:{COLORS.accent_success};"); self._load_books()

    def _on_del_book(self) -> None:
        if not self._cur_wb: return
        if QMessageBox.question(self,"확인","삭제?") == QMessageBox.StandardButton.Yes:
            self._svc.delete_worldbook(self._cur_wb); self._on_new_book(); self._load_books()

    def _on_new_entry(self) -> None:
        self._cur_we = None; self._e_title.clear(); self._e_content.clear(); self._e_pri.setValue(100)

    def _on_save_entry(self) -> None:
        if not self._cur_wb: self._st.setText("⚠️ 월드북 먼저 선택"); return
        t = self._e_title.text().strip(); c = self._e_content.toPlainText().strip()
        if not t or not c: self._st.setText("⚠️ 제목, 내용 필수"); return
        self._svc.save_world_entry(worldbook_id=self._cur_wb, title=t, content=c,
            priority=self._e_pri.value(), existing_id=self._cur_we)
        self._st.setText(f"✅ 엔트리 '{t}' 저장!"); self._st.setStyleSheet(f"color:{COLORS.accent_success};")
        self._load_entries()

    def _on_del_entry(self) -> None:
        if not self._cur_we: return
        if QMessageBox.question(self,"확인","삭제?") == QMessageBox.StandardButton.Yes:
            self._svc.delete_world_entry(self._cur_we); self._on_new_entry(); self._load_entries()
