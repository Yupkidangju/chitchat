# src/chitchat/ui/pages/lorebook_page.py
# [v0.1.0b0] 로어북 관리 페이지
# [v0.2.0] Vibe Fill Phase 2: AI 로어 엔트리 자동 생성 + 미리보기 Append
from __future__ import annotations
import json
import logging
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
    QScrollArea, QSpinBox, QSplitter, QTextEdit, QVBoxLayout, QWidget,
)
from chitchat.services.profile_service import ProfileService
from chitchat.services.provider_service import ProviderService
from chitchat.services.vibe_fill_service import VibeFillService
from chitchat.ui.async_bridge import AsyncSignalBridge
from chitchat.i18n import tr
from chitchat.ui.theme import COLORS, SPACING

logger = logging.getLogger(__name__)


class LorebookPage(QWidget):
    """로어북 + 엔트리 관리 페이지.

    [v0.2.0] Vibe Fill Phase 2 확장:
    - AI Persona 선택 드롭다운으로 캐릭터 컨텍스트 주입
    - 바이브 텍스트 → AI 로어 엔트리 복수 건 생성
    - 생성 결과 미리보기 체크리스트 → 선택 항목만 Append 저장
    """

    def __init__(
        self,
        service: ProfileService,
        vibe_service: VibeFillService | None = None,
        provider_service: ProviderService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._svc = service
        self._vibe_svc = vibe_service
        self._prov_svc = provider_service
        self._cur_lb: str | None = None
        self._cur_le: str | None = None
        # Vibe Fill 생성 결과 임시 저장
        self._pending_entries: list[dict[str, Any]] = []
        self._pending_checks: list[QCheckBox] = []
        self._bridge: AsyncSignalBridge | None = None
        self._setup_ui()
        self._load_books()

    def _setup_ui(self) -> None:
        lo = QHBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        sp = QSplitter(Qt.Orientation.Horizontal)
        lo.addWidget(sp)

        # === 좌측: 로어북 목록 ===
        lw = QWidget()
        ll = QVBoxLayout(lw)
        ll.setContentsMargins(SPACING.md, SPACING.md, SPACING.md, SPACING.md)
        ll.addWidget(QLabel(tr("lorebook.list_title")))
        self._book_list = QListWidget()
        self._book_list.currentItemChanged.connect(self._on_book_sel)
        ll.addWidget(self._book_list)
        bl = QHBoxLayout()
        b1 = QPushButton(tr("lorebook.new_btn"))
        b1.setObjectName("primaryButton")
        b1.clicked.connect(self._on_new_book)
        b2 = QPushButton(tr("common.delete"))
        b2.setObjectName("dangerButton")
        b2.clicked.connect(self._on_del_book)
        bl.addWidget(b1)
        bl.addWidget(b2)
        ll.addLayout(bl)
        # 로어북 편집
        g1 = QGroupBox(tr("lorebook.info_title"))
        f1 = QFormLayout(g1)
        self._bk_name = QLineEdit()
        f1.addRow(tr("common.name"), self._bk_name)
        self._bk_desc = QLineEdit()
        f1.addRow(tr("common.description"), self._bk_desc)
        ll.addWidget(g1)
        bs1 = QPushButton(tr("lorebook.save_book_btn"))
        bs1.clicked.connect(self._on_save_book)
        ll.addWidget(bs1)
        sp.addWidget(lw)

        # === 중앙: 엔트리 목록 ===
        mw = QWidget()
        ml = QVBoxLayout(mw)
        ml.setContentsMargins(SPACING.md, SPACING.md, SPACING.md, SPACING.md)
        ml.addWidget(QLabel(tr("lorebook.entry_list")))
        self._entry_list = QListWidget()
        self._entry_list.currentItemChanged.connect(self._on_entry_sel)
        ml.addWidget(self._entry_list)
        el = QHBoxLayout()
        e1 = QPushButton(tr("lorebook.new_entry"))
        e1.setObjectName("primaryButton")
        e1.clicked.connect(self._on_new_entry)
        e2 = QPushButton(tr("common.delete"))
        e2.setObjectName("dangerButton")
        e2.clicked.connect(self._on_del_entry)
        el.addWidget(e1)
        el.addWidget(e2)
        ml.addLayout(el)
        sp.addWidget(mw)

        # === 우측: Vibe Fill + 엔트리 편집 (스크롤) ===
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        rw = QWidget()
        rl = QVBoxLayout(rw)
        rl.setContentsMargins(SPACING.lg, SPACING.md, SPACING.lg, SPACING.md)

        # --- Vibe Fill 패널 ---
        vibe_group = QGroupBox(tr("lorebook.vibe_title"))
        vibe_layout = QVBoxLayout(vibe_group)

        # AI Persona 선택 (선택 — 복수 불가, 단일 선택으로 간결하게)
        persona_layout = QHBoxLayout()
        persona_layout.addWidget(QLabel(tr("lorebook.char_ref")))
        self._persona_combo = QComboBox()
        persona_layout.addWidget(self._persona_combo, 1)
        vibe_layout.addLayout(persona_layout)

        # 바이브 텍스트 입력
        self._vibe_text = QTextEdit()
        self._vibe_text.setMaximumHeight(100)
        self._vibe_text.setPlaceholderText(tr("lorebook.vibe_ph"))
        vibe_layout.addWidget(self._vibe_text)

        # Provider + Model 선택
        sel_layout = QHBoxLayout()
        sel_layout.addWidget(QLabel(tr("vibe.provider_label")))
        self._prov_combo = QComboBox()
        self._prov_combo.currentIndexChanged.connect(self._on_provider_changed)
        sel_layout.addWidget(self._prov_combo, 1)
        sel_layout.addWidget(QLabel(tr("vibe.model_label")))
        self._model_combo = QComboBox()
        sel_layout.addWidget(self._model_combo, 1)
        vibe_layout.addLayout(sel_layout)

        self._btn_vibe = QPushButton(tr("lorebook.vibe_fill_btn"))
        self._btn_vibe.setObjectName("primaryButton")
        self._btn_vibe.clicked.connect(self._on_vibe_fill)
        vibe_layout.addWidget(self._btn_vibe)

        self._vibe_status = QLabel("")
        self._vibe_status.setObjectName("subtitle")
        vibe_layout.addWidget(self._vibe_status)

        rl.addWidget(vibe_group)

        # --- 생성 미리보기 (체크리스트) ---
        self._preview_group = QGroupBox(tr("lorebook.preview_title"))
        self._preview_layout = QVBoxLayout(self._preview_group)
        self._preview_group.setVisible(False)  # 생성 결과가 있을 때만 표시

        self._btn_append = QPushButton(tr("lorebook.append_btn"))
        self._btn_append.setObjectName("primaryButton")
        self._btn_append.clicked.connect(self._on_append_entries)
        self._preview_layout.addWidget(self._btn_append)

        rl.addWidget(self._preview_group)

        # --- 수동 엔트리 편집 ---
        g2 = QGroupBox(tr("lorebook.edit_title"))
        f2 = QFormLayout(g2)
        self._e_title = QLineEdit()
        f2.addRow(tr("lorebook.title_label"), self._e_title)
        self._e_keys = QLineEdit()
        self._e_keys.setPlaceholderText(tr("lorebook.keys_ph"))
        f2.addRow(tr("lorebook.keys_label"), self._e_keys)
        self._e_content = QTextEdit()
        self._e_content.setMaximumHeight(150)
        f2.addRow(tr("lorebook.content_label"), self._e_content)
        self._e_pri = QSpinBox()
        self._e_pri.setRange(0, 1000)
        self._e_pri.setValue(100)
        f2.addRow(tr("lorebook.priority_label"), self._e_pri)
        rl.addWidget(g2)

        bs2 = QPushButton(tr("lorebook.save_entry_btn"))
        bs2.setObjectName("primaryButton")
        bs2.clicked.connect(self._on_save_entry)
        rl.addWidget(bs2)
        self._st = QLabel("")
        self._st.setObjectName("subtitle")
        rl.addWidget(self._st)
        rl.addStretch()

        scroll.setWidget(rw)
        sp.addWidget(scroll)
        sp.setSizes([220, 220, 500])

        # 드롭다운 초기화
        self._load_providers()
        self._load_personas()

    # --- Provider/Model/Persona 드롭다운 ---

    def _load_providers(self) -> None:
        """등록된 Provider 목록을 드롭다운에 로드한다."""
        self._prov_combo.clear()
        if not self._prov_svc:
            self._prov_combo.addItem(tr("vibe.no_provider_connected"), "")
            return
        providers = self._prov_svc.get_all_providers()
        if not providers:
            self._prov_combo.addItem(tr("vibe.no_provider_registered"), "")
            return
        for p in providers:
            self._prov_combo.addItem(f"{p.name} ({p.provider_kind})", p.id)

    def _on_provider_changed(self, _index: int) -> None:
        """Provider 변경 시 모델 목록 갱신."""
        self._model_combo.clear()
        prov_id = self._prov_combo.currentData()
        if not prov_id or not self._prov_svc:
            return
        models = self._prov_svc.get_cached_models(prov_id)
        if not models:
            self._model_combo.addItem(tr("vibe.no_model"), "")
            return
        for m in models:
            self._model_combo.addItem(m.model_id, m.model_id)

    def _load_personas(self) -> None:
        """AI Persona 목록을 드롭다운에 로드한다."""
        self._persona_combo.clear()
        self._persona_combo.addItem(tr("lorebook.no_char_ref"), "")
        for p in self._svc.get_all_ai_personas():
            self._persona_combo.addItem(
                f"{p.name} — {p.role_name}",
                p.id,
            )

    # --- 로어북 목록 ---

    def _load_books(self) -> None:
        self._book_list.clear()
        for b in self._svc.get_all_lorebooks():
            it = QListWidgetItem(b.name)
            it.setData(Qt.ItemDataRole.UserRole, b.id)
            self._book_list.addItem(it)

    def _on_book_sel(self, c: QListWidgetItem | None, _: QListWidgetItem | None) -> None:
        if not c:
            return
        b = self._svc.get_lorebook(c.data(Qt.ItemDataRole.UserRole))
        if not b:
            return
        self._cur_lb = b.id
        self._bk_name.setText(b.name)
        self._bk_desc.setText(b.description)
        self._load_entries()

    def _load_entries(self) -> None:
        self._entry_list.clear()
        self._cur_le = None
        if not self._cur_lb:
            return
        for e in self._svc.get_lore_entries(self._cur_lb):
            it = QListWidgetItem(f"[{e.priority}] {e.title}")
            it.setData(Qt.ItemDataRole.UserRole, e.id)
            self._entry_list.addItem(it)

    def _on_entry_sel(self, c: QListWidgetItem | None, _: QListWidgetItem | None) -> None:
        if not c:
            return
        entries = self._svc.get_lore_entries(self._cur_lb or "")
        eid = c.data(Qt.ItemDataRole.UserRole)
        for e in entries:
            if e.id == eid:
                self._cur_le = e.id
                self._e_title.setText(e.title)
                keys = json.loads(e.activation_keys_json)
                self._e_keys.setText(", ".join(keys))
                self._e_content.setPlainText(e.content)
                self._e_pri.setValue(e.priority)
                break

    def _on_new_book(self) -> None:
        self._cur_lb = None
        self._bk_name.clear()
        self._bk_desc.clear()
        self._entry_list.clear()

    def _on_save_book(self) -> None:
        n = self._bk_name.text().strip()
        if not n:
            self._st.setText(tr("lorebook.name_required"))
            return
        self._svc.save_lorebook(
            name=n,
            description=self._bk_desc.text().strip(),
            existing_id=self._cur_lb,
        )
        self._st.setText(tr("chat_profile.saved", name=n))
        self._st.setStyleSheet(f"color:{COLORS.accent_success};")
        self._load_books()

    def _on_del_book(self) -> None:
        if not self._cur_lb:
            return
        if QMessageBox.question(self, tr("common.confirm"), tr("common.delete_short")) == QMessageBox.StandardButton.Yes:
            self._svc.delete_lorebook(self._cur_lb)
            self._on_new_book()
            self._load_books()

    def _on_new_entry(self) -> None:
        self._cur_le = None
        self._e_title.clear()
        self._e_keys.clear()
        self._e_content.clear()
        self._e_pri.setValue(100)

    def _on_save_entry(self) -> None:
        if not self._cur_lb:
            self._st.setText(tr("lorebook.select_book_first"))
            return
        t = self._e_title.text().strip()
        c = self._e_content.toPlainText().strip()
        keys = [k.strip() for k in self._e_keys.text().split(",") if k.strip()]
        if not t or not keys or not c:
            self._st.setText(tr("lorebook.entry_fields_required"))
            return
        self._svc.save_lore_entry(
            lorebook_id=self._cur_lb,
            title=t,
            activation_keys=keys,
            content=c,
            priority=self._e_pri.value(),
            existing_id=self._cur_le,
        )
        self._st.setText(tr("lorebook.entry_saved", title=t))
        self._st.setStyleSheet(f"color:{COLORS.accent_success};")
        self._load_entries()

    def _on_del_entry(self) -> None:
        if not self._cur_le:
            return
        if QMessageBox.question(self, tr("common.confirm"), tr("common.delete_short")) == QMessageBox.StandardButton.Yes:
            self._svc.delete_lore_entry(self._cur_le)
            self._on_new_entry()
            self._load_entries()

    # --- Vibe Fill ---

    def _on_vibe_fill(self) -> None:
        """AI로 엔트리 생성 버튼 클릭."""
        if not self._cur_lb:
            self._vibe_status.setText(tr("lorebook.select_book_first"))
            self._vibe_status.setStyleSheet(f"color:{COLORS.accent_danger};")
            return

        vibe = self._vibe_text.toPlainText().strip()
        if not vibe:
            self._vibe_status.setText(tr("vibe.enter_vibe_text"))
            self._vibe_status.setStyleSheet(f"color:{COLORS.accent_danger};")
            return

        if not self._vibe_svc:
            self._vibe_status.setText(tr("vibe.no_service"))
            self._vibe_status.setStyleSheet(f"color:{COLORS.accent_danger};")
            return

        prov_id = self._prov_combo.currentData()
        model_id = self._model_combo.currentData()
        if not prov_id or not model_id:
            self._vibe_status.setText(tr("vibe.provider_model_select"))
            self._vibe_status.setStyleSheet(f"color:{COLORS.accent_danger};")
            return

        # AI Persona 선택 (선택 사항)
        persona_id = self._persona_combo.currentData()
        persona_ids = [persona_id] if persona_id else None

        # UI 비활성화
        self._btn_vibe.setEnabled(False)
        self._vibe_status.setText(tr("lorebook.generating"))
        self._vibe_status.setStyleSheet("")

        # AsyncSignalBridge 지연 생성
        if not self._bridge:
            self._bridge = AsyncSignalBridge()
            self._bridge.task_result.connect(self._slot_lore_result)
            self._bridge.task_error.connect(self._slot_lore_error)

        # 비동기 LLM 호출
        self._bridge.run_coroutine_in_thread(
            self._vibe_svc.generate_lore_entries(
                vibe, self._cur_lb, prov_id, model_id, persona_ids,
            )
        )

    def _slot_lore_result(self, result: object) -> None:
        """Lore Fill 결과 수신 (메인 스레드)."""
        self._btn_vibe.setEnabled(True)

        success = getattr(result, "success", False)
        entries: list[dict[str, Any]] = getattr(result, "entries", [])
        error = getattr(result, "error", "")

        if not success:
            self._vibe_status.setText(tr("vibe.gen_failed", error=error))
            self._vibe_status.setStyleSheet(f"color:{COLORS.accent_danger};")
            return

        # 미리보기 표시
        self._show_preview(entries)
        count = len(entries)
        self._vibe_status.setText(
            tr("lorebook.gen_success", count=count)
        )
        self._vibe_status.setStyleSheet(f"color:{COLORS.accent_success};")

    def _slot_lore_error(self, error: object) -> None:
        """Lore Fill 에러 수신 (메인 스레드)."""
        self._btn_vibe.setEnabled(True)
        msg = getattr(error, "message", str(error))
        self._vibe_status.setText(tr("common.error", msg=msg))
        self._vibe_status.setStyleSheet(f"color:{COLORS.accent_danger};")

    def _show_preview(self, entries: list[dict[str, Any]]) -> None:
        """생성된 엔트리를 미리보기 체크리스트로 표시한다."""
        # 기존 미리보기 위젯 정리 (btn_append 제외)
        self._pending_entries = entries
        self._pending_checks = []

        # 기존 체크박스 위젯 제거
        while self._preview_layout.count() > 1:
            item = self._preview_layout.takeAt(0)
            if item is not None:
                w = item.widget()
                if w is not None:
                    w.deleteLater()

        # 엔트리별 체크박스 + 요약 추가
        for i, entry in enumerate(entries):
            title = entry.get("title", "?")
            keys = entry.get("activation_keys", [])
            priority = entry.get("priority", 100)
            content = entry.get("content", "")
            # 내용 요약 (최대 60글자)
            summary = content[:60] + "..." if len(content) > 60 else content

            cb = QCheckBox(f"[{priority}] {title}")
            cb.setChecked(True)
            cb.setToolTip(tr("lorebook.tooltip_keys", keys=", ".join(keys), summary=summary))
            self._pending_checks.append(cb)
            # btn_append 위에 삽입 (마지막은 btn_append)
            self._preview_layout.insertWidget(i, cb)

        self._preview_group.setVisible(True)
        self._preview_group.setTitle(tr("lorebook.preview_count", count=len(entries)))

    def _on_append_entries(self) -> None:
        """선택된 엔트리만 로어북에 Append 저장한다."""
        if not self._cur_lb:
            return

        # 중복 방지를 위한 기존 엔트리 제목 목록 확보
        existing_entries = self._svc.get_lore_entries(self._cur_lb)
        existing_titles = {e.title for e in existing_entries}

        saved = 0
        for cb, entry in zip(self._pending_checks, self._pending_entries):
            if not cb.isChecked():
                continue
            if entry["title"] in existing_titles:
                continue  # 이미 존재하는 제목이면 무시 (DD-13 정책)

            self._svc.save_lore_entry(
                lorebook_id=self._cur_lb,
                title=entry["title"],
                activation_keys=entry["activation_keys"],
                content=entry["content"],
                priority=entry["priority"],
            )
            saved += 1

        self._st.setText(tr("lorebook.appended", count=saved))
        self._st.setStyleSheet(f"color:{COLORS.accent_success};")
        self._load_entries()

        # 미리보기 숨기기
        self._preview_group.setVisible(False)
        self._pending_entries = []
        self._pending_checks = []
