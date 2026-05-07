# src/chitchat/api/routes/personas.py
# [v1.0.0] VibeSmith 페르소나 CRUD + Vibe Fill REST API
#
# [v1.0.0 Phase 6 변경사항]
# - Vibe Fill 스텁 → VibeFillService 실제 AI 생성 연결
# - 생성 결과를 PersonaCardRepository에 자동 저장
# - Provider/Model 선택을 요청에 포함

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from chitchat.api.dependencies import get_repos, get_vibe_fill_service
from chitchat.db.repositories import RepositoryRegistry

from chitchat.domain.ids import new_id

logger = logging.getLogger(__name__)

router = APIRouter()


# --- 요청/응답 스키마 ---

class VibeFillRequest(BaseModel):
    """Vibe Fill 요청 — 바이브 텍스트로 9섹션 페르소나를 자동 생성한다."""
    vibe_text: str = Field(min_length=2, max_length=2000, description="캐릭터 바이브 텍스트")
    provider_profile_id: str = Field(description="사용할 Provider 프로필 ID")
    model_id: str = Field(description="사용할 모델 ID")
    output_language: str = Field(default="ko", description="출력 언어 (ko, en)")


class PersonaListItem(BaseModel):
    """페르소나 목록 아이템."""
    id: str
    name: str
    age: str
    gender: str
    occupation: str
    core_tension: str
    realism_level: str
    enabled: bool


class PersonaSummaryResponse(BaseModel):
    """페르소나 요약 응답 (Vibe Fill 결과 미리보기)."""
    id: str
    name: str
    age: str
    gender: str
    occupation: str
    core_tension: str
    interpretation: str
    realism_level: str


class PersonaDetailResponse(BaseModel):
    """페르소나 상세 응답 — 전체 persona_json 포함."""
    id: str
    name: str
    age: str
    gender: str
    occupation: str
    core_tension: str
    realism_level: str
    enabled: bool
    persona_json: dict[str, Any]
    created_at: str
    updated_at: str


# --- 엔드포인트 ---

@router.get("/personas")
async def list_personas(
    repos: RepositoryRegistry = Depends(get_repos),
) -> list[PersonaListItem]:
    """모든 페르소나 카드 목록을 반환한다."""
    rows = repos.persona_cards.get_all()
    return [
        PersonaListItem(
            id=r.id,
            name=r.name,
            age=r.age,
            gender=r.gender,
            occupation=r.occupation,
            core_tension=r.core_tension,
            realism_level=r.realism_level,
            enabled=bool(r.enabled),
        )
        for r in rows
    ]


