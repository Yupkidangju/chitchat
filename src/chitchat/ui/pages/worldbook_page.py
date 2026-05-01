# src/chitchat/ui/pages/worldbook_page.py
# [v0.1.0b0] 월드북 관리 페이지
# [v0.2.0] Vibe Fill Phase 3: AI 세계관 엔트리 자동 생성 + 청크 분할 + 미리보기
from __future__ import annotations
import logging
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QProgressBar,
    QPushButton, QScrollArea, QSpinBox, QSplitter, QTextEdit,
    QVBoxLayout, QWidget,
)
from chitchat.domain.vibe_fill import WORLD_CATEGORIES
from chitchat.services.profile_service import ProfileService
from chitchat.services.provider_service import ProviderService
from chitchat.services.vibe_fill_service import VibeFillService
from chitchat.ui.async_bridge import AsyncSignalBridge
from chitchat.i18n import tr
from chitchat.ui.theme import COLORS, SPACING

logger = logging.getLogger(__name__)


class WorldbookPage(QWidget):
    """월드북 + 엔트리 관리 페이지.

    [v0.2.0] Vibe Fill Phase 3 확장:
    - AI Persona + Lorebook 복수 선택으로 컨텍스트 주입
    - 10개 카테고리 체크박스로 생성 범위 선택
    - 청크 분할 생성 + 진행률 표시
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
        self._cur_wb: str | None = None
        self._cur_we: str | None = None
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

        # === 좌측: 월드북 목록 ===
        lw = QWidget()
        ll = QVBoxLayout(lw)
        ll.setContentsMargins(SPACING.md, SPACING.md, SPACING.md, SPACING.md)
        ll.addWidget(QLabel(tr("worldbook.list_title")))
        self._book_list = QListWidget()
        self._book_list.currentItemChanged.connect(self._on_book_sel)
        ll.addWidget(self._book_list)
        bl = QHBoxLayout()
        b1 = QPushButton(tr("worldbook.new_btn"))
        b1.setObjectName("primaryButton")
        b1.clicked.connect(self._on_new_book)
        b2 = QPushButton(tr("common.delete"))
        b2.setObjectName("dangerButton")
        b2.clicked.connect(self._on_del_book)
        bl.addWidget(b1)
        bl.addWidget(b2)
        ll.addLayout(bl)
        # 월드북 편집
        g1 = QGroupBox(tr("worldbook.info_title"))
        f1 = QFormLayout(g1)
        self._bk_name = QLineEdit()
        f1.addRow(tr("common.name"), self._bk_name)
        self._bk_desc = QLineEdit()
        f1.addRow(tr("common.description"), self._bk_desc)
        ll.addWidget(g1)
        bs1 = QPushButton(tr("worldbook.save_book_btn"))
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
        vibe_group = QGroupBox(tr("worldbook.vibe_title"))
        vibe_layout = QVBoxLayout(vibe_group)

        # AI Persona 선택 (복수 불가, 단일 드롭다운 × 2)
        p_layout = QHBoxLayout()
        p_layout.addWidget(QLabel(tr("worldbook.char_label")))
        self._persona_combo1 = QComboBox()
        p_layout.addWidget(self._persona_combo1, 1)
        self._persona_combo2 = QComboBox()
        p_layout.addWidget(self._persona_combo2, 1)
        vibe_layout.addLayout(p_layout)

        # Lorebook 선택 (2개 드롭다운)
        lb_layout = QHBoxLayout()
        lb_layout.addWidget(QLabel(tr("worldbook.lorebook_label")))
        self._lore_combo1 = QComboBox()
        lb_layout.addWidget(self._lore_combo1, 1)
        self._lore_combo2 = QComboBox()
        lb_layout.addWidget(self._lore_combo2, 1)
        vibe_layout.addLayout(lb_layout)

        # 바이브 텍스트 입력
        self._vibe_text = QTextEdit()
        self._vibe_text.setMaximumHeight(80)
        self._vibe_text.setPlaceholderText(tr("worldbook.vibe_ph"))
        vibe_layout.addWidget(self._vibe_text)

        # 카테고리 선택 (체크박스 2열)
        cat_group = QGroupBox(tr("worldbook.category_title"))
        cat_grid = QHBoxLayout(cat_group)
        col1 = QVBoxLayout()
        col2 = QVBoxLayout()
        self._cat_checks: dict[str, QCheckBox] = {}
        for i, cat in enumerate(WORLD_CATEGORIES):
            cb = QCheckBox(f"{cat.label}")
            cb.setChecked(True)
            cb.setToolTip(cat.description)
            self._cat_checks[cat.key] = cb
            if i < 5:
                col1.addWidget(cb)
            else:
                col2.addWidget(cb)
        cat_grid.addLayout(col1)
        cat_grid.addLayout(col2)
        vibe_layout.addWidget(cat_group)

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

        self._btn_vibe = QPushButton(tr("worldbook.vibe_fill_btn"))
        self._btn_vibe.setObjectName("primaryButton")
        self._btn_vibe.clicked.connect(self._on_vibe_fill)
        vibe_layout.addWidget(self._btn_vibe)

        # 진행률 바
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setTextVisible(True)
        vibe_layout.addWidget(self._progress)

        self._vibe_status = QLabel("")
        self._vibe_status.setObjectName("subtitle")
        vibe_layout.addWidget(self._vibe_status)

        rl.addWidget(vibe_group)

        # --- 생성 미리보기 (체크리스트) ---
        self._preview_group = QGroupBox(tr("lorebook.preview_title"))
        self._preview_layout = QVBoxLayout(self._preview_group)
        self._preview_group.setVisible(False)

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
        self._load_lorebooks()

    # --- Provider/Model/Persona/Lorebook 드롭다운 ---

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
        """AI Persona 목록을 드롭다운에 로드한다 (2개 슬롯)."""
        for combo in (self._persona_combo1, self._persona_combo2):
            combo.clear()
            combo.addItem(tr("worldbook.none_selected"), "")
            for p in self._svc.get_all_ai_personas():
                combo.addItem(f"{p.name} — {p.role_name}", p.id)

    def _load_lorebooks(self) -> None:
        """Lorebook 목록을 드롭다운에 로드한다 (2개 슬롯)."""
        for combo in (self._lore_combo1, self._lore_combo2):
            combo.clear()
            combo.addItem(tr("worldbook.none_selected"), "")
            for lb in self._svc.get_all_lorebooks():
                combo.addItem(lb.name, lb.id)

    def _get_selected_persona_ids(self) -> list[str]:
        """선택된 AI Persona ID 목록을 반환한다 (중복 제거)."""
        ids: list[str] = []
        for combo in (self._persona_combo1, self._persona_combo2):
            pid = combo.currentData()
            if pid and pid not in ids:
                ids.append(pid)
        return ids

    def _get_selected_lorebook_ids(self) -> list[str]:
        """선택된 Lorebook ID 목록을 반환한다 (중복 제거)."""
        ids: list[str] = []
        for combo in (self._lore_combo1, self._lore_combo2):
            lid = combo.currentData()
            if lid and lid not in ids:
                ids.append(lid)
        return ids

    def _get_selected_categories(self) -> list[str]:
        """체크된 카테고리 키 목록을 반환한다."""
        return [key for key, cb in self._cat_checks.items() if cb.isChecked()]

    # --- 월드북 목록 ---

    def _load_books(self) -> None:
        self._book_list.clear()
        for b in self._svc.get_all_worldbooks():
            it = QListWidgetItem(b.name)
            it.setData(Qt.ItemDataRole.UserRole, b.id)
            self._book_list.addItem(it)

    def _on_book_sel(self, c: QListWidgetItem | None, _: QListWidgetItem | None) -> None:
        if not c:
            return
        b = self._svc.get_worldbook(c.data(Qt.ItemDataRole.UserRole))
        if not b:
            return
        self._cur_wb = b.id
        self._bk_name.setText(b.name)
        self._bk_desc.setText(b.description)
        self._load_entries()

    def _load_entries(self) -> None:
        self._entry_list.clear()
        self._cur_we = None
        if not self._cur_wb:
            return
        for e in self._svc.get_world_entries(self._cur_wb):
            it = QListWidgetItem(f"[{e.priority}] {e.title}")
            it.setData(Qt.ItemDataRole.UserRole, e.id)
            self._entry_list.addItem(it)

    def _on_entry_sel(self, c: QListWidgetItem | None, _: QListWidgetItem | None) -> None:
        if not c:
            return
        entries = self._svc.get_world_entries(self._cur_wb or "")
        eid = c.data(Qt.ItemDataRole.UserRole)
        for e in entries:
            if e.id == eid:
                self._cur_we = e.id
                self._e_title.setText(e.title)
                self._e_content.setPlainText(e.content)
                self._e_pri.setValue(e.priority)
                break

    def _on_new_book(self) -> None:
        self._cur_wb = None
        self._bk_name.clear()
        self._bk_desc.clear()
        self._entry_list.clear()

    def _on_save_book(self) -> None:
        n = self._bk_name.text().strip()
        if not n:
            self._st.setText(tr("lorebook.name_required"))
            return
        self._svc.save_worldbook(
            name=n,
            description=self._bk_desc.text().strip(),
            existing_id=self._cur_wb,
        )
        self._st.setText(tr("chat_profile.saved", name=n))
        self._st.setStyleSheet(f"color:{COLORS.accent_success};")
        self._load_books()

    def _on_del_book(self) -> None:
        if not self._cur_wb:
            return
        if QMessageBox.question(self, tr("common.confirm"), tr("common.delete_short")) == QMessageBox.StandardButton.Yes:
            self._svc.delete_worldbook(self._cur_wb)
            self._on_new_book()
            self._load_books()

    def _on_new_entry(self) -> None:
        self._cur_we = None
        self._e_title.clear()
        self._e_content.clear()
        self._e_pri.setValue(100)

    def _on_save_entry(self) -> None:
        if not self._cur_wb:
            self._st.setText(tr("worldbook.select_book_first"))
            return
        t = self._e_title.text().strip()
        c = self._e_content.toPlainText().strip()
        if not t or not c:
            self._st.setText(tr("worldbook.entry_fields_required"))
            return
        self._svc.save_world_entry(
            worldbook_id=self._cur_wb,
            title=t,
            content=c,
            priority=self._e_pri.value(),
            existing_id=self._cur_we,
        )
        self._st.setText(tr("lorebook.entry_saved", title=t))
        self._st.setStyleSheet(f"color:{COLORS.accent_success};")
        self._load_entries()

    def _on_del_entry(self) -> None:
        if not self._cur_we:
            return
        if QMessageBox.question(self, tr("common.confirm"), tr("common.delete_short")) == QMessageBox.StandardButton.Yes:
            self._svc.delete_world_entry(self._cur_we)
            self._on_new_entry()
            self._load_entries()

    # --- Vibe Fill ---

    def _on_vibe_fill(self) -> None:
        """AI로 세계관 생성 버튼 클릭."""
        if not self._cur_wb:
            self._vibe_status.setText(tr("worldbook.select_book_first"))
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

        cat_keys = self._get_selected_categories()
        if not cat_keys:
            self._vibe_status.setText(tr("worldbook.select_category"))
            self._vibe_status.setStyleSheet(f"color:{COLORS.accent_danger};")
            return

        # 컨텍스트 수집
        persona_ids = self._get_selected_persona_ids() or None
        lorebook_ids = self._get_selected_lorebook_ids() or None

        # UI 비활성화 + 진행률 초기화
        self._btn_vibe.setEnabled(False)
        self._progress.setVisible(True)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFormat(tr("worldbook.preparing"))
        self._vibe_status.setText(tr("worldbook.generating"))
        self._vibe_status.setStyleSheet("")

        # AsyncSignalBridge 지연 생성
        if not self._bridge:
            self._bridge = AsyncSignalBridge()
            self._bridge.task_result.connect(self._slot_world_result)
            self._bridge.task_error.connect(self._slot_world_error)
            self._bridge.task_progress.connect(self._slot_progress)

        # 비동기 LLM 호출 (청크 분할)
        self._bridge.run_coroutine_in_thread(
            self._vibe_svc.generate_world_entries(
                vibe, self._cur_wb, prov_id, model_id,
                cat_keys, persona_ids, lorebook_ids,
                progress_callback=self._on_progress,
            )
        )

    def _on_progress(self, current: int, total: int, status: str) -> None:
        """청크 진행률 콜백 (워커 스레드에서 호출됨).

        메인 스레드로 진행 상태를 안전하게 전달하기 위해 시그널을 발생시킨다.
        """
        if self._bridge:
            self._bridge.task_progress.emit(current, total, status)

    def _slot_progress(self, current: int, total: int, status: str) -> None:
        """World Fill 진행 상태 수신 (메인 스레드)."""
        pct = int((current / total) * 100) if total > 0 else 0
        self._progress.setValue(pct)
        self._progress.setFormat(f"{current}/{total} — {status}")

    def _slot_world_result(self, result: object) -> None:
        """World Fill 결과 수신 (메인 스레드)."""
        self._btn_vibe.setEnabled(True)
        self._progress.setVisible(False)

        success = getattr(result, "success", False)
        entries: list[dict[str, Any]] = getattr(result, "entries", [])
        error = getattr(result, "error", "")

        if not success:
            self._vibe_status.setText(tr("vibe.gen_failed", error=error))
            self._vibe_status.setStyleSheet(f"color:{COLORS.accent_danger};")
            return

        # 부분 성공 경고
        warning = ""
        if error:
            warning = f" (⚠️ {error})"

        # 미리보기 표시
        self._show_preview(entries)
        count = len(entries)
        self._vibe_status.setText(
            tr("worldbook.gen_success", count=count, warning=warning)
        )
        self._vibe_status.setStyleSheet(f"color:{COLORS.accent_success};")

    def _slot_world_error(self, error: object) -> None:
        """World Fill 에러 수신 (메인 스레드)."""
        self._btn_vibe.setEnabled(True)
        self._progress.setVisible(False)
        msg = getattr(error, "message", str(error))
        self._vibe_status.setText(tr("common.error", msg=msg))
        self._vibe_status.setStyleSheet(f"color:{COLORS.accent_danger};")

    def _show_preview(self, entries: list[dict[str, Any]]) -> None:
        """생성된 엔트리를 미리보기 체크리스트로 표시한다."""
        self._pending_entries = entries
        self._pending_checks = []

        # 기존 체크박스 위젯 제거 (btn_append 제외)
        while self._preview_layout.count() > 1:
            item = self._preview_layout.takeAt(0)
            if item is not None:
                w = item.widget()
                if w is not None:
                    w.deleteLater()

        # 엔트리별 체크박스 추가
        for i, entry in enumerate(entries):
            title = entry.get("title", "?")
            category = entry.get("category", "")
            priority = entry.get("priority", 100)
            content = entry.get("content", "")
            summary = content[:60] + "..." if len(content) > 60 else content

            cb = QCheckBox(f"[{priority}] {title}")
            cb.setChecked(True)
            cb.setToolTip(tr("worldbook.tooltip_category", category=category, summary=summary))
            self._pending_checks.append(cb)
            self._preview_layout.insertWidget(i, cb)

        self._preview_group.setVisible(True)
        self._preview_group.setTitle(tr("lorebook.preview_count", count=len(entries)))

    def _on_append_entries(self) -> None:
        """선택된 엔트리만 월드북에 Append 저장한다."""
        if not self._cur_wb:
            return

        # 중복 방지를 위한 기존 엔트리 제목 목록 확보
        existing_entries = self._svc.get_world_entries(self._cur_wb)
        existing_titles = {e.title for e in existing_entries}

        saved = 0
        for cb, entry in zip(self._pending_checks, self._pending_entries):
            if not cb.isChecked():
                continue
            if entry["title"] in existing_titles:
                continue  # 이미 존재하는 제목이면 무시 (DD-13 정책)

            self._svc.save_world_entry(
                worldbook_id=self._cur_wb,
                title=entry["title"],
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
