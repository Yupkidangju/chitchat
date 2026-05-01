# src/chitchat/ui/pages/chat_profile_page.py
# [v0.1.1] 채팅 프로필 관리 페이지
#
# [v0.1.1] 변경: 참조 엔티티 선택 UI를 "태그 + [추가...] 다이얼로그" 패턴으로 전면 개선
#   — 기존 QListWidget(MultiSelection) 방식에서 EntityPickerDialog 기반으로 변경
#   — 선택된 항목이 태그 형태로 표시되어 직관적이며, [×] 버튼으로 개별 해제 가능
#   — 빈 상태일 때 안내 문구가 표시되어 사용자 행동을 유도함
#
# ModelProfile 선택 + AI Persona 선택 + Lorebook/Worldbook 선택 + PromptOrder + system_base.
# 첫 사용자 완주 루트의 마지막 퍼즐.
from __future__ import annotations

import json
import logging
from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
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
from chitchat.ui.widgets.entity_picker_dialog import EntityPickerDialog

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


# --- 태그 위젯 ---

class _TagWidget(QWidget):
    """선택된 엔티티를 표시하는 태그 위젯.

    태그 라벨 + [×] 제거 버튼으로 구성된다.
    """

    def __init__(
        self,
        entity_id: str,
        display_name: str,
        on_remove: Callable[[str], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.entity_id = entity_id
        lo = QHBoxLayout(self)
        lo.setContentsMargins(6, 2, 2, 2)
        lo.setSpacing(4)

        # 태그 라벨
        label = QLabel(display_name)
        label.setStyleSheet(
            f"color: {COLORS.text_primary}; "
            f"font-size: 12px; "
            f"background: transparent;"
        )
        lo.addWidget(label)

        # 제거 버튼
        btn = QPushButton("×")
        btn.setFixedSize(18, 18)
        btn.setStyleSheet(
            f"QPushButton {{ "
            f"  background: transparent; "
            f"  color: {COLORS.text_muted}; "
            f"  border: none; "
            f"  font-size: 14px; "
            f"  font-weight: bold; "
            f"  padding: 0px; "
            f"  min-height: 0px; "
            f"}} "
            f"QPushButton:hover {{ color: {COLORS.accent_danger}; }}"
        )
        btn.clicked.connect(lambda: on_remove(entity_id))
        lo.addWidget(btn)

        # 태그 컨테이너 스타일
        self.setStyleSheet(
            f"_TagWidget {{ "
            f"  background-color: {COLORS.bg_tertiary}; "
            f"  border: 1px solid {COLORS.text_muted}; "
            f"  border-radius: 4px; "
            f"}}"
        )
        self.setMaximumHeight(28)


# --- 태그 + 추가 영역 위젯 ---

class _EntityTagArea(QWidget):
    """선택된 엔티티들을 태그로 표시하고 [+ 추가...] 버튼을 제공하는 위젯.

    tag_area: 태그들이 나열되는 영역 (Flow 형태)
    add_button: 모달 다이얼로그를 여는 버튼
    empty_label: 항목이 없을 때 안내 문구
    """

    def __init__(
        self,
        section_title: str,
        dialog_title: str,
        max_count: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._dialog_title = dialog_title
        self._max_count = max_count
        # 선택된 엔티티 정보: {id: display_name}
        self._selected: dict[str, str] = {}
        # 전체 후보 목록: [(id, display_name)]
        self._all_items: list[tuple[str, str]] = []

        lo = QVBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(SPACING.xs)

        # 섹션 헤더: 라벨 + [+ 추가...] 버튼
        header = QHBoxLayout()
        lbl = QLabel(section_title)
        lbl.setStyleSheet("font-weight: bold; font-size: 13px; background: transparent;")
        header.addWidget(lbl)
        header.addStretch()

        self._add_btn = QPushButton(tr("common.add_more"))
        self._add_btn.setFixedHeight(26)
        self._add_btn.setStyleSheet(
            "QPushButton { "
            "  font-size: 12px; "
            "  padding: 2px 10px; "
            "  min-height: 0px; "
            "}"
        )
        self._add_btn.clicked.connect(self._on_add_clicked)
        header.addWidget(self._add_btn)
        lo.addLayout(header)

        # 태그 영역 (수평 줄바꿈 레이아웃)
        self._tag_container = QWidget()
        self._tag_layout = QHBoxLayout(self._tag_container)
        self._tag_layout.setContentsMargins(0, 0, 0, 0)
        self._tag_layout.setSpacing(SPACING.xs)
        self._tag_layout.addStretch()
        lo.addWidget(self._tag_container)

        # 빈 상태 안내 문구
        self._empty_label = QLabel(tr("chat_profile.no_selection"))
        self._empty_label.setObjectName("subtitle")
        self._empty_label.setStyleSheet(
            f"color: {COLORS.text_muted}; font-size: 12px; padding: 4px 0; background: transparent;"
        )
        lo.addWidget(self._empty_label)

    def set_all_items(self, items: list[tuple[str, str]]) -> None:
        """다이얼로그에서 보여줄 전체 후보 목록을 설정한다."""
        self._all_items = items

    def set_selected(self, selected: dict[str, str]) -> None:
        """선택된 항목을 설정하고 태그를 다시 렌더링한다."""
        self._selected = dict(selected)
        self._rebuild_tags()

    def get_selected_ids(self) -> list[str]:
        """현재 선택된 ID 목록을 반환한다."""
        return list(self._selected.keys())

    def _on_add_clicked(self) -> None:
        """[+ 추가...] 버튼 클릭 시 EntityPickerDialog를 연다."""
        dialog = EntityPickerDialog(
            title=self._dialog_title,
            items=self._all_items,
            selected_ids=set(self._selected.keys()),
            max_count=self._max_count,
            parent=self,
        )
        if dialog.exec():
            new_ids = dialog.get_selected_ids()
            # 선택 결과 반영: 전체 후보에서 display_name을 찾아 매핑
            id_to_name = dict(self._all_items)
            self._selected = {eid: id_to_name.get(eid, eid) for eid in new_ids}
            self._rebuild_tags()

    def _on_remove_tag(self, entity_id: str) -> None:
        """태그의 [×] 버튼으로 개별 항목을 제거한다."""
        self._selected.pop(entity_id, None)
        self._rebuild_tags()

    def _rebuild_tags(self) -> None:
        """태그 영역을 다시 렌더링한다."""
        # 기존 태그 모두 제거 (stretch 제외)
        while self._tag_layout.count() > 0:
            item = self._tag_layout.takeAt(0)
            w = item.widget() if item else None
            if w:
                w.deleteLater()

        # 새 태그 추가
        if self._selected:
            for eid, name in self._selected.items():
                tag = _TagWidget(eid, name, self._on_remove_tag)
                self._tag_layout.addWidget(tag)
            self._tag_layout.addStretch()
            self._empty_label.hide()
        else:
            self._tag_layout.addStretch()
            self._empty_label.show()


# --- 채팅 프로필 페이지 ---

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
        lo = QHBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(0)
        sp = QSplitter(Qt.Orientation.Horizontal)
        lo.addWidget(sp)

        # 좌측: 채팅 프로필 목록
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(SPACING.md, SPACING.md, SPACING.md, SPACING.md)
        ll.addWidget(QLabel(tr("chat_profile.list_title")))
        self._list = QListWidget()
        self._list.currentItemChanged.connect(self._on_sel)
        ll.addWidget(self._list)
        blo = QHBoxLayout()
        bn = QPushButton(tr("chat_profile.new_btn"))
        bn.setObjectName("primaryButton")
        bn.clicked.connect(self._on_new)
        blo.addWidget(bn)
        bd = QPushButton(tr("common.delete"))
        bd.setObjectName("dangerButton")
        bd.clicked.connect(self._on_delete)
        blo.addWidget(bd)
        ll.addLayout(blo)
        sp.addWidget(left)

        # 우측: 편집 폼
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(SPACING.lg, SPACING.md, SPACING.lg, SPACING.md)
        rl.addWidget(QLabel(tr("chat_profile.form_title")))

        # 기본 정보
        fg = QGroupBox(tr("provider.group_basic"))
        form = QFormLayout(fg)
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText(tr("chat_profile.name_ph"))
        form.addRow(tr("model.name_label"), self._name_edit)

        # ModelProfile 선택 (리스트 위젯, 단일 선택)
        self._mp_list = QListWidget()
        self._mp_list.setMaximumHeight(80)
        form.addRow(tr("chat_profile.model_profile_label"), self._mp_list)

        rl.addWidget(fg)

        # 참조 엔티티 선택 — 태그 + [추가...] 다이얼로그 패턴
        rg = QGroupBox(tr("chat_profile.ref_entities"))
        rg_layout = QVBoxLayout(rg)
        rg_layout.setSpacing(SPACING.md)

        # AI 페르소나 태그 영역 (최대 5개, spec.md §8.3)
        self._ai_tags = _EntityTagArea(
            section_title=tr("persona.ai_title"),
            dialog_title=tr("chat_profile.ai_persona_dialog"),
            max_count=5,
        )
        rg_layout.addWidget(self._ai_tags)

        # 로어북 태그 영역 (최대 10개, spec.md §8.3)
        self._lb_tags = _EntityTagArea(
            section_title=tr("lorebook.list_title_short"),
            dialog_title=tr("chat_profile.lorebook_dialog"),
            max_count=10,
        )
        rg_layout.addWidget(self._lb_tags)

        # 월드북 태그 영역 (최대 10개, spec.md §8.3)
        self._wb_tags = _EntityTagArea(
            section_title=tr("worldbook.list_title_short"),
            dialog_title=tr("chat_profile.worldbook_dialog"),
            max_count=10,
        )
        rg_layout.addWidget(self._wb_tags)

        rl.addWidget(rg)

        # System Base 프롬프트
        sg = QGroupBox(tr("chat_profile.system_prompt"))
        sl = QVBoxLayout(sg)
        self._system_edit = QTextEdit()
        self._system_edit.setPlaceholderText(tr("chat_profile.system_prompt_ph"))
        self._system_edit.setMaximumHeight(100)
        sl.addWidget(self._system_edit)
        rl.addWidget(sg)

        # 저장 버튼
        alo = QHBoxLayout()
        bs = QPushButton(tr("common.save"))
        bs.setObjectName("primaryButton")
        bs.clicked.connect(self._on_save)
        alo.addWidget(bs)
        rl.addLayout(alo)

        self._status = QLabel("")
        self._status.setWordWrap(True)
        rl.addWidget(self._status)
        rl.addStretch()
        sp.addWidget(right)
        sp.setSizes([260, 640])

    # --- 데이터 로드 ---

    def _load_list(self) -> None:
        """채팅 프로필 목록과 참조 엔티티 후보를 새로고침한다."""
        self._list.clear()
        for cp in self._svc.get_all_chat_profiles():
            it = QListWidgetItem(cp.name)
            it.setData(Qt.ItemDataRole.UserRole, cp.id)
            self._list.addItem(it)
        self._load_combos()

    def _load_combos(self) -> None:
        """참조 엔티티 후보 목록을 각 태그 영역에 설정한다."""
        # ModelProfile
        self._mp_list.clear()
        for mp in self._svc.get_all_model_profiles():
            it = QListWidgetItem(mp.name)
            it.setData(Qt.ItemDataRole.UserRole, mp.id)
            self._mp_list.addItem(it)

        # AI Persona — 다이얼로그용 전체 후보
        ai_items = [
            (ai.id, f"{ai.name} ({ai.role_name})")
            for ai in self._svc.get_all_ai_personas()
        ]
        self._ai_tags.set_all_items(ai_items)

        # Lorebook
        lb_items = [
            (lb.id, lb.name) for lb in self._svc.get_all_lorebooks()
        ]
        self._lb_tags.set_all_items(lb_items)

        # Worldbook
        wb_items = [
            (wb.id, wb.name) for wb in self._svc.get_all_worldbooks()
        ]
        self._wb_tags.set_all_items(wb_items)

    def _on_sel(self, cur: QListWidgetItem | None, _: QListWidgetItem | None) -> None:
        """채팅 프로필 선택 시 편집 폼에 데이터를 로드한다."""
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

        # AI Persona — 저장된 ID들을 태그로 복원
        ai_ids = set(json.loads(cp.ai_persona_ids_json))
        ai_id_to_name = dict(self._ai_tags._all_items)
        self._ai_tags.set_selected({eid: ai_id_to_name.get(eid, eid) for eid in ai_ids})

        # Lorebook
        lb_ids = set(json.loads(cp.lorebook_ids_json))
        lb_id_to_name = dict(self._lb_tags._all_items)
        self._lb_tags.set_selected({eid: lb_id_to_name.get(eid, eid) for eid in lb_ids})

        # Worldbook
        wb_ids = set(json.loads(cp.worldbook_ids_json))
        wb_id_to_name = dict(self._wb_tags._all_items)
        self._wb_tags.set_selected({eid: wb_id_to_name.get(eid, eid) for eid in wb_ids})

        self._status.setText(tr("model.loaded", name=cp.name))

    def _on_new(self) -> None:
        """새 채팅 프로필 작성 모드로 전환한다."""
        self._current_id = None
        self._name_edit.clear()
        self._system_edit.clear()
        self._mp_list.clearSelection()
        self._ai_tags.set_selected({})
        self._lb_tags.set_selected({})
        self._wb_tags.set_selected({})
        self._status.setText(tr("chat_profile.new_msg"))

    def _on_delete(self) -> None:
        """선택된 채팅 프로필을 삭제한다."""
        if not self._current_id:
            return
        if QMessageBox.question(self, tr("common.confirm"), tr("common.delete_confirm")) == QMessageBox.StandardButton.Yes:
            self._svc.delete_chat_profile(self._current_id)
            self._current_id = None
            self._load_list()

    def _on_save(self) -> None:
        """편집 중인 채팅 프로필을 저장한다."""
        name = self._name_edit.text().strip()
        system_base = self._system_edit.toPlainText().strip()

        if not name:
            self._status.setText(tr("provider.name_required"))
            self._status.setStyleSheet(f"color:{COLORS.accent_danger};")
            return
        if not system_base:
            self._status.setText(tr("chat_profile.system_prompt_required"))
            self._status.setStyleSheet(f"color:{COLORS.accent_danger};")
            return

        # ModelProfile ID
        mp_item = self._mp_list.currentItem()
        if not mp_item:
            self._status.setText(tr("chat_profile.model_required"))
            self._status.setStyleSheet(f"color:{COLORS.accent_danger};")
            return
        mp_id = mp_item.data(Qt.ItemDataRole.UserRole)

        # 태그 영역에서 선택된 ID 수집
        ai_ids = self._ai_tags.get_selected_ids()
        lb_ids = self._lb_tags.get_selected_ids()
        wb_ids = self._wb_tags.get_selected_ids()

        # [v0.1.4] PromptOrder 보존: 기존 프로필 편집 시 DB에 저장된 순서를 유지한다.
        # PromptOrderPage에서 변경한 순서가 ChatProfile 저장 시 초기화되는 버그 수정.
        # 새 프로필 생성 시에만 기본 순서(_DEFAULT_PROMPT_ORDER)를 적용한다.
        prompt_order = _DEFAULT_PROMPT_ORDER
        if self._current_id:
            existing = self._svc.get_chat_profile(self._current_id)
            if existing and existing.prompt_order_json:
                prompt_order = existing.prompt_order_json

        try:
            self._svc.save_chat_profile(
                name=name,
                model_profile_id=mp_id,
                ai_persona_ids=ai_ids,
                lorebook_ids=lb_ids,
                worldbook_ids=wb_ids,
                prompt_order_json=prompt_order,
                system_base=system_base,
                existing_id=self._current_id,
            )
            self._status.setText(tr("provider.saved", name=name))
            self._status.setStyleSheet(f"color:{COLORS.accent_success};")
            self._load_list()
        except Exception as e:
            self._status.setText(tr("common.save_failed", e=e))
            self._status.setStyleSheet(f"color:{COLORS.accent_danger};")
