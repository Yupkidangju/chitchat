# src/chitchat/ui/pages/model_profile_page.py
# [v0.1.0b0] 모델 프로필 관리 페이지
#
# Provider 선택 → 캐시된 모델 선택 → context/max_output/temperature 등 저장.
# 첫 사용자 완주 루트: Provider → 모델 패치 → ModelProfile 생성.
from __future__ import annotations
import json
import logging
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
    QPushButton, QSpinBox, QSplitter, QVBoxLayout, QWidget,
)
from chitchat.services.profile_service import ProfileService
from chitchat.services.provider_service import ProviderService
from chitchat.ui.theme import COLORS, SPACING

logger = logging.getLogger(__name__)


class ModelProfilePage(QWidget):
    """모델 프로필 관리 페이지.

    Provider 선택 → 캐시된 모델 선택 → 생성 파라미터 설정 → 저장.
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
        self._setup_ui()
        self._load_list()

    def _setup_ui(self) -> None:
        lo = QHBoxLayout(self); lo.setContentsMargins(0, 0, 0, 0); lo.setSpacing(0)
        sp = QSplitter(Qt.Orientation.Horizontal); lo.addWidget(sp)

        # 좌측: 프로필 목록
        left = QWidget(); ll = QVBoxLayout(left)
        ll.setContentsMargins(SPACING.md, SPACING.md, SPACING.md, SPACING.md)
        ll.addWidget(QLabel("⚙️ 모델 프로필 목록"))
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
        rl.addWidget(QLabel("모델 프로필 설정"))
        fg = QGroupBox("기본 정보"); form = QFormLayout(fg)

        self._name_edit = QLineEdit(); self._name_edit.setPlaceholderText("예: Gemini Flash 기본")
        form.addRow("프로필 이름:", self._name_edit)

        self._prov_combo = QComboBox(); self._prov_combo.currentIndexChanged.connect(self._on_prov_changed)
        form.addRow("Provider:", self._prov_combo)

        self._model_combo = QComboBox()
        form.addRow("모델:", self._model_combo)

        rl.addWidget(fg)

        # 생성 파라미터 그룹
        pg = QGroupBox("생성 파라미터"); pf = QFormLayout(pg)

        self._ctx_spin = QSpinBox(); self._ctx_spin.setRange(512, 2_000_000); self._ctx_spin.setValue(8192)
        pf.addRow("컨텍스트 윈도우:", self._ctx_spin)

        self._max_out_spin = QSpinBox(); self._max_out_spin.setRange(64, 128_000); self._max_out_spin.setValue(2048)
        pf.addRow("최대 출력 토큰:", self._max_out_spin)

        self._temp_spin = QDoubleSpinBox(); self._temp_spin.setRange(0.0, 2.0); self._temp_spin.setValue(0.7); self._temp_spin.setSingleStep(0.1)
        pf.addRow("Temperature:", self._temp_spin)

        self._top_p_spin = QDoubleSpinBox(); self._top_p_spin.setRange(0.0, 1.0); self._top_p_spin.setValue(0.95); self._top_p_spin.setSingleStep(0.05)
        pf.addRow("Top-P:", self._top_p_spin)

        self._top_k_spin = QSpinBox(); self._top_k_spin.setRange(0, 500); self._top_k_spin.setValue(40)
        pf.addRow("Top-K:", self._top_k_spin)

        self._freq_spin = QDoubleSpinBox(); self._freq_spin.setRange(-2.0, 2.0); self._freq_spin.setValue(0.0); self._freq_spin.setSingleStep(0.1)
        pf.addRow("Frequency Penalty:", self._freq_spin)

        self._pres_spin = QDoubleSpinBox(); self._pres_spin.setRange(-2.0, 2.0); self._pres_spin.setValue(0.0); self._pres_spin.setSingleStep(0.1)
        pf.addRow("Presence Penalty:", self._pres_spin)

        rl.addWidget(pg)

        # 저장 버튼 + 상태
        alo = QHBoxLayout()
        bs = QPushButton("💾 저장"); bs.setObjectName("primaryButton"); bs.clicked.connect(self._on_save); alo.addWidget(bs)
        rl.addLayout(alo)

        self._status = QLabel(""); self._status.setWordWrap(True); rl.addWidget(self._status)
        rl.addStretch()
        sp.addWidget(right)
        sp.setSizes([280, 620])

    # --- 데이터 로드 ---

    def _load_list(self) -> None:
        self._list.clear()
        for mp in self._psvc.get_all_model_profiles():
            it = QListWidgetItem(mp.name); it.setData(Qt.ItemDataRole.UserRole, mp.id)
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
        self._model_combo.clear()
        pid = self._prov_combo.currentData()
        if not pid:
            return
        for mc in self._prov_svc.get_cached_models(pid):
            label = f"{mc.display_name} (ctx:{mc.context_window_tokens})"
            self._model_combo.addItem(label, mc.model_id)
            # 컨텍스트/출력 기본값 자동 설정
        if self._model_combo.count() > 0:
            self._auto_fill_from_cache()

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
        self._status.setText(f"로드 완료: {mp.name}")

    def _on_new(self) -> None:
        self._current_id = None
        self._name_edit.clear()
        self._status.setText("새 모델 프로필을 작성하세요.")

    def _on_delete(self) -> None:
        if not self._current_id:
            return
        if QMessageBox.question(self, "확인", "삭제하시겠습니까?") == QMessageBox.StandardButton.Yes:
            self._psvc.delete_model_profile(self._current_id)
            self._current_id = None
            self._load_list()

    def _on_save(self) -> None:
        name = self._name_edit.text().strip()
        pid = self._prov_combo.currentData()
        mid = self._model_combo.currentData()
        if not name:
            self._status.setText("⚠️ 이름을 입력하세요."); self._status.setStyleSheet(f"color:{COLORS.accent_danger};"); return
        if not pid or not mid:
            self._status.setText("⚠️ Provider와 모델을 선택하세요."); self._status.setStyleSheet(f"color:{COLORS.accent_danger};"); return
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
            self._psvc.save_model_profile(name=name, provider_profile_id=pid, model_id=mid, settings_json=settings, existing_id=self._current_id)
            self._status.setText(f"✅ '{name}' 저장 완료!"); self._status.setStyleSheet(f"color:{COLORS.accent_success};")
            self._load_list()
        except Exception as e:
            self._status.setText(f"❌ 저장 실패: {e}"); self._status.setStyleSheet(f"color:{COLORS.accent_danger};")
