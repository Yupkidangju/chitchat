# src/chitchat/ui/pages/provider_page.py
# [v0.3.0] Provider 관리 페이지
#
# designs.md §4.1에서 정의된 Provider 관리 화면을 구현한다.
# 좌측: Provider 목록 + 추가 버튼
# 우측: 선택된 Provider 편집 폼 (이름, 종류, API Key, Base URL, 타임아웃)
# 연결 테스트, 모델 패치 버튼 포함.
#
# [v0.1.0b0 Remediation] AsyncSignalBridge로 비동기 작업 실행.
# asyncio.get_event_loop().run_until_complete() → worker 스레드 + Signal로 교체.

from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
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

from chitchat.services.provider_service import ProviderService
from chitchat.i18n import tr
from chitchat.ui.async_bridge import AsyncSignalBridge
from chitchat.ui.theme import COLORS, SPACING

logger = logging.getLogger(__name__)


class ProviderPage(QWidget):
    """Provider 관리 페이지.

    Provider 목록, 편집 폼, 연결 테스트, 모델 패치 기능을 제공한다.
    """

    def __init__(
        self,
        provider_service: ProviderService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = provider_service
        self._current_id: str | None = None
        # Signal 브리지: 비동기 결과를 메인 스레드로 전달
        self._bridge = AsyncSignalBridge(self)
        self._bridge.task_result.connect(self._slot_task_result)
        self._bridge.task_error.connect(self._slot_task_error)
        self._pending_action: str = ""  # "test" 또는 "fetch"
        self._setup_ui()
        self._load_list()

    def _setup_ui(self) -> None:
        """UI를 구성한다."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # 좌측: Provider 목록
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(SPACING.md, SPACING.md, SPACING.md, SPACING.md)

        title = QLabel(tr("provider.list_title"))
        title.setObjectName("sectionTitle")
        left_layout.addWidget(title)

        self._list = QListWidget()
        self._list.currentItemChanged.connect(self._on_selection_changed)
        left_layout.addWidget(self._list)

        btn_layout = QHBoxLayout()
        btn_new = QPushButton(tr("provider.new_btn"))
        btn_new.setObjectName("primaryButton")
        btn_new.clicked.connect(self._on_new)
        btn_layout.addWidget(btn_new)

        btn_delete = QPushButton(tr("common.delete"))
        btn_delete.setObjectName("dangerButton")
        btn_delete.clicked.connect(self._on_delete)
        btn_layout.addWidget(btn_delete)
        left_layout.addLayout(btn_layout)

        splitter.addWidget(left)

        # 우측: 편집 폼
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(SPACING.lg, SPACING.md, SPACING.lg, SPACING.md)

        form_title = QLabel(tr("provider.form_title"))
        form_title.setObjectName("sectionTitle")
        right_layout.addWidget(form_title)

        form_group = QGroupBox(tr("provider.group_basic"))
        form = QFormLayout(form_group)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText(tr("provider.name_ph"))
        form.addRow(tr("common.name"), self._name_edit)

        self._kind_combo = QComboBox()
        self._kind_combo.addItems(["gemini", "openrouter", "lm_studio"])
        self._kind_combo.currentTextChanged.connect(self._on_kind_changed)
        form.addRow(tr("provider.kind_label"), self._kind_combo)

        self._api_key_edit = QLineEdit()
        self._api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key_edit.setPlaceholderText(tr("provider.apikey_ph"))
        form.addRow(tr("provider.apikey_label"), self._api_key_edit)

        self._base_url_edit = QLineEdit()
        self._base_url_edit.setPlaceholderText(tr("provider.baseurl_ph"))
        form.addRow(tr("provider.baseurl_label"), self._base_url_edit)

        self._timeout_spin = QSpinBox()
        self._timeout_spin.setRange(5, 300)
        self._timeout_spin.setValue(60)
        self._timeout_spin.setSuffix(tr("provider.timeout_suffix"))
        form.addRow(tr("provider.timeout_label"), self._timeout_spin)

        right_layout.addWidget(form_group)

        # 액션 버튼
        action_layout = QHBoxLayout()

        btn_save = QPushButton(tr("common.save"))
        btn_save.setObjectName("primaryButton")
        btn_save.clicked.connect(self._on_save)
        action_layout.addWidget(btn_save)

        self._btn_test = QPushButton(tr("provider.test_btn"))
        self._btn_test.clicked.connect(self._on_test_connection)
        action_layout.addWidget(self._btn_test)

        self._btn_fetch = QPushButton(tr("provider.fetch_btn"))
        self._btn_fetch.clicked.connect(self._on_fetch_models)
        action_layout.addWidget(self._btn_fetch)

        right_layout.addLayout(action_layout)

        # 상태 레이블
        self._status_label = QLabel("")
        self._status_label.setObjectName("subtitle")
        self._status_label.setWordWrap(True)
        right_layout.addWidget(self._status_label)

        # [v0.1.3] Provider Setup State 시각화 (spec §13.1)
        state_group = QGroupBox(tr("provider.setup_title"))
        state_layout = QVBoxLayout(state_group)
        self._state_labels: list[QLabel] = []
        _STEPS = [
            ("1️⃣", tr("provider.step1")),
            ("2️⃣", tr("provider.step2")),
            ("3️⃣", tr("provider.step3")),
            ("4️⃣", tr("provider.step4")),
            ("5️⃣", tr("provider.step5")),
        ]
        for emoji, step_name in _STEPS:
            lbl = QLabel(f"  ⬜ {emoji} {step_name}")
            lbl.setWordWrap(True)
            self._state_labels.append(lbl)
            state_layout.addWidget(lbl)
        right_layout.addWidget(state_group)

        right_layout.addStretch()
        splitter.addWidget(right)
        splitter.setSizes([300, 600])

    def _load_list(self) -> None:
        """Provider 목록을 로드한다."""
        self._list.clear()
        providers = self._service.get_all_providers()
        for p in providers:
            item = QListWidgetItem(f"{p.name} ({p.provider_kind})")
            item.setData(Qt.ItemDataRole.UserRole, p.id)
            self._list.addItem(item)

    def _on_selection_changed(self, current: QListWidgetItem | None, _prev: QListWidgetItem | None) -> None:
        if not current:
            return
        pid = current.data(Qt.ItemDataRole.UserRole)
        provider = self._service.get_provider(pid)
        if not provider:
            return
        self._current_id = provider.id
        self._name_edit.setText(provider.name)
        self._kind_combo.setCurrentText(provider.provider_kind)
        self._base_url_edit.setText(provider.base_url or "")
        self._timeout_spin.setValue(provider.timeout_seconds)
        self._api_key_edit.clear()
        self._status_label.setText(tr("provider.loaded", name=provider.name))
        # [v0.1.3] 셀업 상태 갱신
        self._update_setup_state(provider.id)

    def _on_kind_changed(self, kind: str) -> None:
        is_lm = kind == "lm_studio"
        self._api_key_edit.setEnabled(not is_lm)
        if is_lm:
            self._api_key_edit.clear()
            self._api_key_edit.setPlaceholderText(tr("provider.apikey_lm"))
        else:
            self._api_key_edit.setPlaceholderText(tr("provider.apikey_ph"))

    def _on_new(self) -> None:
        self._current_id = None
        self._name_edit.clear()
        self._kind_combo.setCurrentIndex(0)
        self._api_key_edit.clear()
        self._base_url_edit.clear()
        self._timeout_spin.setValue(60)
        self._status_label.setText(tr("provider.new_msg"))

    def _on_save(self) -> None:
        name = self._name_edit.text().strip()
        if not name:
            self._status_label.setText(tr("provider.name_required"))
            self._status_label.setStyleSheet(f"color: {COLORS.accent_danger};")
            return
        kind = self._kind_combo.currentText()
        api_key = self._api_key_edit.text().strip() or None
        base_url = self._base_url_edit.text().strip() or None
        timeout = self._timeout_spin.value()
        try:
            self._service.save_provider(
                name=name, provider_kind=kind, api_key=api_key,  # type: ignore[arg-type]
                base_url=base_url, timeout_seconds=timeout, existing_id=self._current_id,
            )
            self._status_label.setText(tr("provider.saved", name=name))
            self._status_label.setStyleSheet(f"color: {COLORS.accent_success};")
            self._load_list()
        except Exception as e:
            self._status_label.setText(tr("common.save_failed", e=e))
            self._status_label.setStyleSheet(f"color: {COLORS.accent_danger};")

    def _on_delete(self) -> None:
        if not self._current_id:
            return
        result = QMessageBox.question(
            self, tr("common.confirm"), tr("provider.delete_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if result == QMessageBox.StandardButton.Yes:
            self._service.delete_provider(self._current_id)
            self._current_id = None
            self._on_new()
            self._load_list()
            self._status_label.setText(tr("common.deleted"))

    def _on_test_connection(self) -> None:
        """연결 테스트 (worker 스레드에서 비동기 실행, Signal로 결과 수신)."""
        if not self._current_id:
            self._status_label.setText(tr("provider.save_first"))
            return
        self._pending_action = "test"
        self._btn_test.setEnabled(False)
        self._btn_fetch.setEnabled(False)
        self._status_label.setText(tr("provider.testing"))
        self._status_label.setStyleSheet("")
        self._bridge.run_coroutine_in_thread(self._service.test_connection(self._current_id))

    def _on_fetch_models(self) -> None:
        """모델 패치 (worker 스레드에서 비동기 실행, Signal로 결과 수신)."""
        if not self._current_id:
            self._status_label.setText(tr("provider.save_first"))
            return
        self._pending_action = "fetch"
        self._btn_test.setEnabled(False)
        self._btn_fetch.setEnabled(False)
        self._status_label.setText(tr("provider.fetching"))
        self._status_label.setStyleSheet("")
        self._bridge.run_coroutine_in_thread(self._service.fetch_models(self._current_id))

    # --- Signal Slots (메인 스레드에서 실행됨) ---

    def _slot_task_result(self, result: object) -> None:
        """비동기 작업 결과 수신 (메인 스레드). UI 갱신 안전."""
        self._btn_test.setEnabled(True)
        self._btn_fetch.setEnabled(True)
        if self._pending_action == "test":
            # [v0.1.4] getattr 패턴으로 object 타입 안전 접근 (mypy 수정)
            ok = getattr(result, "ok", False)
            message = getattr(result, "message", str(result))
            latency = getattr(result, "latency_ms", None)
            if ok:
                msg = f"✅ {message}"
                if latency:
                    msg += f" ({latency}ms)"
                self._status_label.setStyleSheet(f"color: {COLORS.accent_success};")
            else:
                msg = f"❌ {message}"
                self._status_label.setStyleSheet(f"color: {COLORS.accent_danger};")
            self._status_label.setText(msg)
            # [v0.1.3] 연결 테스트 성공 시 상태 갱신
            if ok and self._current_id:
                self._update_setup_state(self._current_id)
        elif self._pending_action == "fetch":
            count = len(result) if isinstance(result, list) else 0
            self._status_label.setText(tr("provider.models_loaded", count=count))
            self._status_label.setStyleSheet(f"color: {COLORS.accent_success};")
            # [v0.1.3] 모델 패치 성공 시 상태 갱신
            if self._current_id:
                self._update_setup_state(self._current_id)

    def _slot_task_error(self, error_msg: str) -> None:
        """비동기 작업 에러 수신 (메인 스레드). UI 갱신 안전."""
        self._btn_test.setEnabled(True)
        self._btn_fetch.setEnabled(True)
        action = tr("provider.action_test") if self._pending_action == "test" else tr("provider.action_fetch")
        self._status_label.setText(tr("provider.action_failed", action=action, error=error_msg))
        self._status_label.setStyleSheet(f"color: {COLORS.accent_danger};")

    # --- [v0.1.3] Provider Setup State 시각화 ---

    def _update_setup_state(self, provider_id: str) -> None:
        """[v0.1.3] spec §13.1 Provider Setup State를 시각적으로 갱신한다.

        7단계 상태 머신을 현재 데이터 기준으로 판단:
        1. 기본 정보 저장: provider가 DB에 존재
        2. API Key 저장: secret_ref가 설정됨 (LM Studio는 자동 통과)
        3. 연결 테스트: 상태 레이블에 성공 메시지가 있는지 (추정)
        4. 모델 목록 로드: 캐시된 모델이 1개 이상
        5. 모델 프로필 생성 가능: ModelProfile이 이 Provider를 참조
        """
        provider = self._service.get_provider(provider_id)
        if not provider:
            return

        # 단계 판정
        steps_done = [False] * 5

        # 1. 기본 정보 저장 (항상 True — 선택된 시점에 이미 DB에 있음)
        steps_done[0] = True

        # 2. API Key 저장: LM Studio는 불필요, 나머지는 secret_ref 존재 여부
        if provider.provider_kind == "lm_studio":
            steps_done[1] = True
        else:
            steps_done[1] = bool(provider.secret_ref)

        # 3. 연결 테스트: 상태 레이블에 ✅가 있으면 성공으로 추정
        current_status = self._status_label.text()
        steps_done[2] = "✅" in current_status and ("연결" in current_status or "Connection" in current_status or "ms)" in current_status)

        # 4. 모델 목록 로드: 캐시된 모델 수 확인
        cached_models = self._service.get_cached_models(provider_id)
        steps_done[3] = len(cached_models) > 0

        # 5. 모델 프로필: 이 Provider를 참조하는 ModelProfile 존재 여부
        # 간접 확인: 캐시된 모델이 있으면 프로필 생성 가능
        steps_done[4] = steps_done[3]

        # UI 갱신
        _STEP_NAMES = [
            tr("provider.step1"),
            tr("provider.step2"),
            tr("provider.step3"),
            tr("provider.step4"),
            tr("provider.step5"),
        ]
        _EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
        for i, (done, name) in enumerate(zip(steps_done, _STEP_NAMES)):
            icon = "✅" if done else "⬜"
            self._state_labels[i].setText(f"  {icon} {_EMOJIS[i]} {name}")
            if done:
                self._state_labels[i].setStyleSheet(f"color:{COLORS.accent_success};")
            else:
                self._state_labels[i].setStyleSheet(f"color:{COLORS.text_secondary};")
