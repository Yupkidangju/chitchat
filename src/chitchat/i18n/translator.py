# src/chitchat/i18n/translator.py
# [v0.3.0] JSON 기반 경량 i18n 번역 엔진
#
# Qt의 QTranslator/.ts/.qm 대신 JSON 사전을 사용하는 경량 i18n 시스템.
# 장점: PyInstaller 번들링이 간단하고, 사용자가 직접 번역 파일을 편집 가능.
#
# 키 규칙: "페이지명.항목" 형식 (예: "nav.chat", "provider.save_btn")
# 키가 사전에 없으면 키 문자열 자체를 반환하여 UI 크래시를 방지한다.

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# 지원 로케일 목록 (순서: 한 / 영 / 일 / 중(번체) / 중(간체))
SUPPORTED_LOCALES = ["ko", "en", "ja", "zh_tw", "zh_cn"]

# 로케일별 표시 이름 (UI 드롭다운에 사용)
LOCALE_DISPLAY_NAMES: dict[str, str] = {
    "ko": "한국어",
    "en": "English",
    "ja": "日本語",
    "zh_tw": "繁體中文",
    "zh_cn": "简体中文",
}

# 기본 로케일
DEFAULT_LOCALE = "ko"

# 번역 사전 파일 경로 (패키지 내장)
_LOCALES_DIR = Path(__file__).parent / "locales"


class Translator:
    """JSON 기반 경량 번역 엔진 (싱글톤).

    set_locale()으로 로케일을 변경하면 해당 로케일의 JSON 사전을 로드한다.
    tr(key)로 번역된 문자열을 조회한다.
    """

    _instance: Translator | None = None

    def __init__(self) -> None:
        # 현재 로케일과 로드된 번역 사전
        self._locale: str = DEFAULT_LOCALE
        self._dict: dict[str, str] = {}
        # 초기 로케일 로드
        self._load_locale(self._locale)

    @classmethod
    def instance(cls) -> Translator:
        """싱글톤 인스턴스를 반환한다."""
        if cls._instance is None:
            cls._instance = Translator()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """싱글톤 인스턴스를 초기화한다 (테스트용)."""
        cls._instance = None

    def get_locale(self) -> str:
        """현재 로케일 코드를 반환한다."""
        return self._locale

    def set_locale(self, locale: str) -> None:
        """로케일을 변경하고 해당 사전을 로드한다.

        지원하지 않는 로케일이면 기본 로케일(ko)로 폴백한다.

        Args:
            locale: 로케일 코드 (예: "ko", "en", "ja", "zh_tw", "zh_cn")
        """
        if locale not in SUPPORTED_LOCALES:
            logger.warning(
                "지원하지 않는 로케일 '%s'. 기본 로케일 '%s'로 폴백합니다.",
                locale, DEFAULT_LOCALE,
            )
            locale = DEFAULT_LOCALE
        self._locale = locale
        self._load_locale(locale)
        logger.info("로케일 변경: %s", locale)

    def tr(self, key: str, **kwargs: Any) -> str:
        """번역 키를 현재 로케일의 문자열로 변환한다.

        키가 사전에 없으면 키 문자열 자체를 반환하여 UI 크래시를 방지한다.
        kwargs가 있으면 str.format()으로 치환한다.

        Args:
            key: 점(.) 구분 번역 키.
            **kwargs: format 치환용 키워드 인자.

        Returns:
            번역된 문자열.
        """
        value = self._dict.get(key, key)
        if kwargs:
            try:
                value = value.format(**kwargs)
            except (KeyError, IndexError):
                # format 치환 실패 시 원본 반환
                logger.warning("번역 문자열 format 실패: key=%s, kwargs=%s", key, kwargs)
        return value

    def available_locales(self) -> list[str]:
        """사용 가능한 로케일 코드 목록을 반환한다."""
        return list(SUPPORTED_LOCALES)

    def _load_locale(self, locale: str) -> None:
        """지정된 로케일의 JSON 사전 파일을 로드한다.

        파일이 없거나 파싱 실패 시 빈 사전으로 폴백한다.

        Args:
            locale: 로케일 코드.
        """
        locale_file = _LOCALES_DIR / f"{locale}.json"
        if not locale_file.exists():
            logger.warning("번역 파일을 찾을 수 없음: %s", locale_file)
            self._dict = {}
            return

        try:
            with open(locale_file, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                self._dict = data
                logger.debug("번역 사전 로드 완료: %s (%d개 키)", locale, len(data))
            else:
                logger.warning("번역 파일이 JSON 객체가 아님: %s", locale_file)
                self._dict = {}
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("번역 파일 로드 실패: %s — %s", locale_file, e)
            self._dict = {}
