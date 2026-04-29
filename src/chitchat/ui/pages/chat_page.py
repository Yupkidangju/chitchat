# src/chitchat/ui/pages/chat_page.py
# [v0.1.0b0] 채팅 페이지: 세션 리스트 + 타임라인 + 컴포저 + Inspector
#
# [v0.1.0b0 Remediation] Signal 브리지로 thread-safe UI 갱신 적용.
# worker 스레드에서 직접 QWidget을 건드리지 않고, Signal.emit()으로 메인 스레드에 전달.
from __future__ import annotations
import json
import logging
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMessageBox, QPushButton, QScrollArea, QSplitter, QTabWidget,
    QTextEdit, QVBoxLayout, QWidget,
)
from chitchat.services.chat_service import ChatService
from chitchat.ui.async_bridge import AsyncSignalBridge
from chitchat.ui.theme import COLORS, SPACING
from chitchat.ui.widgets.chat_message_view import ChatMessageView
from chitchat.ui.widgets.token_budget_bar import TokenBudgetBar

logger = logging.getLogger(__name__)


class ChatPage(QWidget):
    """채팅 페이지. 세션 목록 + 메시지 타임라인 + 입력 컴포저 + Inspector."""
    def __init__(self, chat_service: ChatService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._svc = chat_service
        self._cur_session: str | None = None
        self._streaming_buffer = ""
        # Signal 브리지 생성: 모든 비동기 결과는 Signal로 메인 스레드에 전달
        self._bridge = AsyncSignalBridge(self)
        self._bridge.chunk_received.connect(self._slot_chunk)
        self._bridge.stream_finished.connect(self._slot_finish)
        self._bridge.stream_error.connect(self._slot_error)
        self._setup_ui()
        self._load_sessions()

    def _setup_ui(self) -> None:
        lo = QHBoxLayout(self); lo.setContentsMargins(0,0,0,0); lo.setSpacing(0)
        sp = QSplitter(Qt.Orientation.Horizontal); lo.addWidget(sp)

        # 좌측: 세션 목록
        left = QWidget(); ll = QVBoxLayout(left)
        ll.setContentsMargins(SPACING.md, SPACING.md, SPACING.md, SPACING.md)
        ll.addWidget(QLabel("💬 세션 목록"))
        self._session_list = QListWidget()
        self._session_list.currentItemChanged.connect(self._on_session_sel)
        ll.addWidget(self._session_list)
        btn_new = QPushButton("+ 새 세션"); btn_new.setObjectName("primaryButton")
        btn_new.clicked.connect(self._on_new_session); ll.addWidget(btn_new)
        sp.addWidget(left)

        # 중앙: 타임라인 + 컴포저
        center = QWidget(); cl = QVBoxLayout(center)
        cl.setContentsMargins(0,0,0,0); cl.setSpacing(0)
        # 타임라인 (스크롤 영역)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        self._timeline = QWidget()
        self._timeline_layout = QVBoxLayout(self._timeline)
        self._timeline_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._timeline_layout.setSpacing(SPACING.xs)
        scroll.setWidget(self._timeline)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background-color: {COLORS.bg_primary}; }}")
        cl.addWidget(scroll, stretch=1)
        # 토큰 예산 바
        self._budget_bar = TokenBudgetBar()
        cl.addWidget(self._budget_bar)
        # 컴포저 (입력 + Send/Stop 버튼)
        composer = QWidget()
        composer.setStyleSheet(f"background-color:{COLORS.bg_secondary}; border-top:2px solid {COLORS.border};")
        clo = QHBoxLayout(composer)
        clo.setContentsMargins(SPACING.md, SPACING.sm, SPACING.md, SPACING.sm)
        self._input = QTextEdit()
        self._input.setMaximumHeight(80)
        self._input.setPlaceholderText("메시지를 입력하세요...")
        clo.addWidget(self._input, stretch=1)
        btn_lo = QVBoxLayout()
        self._btn_send = QPushButton("📤 Send"); self._btn_send.setObjectName("primaryButton")
        self._btn_send.clicked.connect(self._on_send); btn_lo.addWidget(self._btn_send)
        self._btn_stop = QPushButton("⏹ Stop"); self._btn_stop.setObjectName("dangerButton")
        self._btn_stop.clicked.connect(self._on_stop); self._btn_stop.setEnabled(False)
        btn_lo.addWidget(self._btn_stop); clo.addLayout(btn_lo)
        cl.addWidget(composer)
        sp.addWidget(center)

        # 우측: Inspector 탭
        right = QWidget(); rl = QVBoxLayout(right)
        rl.setContentsMargins(SPACING.md, SPACING.md, SPACING.md, SPACING.md)
        tabs = QTabWidget()
        # 세션 정보 탭
        self._info_text = QTextEdit(); self._info_text.setReadOnly(True)
        tabs.addTab(self._info_text, "세션 정보")
        # 프롬프트 스냅샷 탭
        self._snapshot_text = QTextEdit(); self._snapshot_text.setReadOnly(True)
        tabs.addTab(self._snapshot_text, "프롬프트 스냅샷")
        rl.addWidget(tabs)
        sp.addWidget(right)
        sp.setSizes([220, 550, 280])

    def _load_sessions(self) -> None:
        self._session_list.clear()
        for s in self._svc.get_all_sessions():
            it = QListWidgetItem(f"[{s.status}] {s.title}")
            it.setData(Qt.ItemDataRole.UserRole, s.id)
            self._session_list.addItem(it)

    def _on_session_sel(self, c: QListWidgetItem | None, _: QListWidgetItem | None) -> None:
        if not c: return
        sid = c.data(Qt.ItemDataRole.UserRole)
        self._cur_session = sid
        self._load_messages(sid)
        # 세션 정보 표시
        s = self._svc.get_session(sid)
        if s:
            self._info_text.setPlainText(
                f"ID: {s.id}\n제목: {s.title}\n상태: {s.status}\n"
                f"프로필: {s.chat_profile_id}\n페르소나: {s.user_persona_id}\n"
                f"생성: {s.created_at}\n수정: {s.updated_at}"
            )

    def _load_messages(self, session_id: str) -> None:
        # 타임라인 초기화
        while self._timeline_layout.count():
            child = self._timeline_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        # 메시지 로드
        msgs = self._svc.get_session_messages(session_id)
        for m in msgs:
            view = ChatMessageView(m.role, m.content, m.created_at)
            self._timeline_layout.addWidget(view)
            # 마지막 assistant 메시지의 스냅샷 표시
            if m.role == "assistant" and m.prompt_snapshot_json:
                try:
                    snap = json.loads(m.prompt_snapshot_json)
                    self._snapshot_text.setPlainText(json.dumps(snap, indent=2, ensure_ascii=False))
                    if "total_tokens" in snap and "budget_tokens" in snap:
                        self._budget_bar.set_budget(snap["total_tokens"], snap["budget_tokens"])
                except Exception:
                    pass

    def _on_new_session(self) -> None:
        # ChatService를 통해 프로필/페르소나 존재 여부 확인
        profiles = self._svc.get_available_chat_profiles()
        personas = self._svc.get_available_user_personas()
        if not profiles or not personas:
            QMessageBox.warning(self, "경고", "채팅 프로필과 사용자 페르소나를 먼저 생성하세요.")
            return
        s = self._svc.create_session(
            title=f"세션 #{self._session_list.count() + 1}",
            chat_profile_id=profiles[0].id,
            user_persona_id=personas[0].id,
        )
        self._load_sessions()
        # 새 세션 선택
        for i in range(self._session_list.count()):
            it = self._session_list.item(i)
            if it and it.data(Qt.ItemDataRole.UserRole) == s.id:
                self._session_list.setCurrentRow(i)
                break

    def _on_send(self) -> None:
        text = self._input.toPlainText().strip()
        if not text or not self._cur_session: return
        # 사용자 메시지 저장 및 표시
        self._svc.save_user_message(self._cur_session, text)
        self._timeline_layout.addWidget(ChatMessageView("user", text))
        self._input.clear()
        # UI 상태 전환
        self._btn_send.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._streaming_buffer = ""
        # Signal 브리지를 통해 스트리밍 실행 (thread-safe)
        session_id = self._cur_session
        self._bridge.run_stream_in_thread(
            lambda on_chunk, on_finish, on_error:
                self._svc.start_stream(session_id, on_chunk, on_finish, on_error)
        )

    # --- Signal Slots (메인 스레드에서 실행됨, thread-safe) ---

    def _slot_chunk(self, delta: str) -> None:
        """스트리밍 청크 수신. 메인 스레드에서 실행됨."""
        self._streaming_buffer += delta

    def _slot_finish(self, full_text: str, usage: object) -> None:
        """스트리밍 완료. 메인 스레드에서 실행됨 → UI 갱신 안전."""
        self._timeline_layout.addWidget(ChatMessageView("assistant", full_text))
        self._btn_send.setEnabled(True)
        self._btn_stop.setEnabled(False)
        if self._cur_session:
            self._load_messages(self._cur_session)
        self._load_sessions()

    def _slot_error(self, error_msg: str) -> None:
        """스트리밍 에러. 메인 스레드에서 실행됨 → UI 갱신 안전."""
        QMessageBox.warning(self, "스트리밍 오류", error_msg)
        self._btn_send.setEnabled(True)
        self._btn_stop.setEnabled(False)

    def _on_stop(self) -> None:
        # thread-safe 취소: loop.call_soon_threadsafe(task.cancel)
        self._bridge.cancel_stream()
        self._btn_send.setEnabled(True)
        self._btn_stop.setEnabled(False)
