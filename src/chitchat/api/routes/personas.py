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

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

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


# --- 서비스 접근 헬퍼 ---

def _get_repos(request: Request) -> Any:
    """요청에서 RepositoryRegistry를 가져온다."""
    return request.app.state.repos


# --- 엔드포인트 ---

@router.get("/personas")
async def list_personas(request: Request) -> list[PersonaListItem]:
    """모든 페르소나 카드 목록을 반환한다."""
    repos = _get_repos(request)
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
async def get_persona(persona_id: str, request: Request) -> PersonaDetailResponse:
    """페르소나 카드 상세를 반환한다."""
    repos = _get_repos(request)
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
async def vibe_fill(body: VibeFillRequest, request: Request) -> PersonaSummaryResponse:
    """바이브 텍스트로 9섹션 페르소나를 자동 생성한다.

    [v1.0.0 Phase 6] VibeFillService를 호출하여 실제 AI가 캐릭터를 생성하고,
    결과를 PersonaCardRepository에 자동 저장한다.
    """
    vibe_fill_service = request.app.state.vibe_fill_service
    repos = _get_repos(request)

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
async def delete_persona(persona_id: str, request: Request) -> dict[str, bool]:
    """페르소나를 삭제한다."""
    repos = _get_repos(request)
    ok = repos.persona_cards.delete_by_id(persona_id)
    if not ok:
        raise HTTPException(status_code=404, detail="페르소나를 찾을 수 없습니다")
    return {"deleted": True}
