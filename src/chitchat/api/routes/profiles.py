# src/chitchat/api/routes/profiles.py
# [v1.0.0] ModelProfile, ChatProfile, Lorebook, Worldbook CRUD REST API
#
# ProfileService의 CRUD 메서드를 REST 엔드포인트로 노출한다.
# Provider/Persona와 함께 채팅 세션 생성 워크플로우를 완성하는 핵심 라우트.

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()


# --- 요청/응답 스키마 ---

# ModelProfile
class ModelProfileCreateRequest(BaseModel):
    """ModelProfile 생성/수정 요청."""
    name: str = Field(min_length=1, max_length=80)
    provider_profile_id: str
    model_id: str
    settings_json: str = Field(default="{}")


class ModelProfileResponse(BaseModel):
    """ModelProfile 응답."""
    id: str
    name: str
    provider_profile_id: str
    model_id: str
    settings_json: str
    created_at: str
    updated_at: str


# ChatProfile
class ChatProfileCreateRequest(BaseModel):
    """ChatProfile 생성/수정 요청."""
    name: str = Field(min_length=1, max_length=80)
    model_profile_id: str
    ai_persona_ids: list[str] = Field(default_factory=list)
    lorebook_ids: list[str] = Field(default_factory=list)
    worldbook_ids: list[str] = Field(default_factory=list)
    prompt_order_json: str = Field(default="[]")
    system_base: str = Field(default="")


class ChatProfileResponse(BaseModel):
    """ChatProfile 응답."""
    id: str
    name: str
    model_profile_id: str
    ai_persona_ids: list[str]
    lorebook_ids: list[str]
    worldbook_ids: list[str]
    prompt_order_json: str
    system_base: str
    created_at: str
    updated_at: str


# Lorebook / Worldbook
class BookCreateRequest(BaseModel):
    """Lorebook/Worldbook 생성 요청."""
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="")


class BookResponse(BaseModel):
    """Lorebook/Worldbook 응답."""
    id: str
    name: str
    description: str


# LoreEntry
class LoreEntryCreateRequest(BaseModel):
    """LoreEntry 생성 요청."""
    title: str = Field(min_length=1, max_length=120)
    activation_keys: list[str] = Field(default_factory=list)
    content: str = Field(default="")
    priority: int = Field(default=100, ge=0, le=1000)
    enabled: bool = True


class LoreEntryResponse(BaseModel):
    """LoreEntry 응답."""
    id: str
    lorebook_id: str
    title: str
    activation_keys: list[str]
    content: str
    priority: int
    enabled: bool


# WorldEntry
class WorldEntryCreateRequest(BaseModel):
    """WorldEntry 생성 요청."""
    title: str = Field(min_length=1, max_length=120)
    content: str = Field(default="")
    priority: int = Field(default=100, ge=0, le=1000)
    enabled: bool = True


class WorldEntryResponse(BaseModel):
    """WorldEntry 응답."""
    id: str
    worldbook_id: str
    title: str
    content: str
    priority: int
    enabled: bool


# --- 서비스 접근 헬퍼 ---

def _get_profile_service(request: Request) -> Any:
    """요청에서 ProfileService를 가져온다."""
    return request.app.state.profile_service


# ━━━ ModelProfile ━━━

@router.get("/model-profiles")
async def list_model_profiles(request: Request) -> list[ModelProfileResponse]:
    """모든 ModelProfile을 반환한다."""
    svc = _get_profile_service(request)
    rows = svc.get_all_model_profiles()
    return [
        ModelProfileResponse(
            id=r.id, name=r.name,
            provider_profile_id=r.provider_profile_id,
            model_id=r.model_id,
            settings_json=r.settings_json,
            created_at=r.created_at, updated_at=r.updated_at,
        )
        for r in rows
    ]


@router.post("/model-profiles", status_code=201)
async def create_model_profile(
    body: ModelProfileCreateRequest, request: Request,
) -> ModelProfileResponse:
    """새 ModelProfile을 생성한다."""
    svc = _get_profile_service(request)
    row = svc.save_model_profile(
        name=body.name,
        provider_profile_id=body.provider_profile_id,
        model_id=body.model_id,
        settings_json=body.settings_json,
    )
    return ModelProfileResponse(
        id=row.id, name=row.name,
        provider_profile_id=row.provider_profile_id,
        model_id=row.model_id,
        settings_json=row.settings_json,
        created_at=row.created_at, updated_at=row.updated_at,
    )


@router.put("/model-profiles/{profile_id}")
async def update_model_profile(
    profile_id: str, body: ModelProfileCreateRequest, request: Request,
) -> ModelProfileResponse:
    """ModelProfile을 수정한다."""
    svc = _get_profile_service(request)
    existing = svc.get_model_profile(profile_id)
    if not existing:
        raise HTTPException(status_code=404, detail="ModelProfile을 찾을 수 없습니다")
    row = svc.save_model_profile(
        name=body.name,
        provider_profile_id=body.provider_profile_id,
        model_id=body.model_id,
        settings_json=body.settings_json,
        existing_id=profile_id,
    )
    return ModelProfileResponse(
        id=row.id, name=row.name,
        provider_profile_id=row.provider_profile_id,
        model_id=row.model_id,
        settings_json=row.settings_json,
        created_at=row.created_at, updated_at=row.updated_at,
    )


