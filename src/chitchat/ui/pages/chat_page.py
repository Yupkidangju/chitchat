# src/chitchat/ui/pages/chat_page.py
# [v0.1.0b0] 채팅 페이지: 세션 리스트 + 타임라인 + 컴포저 + Inspector
#
# [v0.1.0b0 Remediation] Signal 브리지로 thread-safe UI 갱신 적용.
# worker 스레드에서 직접 QWidget을 건드리지 않고, Signal.emit()으로 메인 스레드에 전달.
#
# [v0.1.2] 감사 항목 수정:
#   1. 스트리밍 중 실시간 UI 표시 — _streaming_view 위젯으로 chunk마다 갱신
#   2. ChatProfile / UserPersona 선택 드롭다운 추가 — 사용자가 직접 프로필·페르소나를 선택
#   3. 세션 삭제 버튼 추가
#   4. 스크롤 자동 맨 아래 이동 (스트리밍/메시지 추가 시)
from __future__ import annotations

import json
import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from chitchat.services.chat_service import ChatService
from chitchat.ui.async_bridge import AsyncSignalBridge
from chitchat.i18n import tr
from chitchat.ui.theme import COLORS, SPACING
from chitchat.ui.widgets.chat_message_view import ChatMessageView
from chitchat.ui.widgets.token_budget_bar import TokenBudgetBar

logger = logging.getLogger(__name__)


