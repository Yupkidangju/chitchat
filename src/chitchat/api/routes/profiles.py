# src/chitchat/api/routes/profiles.py
# [v1.0.0] ModelProfile, ChatProfile, Lorebook, Worldbook CRUD REST API
#
# ProfileService의 CRUD 메서드를 REST 엔드포인트로 노출한다.
# Provider/Persona와 함께 채팅 세션 생성 워크플로우를 완성하는 핵심 라우트.

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from chitchat.api.dependencies import get_profile_service, get_vibe_fill_service
from chitchat.services.profile_service import ProfileService
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



# ━━━ UserPersona ━━━

class UserPersonaCreateRequest(BaseModel):
    """UserPersona 생성/수정 요청."""
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="")
    speaking_style: str = Field(default="")
    boundaries: str = Field(default="")


class UserPersonaResponse(BaseModel):
    """UserPersona 응답."""
    id: str
    name: str
    description: str
    speaking_style: str
    boundaries: str
    enabled: bool


@router.get("/user-personas")
async def list_user_personas(
    svc: ProfileService = Depends(get_profile_service),
) -> list[UserPersonaResponse]:
    """모든 UserPersona를 반환한다."""
    rows = svc.get_all_user_personas()
    return [
        UserPersonaResponse(
            id=r.id, name=r.name, description=r.description,
            speaking_style=r.speaking_style, boundaries=r.boundaries,
            enabled=bool(r.enabled),
        )
        for r in rows
    ]


@router.post("/user-personas", status_code=201)
async def create_user_persona(
    body: UserPersonaCreateRequest,
    svc: ProfileService = Depends(get_profile_service),
) -> UserPersonaResponse:
    """새 UserPersona를 생성한다."""
    row = svc.save_user_persona(
        name=body.name, description=body.description,
        speaking_style=body.speaking_style, boundaries=body.boundaries,
    )
    return UserPersonaResponse(
        id=row.id, name=row.name, description=row.description,
        speaking_style=row.speaking_style, boundaries=row.boundaries,
        enabled=bool(row.enabled),
    )


