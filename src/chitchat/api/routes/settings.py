# src/chitchat/api/routes/settings.py
# [v1.0.0] 사용자 설정 REST API
#
# 언어 설정, Vibe Fill 출력 언어 등 사용자 환경설정을 관리한다.

from __future__ import annotations

import logging

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


class SettingsUpdateRequest(BaseModel):
    """설정 변경 요청."""
    ui_locale: str | None = Field(default=None, description="UI 표시 언어 (ko, en, ja, zh_tw, zh_cn)")
    vibe_output_language: str | None = Field(default=None, description="Vibe Fill 출력 언어 (ko, en)")


@router.get("/settings")
async def get_settings(request: Request) -> SettingsResponse:
    """현재 사용자 설정을 반환한다."""
    prefs = UserPreferences.instance()
    return SettingsResponse(
        ui_locale=prefs.ui_locale,
        vibe_output_language=prefs.vibe_output_language,
    )


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

    prefs.save(app_data_dir)

    return SettingsResponse(
        ui_locale=prefs.ui_locale,
        vibe_output_language=prefs.vibe_output_language,
    )
