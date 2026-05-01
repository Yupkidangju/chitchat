# src/chitchat/ui/pages/persona_page.py
# [v0.1.1] UserPersona + AIPersona 관리 페이지
# [v0.1.1] 변경: 모든 입력 필드에 구체적인 Placeholder 예제 추가
# [v0.2.0] AIPersonaPage 전면 개편: 14개 필드 + Vibe Fill UI
from __future__ import annotations
import logging
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMessageBox, QPushButton, QScrollArea,
    QSplitter, QTextEdit, QVBoxLayout, QWidget,
)
from chitchat.services.profile_service import ProfileService
from chitchat.services.provider_service import ProviderService
from chitchat.services.vibe_fill_service import VibeFillService
from chitchat.ui.async_bridge import AsyncSignalBridge
from chitchat.i18n import tr
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
        ll.addWidget(QLabel(tr("persona.user_title")))
        self._list = QListWidget()
        self._list.currentItemChanged.connect(self._on_sel)
        ll.addWidget(self._list)
        bl = QHBoxLayout()
        b1 = QPushButton(tr("persona.user_new")); b1.setObjectName("primaryButton"); b1.clicked.connect(self._on_new)
        b2 = QPushButton(tr("common.delete")); b2.setObjectName("dangerButton"); b2.clicked.connect(self._on_del)
        bl.addWidget(b1); bl.addWidget(b2)
        ll.addLayout(bl)
        sp.addWidget(lw)
        # 우측
        rw = QWidget()
        rl = QVBoxLayout(rw)
        rl.setContentsMargins(SPACING.lg, SPACING.md, SPACING.lg, SPACING.md)
        g = QGroupBox(tr("common.edit"))
        f = QFormLayout(g)
        self._name = QLineEdit()
        self._name.setPlaceholderText(tr("persona.role_ph"))
        f.addRow(tr("common.name"), self._name)

        self._desc = QTextEdit()
        self._desc.setMaximumHeight(120)
        self._desc.setPlaceholderText(tr("persona.user_desc_ph"))
        f.addRow(tr("common.description"), self._desc)

        self._style = QTextEdit()
        self._style.setMaximumHeight(80)
        self._style.setPlaceholderText(tr("persona.user_style_ph"))
        f.addRow(tr("persona.speaking_label_ro"), self._style)

        self._bound = QTextEdit()
        self._bound.setMaximumHeight(80)
        self._bound.setPlaceholderText(tr("persona.user_bound_ph"))
        f.addRow(tr("persona.restrictions_label"), self._bound)
        rl.addWidget(g)
        bs = QPushButton(tr("common.save")); bs.setObjectName("primaryButton"); bs.clicked.connect(self._on_save)
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
        if not n or not d: self._st.setText(tr("lorebook.name_desc_required")); return
        self._svc.save_user_persona(name=n, description=d, speaking_style=self._style.toPlainText().strip(),
            boundaries=self._bound.toPlainText().strip(), existing_id=self._cur_id)
        self._st.setText(tr("chat_profile.saved", name=n)); self._st.setStyleSheet(f"color:{COLORS.accent_success};"); self._load()

    def _on_del(self) -> None:
        if not self._cur_id: return
        if QMessageBox.question(self, tr("common.confirm"), tr("common.delete_short")) == QMessageBox.StandardButton.Yes:
            self._svc.delete_user_persona(self._cur_id); self._on_new(); self._load()


