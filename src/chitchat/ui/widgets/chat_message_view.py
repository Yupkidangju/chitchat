# src/chitchat/ui/widgets/chat_message_view.py
# [v0.1.0b0] 채팅 메시지 버블 위젯
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget
from chitchat.i18n import tr
from chitchat.ui.theme import COLORS, SPACING, TYPOGRAPHY


class ChatMessageView(QWidget):
    """단일 채팅 메시지 버블.

    [v0.1.2] update_content() 메서드 추가로 스트리밍 중 실시간 내용 갱신 지원.
    """
    def __init__(self, role: str, content: str, timestamp: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._role = role
        # [v0.1.2] 메시지 QLabel을 인스턴스 변수로 저장 (실시간 갱신용)
        self._msg_label: QLabel | None = None
        self._setup_ui(role, content, timestamp)

    def update_content(self, new_content: str) -> None:
        """메시지 내용을 동적으로 갱신한다.

        [v0.1.2] 스트리밍 중 매 청크마다 호출되어 버블 텍스트를 실시간으로 교체한다.
        """
        if self._msg_label:
            self._msg_label.setText(new_content)

    def _setup_ui(self, role: str, content: str, timestamp: str) -> None:
        lo = QHBoxLayout(self)
        lo.setContentsMargins(SPACING.sm, SPACING.xs, SPACING.sm, SPACING.xs)
        is_user = role == "user"
        if is_user:
            lo.addStretch()
        bubble = QWidget()
        bl = QVBoxLayout(bubble)
        bl.setContentsMargins(SPACING.md, SPACING.sm, SPACING.md, SPACING.sm)
        # 역할 레이블
        role_label = QLabel(tr("chat.me") if is_user else "🤖 AI")
        role_label.setStyleSheet(f"font-size:{TYPOGRAPHY.font_size_xs}px;color:{COLORS.text_muted};background:transparent;")
        bl.addWidget(role_label)
        # 메시지 내용
        msg = QLabel(content)
        msg.setWordWrap(True)
        msg.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        msg.setStyleSheet(f"font-size:{TYPOGRAPHY.font_size_md}px;background:transparent;color:{COLORS.text_primary};")
        bl.addWidget(msg)
        # [v0.1.2] 인스턴스 변수에 저장 (실시간 갱신용)
        self._msg_label = msg
        # 타임스탬프
        if timestamp:
            ts = QLabel(timestamp)
            ts.setStyleSheet(f"font-size:{TYPOGRAPHY.font_size_xs}px;color:{COLORS.text_muted};background:transparent;")
            bl.addWidget(ts)
        # 버블 스타일
        bg = COLORS.accent_primary if is_user else COLORS.bg_secondary
        fg = COLORS.bg_secondary if is_user else COLORS.text_primary
        bubble.setStyleSheet(f"""
            QWidget {{ background-color:{bg}; border:2px solid {COLORS.border};
            border-radius:12px; }}
            QLabel {{ color:{fg}; }}
        """)
        bubble.setMaximumWidth(600)
        lo.addWidget(bubble)
        if not is_user:
            lo.addStretch()

