# src/chitchat/ui/pages/provider_page.py
# [v0.1.0b0] Provider 관리 페이지
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

        title = QLabel("Provider 목록")
        title.setObjectName("sectionTitle")
        left_layout.addWidget(title)

        self._list = QListWidget()
        self._list.currentItemChanged.connect(self._on_selection_changed)
        left_layout.addWidget(self._list)

        btn_layout = QHBoxLayout()
        btn_new = QPushButton("+ 새 Provider")
        btn_new.setObjectName("primaryButton")
        btn_new.clicked.connect(self._on_new)
        btn_layout.addWidget(btn_new)

        btn_delete = QPushButton("삭제")
        btn_delete.setObjectName("dangerButton")
        btn_delete.clicked.connect(self._on_delete)
        btn_layout.addWidget(btn_delete)
        left_layout.addLayout(btn_layout)

        splitter.addWidget(left)

        # 우측: 편집 폼
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(SPACING.lg, SPACING.md, SPACING.lg, SPACING.md)

        form_title = QLabel("Provider 설정")
        form_title.setObjectName("sectionTitle")
        right_layout.addWidget(form_title)

        form_group = QGroupBox("기본 정보")
        form = QFormLayout(form_group)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("예: Gemini Main")
        form.addRow("이름:", self._name_edit)

        self._kind_combo = QComboBox()
        self._kind_combo.addItems(["gemini", "openrouter", "lm_studio"])
        self._kind_combo.currentTextChanged.connect(self._on_kind_changed)
        form.addRow("종류:", self._kind_combo)

        self._api_key_edit = QLineEdit()
        self._api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key_edit.setPlaceholderText("API Key (비밀번호 형태로 표시)")
        form.addRow("API Key:", self._api_key_edit)

        self._base_url_edit = QLineEdit()
        self._base_url_edit.setPlaceholderText("기본값 사용 시 비워두세요")
        form.addRow("Base URL:", self._base_url_edit)

        self._timeout_spin = QSpinBox()
        self._timeout_spin.setRange(5, 300)
        self._timeout_spin.setValue(60)
        self._timeout_spin.setSuffix(" 초")
        form.addRow("타임아웃:", self._timeout_spin)

        right_layout.addWidget(form_group)

        # 액션 버튼
        action_layout = QHBoxLayout()

        btn_save = QPushButton("💾 저장")
        btn_save.setObjectName("primaryButton")
        btn_save.clicked.connect(self._on_save)
        action_layout.addWidget(btn_save)

        self._btn_test = QPushButton("🔗 연결 테스트")
        self._btn_test.clicked.connect(self._on_test_connection)
        action_layout.addWidget(self._btn_test)

        self._btn_fetch = QPushButton("📋 모델 패치")
        self._btn_fetch.clicked.connect(self._on_fetch_models)
        action_layout.addWidget(self._btn_fetch)

        right_layout.addLayout(action_layout)

        # 상태 레이블
        self._status_label = QLabel("")
        self._status_label.setObjectName("subtitle")
        self._status_label.setWordWrap(True)
        right_layout.addWidget(self._status_label)

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
        self._status_label.setText(f"Provider 로드 완료: {provider.name}")

    def _on_kind_changed(self, kind: str) -> None:
        is_lm = kind == "lm_studio"
        self._api_key_edit.setEnabled(not is_lm)
        if is_lm:
            self._api_key_edit.clear()
            self._api_key_edit.setPlaceholderText("LM Studio는 API Key 불필요")
        else:
            self._api_key_edit.setPlaceholderText("API Key (비밀번호 형태로 표시)")

    def _on_new(self) -> None:
        self._current_id = None
        self._name_edit.clear()
        self._kind_combo.setCurrentIndex(0)
        self._api_key_edit.clear()
        self._base_url_edit.clear()
        self._timeout_spin.setValue(60)
        self._status_label.setText("새 Provider를 작성하세요.")

    def _on_save(self) -> None:
        name = self._name_edit.text().strip()
        if not name:
            self._status_label.setText("⚠️ 이름을 입력하세요.")
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
            self._status_label.setText(f"✅ '{name}' 저장 완료!")
            self._status_label.setStyleSheet(f"color: {COLORS.accent_success};")
            self._load_list()
        except Exception as e:
            self._status_label.setText(f"❌ 저장 실패: {e}")
            self._status_label.setStyleSheet(f"color: {COLORS.accent_danger};")

    def _on_delete(self) -> None:
        if not self._current_id:
            return
        result = QMessageBox.question(
            self, "확인", "이 Provider를 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if result == QMessageBox.StandardButton.Yes:
            self._service.delete_provider(self._current_id)
            self._current_id = None
            self._on_new()
            self._load_list()
            self._status_label.setText("🗑️ 삭제 완료.")

    def _on_test_connection(self) -> None:
        """연결 테스트 (worker 스레드에서 비동기 실행, Signal로 결과 수신)."""
        if not self._current_id:
            self._status_label.setText("⚠️ 먼저 Provider를 저장하세요.")
            return
        self._pending_action = "test"
        self._btn_test.setEnabled(False)
        self._btn_fetch.setEnabled(False)
        self._status_label.setText("🔄 연결 테스트 중...")
        self._status_label.setStyleSheet("")
        self._bridge.run_coroutine_in_thread(self._service.test_connection(self._current_id))

    def _on_fetch_models(self) -> None:
        """모델 패치 (worker 스레드에서 비동기 실행, Signal로 결과 수신)."""
        if not self._current_id:
            self._status_label.setText("⚠️ 먼저 Provider를 저장하세요.")
            return
        self._pending_action = "fetch"
        self._btn_test.setEnabled(False)
        self._btn_fetch.setEnabled(False)
        self._status_label.setText("🔄 모델 목록 가져오는 중...")
        self._status_label.setStyleSheet("")
        self._bridge.run_coroutine_in_thread(self._service.fetch_models(self._current_id))

    # --- Signal Slots (메인 스레드에서 실행됨) ---

    def _slot_task_result(self, result: object) -> None:
        """비동기 작업 결과 수신 (메인 스레드). UI 갱신 안전."""
        self._btn_test.setEnabled(True)
        self._btn_fetch.setEnabled(True)
        if self._pending_action == "test":
            if hasattr(result, "ok") and result.ok:  # type: ignore[union-attr]
                msg = f"✅ {result.message}"  # type: ignore[union-attr]
                if hasattr(result, "latency_ms") and result.latency_ms:  # type: ignore[union-attr]
                    msg += f" ({result.latency_ms}ms)"  # type: ignore[union-attr]
                self._status_label.setStyleSheet(f"color: {COLORS.accent_success};")
            else:
                msg = f"❌ {getattr(result, 'message', str(result))}"
                self._status_label.setStyleSheet(f"color: {COLORS.accent_danger};")
            self._status_label.setText(msg)
        elif self._pending_action == "fetch":
            count = len(result) if isinstance(result, list) else 0
            self._status_label.setText(f"✅ {count}개 모델 로드 완료.")
            self._status_label.setStyleSheet(f"color: {COLORS.accent_success};")

    def _slot_task_error(self, error_msg: str) -> None:
        """비동기 작업 에러 수신 (메인 스레드). UI 갱신 안전."""
        self._btn_test.setEnabled(True)
        self._btn_fetch.setEnabled(True)
        action = "연결 테스트" if self._pending_action == "test" else "모델 패치"
        self._status_label.setText(f"❌ {action} 실패: {error_msg}")
        self._status_label.setStyleSheet(f"color: {COLORS.accent_danger};")
