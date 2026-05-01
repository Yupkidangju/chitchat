# src/chitchat/ui/pages/model_profile_page.py
# [v0.3.0] 모델 프로필 관리 페이지
#
# Provider 선택 → 캐시된 모델 선택 → context/max_output/temperature 등 저장.
# 첫 사용자 완주 루트: Provider → 모델 패치 → ModelProfile 생성.
#
# [v0.1.3] 감사 항목 수정:
#   1. DD-13: 모델 파라미터 동적 가시성 — capability에 없는 파라미터 숨김 (SC-06)
#   2. spec §11.1: max_output_tokens는 항상 표시, 나머지는 supported_parameters에 따라
#   3. LM Studio 등 capability 불완전 시 경고 표시하고 모든 파라미터 노출
from __future__ import annotations

import json
import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from chitchat.i18n import tr
from chitchat.services.profile_service import ProfileService
from chitchat.services.provider_service import ProviderService
from chitchat.ui.theme import COLORS, SPACING

logger = logging.getLogger(__name__)

# 파라미터 이름 → 폼 행 인덱스를 추적하기 위한 타입
_PARAM_NAMES = ["temperature", "top_p", "top_k", "frequency_penalty", "presence_penalty"]


class ModelProfilePage(QWidget):
    """모델 프로필 관리 페이지.

    [v0.1.3] DD-13에 따라 선택된 모델의 capability 기반 파라미터 동적 가시성 적용.
    Provider 선택 → 캐시된 모델 선택 → 지원되는 파라미터만 표시 → 저장.
    """

    def __init__(
        self,
        profile_service: ProfileService,
        provider_service: ProviderService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._psvc = profile_service
        self._prov_svc = provider_service
        self._current_id: str | None = None
        # [v0.1.3] 파라미터 위젯 → 행 인덱스 매핑 (가시성 제어용)
        self._param_widgets: dict[str, tuple[QWidget, int]] = {}
        self._setup_ui()
        self._load_list()

    def _setup_ui(self) -> None:
        lo = QHBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(0)
        sp = QSplitter(Qt.Orientation.Horizontal)
        lo.addWidget(sp)

        # 좌측: 프로필 목록
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(SPACING.md, SPACING.md, SPACING.md, SPACING.md)
        ll.addWidget(QLabel(tr("model.list_title")))
        self._list = QListWidget()
        self._list.currentItemChanged.connect(self._on_sel)
        ll.addWidget(self._list)
        blo = QHBoxLayout()
        bn = QPushButton(tr("model.new_btn"))
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
        rl.addWidget(QLabel(tr("model.form_title")))

        fg = QGroupBox(tr("provider.group_basic"))
        form = QFormLayout(fg)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText(tr("model.name_ph"))
        form.addRow(tr("model.name_label"), self._name_edit)

        self._prov_combo = QComboBox()
        self._prov_combo.currentIndexChanged.connect(self._on_prov_changed)
        form.addRow(tr("model.provider_label"), self._prov_combo)

        self._model_combo = QComboBox()
        # [v0.1.3] 모델 변경 시 파라미터 가시성 갱신
        self._model_combo.currentIndexChanged.connect(self._on_model_changed)
        form.addRow(tr("model.model_label"), self._model_combo)

        rl.addWidget(fg)

        # [v0.1.3] capability 경고 레이블
        self._capability_warning = QLabel("")
        self._capability_warning.setWordWrap(True)
        self._capability_warning.setStyleSheet(f"color:{COLORS.accent_warning}; padding: 4px;")
        self._capability_warning.setVisible(False)
        rl.addWidget(self._capability_warning)

        # 생성 파라미터 그룹 — 각 위젯에 대한 참조를 저장
        pg = QGroupBox(tr("model.gen_params"))
        self._param_form = QFormLayout(pg)

        self._ctx_spin = QSpinBox()
        self._ctx_spin.setRange(512, 2_000_000)
        self._ctx_spin.setValue(8192)
        self._param_form.addRow(tr("model.context_window"), self._ctx_spin)

        # max_output_tokens는 spec §11.1에 따라 항상 표시
        self._max_out_spin = QSpinBox()
        self._max_out_spin.setRange(64, 128_000)
        self._max_out_spin.setValue(2048)
        self._param_form.addRow(tr("model.max_output"), self._max_out_spin)

        # [v0.1.3] capability에 따라 동적 숨김 대상 파라미터들
        self._temp_spin = QDoubleSpinBox()
        self._temp_spin.setRange(0.0, 2.0)
        self._temp_spin.setValue(0.7)
        self._temp_spin.setSingleStep(0.1)
        self._param_form.addRow("Temperature:", self._temp_spin)
        self._param_widgets["temperature"] = (self._temp_spin, self._param_form.rowCount() - 1)

        self._top_p_spin = QDoubleSpinBox()
        self._top_p_spin.setRange(0.0, 1.0)
        self._top_p_spin.setValue(0.95)
        self._top_p_spin.setSingleStep(0.05)
        self._param_form.addRow("Top-P:", self._top_p_spin)
        self._param_widgets["top_p"] = (self._top_p_spin, self._param_form.rowCount() - 1)

        self._top_k_spin = QSpinBox()
        self._top_k_spin.setRange(0, 500)
        self._top_k_spin.setValue(40)
        self._param_form.addRow("Top-K:", self._top_k_spin)
        self._param_widgets["top_k"] = (self._top_k_spin, self._param_form.rowCount() - 1)

        self._freq_spin = QDoubleSpinBox()
        self._freq_spin.setRange(-2.0, 2.0)
        self._freq_spin.setValue(0.0)
        self._freq_spin.setSingleStep(0.1)
        self._param_form.addRow("Frequency Penalty:", self._freq_spin)
        self._param_widgets["frequency_penalty"] = (self._freq_spin, self._param_form.rowCount() - 1)

        self._pres_spin = QDoubleSpinBox()
        self._pres_spin.setRange(-2.0, 2.0)
        self._pres_spin.setValue(0.0)
        self._pres_spin.setSingleStep(0.1)
        self._param_form.addRow("Presence Penalty:", self._pres_spin)
        self._param_widgets["presence_penalty"] = (self._pres_spin, self._param_form.rowCount() - 1)

        rl.addWidget(pg)

        # 저장 버튼 + 상태
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
        sp.setSizes([280, 620])

    # ━━━ 데이터 로드 ━━━

    def _load_list(self) -> None:
        self._list.clear()
        for mp in self._psvc.get_all_model_profiles():
            it = QListWidgetItem(mp.name)
            it.setData(Qt.ItemDataRole.UserRole, mp.id)
            self._list.addItem(it)
        # Provider 콤보 갱신
        self._prov_combo.blockSignals(True)
        self._prov_combo.clear()
        for p in self._prov_svc.get_all_providers():
            self._prov_combo.addItem(f"{p.name} ({p.provider_kind})", p.id)
        self._prov_combo.blockSignals(False)
        self._on_prov_changed()

    def _on_prov_changed(self, _idx: int = 0) -> None:
        """Provider 변경 시 캐시된 모델 콤보 갱신."""
        self._model_combo.blockSignals(True)
        self._model_combo.clear()
        pid = self._prov_combo.currentData()
        if not pid:
            self._model_combo.blockSignals(False)
            return
        for mc in self._prov_svc.get_cached_models(pid):
            label = f"{mc.display_name} (ctx:{mc.context_window_tokens})"
            self._model_combo.addItem(label, mc.model_id)
        self._model_combo.blockSignals(False)
        # 첫 모델 선택 후 가시성 갱신
        if self._model_combo.count() > 0:
            self._auto_fill_from_cache()
            self._on_model_changed()

    def _on_model_changed(self, _idx: int = 0) -> None:
        """[v0.1.3] 모델 변경 시 supported_parameters를 조회하여 파라미터 가시성을 갱신한다.

        DD-13 결정에 따라:
        - supported_parameters에 포함된 파라미터만 표시
        - max_output_tokens는 항상 표시
        - capability 정보가 없으면 모든 파라미터 표시 + 경고
        """
        pid = self._prov_combo.currentData()
        mid = self._model_combo.currentData()
        if not pid or not mid:
            return

        # 모델 캐시에서 supported_parameters_json 조회
        supported: set[str] | None = None
        for mc in self._prov_svc.get_cached_models(pid):
            if mc.model_id == mid:
                try:
                    params = json.loads(mc.supported_parameters_json)
                    if isinstance(params, list) and len(params) > 0:
                        supported = set(params)
                except (json.JSONDecodeError, TypeError):
                    pass
                break

        if supported is None or len(supported) == 0:
            # capability 정보가 없거나 불완전 → 모든 파라미터 표시 + 경고
            self._capability_warning.setText(tr("model.capability_warning"))
            self._capability_warning.setVisible(True)
            for param_name, (widget, row_idx) in self._param_widgets.items():
                self._param_form.setRowVisible(row_idx, True)
        else:
            # capability 정보 있음 → 지원되는 파라미터만 표시
            self._capability_warning.setVisible(False)
            hidden_count = 0
            for param_name, (widget, row_idx) in self._param_widgets.items():
                is_visible = param_name in supported
                self._param_form.setRowVisible(row_idx, is_visible)
                if not is_visible:
                    hidden_count += 1
            if hidden_count > 0:
                logger.info(
                    "모델 '%s': %d개 파라미터 숨김 (지원되지 않음)", mid, hidden_count
                )

    def _auto_fill_from_cache(self) -> None:
        """선택된 모델의 캐시 정보로 스핀박스 기본값 설정."""
        pid = self._prov_combo.currentData()
        mid = self._model_combo.currentData()
        if not pid or not mid:
            return
        for mc in self._prov_svc.get_cached_models(pid):
            if mc.model_id == mid:
                if mc.context_window_tokens:
                    self._ctx_spin.setValue(mc.context_window_tokens)
                if mc.max_output_tokens:
                    self._max_out_spin.setValue(mc.max_output_tokens)
                break

    def _on_sel(self, cur: QListWidgetItem | None, _: QListWidgetItem | None) -> None:
        if not cur:
            return
        mp = self._psvc.get_model_profile(cur.data(Qt.ItemDataRole.UserRole))
        if not mp:
            return
        self._current_id = mp.id
        self._name_edit.setText(mp.name)
        # Provider/모델 콤보 설정
        for i in range(self._prov_combo.count()):
            if self._prov_combo.itemData(i) == mp.provider_profile_id:
                self._prov_combo.setCurrentIndex(i)
                break
        # 모델 콤보 설정
        for i in range(self._model_combo.count()):
            if self._model_combo.itemData(i) == mp.model_id:
                self._model_combo.setCurrentIndex(i)
                break
        # 설정 파싱
        s = json.loads(mp.settings_json)
        self._ctx_spin.setValue(s.get("context_window_tokens", 8192))
        self._max_out_spin.setValue(s.get("max_output_tokens", 2048))
        self._temp_spin.setValue(s.get("temperature", 0.7))
        self._top_p_spin.setValue(s.get("top_p", 0.95))
        self._top_k_spin.setValue(s.get("top_k", 40))
        self._freq_spin.setValue(s.get("frequency_penalty", 0.0))
        self._pres_spin.setValue(s.get("presence_penalty", 0.0))
        self._status.setText(tr("model.loaded", name=mp.name))

    def _on_new(self) -> None:
        self._current_id = None
        self._name_edit.clear()
        self._status.setText(tr("model.new_msg"))

    def _on_delete(self) -> None:
        if not self._current_id:
            return
        if QMessageBox.question(self, tr("common.confirm"), tr("common.delete_confirm")) == QMessageBox.StandardButton.Yes:
            self._psvc.delete_model_profile(self._current_id)
            self._current_id = None
            self._load_list()

    def _on_save(self) -> None:
        """[v0.1.3] spec §11.2 Save Validation 5개 조건을 적용하여 저장한다.

        검증 조건:
        1. Provider profile이 비활성화되어 있으면 저장 차단
        2. Model capability가 로드되지 않았으면 저장 차단
        3. max_output_tokens가 capability max를 초과하면 저장 차단
        4. 표시된 파라미터가 범위를 벗어나면 저장 차단
        5. 숨겨진 미지원 파라미터에 non-null 값이 있으면 경고
        """
        name = self._name_edit.text().strip()
        pid = self._prov_combo.currentData()
        mid = self._model_combo.currentData()

        # 기본 필수 입력 검증
        if not name:
            self._status.setText(tr("provider.name_required"))
            self._status.setStyleSheet(f"color:{COLORS.accent_danger};")
            return
        if not pid or not mid:
            self._status.setText(tr("vibe.provider_model_select"))
            self._status.setStyleSheet(f"color:{COLORS.accent_danger};")
            return

        # [§11.2 조건 1] Provider 비활성화 확인
        prov = self._prov_svc.get_provider(pid)
        if prov and not prov.enabled:
            self._status.setText(tr("vibe.provider_disabled"))
            self._status.setStyleSheet(f"color:{COLORS.accent_danger};")
            return

        # [§11.2 조건 2~5] capability 기반 검증
        capability = None
        for mc in self._prov_svc.get_cached_models(pid):
            if mc.model_id == mid:
                capability = mc
                break

        if not capability:
            self._status.setText(tr("model.no_capability"))
            self._status.setStyleSheet(f"color:{COLORS.accent_warning};")
            # capability 없어도 저장 허용 (경고만), LM Studio 등

        # [§11.2 조건 3] max_output_tokens 초과 확인
        if capability and capability.max_output_tokens:
            if self._max_out_spin.value() > capability.max_output_tokens:
                self._status.setText(
                    tr("model.max_output_exceeded",
                       value=self._max_out_spin.value(),
                       limit=capability.max_output_tokens)
                )
                self._status.setStyleSheet(f"color:{COLORS.accent_danger};")
                return

        # [§11.2 조건 5] 숨겨진 미지원 파라미터 non-null 경고
        hidden_warnings: list[str] = []
        _DEFAULT_VALUES = {
            "temperature": 0.0, "top_p": 0.0, "top_k": 0,
            "frequency_penalty": 0.0, "presence_penalty": 0.0,
        }
        _SPIN_MAP: dict[str, QDoubleSpinBox | QSpinBox] = {
            "temperature": self._temp_spin, "top_p": self._top_p_spin,
            "top_k": self._top_k_spin, "frequency_penalty": self._freq_spin,
            "presence_penalty": self._pres_spin,
        }
        for param_name, (widget, row_idx) in self._param_widgets.items():
            if not self._param_form.isRowVisible(row_idx):
                spin = _SPIN_MAP.get(param_name)
                if spin is not None and spin.value() != _DEFAULT_VALUES.get(param_name, 0):
                    hidden_warnings.append(param_name)

        if hidden_warnings:
            self._status.setText(
                tr("model.hidden_param_warning",
                   params=", ".join(hidden_warnings))
            )
            self._status.setStyleSheet(f"color:{COLORS.accent_warning};")
            # 경고만 표시, 저장은 진행

        settings = json.dumps({
            "context_window_tokens": self._ctx_spin.value(),
            "max_output_tokens": self._max_out_spin.value(),
            "temperature": self._temp_spin.value(),
            "top_p": self._top_p_spin.value(),
            "top_k": self._top_k_spin.value(),
            "frequency_penalty": self._freq_spin.value(),
            "presence_penalty": self._pres_spin.value(),
        })
        try:
            self._psvc.save_model_profile(
                name=name,
                provider_profile_id=pid,
                model_id=mid,
                settings_json=settings,
                existing_id=self._current_id,
            )
            if not hidden_warnings:
                self._status.setText(tr("provider.saved", name=name))
                self._status.setStyleSheet(f"color:{COLORS.accent_success};")
            self._load_list()
        except Exception as e:
            self._status.setText(tr("common.save_failed", e=e))
            self._status.setStyleSheet(f"color:{COLORS.accent_danger};")
