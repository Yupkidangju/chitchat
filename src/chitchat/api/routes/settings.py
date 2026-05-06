# src/chitchat/api/routes/settings.py
# [v1.0.0] 사용자 설정 REST API
#
# 언어 설정, 테마, 폰트 크기, 스트리밍 사용 등 사용자 환경설정을 관리한다.
# [v1.0.0] DD-12 설정 페이지 범위 구현:
# - 언어 설정 (UI 로케일, Vibe Fill 출력)
# - 표시 설정 (테마, 폰트 크기)
# - 일반 설정 (스트리밍, 기본 Provider)
# - 데이터 관리 (앱 데이터 경로 표시, 설정 초기화)

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from chitchat.config.user_preferences import UserPreferences
from chitchat.i18n.translator import Translator

logger = logging.getLogger(__name__)

router = APIRouter()


class SettingsResponse(BaseModel):
    """현재 설정 응답."""
    ui_locale: str
    vibe_output_language: str
    # [v1.0.0] 확장 설정 필드
    theme: str
    font_size: str
    streaming_enabled: bool
    default_provider_id: str
    # 데이터 관리 정보 (읽기 전용)
    app_data_dir: str = ""


class SettingsUpdateRequest(BaseModel):
    """설정 변경 요청."""
    ui_locale: str | None = Field(default=None, description="UI 표시 언어 (ko, en, ja, zh_tw, zh_cn)")
    vibe_output_language: str | None = Field(default=None, description="Vibe Fill 출력 언어 (ko, en)")
    # [v1.0.0] 확장 설정 필드
    theme: str | None = Field(default=None, description="테마 (light, dark)")
    font_size: str | None = Field(default=None, description="폰트 크기 (small, medium, large)")
    streaming_enabled: bool | None = Field(default=None, description="스트리밍 채팅 사용 여부")
    default_provider_id: str | None = Field(default=None, description="기본 Provider 프로필 ID")


def _build_response(prefs: UserPreferences, app_data_dir: Path) -> SettingsResponse:
    """현재 설정으로 응답 객체를 생성한다."""
    return SettingsResponse(
        ui_locale=prefs.ui_locale,
        vibe_output_language=prefs.vibe_output_language,
        theme=prefs.theme,
        font_size=prefs.font_size,
        streaming_enabled=prefs.streaming_enabled,
        default_provider_id=prefs.default_provider_id,
        app_data_dir=str(app_data_dir),
    )


@router.get("/settings")
async def get_settings(request: Request) -> SettingsResponse:
    """현재 사용자 설정을 반환한다."""
    prefs = UserPreferences.instance()
    return _build_response(prefs, request.app.state.app_data_dir)


@router.put("/settings")
async def update_settings(
    body: SettingsUpdateRequest, request: Request,
) -> SettingsResponse:
    """사용자 설정을 변경한다."""
    prefs = UserPreferences.instance()
    app_data_dir = request.app.state.app_data_dir

    if body.ui_locale is not None:
        prefs.ui_locale = body.ui_locale
        # i18n 번역기도 즉시 갱신
        translator = Translator.instance()
        translator.set_locale(body.ui_locale)
        logger.info("UI 언어 변경: %s", body.ui_locale)

    if body.vibe_output_language is not None:
        prefs.vibe_output_language = body.vibe_output_language
        logger.info("Vibe Fill 출력 언어 변경: %s", body.vibe_output_language)

    # [v1.0.0] 확장 설정 필드 처리
    if body.theme is not None:
        prefs.theme = body.theme
        logger.info("테마 변경: %s", body.theme)

    if body.font_size is not None:
        prefs.font_size = body.font_size
        logger.info("폰트 크기 변경: %s", body.font_size)

    if body.streaming_enabled is not None:
        prefs.streaming_enabled = body.streaming_enabled
        logger.info("스트리밍 설정 변경: %s", body.streaming_enabled)

    if body.default_provider_id is not None:
        prefs.default_provider_id = body.default_provider_id
        logger.info("기본 Provider 변경: %s", body.default_provider_id)

    prefs.save(app_data_dir)

    return _build_response(prefs, app_data_dir)


@router.post("/settings/reset")
async def reset_settings(request: Request) -> SettingsResponse:
    """[v1.0.0] 모든 설정을 기본값으로 초기화한다.

    DD-12: 설정 초기화 기능.
    """
    app_data_dir = request.app.state.app_data_dir

    # 싱글톤 초기화 후 새 인스턴스 생성
    UserPreferences.reset()
    new_prefs = UserPreferences.instance()
    new_prefs.save(app_data_dir)

    # 번역기 로케일도 기본값으로 복원
    translator = Translator.instance()
    translator.set_locale("ko")

    logger.info("설정 초기화 완료")
    return _build_response(new_prefs, app_data_dir)