@router.delete("/model-profiles/{profile_id}")
async def delete_model_profile(
    profile_id: str, request: Request,
) -> dict[str, bool]:
    """ModelProfile을 삭제한다."""
    svc = _get_profile_service(request)
    ok = svc.delete_model_profile(profile_id)
    if not ok:
        raise HTTPException(status_code=404, detail="ModelProfile을 찾을 수 없습니다")
    return {"deleted": True}


# ━━━ ChatProfile ━━━

@router.get("/chat-profiles")
async def list_chat_profiles(request: Request) -> list[ChatProfileResponse]:
    """모든 ChatProfile을 반환한다."""
    svc = _get_profile_service(request)
    rows = svc.get_all_chat_profiles()
    return [
        ChatProfileResponse(
            id=r.id, name=r.name,
            model_profile_id=r.model_profile_id,
            ai_persona_ids=json.loads(r.ai_persona_ids_json),
            lorebook_ids=json.loads(r.lorebook_ids_json),
            worldbook_ids=json.loads(r.worldbook_ids_json),
            prompt_order_json=r.prompt_order_json,
            system_base=r.system_base,
            created_at=r.created_at, updated_at=r.updated_at,
        )
        for r in rows
    ]


@router.post("/chat-profiles", status_code=201)
async def create_chat_profile(
    body: ChatProfileCreateRequest, request: Request,
) -> ChatProfileResponse:
    """새 ChatProfile을 생성한다."""
    svc = _get_profile_service(request)
    row = svc.save_chat_profile(
        name=body.name,
        model_profile_id=body.model_profile_id,
        ai_persona_ids=body.ai_persona_ids,
        lorebook_ids=body.lorebook_ids,
        worldbook_ids=body.worldbook_ids,
        prompt_order_json=body.prompt_order_json,
        system_base=body.system_base,
    )
    return ChatProfileResponse(
        id=row.id, name=row.name,
        model_profile_id=row.model_profile_id,
        ai_persona_ids=json.loads(row.ai_persona_ids_json),
        lorebook_ids=json.loads(row.lorebook_ids_json),
        worldbook_ids=json.loads(row.worldbook_ids_json),
        prompt_order_json=row.prompt_order_json,
        system_base=row.system_base,
        created_at=row.created_at, updated_at=row.updated_at,
    )


@router.put("/chat-profiles/{profile_id}")
async def update_chat_profile(
    profile_id: str, body: ChatProfileCreateRequest, request: Request,
) -> ChatProfileResponse:
    """ChatProfile을 수정한다."""
    svc = _get_profile_service(request)
    existing = svc.get_chat_profile(profile_id)
    if not existing:
        raise HTTPException(status_code=404, detail="ChatProfile을 찾을 수 없습니다")
    row = svc.save_chat_profile(
        name=body.name,
        model_profile_id=body.model_profile_id,
        ai_persona_ids=body.ai_persona_ids,
        lorebook_ids=body.lorebook_ids,
        worldbook_ids=body.worldbook_ids,
        prompt_order_json=body.prompt_order_json,
        system_base=body.system_base,
        existing_id=profile_id,
    )
    return ChatProfileResponse(
        id=row.id, name=row.name,
        model_profile_id=row.model_profile_id,
        ai_persona_ids=json.loads(row.ai_persona_ids_json),
        lorebook_ids=json.loads(row.lorebook_ids_json),
        worldbook_ids=json.loads(row.worldbook_ids_json),
        prompt_order_json=row.prompt_order_json,
        system_base=row.system_base,
        created_at=row.created_at, updated_at=row.updated_at,
    )


@router.delete("/chat-profiles/{profile_id}")
async def delete_chat_profile(
    profile_id: str, request: Request,
) -> dict[str, bool]:
    """ChatProfile을 삭제한다."""
    svc = _get_profile_service(request)
    ok = svc.delete_chat_profile(profile_id)
    if not ok:
        raise HTTPException(status_code=404, detail="ChatProfile을 찾을 수 없습니다")
    return {"deleted": True}


# ━━━ Lorebook ━━━

@router.get("/lorebooks")
async def list_lorebooks(request: Request) -> list[BookResponse]:
    """모든 Lorebook을 반환한다."""
    svc = _get_profile_service(request)
    rows = svc.get_all_lorebooks()
    return [
        BookResponse(id=r.id, name=r.name, description=r.description)
        for r in rows
    ]


@router.post("/lorebooks", status_code=201)
async def create_lorebook(
    body: BookCreateRequest, request: Request,
) -> BookResponse:
    """새 Lorebook을 생성한다."""
    svc = _get_profile_service(request)
    row = svc.save_lorebook(name=body.name, description=body.description)
    return BookResponse(id=row.id, name=row.name, description=row.description)