@router.get("/personas/{persona_id}")
async def get_persona(
    persona_id: str,
    repos: RepositoryRegistry = Depends(get_repos),
) -> PersonaDetailResponse:
    """페르소나 카드 상세를 반환한다."""
    row = repos.persona_cards.get_by_id(persona_id)
    if not row:
        raise HTTPException(status_code=404, detail="페르소나를 찾을 수 없습니다")

    # persona_json을 dict로 파싱
    try:
        persona_data = json.loads(row.persona_json)
    except (json.JSONDecodeError, TypeError):
        persona_data = {}

    return PersonaDetailResponse(
        id=row.id,
        name=row.name,
        age=row.age,
        gender=row.gender,
        occupation=row.occupation,
        core_tension=row.core_tension,
        realism_level=row.realism_level,
        enabled=bool(row.enabled),
        persona_json=persona_data,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.post("/personas/vibe-fill")
async def vibe_fill(
    body: VibeFillRequest,
    repos: RepositoryRegistry = Depends(get_repos),
    vibe_fill_service: Any = Depends(get_vibe_fill_service),
) -> PersonaSummaryResponse:
    """바이브 텍스트로 9섹션 페르소나를 자동 생성한다.

    [v1.0.0 Phase 6] VibeFillService를 호출하여 실제 AI가 캐릭터를 생성하고,
    결과를 PersonaCardRepository에 자동 저장한다.
    """

    # AI를 호출하여 페르소나 생성
    result = await vibe_fill_service.generate_persona(
        vibe_text=body.vibe_text,
        provider_profile_id=body.provider_profile_id,
        model_id=body.model_id,
    )

    if not result.success:
        raise HTTPException(status_code=422, detail=f"페르소나 생성 실패: {result.error}")

    # 생성된 데이터에서 메타데이터 추출
    data = result.persona_data
    gen_summary = data.get("generation_summary", {})
    fixed_canon = data.get("fixed_canon", {})
    identity = fixed_canon.get("identity", {})

    name = identity.get("name", "이름 없음")
    age = identity.get("age", "")
    gender = identity.get("gender", "")
    occupation = identity.get("occupation", "")
    core_tension = gen_summary.get("core_tension", "")
    interpretation = gen_summary.get("interpretation", "")
    realism_level = gen_summary.get("realism_level", "grounded")

    # DB에 자동 저장
    now = datetime.now(timezone.utc).isoformat()
    from chitchat.db.models import PersonaCardRow
    row = PersonaCardRow(
        id=new_id("pc_"),
        name=name,
        age=str(age),
        gender=str(gender),
        occupation=str(occupation),
        core_tension=str(core_tension),
        realism_level=str(realism_level),
        persona_json=json.dumps(data, ensure_ascii=False),
        enabled=1,
        created_at=now,
        updated_at=now,
    )
    repos.persona_cards.upsert(row)
    logger.info("VibeSmith 페르소나 저장: %s (%s)", name, row.id)

    return PersonaSummaryResponse(
        id=row.id,
        name=name,
        age=str(age),
        gender=str(gender),
        occupation=str(occupation),
        core_tension=str(core_tension),
        interpretation=str(interpretation),
        realism_level=str(realism_level),
    )


@router.delete("/personas/{persona_id}")
async def delete_persona(
    persona_id: str,
    repos: RepositoryRegistry = Depends(get_repos),
) -> dict[str, bool]:
    """페르소나를 삭제한다."""
    ok = repos.persona_cards.delete_by_id(persona_id)
    if not ok:
        raise HTTPException(status_code=404, detail="페르소나를 찾을 수 없습니다")
    return {"deleted": True}


# ━━━ 페르소나 수동 편집 ━━━

class PersonaUpdateRequest(BaseModel):
    """[v1.1.0] 페르소나 수정 요청 — 이름, persona_json, 활성 상태를 수정한다."""
    name: str = Field(min_length=1, max_length=80)
    persona_json: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


@router.put("/personas/{persona_id}")
async def update_persona(
    persona_id: str, body: PersonaUpdateRequest,
    repos: RepositoryRegistry = Depends(get_repos),
) -> PersonaDetailResponse:
    """[v1.1.0] 페르소나 카드를 수정한다.

    name, persona_json, enabled 필드를 갱신한다.
    persona_json 내부의 generation_summary, fixed_canon 등 메타데이터도 함께 갱신한다.
    """
    existing = repos.persona_cards.get_by_id(persona_id)
    if not existing:
        raise HTTPException(status_code=404, detail="페르소나를 찾을 수 없습니다")

    # persona_json에서 메타데이터 추출
    data = body.persona_json
    gen_summary = data.get("generation_summary", {})
    fixed_canon = data.get("fixed_canon", {})
    identity = fixed_canon.get("identity", {})

    # 기존 Row 갱신
    now = datetime.now(timezone.utc).isoformat()
    existing.name = body.name
    existing.age = str(identity.get("age", existing.age))
    existing.gender = str(identity.get("gender", existing.gender))
    existing.occupation = str(identity.get("occupation", existing.occupation))
    existing.core_tension = str(gen_summary.get("core_tension", existing.core_tension))
    existing.realism_level = str(gen_summary.get("realism_level", existing.realism_level))
    existing.persona_json = json.dumps(data, ensure_ascii=False)
    existing.enabled = int(body.enabled)
    existing.updated_at = now

    saved = repos.persona_cards.upsert(existing)
    logger.info("페르소나 수정: %s (%s)", saved.name, saved.id)

    try:
        persona_data = json.loads(saved.persona_json)
    except (json.JSONDecodeError, TypeError):
        persona_data = {}

    return PersonaDetailResponse(
        id=saved.id,
        name=saved.name,
        age=saved.age,
        gender=saved.gender,
        occupation=saved.occupation,
        core_tension=saved.core_tension,
        realism_level=saved.realism_level,
        enabled=bool(saved.enabled),
        persona_json=persona_data,
        created_at=saved.created_at,
        updated_at=saved.updated_at,
    )