class ChatPage(QWidget):
    """채팅 페이지. 세션 목록 + 메시지 타임라인 + 입력 컴포저 + Inspector.

    [v0.1.2] 스트리밍 실시간 표시, 프로필/페르소나 선택 드롭다운 추가.
    """

    def __init__(self, chat_service: ChatService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._svc = chat_service
        self._cur_session: str | None = None
        self._streaming_buffer = ""
        # [v0.1.2] 스트리밍 중 실시간 업데이트되는 버블 위젯 참조
        self._streaming_view: ChatMessageView | None = None
        # Signal 브리지 생성: 모든 비동기 결과는 Signal로 메인 스레드에 전달
        self._bridge = AsyncSignalBridge(self)
        self._bridge.chunk_received.connect(self._slot_chunk)
        self._bridge.stream_finished.connect(self._slot_finish)
        self._bridge.stream_error.connect(self._slot_error)
        self._setup_ui()
        self._load_sessions()

    def _setup_ui(self) -> None:
        lo = QHBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(0)
        sp = QSplitter(Qt.Orientation.Horizontal)
        lo.addWidget(sp)

        # ━━━ 좌측: 세션 목록 + 프로필/페르소나 선택 ━━━
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(SPACING.md, SPACING.md, SPACING.md, SPACING.md)
        ll.addWidget(QLabel(tr("chat.session_list")))

        self._session_list = QListWidget()
        self._session_list.currentItemChanged.connect(self._on_session_sel)
        ll.addWidget(self._session_list)

        # [v0.1.2] 세션 생성/삭제 버튼 행
        btn_row = QHBoxLayout()
        btn_new = QPushButton(tr("chat.new_session"))
        btn_new.setObjectName("primaryButton")
        btn_new.clicked.connect(self._on_new_session)
        btn_row.addWidget(btn_new)
        btn_del = QPushButton(tr("common.delete"))
        btn_del.setObjectName("dangerButton")
        btn_del.clicked.connect(self._on_delete_session)
        btn_row.addWidget(btn_del)
        ll.addLayout(btn_row)

        # [v0.1.2] ChatProfile 선택 드롭다운 — 사용자가 어떤 AI 설정 조합으로 대화할지 선택
        ll.addWidget(QLabel(tr("chat.profile_label")))
        self._profile_combo = QComboBox()
        self._profile_combo.setPlaceholderText(tr("chat.profile_ph"))
        ll.addWidget(self._profile_combo)

        # [v0.1.2] UserPersona 선택 드롭다운 — 사용자의 역할/성격을 선택
        ll.addWidget(QLabel(tr("chat.persona_label")))
        self._persona_combo = QComboBox()
        self._persona_combo.setPlaceholderText(tr("chat.persona_ph"))
        ll.addWidget(self._persona_combo)

        sp.addWidget(left)

        # ━━━ 중앙: 타임라인 + 컴포저 ━━━
        center = QWidget()
        cl = QVBoxLayout(center)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        # 타임라인 (스크롤 영역)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._timeline = QWidget()
        self._timeline_layout = QVBoxLayout(self._timeline)
        self._timeline_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._timeline_layout.setSpacing(SPACING.xs)
        self._scroll.setWidget(self._timeline)
        self._scroll.setStyleSheet(
            f"QScrollArea {{ border: none; background-color: {COLORS.bg_primary}; }}"
        )
        cl.addWidget(self._scroll, stretch=1)

        # 토큰 예산 바
        self._budget_bar = TokenBudgetBar()
        cl.addWidget(self._budget_bar)

        # 컴포저 (입력 + Send/Stop 버튼)
        composer = QWidget()
        composer.setStyleSheet(
            f"background-color:{COLORS.bg_secondary}; border-top:2px solid {COLORS.border};"
        )
        clo = QHBoxLayout(composer)
        clo.setContentsMargins(SPACING.md, SPACING.sm, SPACING.md, SPACING.sm)

        self._input = QTextEdit()
        self._input.setMaximumHeight(80)
        self._input.setPlaceholderText(tr("chat.input_ph"))
        clo.addWidget(self._input, stretch=1)

        btn_lo = QVBoxLayout()
        self._btn_send = QPushButton(tr("chat.send_btn"))
        self._btn_send.setObjectName("primaryButton")
        self._btn_send.clicked.connect(self._on_send)
        btn_lo.addWidget(self._btn_send)

        self._btn_stop = QPushButton(tr("chat.stop_btn"))
        self._btn_stop.setObjectName("dangerButton")
        self._btn_stop.clicked.connect(self._on_stop)
        self._btn_stop.setEnabled(False)
        btn_lo.addWidget(self._btn_stop)
        clo.addLayout(btn_lo)

        cl.addWidget(composer)
        sp.addWidget(center)

        # ━━━ 우측: Inspector 탭 ━━━
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(SPACING.md, SPACING.md, SPACING.md, SPACING.md)
        tabs = QTabWidget()

        # 세션 정보 탭
        self._info_text = QTextEdit()
        self._info_text.setReadOnly(True)
        tabs.addTab(self._info_text, tr("chat.session_info"))

        # 프롬프트 스냅샷 탭
        self._snapshot_text = QTextEdit()
        self._snapshot_text.setReadOnly(True)
        tabs.addTab(self._snapshot_text, tr("chat.prompt_snapshot"))

        rl.addWidget(tabs)
        sp.addWidget(right)
        sp.setSizes([220, 550, 280])

    # ━━━ 데이터 로드 ━━━

    def _load_sessions(self) -> None:
        """세션 목록과 프로필/페르소나 드롭다운을 갱신한다."""
        self._session_list.clear()
        for s in self._svc.get_all_sessions():
            it = QListWidgetItem(f"[{s.status}] {s.title}")
            it.setData(Qt.ItemDataRole.UserRole, s.id)
            self._session_list.addItem(it)

        # [v0.1.2] 프로필/페르소나 콤보 갱신
        self._refresh_profile_combos()

    def _refresh_profile_combos(self) -> None:
        """ChatProfile과 UserPersona 드롭다운의 항목을 DB에서 다시 로드한다.

        [v0.1.2] 새 세션 생성 시 사용자가 직접 프로필·페르소나를 선택할 수 있도록
        드롭다운 항목을 최신 DB 상태로 유지한다.
        """
        # 채팅 프로필 콤보
        prev_profile = self._profile_combo.currentData()
        self._profile_combo.blockSignals(True)
        self._profile_combo.clear()
        for cp in self._svc.get_available_chat_profiles():
            self._profile_combo.addItem(cp.name, cp.id)
        # 이전 선택 복원
        if prev_profile:
            for i in range(self._profile_combo.count()):
                if self._profile_combo.itemData(i) == prev_profile:
                    self._profile_combo.setCurrentIndex(i)
                    break
        self._profile_combo.blockSignals(False)

        # 사용자 페르소나 콤보
        prev_persona = self._persona_combo.currentData()
        self._persona_combo.blockSignals(True)
        self._persona_combo.clear()
        for up in self._svc.get_available_user_personas():
            self._persona_combo.addItem(up.name, up.id)
        # 이전 선택 복원
        if prev_persona:
            for i in range(self._persona_combo.count()):
                if self._persona_combo.itemData(i) == prev_persona:
                    self._persona_combo.setCurrentIndex(i)
                    break
        self._persona_combo.blockSignals(False)

    # ━━━ 세션 선택 ━━━

    def _on_session_sel(self, c: QListWidgetItem | None, _: QListWidgetItem | None) -> None:
        if not c:
            return
        sid = c.data(Qt.ItemDataRole.UserRole)
        self._cur_session = sid
        self._load_messages(sid)
        # 세션 정보 표시
        s = self._svc.get_session(sid)
        if s:
            self._info_text.setPlainText(
                tr("chat.session_info_fmt",
                   id=s.id, title=s.title, status=s.status,
                   profile_id=s.chat_profile_id,
                   persona_id=s.user_persona_id,
                   created=s.created_at, updated=s.updated_at)
            )

    def _load_messages(self, session_id: str) -> None:
        """세션의 메시지를 타임라인에 표시한다."""
        # 타임라인 초기화
        while self._timeline_layout.count():
            child = self._timeline_layout.takeAt(0)
            w = child.widget() if child else None
            if w:
                w.deleteLater()
        # 메시지 로드
        msgs = self._svc.get_session_messages(session_id)
        for m in msgs:
            view = ChatMessageView(m.role, m.content, m.created_at)
            self._timeline_layout.addWidget(view)
            # 마지막 assistant 메시지의 스냅샷 표시
            if m.role == "assistant" and m.prompt_snapshot_json:
                try:
                    snap = json.loads(m.prompt_snapshot_json)
                    self._snapshot_text.setPlainText(
                        json.dumps(snap, indent=2, ensure_ascii=False)
                    )
                    if "total_tokens" in snap and "budget_tokens" in snap:
                        self._budget_bar.set_budget(snap["total_tokens"], snap["budget_tokens"])
                except Exception:
                    pass
        # [v0.1.2] 스크롤을 맨 아래로
        self._scroll_to_bottom()

    # ━━━ 세션 생성 / 삭제 ━━━

    def _on_new_session(self) -> None:
        """새 세션을 생성한다.

        [v0.1.2] 사용자가 선택한 ChatProfile과 UserPersona를 사용한다.
        드롭다운에서 선택하지 않으면 경고를 표시한다.
        """
        # 드롭다운에서 선택된 프로필/페르소나 확인
        cp_id = self._profile_combo.currentData()
        up_id = self._persona_combo.currentData()

        if not cp_id:
            QMessageBox.warning(self, tr("common.warning"), tr("chat.select_profile"))
            return
        if not up_id:
            QMessageBox.warning(self, tr("common.warning"), tr("chat.select_persona"))
            return

        s = self._svc.create_session(
            title=tr("chat.session_title_fmt", num=self._session_list.count() + 1),
            chat_profile_id=cp_id,
            user_persona_id=up_id,
        )
        self._load_sessions()
        # 새 세션 선택
        for i in range(self._session_list.count()):
            it = self._session_list.item(i)
            if it and it.data(Qt.ItemDataRole.UserRole) == s.id:
                self._session_list.setCurrentRow(i)
                break

    def _on_delete_session(self) -> None:
        """[v0.1.2] 선택된 세션을 삭제한다."""
        if not self._cur_session:
            return
        result = QMessageBox.question(
            self, tr("chat.delete_session_title"), tr("chat.delete_session_msg"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if result == QMessageBox.StandardButton.Yes:
            self._svc.delete_session(self._cur_session)
            self._cur_session = None
            self._load_sessions()
            # 타임라인 초기화
            while self._timeline_layout.count():
                child = self._timeline_layout.takeAt(0)
                w = child.widget() if child else None
                if w:
                    w.deleteLater()

    # ━━━ 메시지 전송 ━━━

    def _on_send(self) -> None:
        text = self._input.toPlainText().strip()
        if not text or not self._cur_session:
            return
        # 사용자 메시지 저장 및 표시
        self._svc.save_user_message(self._cur_session, text)
        self._timeline_layout.addWidget(ChatMessageView("user", text))
        self._input.clear()
        # [v0.1.2] 스트리밍 실시간 표시를 위한 빈 AI 버블 생성
        self._streaming_buffer = ""
        self._streaming_view = ChatMessageView("assistant", "▍")
        self._timeline_layout.addWidget(self._streaming_view)
        self._scroll_to_bottom()
        # UI 상태 전환
        self._btn_send.setEnabled(False)
        self._btn_stop.setEnabled(True)
        # Signal 브리지를 통해 스트리밍 실행 (thread-safe)
        session_id = self._cur_session
        self._bridge.run_stream_in_thread(
            lambda on_chunk, on_finish, on_error:
                self._svc.start_stream(session_id, on_chunk, on_finish, on_error)
        )

    # ━━━ Signal Slots (메인 스레드에서 실행됨, thread-safe) ━━━

    def _slot_chunk(self, delta: str) -> None:
        """스트리밍 청크 수신. 메인 스레드에서 실행됨.

        [v0.1.2] 버퍼에 쌓는 것과 동시에 _streaming_view 위젯의 텍스트를
        실시간으로 갱신하여 사용자에게 AI가 작성 중인 내용을 즉시 보여준다.
        """
        self._streaming_buffer += delta
        if self._streaming_view:
            self._streaming_view.update_content(self._streaming_buffer + "▍")
        self._scroll_to_bottom()

    def _slot_finish(self, full_text: str, usage: object) -> None:
        """스트리밍 완료. 메인 스레드에서 실행됨 → UI 갱신 안전.

        [v0.1.2] 기존 _streaming_view의 내용을 최종 텍스트로 교체하고,
        DB에서 다시 로드하여 스냅샷 등을 표시한다.
        """
        # 스트리밍 뷰의 커서 제거
        if self._streaming_view:
            self._streaming_view.update_content(full_text)
            self._streaming_view = None
        self._btn_send.setEnabled(True)
        self._btn_stop.setEnabled(False)
        # DB에서 다시 로드하여 스냅샷 포함 전체 갱신
        if self._cur_session:
            self._load_messages(self._cur_session)
        self._load_sessions()

    def _slot_error(self, error_msg: str) -> None:
        """스트리밍 에러. 메인 스레드에서 실행됨 → UI 갱신 안전.

        [v0.1.2] 에러 시 스트리밍 뷰를 에러 메시지로 교체한다.
        """
        if self._streaming_view:
            self._streaming_view.update_content(tr("common.error", msg=error_msg))
            self._streaming_view = None
        QMessageBox.warning(self, tr("chat.streaming_error"), error_msg)
        self._btn_send.setEnabled(True)
        self._btn_stop.setEnabled(False)

    def _on_stop(self) -> None:
        """[v0.1.2] 스트리밍 취소. 버퍼에 쌓인 내용까지만 표시한다."""
        self._bridge.cancel_stream()
        if self._streaming_view:
            display = self._streaming_buffer if self._streaming_buffer else tr("chat.cancelled")
            self._streaming_view.update_content(display)
            self._streaming_view = None
        self._btn_send.setEnabled(True)
        self._btn_stop.setEnabled(False)

    # ━━━ 유틸리티 ━━━

    def _scroll_to_bottom(self) -> None:
        """[v0.1.2] 스크롤을 타임라인 맨 아래로 이동한다."""
        sb = self._scroll.verticalScrollBar()
        sb.setValue(sb.maximum())