@router.delete("/lorebooks/{lorebook_id}")
async def delete_lorebook(lorebook_id: str, request: Request) -> dict[str, bool]:
    """Lorebook을 삭제한다."""
    svc = _get_profile_service(request)
    ok = svc.delete_lorebook(lorebook_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Lorebook을 찾을 수 없습니다")
    return {"deleted": True}


@router.get("/lorebooks/{lorebook_id}/entries")
async def list_lore_entries(lorebook_id: str, request: Request) -> list[LoreEntryResponse]:
    """Lorebook의 LoreEntry 목록을 반환한다."""
    svc = _get_profile_service(request)
    rows = svc.get_lore_entries(lorebook_id)
    return [
        LoreEntryResponse(
            id=r.id, lorebook_id=r.lorebook_id, title=r.title,
            activation_keys=json.loads(r.activation_keys_json),
            content=r.content, priority=r.priority,
            enabled=bool(r.enabled),
        )
        for r in rows
    ]


@router.post("/lorebooks/{lorebook_id}/entries", status_code=201)
async def create_lore_entry(
    lorebook_id: str, body: LoreEntryCreateRequest, request: Request,
) -> LoreEntryResponse:
    """LoreEntry를 추가한다."""
    svc = _get_profile_service(request)
    row = svc.save_lore_entry(
        lorebook_id=lorebook_id,
        title=body.title,
        activation_keys=body.activation_keys,
        content=body.content,
        priority=body.priority,
        enabled=body.enabled,
    )
    return LoreEntryResponse(
        id=row.id, lorebook_id=row.lorebook_id, title=row.title,
        activation_keys=json.loads(row.activation_keys_json),
        content=row.content, priority=row.priority,
        enabled=bool(row.enabled),
    )


@router.delete("/lore-entries/{entry_id}")
async def delete_lore_entry(entry_id: str, request: Request) -> dict[str, bool]:
    """LoreEntry를 삭제한다."""
    svc = _get_profile_service(request)
    ok = svc.delete_lore_entry(entry_id)
    if not ok:
        raise HTTPException(status_code=404, detail="LoreEntry를 찾을 수 없습니다")
    return {"deleted": True}


# ━━━ Worldbook ━━━

@router.get("/worldbooks")
async def list_worldbooks(request: Request) -> list[BookResponse]:
    """모든 Worldbook을 반환한다."""
    svc = _get_profile_service(request)
    rows = svc.get_all_worldbooks()
    return [
        BookResponse(id=r.id, name=r.name, description=r.description)
        for r in rows
    ]


@router.post("/worldbooks", status_code=201)
async def create_worldbook(
    body: BookCreateRequest, request: Request,
) -> BookResponse:
    """새 Worldbook을 생성한다."""
    svc = _get_profile_service(request)
    row = svc.save_worldbook(name=body.name, description=body.description)
    return BookResponse(id=row.id, name=row.name, description=row.description)


@router.delete("/worldbooks/{worldbook_id}")
async def delete_worldbook(worldbook_id: str, request: Request) -> dict[str, bool]:
    """Worldbook을 삭제한다."""
    svc = _get_profile_service(request)
    ok = svc.delete_worldbook(worldbook_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Worldbook을 찾을 수 없습니다")
    return {"deleted": True}


@router.get("/worldbooks/{worldbook_id}/entries")
async def list_world_entries(worldbook_id: str, request: Request) -> list[WorldEntryResponse]:
    """Worldbook의 WorldEntry 목록을 반환한다."""
    svc = _get_profile_service(request)
    rows = svc.get_world_entries(worldbook_id)
    return [
        WorldEntryResponse(
            id=r.id, worldbook_id=r.worldbook_id, title=r.title,
            content=r.content, priority=r.priority,
            enabled=bool(r.enabled),
        )
        for r in rows
    ]


@router.post("/worldbooks/{worldbook_id}/entries", status_code=201)
async def create_world_entry(
    worldbook_id: str, body: WorldEntryCreateRequest, request: Request,
) -> WorldEntryResponse:
    """WorldEntry를 추가한다."""
    svc = _get_profile_service(request)
    row = svc.save_world_entry(
        worldbook_id=worldbook_id,
        title=body.title,
        content=body.content,
        priority=body.priority,
        enabled=body.enabled,
    )
    return WorldEntryResponse(
        id=row.id, worldbook_id=row.worldbook_id, title=row.title,
        content=row.content, priority=row.priority,
        enabled=bool(row.enabled),
    )


@router.delete("/world-entries/{entry_id}")
async def delete_world_entry(entry_id: str, request: Request) -> dict[str, bool]:
    """WorldEntry를 삭제한다."""
    svc = _get_profile_service(request)
    ok = svc.delete_world_entry(entry_id)
    if not ok:
        raise HTTPException(status_code=404, detail="WorldEntry를 찾을 수 없습니다")
    return {"deleted": True}
