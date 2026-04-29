# src/chitchat/ui/theme.py
# [v0.1.0b0] 네오-브루탈리즘 디자인 토큰 및 글로벌 스타일시트
#
# designs.md §2에서 정의된 Clean Neo-Brutal 디자인 토큰을 코드로 구현한다.
# 모든 UI 위젯은 이 모듈의 토큰만 참조하고, 하드코딩 색상을 금지한다.
# 디자인 토큰을 변경하면 전체 앱의 룩앤필이 일괄 변경된다.

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ColorToken:
    """색상 토큰. designs.md §2.1에서 정의된 팔레트.

    bg_primary: 메인 배경 (밝은 회색)
    bg_secondary: 카드/패널 배경 (흰색)
    bg_tertiary: 입력 필드 배경
    accent_primary: 주요 강조색 (파란색 계열)
    accent_secondary: 보조 강조색 (보라색 계열)
    accent_success: 성공 상태 (녹색)
    accent_warning: 경고 상태 (주황색)
    accent_danger: 위험/에러 (빨간색)
    text_primary: 본문 텍스트 (거의 검정)
    text_secondary: 보조 텍스트 (짙은 회색)
    text_muted: 비활성 텍스트 (중간 회색)
    border: 네오-브루탈리즘 외곽선 (검정)
    shadow: 하드 그림자 색상
    """
    bg_primary: str = "#F5F5F0"
    bg_secondary: str = "#FFFFFF"
    bg_tertiary: str = "#FAFAF7"
    accent_primary: str = "#4A6CF7"
    accent_secondary: str = "#7C5CFC"
    accent_success: str = "#22C55E"
    accent_warning: str = "#F59E0B"
    accent_danger: str = "#EF4444"
    text_primary: str = "#1A1A1A"
    text_secondary: str = "#4A4A4A"
    text_muted: str = "#9CA3AF"
    border: str = "#1A1A1A"
    shadow: str = "#1A1A1A"


@dataclass(frozen=True)
class SpacingToken:
    """간격 토큰. designs.md §2.2에서 정의된 간격 체계.

    4px 기반 간격 시스템. xs=4, sm=8, md=16, lg=24, xl=32, xxl=48.
    """
    xs: int = 4
    sm: int = 8
    md: int = 16
    lg: int = 24
    xl: int = 32
    xxl: int = 48


@dataclass(frozen=True)
class TypographyToken:
    """타이포그래피 토큰. designs.md §2.3.

    font_family: 기본 폰트 패밀리
    font_size_*: 글꼴 크기 (px)
    font_weight_*: 글꼴 두께
    """
    font_family: str = "'Inter', 'Noto Sans KR', 'Noto Sans JP', sans-serif"
    font_size_xs: int = 11
    font_size_sm: int = 12
    font_size_md: int = 14
    font_size_lg: int = 16
    font_size_xl: int = 20
    font_size_xxl: int = 24
    font_weight_normal: int = 400
    font_weight_medium: int = 500
    font_weight_bold: int = 700


@dataclass(frozen=True)
class BorderToken:
    """테두리 토큰. 네오-브루탈리즘의 핵심 시각 요소.

    width: 테두리 두께 (px)
    radius_sm: 작은 라운딩 (px)
    radius_md: 중간 라운딩 (px)
    shadow_offset: 하드 그림자 오프셋 (px)
    """
    width: int = 2
    radius_sm: int = 4
    radius_md: int = 8
    shadow_offset: int = 4


# 전역 토큰 인스턴스
COLORS = ColorToken()
SPACING = SpacingToken()
TYPOGRAPHY = TypographyToken()
BORDERS = BorderToken()


