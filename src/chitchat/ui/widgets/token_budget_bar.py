# src/chitchat/ui/widgets/token_budget_bar.py
# [v0.1.0b0] 토큰 예산 시각화 바
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor
from PySide6.QtWidgets import QWidget
from chitchat.ui.theme import COLORS


class TokenBudgetBar(QWidget):
    """토큰 예산 시각화 바. 사용량/전체를 가로 바로 표시한다."""
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(24)
        self._used = 0
        self._total = 1
        self._label = ""

    def set_budget(self, used: int, total: int) -> None:
        self._used = used
        self._total = max(total, 1)
        ratio = self._used / self._total
        self._label = f"{self._used:,} / {self._total:,} ({ratio:.0%})"
        self.update()

    def paintEvent(self, _event: object) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        # 배경
        p.setBrush(QColor(COLORS.bg_tertiary))
        p.setPen(QColor(COLORS.border))
        p.drawRoundedRect(0, 0, w, h, 4, 4)
        # 사용량 바
        ratio = min(self._used / self._total, 1.0)
        bar_w = int(w * ratio)
        color = COLORS.accent_success if ratio < 0.7 else (COLORS.accent_warning if ratio < 0.9 else COLORS.accent_danger)
        p.setBrush(QColor(color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, bar_w, h, 4, 4)
        # 텍스트
        p.setPen(QColor(COLORS.text_primary))
        p.drawText(0, 0, w, h, Qt.AlignmentFlag.AlignCenter, self._label)
        p.end()