@router.delete("/user-personas/{persona_id}")
async def delete_user_persona(persona_id: str,
    svc: ProfileService = Depends(get_profile_service),
) -> dict[str, bool]:
    """[v1.0.0] UserPersona를 삭제한다. 참조 중이면 409 반환."""
    try:
        ok = svc.delete_user_persona(persona_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    if not ok:
        raise HTTPException(status_code=404, detail="UserPersona를 찾을 수 없습니다")
    return {"deleted": True}


# ━━━ ModelProfile ━━━

@router.get("/model-profiles")
async def list_model_profiles(
    svc: ProfileService = Depends(get_profile_service),
) -> list[ModelProfileResponse]:
    """모든 ModelProfile을 반환한다."""
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
    body: ModelProfileCreateRequest,
    svc: ProfileService = Depends(get_profile_service),
) -> ModelProfileResponse:
    """새 ModelProfile을 생성한다."""
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
    profile_id: str, body: ModelProfileCreateRequest,
    svc: ProfileService = Depends(get_profile_service),
) -> ModelProfileResponse:
    """ModelProfile을 수정한다."""
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
    profile_id: str,
    svc: ProfileService = Depends(get_profile_service),
) -> dict[str, bool]:
    """[v1.0.0] ModelProfile을 삭제한다. 참조 중이면 409 반환."""
    try:
        ok = svc.delete_model_profile(profile_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    if not ok:
        raise HTTPException(status_code=404, detail="ModelProfile을 찾을 수 없습니다")
    return {"deleted": True}


# ━━━ ChatProfile ━━━

@router.get("/chat-profiles")
async def list_chat_profiles(
    svc: ProfileService = Depends(get_profile_service),
) -> list[ChatProfileResponse]:
    """모든 ChatProfile을 반환한다."""
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
    body: ChatProfileCreateRequest,
    svc: ProfileService = Depends(get_profile_service),
) -> ChatProfileResponse:
    """새 ChatProfile을 생성한다."""
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
    profile_id: str, body: ChatProfileCreateRequest,
    svc: ProfileService = Depends(get_profile_service),
) -> ChatProfileResponse:
    """ChatProfile을 수정한다."""
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
    profile_id: str,
    svc: ProfileService = Depends(get_profile_service),
) -> dict[str, bool]:
    """[v1.0.0] ChatProfile을 삭제한다. 참조 중이면 409 반환."""
    try:
        ok = svc.delete_chat_profile(profile_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    if not ok:
        raise HTTPException(status_code=404, detail="ChatProfile을 찾을 수 없습니다")
    return {"deleted": True}


# ━━━ Lorebook ━━━

@router.get("/lorebooks")
async def list_lorebooks(
    svc: ProfileService = Depends(get_profile_service),
) -> list[BookResponse]:
    """모든 Lorebook을 반환한다."""
    rows = svc.get_all_lorebooks()
    return [
        BookResponse(id=r.id, name=r.name, description=r.description)
        for r in rows
    ]


@router.post("/lorebooks", status_code=201)
async def create_lorebook(
    body: BookCreateRequest,
    svc: ProfileService = Depends(get_profile_service),
) -> BookResponse:
    """새 Lorebook을 생성한다."""
    row = svc.save_lorebook(name=body.name, description=body.description)
    return BookResponse(id=row.id, name=row.name, description=row.description)


@router.delete("/lorebooks/{lorebook_id}")
async def delete_lorebook(lorebook_id: str,
    svc: ProfileService = Depends(get_profile_service),
) -> dict[str, bool]:
    """[v1.0.0] Lorebook을 삭제한다. 참조 중이면 409 반환."""
    try:
        ok = svc.delete_lorebook(lorebook_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    if not ok:
        raise HTTPException(status_code=404, detail="Lorebook을 찾을 수 없습니다")
    return {"deleted": True}


@router.get("/lorebooks/{lorebook_id}/entries")
async def list_lore_entries(lorebook_id: str,
    svc: ProfileService = Depends(get_profile_service),
) -> list[LoreEntryResponse]:
    """Lorebook의 LoreEntry 목록을 반환한다."""
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
    lorebook_id: str, body: LoreEntryCreateRequest,
    svc: ProfileService = Depends(get_profile_service),
) -> LoreEntryResponse:
    """LoreEntry를 추가한다."""
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
async def delete_lore_entry(entry_id: str,
    svc: ProfileService = Depends(get_profile_service),
) -> dict[str, bool]:
    """LoreEntry를 삭제한다."""
    ok = svc.delete_lore_entry(entry_id)
    if not ok:
        raise HTTPException(status_code=404, detail="LoreEntry를 찾을 수 없습니다")
    return {"deleted": True}


@router.get("/lorebooks/entries/{entry_id}")
async def get_lore_entry(entry_id: str,
    svc: ProfileService = Depends(get_profile_service),
) -> LoreEntryResponse:
    """[v1.1.2] 개별 LoreEntry를 반환한다.

    이벤트 위임에서 entry ID로 편집 모달 데이터를 가져올 때 사용한다.
    """
    row = svc._repos.lore_entries.get_by_id(entry_id)
    if not row:
        raise HTTPException(status_code=404, detail="LoreEntry를 찾을 수 없습니다")
    return LoreEntryResponse(
        id=row.id, lorebook_id=row.lorebook_id, title=row.title,
        activation_keys=json.loads(row.activation_keys_json),
        content=row.content, priority=row.priority,
        enabled=bool(row.enabled),
    )


# ━━━ Worldbook ━━━

@router.get("/worldbooks")
async def list_worldbooks(
    svc: ProfileService = Depends(get_profile_service),
) -> list[BookResponse]:
    """모든 Worldbook을 반환한다."""
    rows = svc.get_all_worldbooks()
    return [
        BookResponse(id=r.id, name=r.name, description=r.description)
        for r in rows
    ]


@router.post("/worldbooks", status_code=201)
async def create_worldbook(
    body: BookCreateRequest,
    svc: ProfileService = Depends(get_profile_service),
) -> BookResponse:
    """새 Worldbook을 생성한다."""
    row = svc.save_worldbook(name=body.name, description=body.description)
    return BookResponse(id=row.id, name=row.name, description=row.description)


@router.delete("/worldbooks/{worldbook_id}")
async def delete_worldbook(worldbook_id: str,
    svc: ProfileService = Depends(get_profile_service),
) -> dict[str, bool]:
    """[v1.0.0] Worldbook을 삭제한다. 참조 중이면 409 반환."""
    try:
        ok = svc.delete_worldbook(worldbook_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    if not ok:
        raise HTTPException(status_code=404, detail="Worldbook을 찾을 수 없습니다")
    return {"deleted": True}


@router.get("/worldbooks/{worldbook_id}/entries")
async def list_world_entries(worldbook_id: str,
    svc: ProfileService = Depends(get_profile_service),
) -> list[WorldEntryResponse]:
    """Worldbook의 WorldEntry 목록을 반환한다."""
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
    worldbook_id: str, body: WorldEntryCreateRequest,
    svc: ProfileService = Depends(get_profile_service),
) -> WorldEntryResponse:
    """WorldEntry를 추가한다."""
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
async def delete_world_entry(entry_id: str,
    svc: ProfileService = Depends(get_profile_service),
) -> dict[str, bool]:
    """WorldEntry를 삭제한다."""
    ok = svc.delete_world_entry(entry_id)
    if not ok:
        raise HTTPException(status_code=404, detail="WorldEntry를 찾을 수 없습니다")
    return {"deleted": True}


@router.get("/worldbooks/entries/{entry_id}")
async def get_world_entry(entry_id: str,
    svc: ProfileService = Depends(get_profile_service),
) -> WorldEntryResponse:
    """[v1.1.2] 개별 WorldEntry를 반환한다.

    이벤트 위임에서 entry ID로 편집 모달 데이터를 가져올 때 사용한다.
    """
    row = svc._repos.world_entries.get_by_id(entry_id)
    if not row:
        raise HTTPException(status_code=404, detail="WorldEntry를 찾을 수 없습니다")
    return WorldEntryResponse(
        id=row.id, worldbook_id=row.worldbook_id, title=row.title,
        content=row.content, priority=row.priority,
        enabled=bool(row.enabled),
    )


# ━━━ LoreEntry / WorldEntry PUT (수동 편집) ━━━


@router.put("/lore-entries/{entry_id}")
async def update_lore_entry(
    entry_id: str, body: LoreEntryCreateRequest,
    svc: ProfileService = Depends(get_profile_service),
) -> LoreEntryResponse:
    """[v1.1.0] LoreEntry를 수정한다.

    기존 entry_id를 유지하면서 내용을 갱신한다.
    """
    # 기존 엔트리가 존재하는지 확인
    existing = svc._repos.lore_entries.get_by_id(entry_id)
    if not existing:
        raise HTTPException(status_code=404, detail="LoreEntry를 찾을 수 없습니다")

    row = svc.save_lore_entry(
        lorebook_id=existing.lorebook_id,
        title=body.title,
        activation_keys=body.activation_keys,
        content=body.content,
        priority=body.priority,
        enabled=body.enabled,
        existing_id=entry_id,
    )
    return LoreEntryResponse(
        id=row.id, lorebook_id=row.lorebook_id, title=row.title,
        activation_keys=json.loads(row.activation_keys_json),
        content=row.content, priority=row.priority,
        enabled=bool(row.enabled),
    )


@router.put("/world-entries/{entry_id}")
async def update_world_entry(
    entry_id: str, body: WorldEntryCreateRequest,
    svc: ProfileService = Depends(get_profile_service),
) -> WorldEntryResponse:
    """[v1.1.0] WorldEntry를 수정한다.

    기존 entry_id를 유지하면서 내용을 갱신한다.
    """
    existing = svc._repos.world_entries.get_by_id(entry_id)
    if not existing:
        raise HTTPException(status_code=404, detail="WorldEntry를 찾을 수 없습니다")

    row = svc.save_world_entry(
        worldbook_id=existing.worldbook_id,
        title=body.title,
        content=body.content,
        priority=body.priority,
        enabled=body.enabled,
        existing_id=entry_id,
    )
    return WorldEntryResponse(
        id=row.id, worldbook_id=row.worldbook_id, title=row.title,
        content=row.content, priority=row.priority,
        enabled=bool(row.enabled),
    )


# ━━━ Lorebook / Worldbook Vibe Fill (AI 자동 생성) ━━━


class LoreVibeFillRequest(BaseModel):
    """[v1.1.0] 로어북 Vibe Fill 요청 — 캐릭터 참조 + 바이브로 엔트리 AI 생성."""
    vibe_text: str = Field(min_length=2, max_length=2000)
    persona_ids: list[str] = Field(default_factory=list)
    provider_profile_id: str
    model_id: str


class WorldVibeFillRequest(BaseModel):
    """[v1.1.0] 월드북 Vibe Fill 요청 — 캐릭터/로어북 참조 + 바이브로 엔트리 AI 생성."""
    vibe_text: str = Field(min_length=2, max_length=2000)
    persona_ids: list[str] = Field(default_factory=list)
    lorebook_ids: list[str] = Field(default_factory=list)
    category_keys: list[str] = Field(default_factory=list)
    provider_profile_id: str
    model_id: str


@router.post("/lorebooks/{lorebook_id}/vibe-fill")
async def lore_vibe_fill(
    lorebook_id: str, body: LoreVibeFillRequest,
    svc: ProfileService = Depends(get_profile_service),
    vibe_svc: Any = Depends(get_vibe_fill_service),
) -> list[LoreEntryResponse]:
    """[v1.1.0] AI가 캐릭터를 참조하여 로어 엔트리를 자동 생성한다.

    1. 선택된 캐릭터(persona_ids)의 시트를 컨텍스트로 주입
    2. VibeFillService.generate_lore_entries() 호출
    3. 생성된 엔트리를 DB에 자동 저장
    4. 저장된 엔트리 목록을 응답으로 반환
    """

    # 대상 로어북 존재 확인
    lb = svc.get_lorebook(lorebook_id)
    if not lb:
        raise HTTPException(status_code=404, detail="Lorebook을 찾을 수 없습니다")

    # AI 생성
    result = await vibe_svc.generate_lore_entries(
        vibe_text=body.vibe_text,
        lorebook_id=lorebook_id,
        provider_profile_id=body.provider_profile_id,
        model_id=body.model_id,
        persona_ids=body.persona_ids or None,
    )

    if not result.success:
        raise HTTPException(status_code=422, detail=f"로어 엔트리 생성 실패: {result.error}")

    # 생성된 엔트리를 DB에 저장
    saved_entries: list[LoreEntryResponse] = []
    for entry_data in result.entries:
        row = svc.save_lore_entry(
            lorebook_id=lorebook_id,
            title=entry_data["title"],
            activation_keys=entry_data["activation_keys"],
            content=entry_data["content"],
            priority=entry_data.get("priority", 100),
        )
        saved_entries.append(LoreEntryResponse(
            id=row.id, lorebook_id=row.lorebook_id, title=row.title,
            activation_keys=json.loads(row.activation_keys_json),
            content=row.content, priority=row.priority,
            enabled=bool(row.enabled),
        ))

    logger.info(
        "Lore Vibe Fill 완료: lorebook=%s, %d개 엔트리 생성",
        lorebook_id, len(saved_entries),
    )
    return saved_entries


@router.post("/worldbooks/{worldbook_id}/vibe-fill")
async def world_vibe_fill(
    worldbook_id: str, body: WorldVibeFillRequest,
    svc: ProfileService = Depends(get_profile_service),
    vibe_svc: Any = Depends(get_vibe_fill_service),
) -> list[WorldEntryResponse]:
    """[v1.1.0] AI가 캐릭터/로어북을 참조하여 월드 엔트리를 자동 생성한다.

    1. 선택된 캐릭터(persona_ids)와 로어북(lorebook_ids)을 컨텍스트로 주입
    2. 카테고리를 청크로 나눠 VibeFillService.generate_world_entries() 호출
    3. 생성된 엔트리를 DB에 자동 저장
    4. 저장된 엔트리 목록을 응답으로 반환
    """

    # 대상 월드북 존재 확인
    wb = svc.get_worldbook(worldbook_id)
    if not wb:
        raise HTTPException(status_code=404, detail="Worldbook을 찾을 수 없습니다")

    # 카테고리가 비어있으면 전체 카테고리 사용
    from chitchat.domain.vibe_fill import WORLD_CATEGORIES
    category_keys = body.category_keys or [c.key for c in WORLD_CATEGORIES]

    # AI 생성
    result = await vibe_svc.generate_world_entries(
        vibe_text=body.vibe_text,
        worldbook_id=worldbook_id,
        provider_profile_id=body.provider_profile_id,
        model_id=body.model_id,
        category_keys=category_keys,
        persona_ids=body.persona_ids or None,
        lorebook_ids=body.lorebook_ids or None,
    )

    if not result.success:
        raise HTTPException(status_code=422, detail=f"월드 엔트리 생성 실패: {result.error}")

    # 생성된 엔트리를 DB에 저장
    saved_entries: list[WorldEntryResponse] = []
    for entry_data in result.entries:
        row = svc.save_world_entry(
            worldbook_id=worldbook_id,
            title=entry_data["title"],
            content=entry_data["content"],
            priority=entry_data.get("priority", 100),
        )
        saved_entries.append(WorldEntryResponse(
            id=row.id, worldbook_id=row.worldbook_id, title=row.title,
            content=row.content, priority=row.priority,
            enabled=bool(row.enabled),
        ))

    logger.info(
        "World Vibe Fill 완료: worldbook=%s, %d개 엔트리 생성",
        worldbook_id, len(saved_entries),
    )
    return saved_entries
