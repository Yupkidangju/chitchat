# src/chitchat/api/routes/providers.py
# [v1.0.0] Provider CRUD + 연결 테스트 + 모델 가져오기 REST API
#
# 기존 ProviderService를 REST endpoint로 노출한다.
# PySide6 UI → FastAPI REST API 전환의 핵심 라우트.

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from chitchat.domain.provider_contracts import ProviderKind

logger = logging.getLogger(__name__)

router = APIRouter()


# --- 요청/응답 스키마 ---

class ProviderCreateRequest(BaseModel):
    """Provider 생성/수정 요청."""
    name: str = Field(min_length=1, max_length=80)
    provider_kind: ProviderKind
    api_key: str | None = None
    base_url: str | None = None
    timeout_seconds: int = Field(default=60, ge=5, le=300)


class ProviderResponse(BaseModel):
    """Provider 응답."""
    id: str
    name: str
    provider_kind: str
    base_url: str | None
    enabled: bool
    timeout_seconds: int
    has_api_key: bool


class ModelCacheResponse(BaseModel):
    """모델 캐시 응답."""
    model_id: str
    display_name: str
    context_window_tokens: int | None
    max_output_tokens: int | None
    supports_streaming: bool
    supports_system_prompt: bool


# --- 서비스 접근 헬퍼 ---

def _get_provider_service(request: Request) -> Any:
    """요청에서 ProviderService를 가져온다."""
    return request.app.state.provider_service


# --- 엔드포인트 ---

@router.get("/providers")
async def list_providers(request: Request) -> list[ProviderResponse]:
    """모든 Provider 프로필을 반환한다."""
    svc = _get_provider_service(request)
    rows = svc.get_all_providers()
    return [
        ProviderResponse(
            id=r.id,
            name=r.name,
            provider_kind=r.provider_kind,
            base_url=r.base_url,
            enabled=bool(r.enabled),
            timeout_seconds=r.timeout_seconds,
            has_api_key=r.secret_ref is not None,
        )
        for r in rows
    ]


@router.post("/providers", status_code=201)
async def create_provider(
    body: ProviderCreateRequest, request: Request,
) -> ProviderResponse:
    """새 Provider를 생성한다."""
    svc = _get_provider_service(request)
    row = svc.save_provider(
        name=body.name,
        provider_kind=body.provider_kind,
        api_key=body.api_key,
        base_url=body.base_url,
        timeout_seconds=body.timeout_seconds,
    )
    return ProviderResponse(
        id=row.id,
        name=row.name,
        provider_kind=row.provider_kind,
        base_url=row.base_url,
        enabled=bool(row.enabled),
        timeout_seconds=row.timeout_seconds,
        has_api_key=row.secret_ref is not None,
    )


@router.put("/providers/{provider_id}")
async def update_provider(
    provider_id: str, body: ProviderCreateRequest, request: Request,
) -> ProviderResponse:
    """Provider를 수정한다."""
    svc = _get_provider_service(request)
    existing = svc.get_provider(provider_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Provider를 찾을 수 없습니다")
    row = svc.save_provider(
        name=body.name,
        provider_kind=body.provider_kind,
        api_key=body.api_key,
        base_url=body.base_url,
        timeout_seconds=body.timeout_seconds,
        existing_id=provider_id,
    )
    return ProviderResponse(
        id=row.id,
        name=row.name,
        provider_kind=row.provider_kind,
        base_url=row.base_url,
        enabled=bool(row.enabled),
        timeout_seconds=row.timeout_seconds,
        has_api_key=row.secret_ref is not None,
    )


@router.delete("/providers/{provider_id}")
async def delete_provider(provider_id: str, request: Request) -> dict[str, bool]:
    """[v1.0.0] Provider를 삭제한다. 참조 중이면 409 반환."""
    svc = _get_provider_service(request)
    try:
        ok = svc.delete_provider(provider_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    if not ok:
        raise HTTPException(status_code=404, detail="Provider를 찾을 수 없습니다")
    return {"deleted": True}


@router.post("/providers/{provider_id}/test")
async def test_connection(provider_id: str, request: Request) -> dict[str, Any]:
    """Provider 연결을 테스트한다."""
    svc = _get_provider_service(request)
    health = await svc.test_connection(provider_id)
    return {
        "ok": health.ok,
        "message": health.message,
        "provider_kind": health.provider_kind,
        "checked_at": health.checked_at_iso,
    }


@router.post("/providers/{provider_id}/fetch-models")
async def fetch_models(provider_id: str, request: Request) -> list[ModelCacheResponse]:
    """Provider의 모델 목록을 가져와 캐시에 저장한다."""
    svc = _get_provider_service(request)
    try:
        caps = await svc.fetch_models(provider_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return [
        ModelCacheResponse(
            model_id=c.model_id,
            display_name=c.display_name,
            context_window_tokens=c.context_window_tokens,
            max_output_tokens=c.max_output_tokens,
            supports_streaming=c.supports_streaming,
            supports_system_prompt=c.supports_system_prompt,
        )
        for c in caps
    ]


@router.get("/providers/{provider_id}/models")
async def get_cached_models(
    provider_id: str, request: Request,
) -> list[ModelCacheResponse]:
    """캐시된 모델 목록을 반환한다."""
    svc = _get_provider_service(request)
    rows = svc.get_cached_models(provider_id)
    return [
        ModelCacheResponse(
            model_id=r.model_id,
            display_name=r.display_name,
            context_window_tokens=r.context_window_tokens,
            max_output_tokens=r.max_output_tokens,
            supports_streaming=bool(r.supports_streaming),
            supports_system_prompt=bool(r.supports_system_prompt),
        )
        for r in rows
    ]
