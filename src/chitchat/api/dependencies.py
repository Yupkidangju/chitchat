# src/chitchat/api/dependencies.py
# [v1.1.1] FastAPI Depends() 기반 의존성 주입 프로바이더
#
# 기존 request.app.state.xxx 직접 접근 패턴을 대체하여
# 테스트 용이성과 결합도를 개선한다.
# DD-21 참조: 라우터에서 Depends()로 서비스를 주입받는 패턴.

from __future__ import annotations

from typing import Any

from fastapi import Request

from chitchat.db.repositories import RepositoryRegistry
from chitchat.services.chat_service import ChatService
from chitchat.services.dynamic_state_engine import DynamicStateEngine
from chitchat.services.profile_service import ProfileService
from chitchat.services.provider_service import ProviderService
from chitchat.services.vibe_fill_service import VibeFillService


def get_repos(request: Request) -> RepositoryRegistry:
    """RepositoryRegistry를 주입한다."""
    return request.app.state.repos  # type: ignore[no-any-return]


def get_provider_service(request: Request) -> ProviderService:
    """ProviderService를 주입한다."""
    return request.app.state.provider_service  # type: ignore[no-any-return]


def get_chat_service(request: Request) -> ChatService:
    """ChatService를 주입한다."""
    return request.app.state.chat_service  # type: ignore[no-any-return]


def get_vibe_fill_service(request: Request) -> VibeFillService:
    """VibeFillService를 주입한다."""
    return request.app.state.vibe_fill_service  # type: ignore[no-any-return]


def get_dynamic_state_engine(request: Request) -> DynamicStateEngine:
    """DynamicStateEngine을 주입한다."""
    return request.app.state.dynamic_state_engine  # type: ignore[no-any-return]


def get_profile_service(request: Request) -> ProfileService:
    """ProfileService를 주입한다."""
    return request.app.state.profile_service  # type: ignore[no-any-return]


def get_app_data_dir(request: Request) -> Any:
    """앱 데이터 디렉토리 경로를 주입한다."""
    return request.app.state.app_data_dir
