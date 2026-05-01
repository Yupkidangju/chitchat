# src/chitchat/i18n/__init__.py
# [v0.3.0] i18n 패키지 초기화
#
# 전역 tr() 함수를 제공하여 UI 문자열의 국제화를 지원한다.
# 사용법: from chitchat.i18n import tr
#         label.setText(tr("nav.chat"))

from chitchat.i18n.translator import Translator

# 모듈 레벨 단축 함수 — 모든 UI 코드에서 이 함수를 사용한다
def tr(key: str, **kwargs: object) -> str:
    """번역 키를 현재 로케일의 문자열로 변환한다.

    Args:
        key: 점(.) 구분 번역 키 (예: "nav.chat", "provider.title")
        **kwargs: format 치환용 키워드 인자 (예: tr("msg.count", count=5))

    Returns:
        번역된 문자열. 키가 없으면 키 자체를 반환한다.
    """
    return Translator.instance().tr(key, **kwargs)
