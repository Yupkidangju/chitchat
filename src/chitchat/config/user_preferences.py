# src/chitchat/config/user_preferences.py
# [v0.3.0] 사용자 설정 영속화
#
# app_data_dir/settings.json에 사용자 설정을 평문 JSON으로 저장한다.
# API Key는 OS keyring(key_store.py)으로 별도 관리되므로 이 파일에 포함하지 않는다.
# 민감 정보가 아니므로 암호화하지 않는다.
#
# 지원 설정:
# - ui_locale: UI 표시 언어 (ko, en, ja, zh_tw, zh_cn)
# - vibe_output_language: Vibe Fill AI 출력 언어 (ko, en)
# - theme: 테마 (dark, light) — v1.0.0에서 이중 팔레트 지원
# - font_size: UI 폰트 크기 (small, medium, large)
# - streaming_enabled: 스트리밍 채팅 사용 여부
# - default_provider_id: 기본 Provider 프로필 ID

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# 설정 파일명
_SETTINGS_FILENAME = "settings.json"

# 기본값
_DEFAULTS: dict[str, str] = {
    "ui_locale": "ko",
    "vibe_output_language": "ko",
    "theme": "dark",
    "font_size": "medium",
    "streaming_enabled": "true",
    "default_provider_id": "",
}


class UserPreferences:
    """사용자 설정 관리 클래스 (싱글톤).

    app_data_dir/settings.json에 평문 JSON으로 저장/로드한다.
    설정값이 없거나 파일이 깨진 경우 기본값으로 폴백한다.
    """

    _instance: UserPreferences | None = None

    def __init__(self) -> None:
        self._data: dict[str, str] = dict(_DEFAULTS)
        self._app_data_dir: Path | None = None

    @classmethod
    def instance(cls) -> UserPreferences:
        """싱글톤 인스턴스를 반환한다."""
        if cls._instance is None:
            cls._instance = UserPreferences()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """싱글톤 인스턴스를 초기화한다 (테스트용)."""
        cls._instance = None

    @property
    def ui_locale(self) -> str:
        """UI 표시 언어 코드를 반환한다 (예: "ko", "en")."""
        return self._data.get("ui_locale", _DEFAULTS["ui_locale"])

    @ui_locale.setter
    def ui_locale(self, value: str) -> None:
        """UI 표시 언어 코드를 설정한다."""
        self._data["ui_locale"] = value

    @property
    def vibe_output_language(self) -> str:
        """Vibe Fill AI 출력 언어 코드를 반환한다 (예: "ko", "en")."""
        return self._data.get("vibe_output_language", _DEFAULTS["vibe_output_language"])

    @vibe_output_language.setter
    def vibe_output_language(self, value: str) -> None:
        """Vibe Fill AI 출력 언어 코드를 설정한다."""
        self._data["vibe_output_language"] = value

    # [v1.0.0] 확장 설정 필드

    @property
    def theme(self) -> str:
        """테마를 반환한다 (light, dark)."""
        return self._data.get("theme", _DEFAULTS["theme"])

    @theme.setter
    def theme(self, value: str) -> None:
        """테마를 설정한다."""
        self._data["theme"] = value

    @property
    def font_size(self) -> str:
        """폰트 크기를 반환한다 (small, medium, large)."""
        return self._data.get("font_size", _DEFAULTS["font_size"])

    @font_size.setter
    def font_size(self, value: str) -> None:
        """폰트 크기를 설정한다."""
        self._data["font_size"] = value

    @property
    def streaming_enabled(self) -> bool:
        """스트리밍 사용 여부를 반환한다."""
        return self._data.get("streaming_enabled", "true") == "true"

    @streaming_enabled.setter
    def streaming_enabled(self, value: bool) -> None:
        """스트리밍 사용 여부를 설정한다."""
        self._data["streaming_enabled"] = "true" if value else "false"

    @property
    def default_provider_id(self) -> str:
        """기본 Provider ID를 반환한다."""
        return self._data.get("default_provider_id", "")

    @default_provider_id.setter
    def default_provider_id(self, value: str) -> None:
        """기본 Provider ID를 설정한다."""
        self._data["default_provider_id"] = value

    def load(self, app_data_dir: Path) -> None:
        """설정 파일을 로드한다.

        파일이 없거나 파싱 실패 시 기본값을 유지한다.

        Args:
            app_data_dir: 앱 데이터 디렉토리 경로.
        """
        self._app_data_dir = app_data_dir
        settings_file = app_data_dir / _SETTINGS_FILENAME

        if not settings_file.exists():
            logger.info("설정 파일 없음. 기본값 사용: %s", settings_file)
            return

        try:
            with open(settings_file, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                # 기본값과 병합 — 파일에 없는 키는 기본값 유지
                for key in _DEFAULTS:
                    if key in data and isinstance(data[key], str):
                        self._data[key] = data[key]
                logger.info("설정 로드 완료: %s", settings_file)
            else:
                logger.warning("설정 파일이 JSON 객체가 아님: %s", settings_file)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("설정 파일 로드 실패: %s — %s", settings_file, e)

    def save(self, app_data_dir: Path | None = None) -> None:
        """설정 파일을 저장한다.

        Args:
            app_data_dir: 앱 데이터 디렉토리 경로. None이면 마지막 load() 경로 사용.
        """
        target_dir = app_data_dir or self._app_data_dir
        if target_dir is None:
            logger.warning("설정 저장 실패: app_data_dir이 지정되지 않음.")
            return

        settings_file = target_dir / _SETTINGS_FILENAME
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            with open(settings_file, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
            logger.info("설정 저장 완료: %s", settings_file)
        except OSError as e:
            logger.warning("설정 저장 실패: %s — %s", settings_file, e)
