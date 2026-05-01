# tests/test_i18n.py
# [v0.3.0] i18n 시스템 테스트
#
# Translator 싱글톤, 로케일 변경, tr() 함수, 폴백 동작 등을 검증한다.

from __future__ import annotations

import json
from pathlib import Path

import pytest

from chitchat.i18n import tr
from chitchat.i18n.translator import (
    DEFAULT_LOCALE,
    LOCALE_DISPLAY_NAMES,
    SUPPORTED_LOCALES,
    Translator,
)


@pytest.fixture(autouse=True)
def _reset_translator() -> None:
    """각 테스트 전에 Translator 싱글톤을 초기화한다."""
    Translator.reset()


# --- Translator 싱글톤 ---


def test_translator_singleton() -> None:
    """Translator.instance()가 동일한 인스턴스를 반환하는지 검증."""
    t1 = Translator.instance()
    t2 = Translator.instance()
    assert t1 is t2


def test_translator_reset() -> None:
    """Translator.reset()이 인스턴스를 초기화하는지 검증."""
    t1 = Translator.instance()
    Translator.reset()
    t2 = Translator.instance()
    assert t1 is not t2


# --- 기본 로케일 ---


def test_default_locale_is_ko() -> None:
    """초기 로케일이 한국어(ko)인지 검증."""
    t = Translator.instance()
    assert t.get_locale() == "ko"


# --- 로케일 변경 ---


def test_set_locale_valid() -> None:
    """유효한 로케일로 변경 시 정상 동작 검증."""
    t = Translator.instance()
    t.set_locale("en")
    assert t.get_locale() == "en"


def test_set_locale_invalid_fallback() -> None:
    """잘못된 로케일 지정 시 기본 로케일로 폴백하는지 검증."""
    t = Translator.instance()
    t.set_locale("xx_INVALID")
    assert t.get_locale() == DEFAULT_LOCALE


# --- tr() 함수 ---


def test_tr_existing_key() -> None:
    """존재하는 키가 번역된 문자열을 반환하는지 검증."""
    t = Translator.instance()
    t.set_locale("ko")
    result = tr("nav.chat")
    assert "채팅" in result


def test_tr_missing_key_returns_key() -> None:
    """존재하지 않는 키를 요청하면 키 자체를 반환하는지 검증."""
    result = tr("nonexistent.key.12345")
    assert result == "nonexistent.key.12345"


def test_tr_with_kwargs() -> None:
    """format 치환이 정상적으로 동작하는지 검증."""
    t = Translator.instance()
    t.set_locale("ko")
    result = tr("provider.saved", name="TestProvider")
    assert "TestProvider" in result
    assert "✅" in result


def test_tr_locale_switch() -> None:
    """로케일 전환 후 번역이 변경되는지 검증."""
    t = Translator.instance()
    t.set_locale("ko")
    ko_result = tr("common.save")
    t.set_locale("en")
    en_result = tr("common.save")
    assert "저장" in ko_result
    assert "Save" in en_result
    assert ko_result != en_result


# --- 번역 사전 파일 무결성 ---


def test_all_locale_files_exist() -> None:
    """지원 로케일별 JSON 파일이 존재하는지 검증."""
    locales_dir = Path(__file__).parent.parent / "src" / "chitchat" / "i18n" / "locales"
    for locale in SUPPORTED_LOCALES:
        locale_file = locales_dir / f"{locale}.json"
        assert locale_file.exists(), f"번역 파일 누락: {locale_file}"


def test_ko_en_key_parity() -> None:
    """모든 로케일 사전의 키가 ko.json과 동일한지 검증."""
    locales_dir = Path(__file__).parent.parent / "src" / "chitchat" / "i18n" / "locales"
    with open(locales_dir / "ko.json", encoding="utf-8") as f:
        ko_keys = set(json.load(f).keys())
    for locale in SUPPORTED_LOCALES:
        if locale == "ko":
            continue
        with open(locales_dir / f"{locale}.json", encoding="utf-8") as f:
            other_keys = set(json.load(f).keys())
        missing = ko_keys - other_keys
        extra = other_keys - ko_keys
        assert not missing, f"{locale}.json에 누락된 키: {missing}"
        assert not extra, f"{locale}.json에 불필요한 키: {extra}"


def test_locale_display_names_complete() -> None:
    """LOCALE_DISPLAY_NAMES가 모든 지원 로케일을 포함하는지 검증."""
    for locale in SUPPORTED_LOCALES:
        assert locale in LOCALE_DISPLAY_NAMES, f"LOCALE_DISPLAY_NAMES에 누락: {locale}"


def test_available_locales() -> None:
    """available_locales()가 SUPPORTED_LOCALES와 동일한지 검증."""
    t = Translator.instance()
    assert t.available_locales() == list(SUPPORTED_LOCALES)