class AIPersonaPage(QWidget):
    """AI 페르소나 관리 페이지.

    [v0.2.0] Vibe Fill 확장:
    - 14개 필드 편집 폼 (기본정보/외면/내면/서사/능력/행동규칙)
    - Vibe Fill 영역: 바이브 텍스트 입력 + Provider/Model 선택 + AI 자동 채우기
    - AsyncSignalBridge를 통한 비동기 LLM 호출
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
        self._cur_id: str | None = None
        # 비동기 브리지 (Vibe Fill LLM 호출용)
        self._bridge: AsyncSignalBridge | None = None
        self._setup_ui()
        self._load()

    def _setup_ui(self) -> None:
        lo = QHBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        sp = QSplitter(Qt.Orientation.Horizontal)
        lo.addWidget(sp)

        # --- 좌측: 페르소나 목록 ---
        lw = QWidget()
        ll = QVBoxLayout(lw)
        ll.setContentsMargins(SPACING.md, SPACING.md, SPACING.md, SPACING.md)
        ll.addWidget(QLabel(tr("persona.ai_title")))
        self._list = QListWidget()
        self._list.currentItemChanged.connect(self._on_sel)
        ll.addWidget(self._list)
        bl = QHBoxLayout()
        b1 = QPushButton(tr("persona.ai_new"))
        b1.setObjectName("primaryButton")
        b1.clicked.connect(self._on_new)
        b2 = QPushButton(tr("common.delete"))
        b2.setObjectName("dangerButton")
        b2.clicked.connect(self._on_del)
        bl.addWidget(b1)
        bl.addWidget(b2)
        ll.addLayout(bl)
        sp.addWidget(lw)

        # --- 우측: 편집 영역 (스크롤) ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        rw = QWidget()
        rl = QVBoxLayout(rw)
        rl.setContentsMargins(SPACING.lg, SPACING.md, SPACING.lg, SPACING.md)

        # Vibe Fill 영역
        vibe_group = QGroupBox(tr("vibe.title"))
        vibe_layout = QVBoxLayout(vibe_group)
        self._vibe_text = QTextEdit()
        self._vibe_text.setMaximumHeight(100)
        self._vibe_text.setPlaceholderText(tr("persona.vibe_ph"))
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

        self._btn_vibe = QPushButton(tr("vibe.fill_btn"))
        self._btn_vibe.setObjectName("primaryButton")
        self._btn_vibe.clicked.connect(self._on_vibe_fill)
        vibe_layout.addWidget(self._btn_vibe)

        self._vibe_status = QLabel("")
        self._vibe_status.setObjectName("subtitle")
        vibe_layout.addWidget(self._vibe_status)

        rl.addWidget(vibe_group)

        # 편집 폼: 4개 섹션으로 구조화
        # --- 기본 정보 ---
        g_basic = QGroupBox(tr("provider.group_basic"))
        f_basic = QFormLayout(g_basic)
        self._name = QLineEdit()
        self._name.setPlaceholderText(tr("persona.name_ph_ai"))
        f_basic.addRow(tr("persona.name_req"), self._name)
        self._age = QLineEdit()
        self._age.setPlaceholderText(tr("persona.age_ph"))
        f_basic.addRow(tr("persona.age_label"), self._age)
        self._gender = QLineEdit()
        self._gender.setPlaceholderText(tr("persona.gender_ph"))
        f_basic.addRow(tr("persona.gender_label"), self._gender)
        self._role = QLineEdit()
        self._role.setPlaceholderText(tr("persona.role_ph"))
        f_basic.addRow(tr("persona.role_label"), self._role)
        rl.addWidget(g_basic)

        # --- 외면 ---
        g_appear = QGroupBox(tr("persona.section_appearance"))
        f_appear = QFormLayout(g_appear)
        self._appearance = QTextEdit()
        self._appearance.setMaximumHeight(80)
        self._appearance.setPlaceholderText(tr("persona.appearance_ph"))
        f_appear.addRow(tr("persona.appearance_label"), self._appearance)
        rl.addWidget(g_appear)

        # --- 내면 ---
        g_inner = QGroupBox(tr("persona.section_inner"))
        f_inner = QFormLayout(g_inner)
        self._pers = QTextEdit()
        self._pers.setMaximumHeight(80)
        self._pers.setPlaceholderText(tr("persona.personality_ph"))
        f_inner.addRow(tr("persona.personality_label"), self._pers)
        self._style = QTextEdit()
        self._style.setMaximumHeight(80)
        self._style.setPlaceholderText(tr("persona.speaking_ph"))
        f_inner.addRow(tr("persona.speaking_label"), self._style)
        self._weaknesses = QTextEdit()
        self._weaknesses.setMaximumHeight(60)
        self._weaknesses.setPlaceholderText(tr("persona.weaknesses_ph"))
        f_inner.addRow(tr("persona.weaknesses_label"), self._weaknesses)
        rl.addWidget(g_inner)

        # --- 서사 ---
        g_story = QGroupBox(tr("persona.section_story"))
        f_story = QFormLayout(g_story)
        self._backstory = QTextEdit()
        self._backstory.setMaximumHeight(80)
        self._backstory.setPlaceholderText(tr("persona.backstory_ph"))
        f_story.addRow(tr("persona.backstory_label"), self._backstory)
        self._relationships = QTextEdit()
        self._relationships.setMaximumHeight(60)
        self._relationships.setPlaceholderText(tr("persona.relationships_ph"))
        f_story.addRow(tr("persona.relationships_label"), self._relationships)
        rl.addWidget(g_story)

        # --- 능력 ---
        g_skill = QGroupBox(tr("persona.section_skill"))
        f_skill = QFormLayout(g_skill)
        self._skills = QTextEdit()
        self._skills.setMaximumHeight(60)
        self._skills.setPlaceholderText(tr("persona.skills_ph"))
        f_skill.addRow(tr("persona.skills_label"), self._skills)
        self._interests = QTextEdit()
        self._interests.setMaximumHeight(60)
        self._interests.setPlaceholderText(tr("persona.interests_ph"))
        f_skill.addRow(tr("persona.interests_label"), self._interests)
        rl.addWidget(g_skill)

        # --- 행동 규칙 ---
        g_rule = QGroupBox(tr("persona.section_rule"))
        f_rule = QFormLayout(g_rule)
        self._goals = QTextEdit()
        self._goals.setMaximumHeight(60)
        self._goals.setPlaceholderText(tr("persona.goals_ph"))
        f_rule.addRow(tr("persona.goals_label"), self._goals)
        self._restr = QTextEdit()
        self._restr.setMaximumHeight(60)
        self._restr.setPlaceholderText(tr("persona.restrictions_ph"))
        f_rule.addRow(tr("persona.restrictions_ai_label"), self._restr)
        rl.addWidget(g_rule)

        # 저장 버튼
        bs = QPushButton(tr("common.save"))
        bs.setObjectName("primaryButton")
        bs.clicked.connect(self._on_save)
        rl.addWidget(bs)
        self._st = QLabel("")
        self._st.setObjectName("subtitle")
        rl.addWidget(self._st)
        rl.addStretch()

        scroll.setWidget(rw)
        sp.addWidget(scroll)
        sp.setSizes([280, 700])

        # Provider/Model 드롭다운 초기화
        self._load_providers()

    # --- Provider/Model 드롭다운 ---

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
            self._prov_combo.addItem(
                f"{p.name} ({p.provider_kind})",
                p.id,
            )

    def _on_provider_changed(self, _index: int) -> None:
        """Provider 선택 변경 시 해당 Provider의 모델 목록을 로드한다."""
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

    # --- 목록 로드 ---

    def _load(self) -> None:
        self._list.clear()
        for p in self._svc.get_all_ai_personas():
            it = QListWidgetItem(f"{p.name} — {p.role_name}")
            it.setData(Qt.ItemDataRole.UserRole, p.id)
            self._list.addItem(it)

    # --- 필드 ↔ UI 매핑 ---

    def _on_sel(self, c: QListWidgetItem | None, _: QListWidgetItem | None) -> None:
        if not c:
            return
        p = self._svc.get_ai_persona(c.data(Qt.ItemDataRole.UserRole))
        if not p:
            return
        self._cur_id = p.id
        self._name.setText(p.name)
        self._role.setText(p.role_name)
        self._pers.setPlainText(p.personality)
        self._style.setPlainText(p.speaking_style)
        self._goals.setPlainText(p.goals)
        self._restr.setPlainText(p.restrictions)
        # [v0.2.0] 확장 필드
        self._age.setText(getattr(p, "age", ""))
        self._gender.setText(getattr(p, "gender", ""))
        self._appearance.setPlainText(getattr(p, "appearance", ""))
        self._backstory.setPlainText(getattr(p, "backstory", ""))
        self._relationships.setPlainText(getattr(p, "relationships", ""))
        self._skills.setPlainText(getattr(p, "skills", ""))
        self._interests.setPlainText(getattr(p, "interests", ""))
        self._weaknesses.setPlainText(getattr(p, "weaknesses", ""))

    def _on_new(self) -> None:
        self._cur_id = None
        self._name.clear()
        self._role.clear()
        self._age.clear()
        self._gender.clear()
        for w in [
            self._pers, self._style, self._goals, self._restr,
            self._appearance, self._backstory, self._relationships,
            self._skills, self._interests, self._weaknesses,
        ]:
            w.clear()

    def _on_save(self) -> None:
        n = self._name.text().strip()
        r = self._role.text().strip()
        pe = self._pers.toPlainText().strip()
        st = self._style.toPlainText().strip()
        if not all([n, r, pe, st]):
            self._st.setText(tr("persona.fields_required"))
            self._st.setStyleSheet(f"color:{COLORS.accent_danger};")
            return
        self._svc.save_ai_persona(
            name=n,
            role_name=r,
            personality=pe,
            speaking_style=st,
            goals=self._goals.toPlainText().strip(),
            restrictions=self._restr.toPlainText().strip(),
            existing_id=self._cur_id,
            # [v0.2.0] 확장 필드
            age=self._age.text().strip(),
            gender=self._gender.text().strip(),
            appearance=self._appearance.toPlainText().strip(),
            backstory=self._backstory.toPlainText().strip(),
            relationships=self._relationships.toPlainText().strip(),
            skills=self._skills.toPlainText().strip(),
            interests=self._interests.toPlainText().strip(),
            weaknesses=self._weaknesses.toPlainText().strip(),
        )
        self._st.setText(tr("chat_profile.saved", name=n))
        self._st.setStyleSheet(f"color:{COLORS.accent_success};")
        self._load()

    def _on_del(self) -> None:
        if not self._cur_id:
            return
        if QMessageBox.question(self, tr("common.confirm"), tr("common.delete_short")) == QMessageBox.StandardButton.Yes:
            self._svc.delete_ai_persona(self._cur_id)
            self._on_new()
            self._load()

    # --- Vibe Fill ---

    def _on_vibe_fill(self) -> None:
        """AI로 채우기 버튼 클릭 시 호출된다."""
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

        # UI 비활성화
        self._btn_vibe.setEnabled(False)
        self._vibe_status.setText(tr("vibe.generating"))
        self._vibe_status.setStyleSheet("")

        # AsyncSignalBridge 생성 (지연 생성)
        if not self._bridge:
            self._bridge = AsyncSignalBridge()
            self._bridge.task_result.connect(self._slot_vibe_result)
            self._bridge.task_error.connect(self._slot_vibe_error)

        # 비동기 LLM 호출
        self._bridge.run_coroutine_in_thread(
            self._vibe_svc.generate_persona(vibe, prov_id, model_id)
        )

    def _slot_vibe_result(self, result: object) -> None:
        """Vibe Fill 결과 수신 (메인 스레드)."""
        self._btn_vibe.setEnabled(True)

        # VibeFillResult 타입 검증
        success = getattr(result, "success", False)
        fields: dict[str, str] = getattr(result, "fields", {})
        error = getattr(result, "error", "")

        if not success:
            self._vibe_status.setText(tr("vibe.gen_failed", error=error))
            self._vibe_status.setStyleSheet(f"color:{COLORS.accent_danger};")
            # 부분 결과라도 채우기
            if fields:
                self._fill_fields(fields)
                self._vibe_status.setText(tr("vibe.partial_gen", error=error))
            return

        # 성공 — 모든 필드 채우기
        self._fill_fields(fields)
        name = fields.get("name", "?")
        self._vibe_status.setText(tr("vibe.gen_success", name=name))
        self._vibe_status.setStyleSheet(f"color:{COLORS.accent_success};")

    def _slot_vibe_error(self, error: object) -> None:
        """Vibe Fill 에러 수신 (메인 스레드)."""
        self._btn_vibe.setEnabled(True)
        msg = getattr(error, "message", str(error))
        self._vibe_status.setText(tr("common.error", msg=msg))
        self._vibe_status.setStyleSheet(f"color:{COLORS.accent_danger};")

    def _fill_fields(self, fields: dict[str, str]) -> None:
        """VibeFillResult의 fields를 UI 필드에 매핑한다."""
        # 필드 매핑: JSON 키 → UI 위젯
        _map_line: list[tuple[str, QLineEdit]] = [
            ("name", self._name),
            ("age", self._age),
            ("gender", self._gender),
            ("role_name", self._role),
        ]
        _map_text: list[tuple[str, QTextEdit]] = [
            ("personality", self._pers),
            ("speaking_style", self._style),
            ("appearance", self._appearance),
            ("backstory", self._backstory),
            ("relationships", self._relationships),
            ("skills", self._skills),
            ("interests", self._interests),
            ("weaknesses", self._weaknesses),
            ("goals", self._goals),
            ("restrictions", self._restr),
        ]
        for key, line_widget in _map_line:
            val = fields.get(key, "")
            if val:
                line_widget.setText(val)
        for key, text_widget in _map_text:
            val = fields.get(key, "")
            if val:
                text_widget.setPlainText(val)