def build_global_stylesheet() -> str:
    """앱 전역 QSS 스타일시트를 생성한다.

    네오-브루탈리즘 디자인 토큰을 기반으로 모든 위젯의 기본 스타일을 설정한다.
    개별 위젯 파일에서 하드코딩된 색상을 사용하는 것을 방지한다.

    Returns:
        Qt StyleSheet 문자열.
    """
    c = COLORS
    s = SPACING
    t = TYPOGRAPHY
    b = BORDERS

    return f"""
    /* === 전역 기본 === */
    QWidget {{
        font-family: {t.font_family};
        font-size: {t.font_size_md}px;
        color: {c.text_primary};
        background-color: {c.bg_primary};
    }}

    /* === 버튼: 네오-브루탈 스타일 === */
    QPushButton {{
        background-color: {c.bg_secondary};
        color: {c.text_primary};
        border: {b.width}px solid {c.border};
        border-radius: {b.radius_sm}px;
        padding: {s.sm}px {s.md}px;
        font-weight: {t.font_weight_medium};
        font-size: {t.font_size_md}px;
        min-height: 32px;
    }}
    QPushButton:hover {{
        background-color: {c.accent_primary};
        color: {c.bg_secondary};
        border-color: {c.border};
    }}
    QPushButton:pressed {{
        background-color: {c.accent_primary};
        color: {c.bg_secondary};
        border: {b.width}px solid {c.border};
        margin-left: {b.shadow_offset}px;
        margin-top: {b.shadow_offset}px;
    }}
    QPushButton:disabled {{
        background-color: {c.bg_tertiary};
        color: {c.text_muted};
        border-color: {c.text_muted};
    }}

    /* === 주요 액션 버튼 === */
    QPushButton#primaryButton {{
        background-color: {c.accent_primary};
        color: {c.bg_secondary};
        font-weight: {t.font_weight_bold};
    }}
    QPushButton#primaryButton:hover {{
        background-color: {c.accent_secondary};
    }}

    /* === 위험 버튼 === */
    QPushButton#dangerButton {{
        background-color: {c.accent_danger};
        color: {c.bg_secondary};
    }}
    QPushButton#dangerButton:hover {{
        background-color: #DC2626;
    }}

    /* === 입력 필드 === */
    QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: {c.bg_secondary};
        color: {c.text_primary};
        border: {b.width}px solid {c.border};
        border-radius: {b.radius_sm}px;
        padding: {s.sm}px;
        font-size: {t.font_size_md}px;
        selection-background-color: {c.accent_primary};
        selection-color: {c.bg_secondary};
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border-color: {c.accent_primary};
        border-width: {b.width + 1}px;
    }}

    /* === 콤보박스 === */
    QComboBox {{
        background-color: {c.bg_secondary};
        color: {c.text_primary};
        border: {b.width}px solid {c.border};
        border-radius: {b.radius_sm}px;
        padding: {s.sm}px;
        min-height: 32px;
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {c.bg_secondary};
        border: {b.width}px solid {c.border};
        selection-background-color: {c.accent_primary};
        selection-color: {c.bg_secondary};
    }}

    /* === 스핀박스 === */
    QSpinBox, QDoubleSpinBox {{
        background-color: {c.bg_secondary};
        color: {c.text_primary};
        border: {b.width}px solid {c.border};
        border-radius: {b.radius_sm}px;
        padding: {s.sm}px;
        min-height: 32px;
    }}

    /* === 체크박스 === */
    QCheckBox {{
        spacing: {s.sm}px;
        font-size: {t.font_size_md}px;
    }}
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border: {b.width}px solid {c.border};
        border-radius: {b.radius_sm}px;
        background-color: {c.bg_secondary};
    }}
    QCheckBox::indicator:checked {{
        background-color: {c.accent_primary};
        border-color: {c.accent_primary};
    }}

    /* === 리스트 위젯 === */
    QListWidget {{
        background-color: {c.bg_secondary};
        border: {b.width}px solid {c.border};
        border-radius: {b.radius_sm}px;
        outline: none;
    }}
    QListWidget::item {{
        padding: {s.sm}px {s.md}px;
        border-bottom: 1px solid {c.bg_tertiary};
    }}
    QListWidget::item:selected {{
        background-color: {c.accent_primary};
        color: {c.bg_secondary};
    }}
    QListWidget::item:hover {{
        background-color: {c.bg_tertiary};
    }}

    /* === 탭 위젯 === */
    QTabWidget::pane {{
        border: {b.width}px solid {c.border};
        border-radius: {b.radius_sm}px;
        background-color: {c.bg_secondary};
    }}
    QTabBar::tab {{
        background-color: {c.bg_tertiary};
        color: {c.text_secondary};
        border: {b.width}px solid {c.border};
        border-bottom: none;
        padding: {s.sm}px {s.md}px;
        font-weight: {t.font_weight_medium};
    }}
    QTabBar::tab:selected {{
        background-color: {c.bg_secondary};
        color: {c.text_primary};
        font-weight: {t.font_weight_bold};
    }}

    /* === 스크롤바 === */
    QScrollBar:vertical {{
        background-color: {c.bg_primary};
        width: 10px;
        border: none;
    }}
    QScrollBar::handle:vertical {{
        background-color: {c.text_muted};
        border-radius: 5px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background-color: {c.text_secondary};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    /* === 레이블 === */
    QLabel {{
        background-color: transparent;
        color: {c.text_primary};
    }}
    QLabel#sectionTitle {{
        font-size: {t.font_size_xl}px;
        font-weight: {t.font_weight_bold};
        color: {c.text_primary};
    }}
    QLabel#subtitle {{
        font-size: {t.font_size_sm}px;
        color: {c.text_secondary};
    }}
    QLabel#errorLabel {{
        color: {c.accent_danger};
        font-size: {t.font_size_sm}px;
    }}
    QLabel#successLabel {{
        color: {c.accent_success};
        font-size: {t.font_size_sm}px;
    }}

    /* === 그룹박스 === */
    QGroupBox {{
        background-color: {c.bg_secondary};
        border: {b.width}px solid {c.border};
        border-radius: {b.radius_md}px;
        margin-top: 20px;
        padding: {s.md}px;
        padding-top: 28px;
        font-weight: {t.font_weight_bold};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 {s.sm}px;
        color: {c.text_primary};
    }}

    /* === 스플리터 === */
    QSplitter::handle {{
        background-color: {c.border};
        width: 1px;
    }}

    /* === 상태바 === */
    QStatusBar {{
        background-color: {c.bg_secondary};
        border-top: {b.width}px solid {c.border};
        color: {c.text_secondary};
        font-size: {t.font_size_sm}px;
    }}

    /* === 메뉴 === */
    QMenuBar {{
        background-color: {c.bg_secondary};
        border-bottom: {b.width}px solid {c.border};
    }}
    QMenuBar::item:selected {{
        background-color: {c.accent_primary};
        color: {c.bg_secondary};
    }}
    """
