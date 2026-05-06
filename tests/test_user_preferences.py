# tests/test_user_preferences.py
# [v0.3.0] UserPreferences 설정 영속화 테스트
#
# settings.json 저장/로드, 기본값 폴백, 싱글톤 동작을 검증한다.

from __future__ import annotations

import json
from pathlib import Path

import pytest

from chitchat.config.user_preferences import UserPreferences


@pytest.fixture(autouse=True)
def _reset_prefs() -> None:
    """각 테스트 전에 UserPreferences 싱글톤을 초기화한다."""
    UserPreferences.reset()


@pytest.fixture()
def tmp_app_dir(tmp_path: Path) -> Path:
    """임시 앱 데이터 디렉토리를 생성한다."""
    app_dir = tmp_path / "chitchat_test"
    app_dir.mkdir()
    return app_dir


# --- 싱글톤 ---


def test_singleton() -> None:
    """UserPreferences.instance()가 동일한 인스턴스를 반환하는지 검증."""
    p1 = UserPreferences.instance()
    p2 = UserPreferences.instance()
    assert p1 is p2


def test_reset() -> None:
    """UserPreferences.reset()이 인스턴스를 초기화하는지 검증."""
    p1 = UserPreferences.instance()
    UserPreferences.reset()
    p2 = UserPreferences.instance()
    assert p1 is not p2


# --- 기본값 ---


def test_default_values() -> None:
    """초기 기본값이 올바른지 검증."""
    prefs = UserPreferences.instance()
    assert prefs.ui_locale == "ko"
    assert prefs.vibe_output_language == "ko"


# --- 저장 및 로드 ---


def test_save_and_load(tmp_app_dir: Path) -> None:
    """설정 저장 후 로드하면 동일한 값이 복원되는지 검증."""
    prefs = UserPreferences.instance()
    prefs.ui_locale = "en"
    prefs.vibe_output_language = "en"
    prefs.save(tmp_app_dir)

    # 새 인스턴스로 로드
    UserPreferences.reset()
    prefs2 = UserPreferences.instance()
    prefs2.load(tmp_app_dir)

    assert prefs2.ui_locale == "en"
    assert prefs2.vibe_output_language == "en"


def test_load_missing_file(tmp_app_dir: Path) -> None:
    """설정 파일이 없으면 기본값을 유지하는지 검증."""
    prefs = UserPreferences.instance()
    prefs.load(tmp_app_dir)
    assert prefs.ui_locale == "ko"
    assert prefs.vibe_output_language == "ko"


def test_load_corrupted_file(tmp_app_dir: Path) -> None:
    """깨진 설정 파일이면 기본값을 유지하는지 검증."""
    settings_file = tmp_app_dir / "settings.json"
    settings_file.write_text("NOT VALID JSON!!!", encoding="utf-8")

    prefs = UserPreferences.instance()
    prefs.load(tmp_app_dir)
    assert prefs.ui_locale == "ko"


def test_load_partial_settings(tmp_app_dir: Path) -> None:
    """일부 키만 있는 설정 파일에서 나머지는 기본값으로 폴백하는지 검증."""
    settings_file = tmp_app_dir / "settings.json"
    settings_file.write_text(
        json.dumps({"ui_locale": "ja"}),
        encoding="utf-8",
    )

    prefs = UserPreferences.instance()
    prefs.load(tmp_app_dir)
    assert prefs.ui_locale == "ja"
    assert prefs.vibe_output_language == "ko"  # 기본값


def test_save_creates_directory(tmp_path: Path) -> None:
    """저장 시 존재하지 않는 디렉토리를 자동으로 생성하는지 검증."""
    nested_dir = tmp_path / "a" / "b" / "c"
    prefs = UserPreferences.instance()
    prefs.save(nested_dir)

    settings_file = nested_dir / "settings.json"
    assert settings_file.exists()


# --- [v1.0.0] 확장 설정 필드 ---


def test_extended_defaults() -> None:
    """[v1.0.0] 확장 설정 필드의 기본값 검증."""
    prefs = UserPreferences.instance()
    assert prefs.theme == "dark"
    assert prefs.font_size == "medium"
    assert prefs.streaming_enabled is True
    assert prefs.default_provider_id == ""


def test_extended_setters() -> None:
    """[v1.0.0] 확장 설정 필드의 setter 검증."""
    prefs = UserPreferences.instance()
    prefs.theme = "dark"
    prefs.font_size = "large"
    prefs.streaming_enabled = False
    prefs.default_provider_id = "prov_abc"

    assert prefs.theme == "dark"
    assert prefs.font_size == "large"
    assert prefs.streaming_enabled is False
    assert prefs.default_provider_id == "prov_abc"


def test_extended_save_and_load(tmp_app_dir: Path) -> None:
    """[v1.0.0] 확장 설정 필드의 저장/로드 검증."""
    prefs = UserPreferences.instance()
    prefs.theme = "dark"
    prefs.font_size = "small"
    prefs.streaming_enabled = False
    prefs.default_provider_id = "prov_xyz"
    prefs.save(tmp_app_dir)

    UserPreferences.reset()
    prefs2 = UserPreferences.instance()
    prefs2.load(tmp_app_dir)

    assert prefs2.theme == "dark"
    assert prefs2.font_size == "small"
    assert prefs2.streaming_enabled is False
    assert prefs2.default_provider_id == "prov_xyz"


def test_reset_restores_defaults() -> None:
    """[v1.0.0] reset() 후 확장 필드가 기본값으로 복원되는지 검증."""
    prefs = UserPreferences.instance()
    prefs.theme = "dark"
    prefs.streaming_enabled = False

    UserPreferences.reset()
    prefs2 = UserPreferences.instance()

    assert prefs2.theme == "dark"
    assert prefs2.streaming_enabled is True

