# src/chitchat/api/routes/personas.py
# [v1.0.0] VibeSmith 페르소나 CRUD + Vibe Fill REST API
#
# 9섹션 PersonaCard의 생성, 조회, 수정, 삭제와
# Vibe Fill(바이브 → 페르소나 자동 생성) 기능을 제공한다.

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()


# --- 요청/응답 스키마 ---

class VibeFillRequest(BaseModel):
    """Vibe Fill 요청 — 바이브 텍스트로 9섹션 페르소나를 자동 생성한다."""
    vibe_text: str = Field(min_length=2, max_length=2000, description="캐릭터 바이브 텍스트")
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
    name: str
    age: str
    gender: str
    occupation: str
    core_tension: str
    interpretation: str
    realism_level: str


# --- 엔드포인트 ---

@router.get("/personas")
async def list_personas(request: Request) -> list[PersonaListItem]:
    """모든 페르소나 카드 목록을 반환한다.

    TODO: PersonaCard 리포지토리 연결 (Phase 3 DB 스키마 완료 후)
    """
    return []


@router.get("/personas/{persona_id}")
async def get_persona(persona_id: str, request: Request) -> dict[str, Any]:
    """페르소나 카드 상세를 반환한다.

    TODO: PersonaCard 리포지토리 연결
    """
    raise HTTPException(status_code=404, detail="페르소나를 찾을 수 없습니다")


@router.post("/personas/vibe-fill")
async def vibe_fill(body: VibeFillRequest, request: Request) -> PersonaSummaryResponse:
    """바이브 텍스트로 9섹션 페르소나를 자동 생성한다.

    TODO: VibeFillService v2 연결 (9섹션 프롬프트 리팩토링 후)
    """
    # 임시 응답 — 실제 AI 생성은 VibeFillService v2 연결 후 구현
    return PersonaSummaryResponse(
        name="(생성 대기)",
        age="",
        gender="",
        occupation="",
        core_tension="",
        interpretation=f"바이브 입력: {body.vibe_text[:100]}",
        realism_level="grounded",
    )


@router.delete("/personas/{persona_id}")
async def delete_persona(persona_id: str, request: Request) -> dict[str, bool]:
    """페르소나를 삭제한다.

    TODO: PersonaCard 리포지토리 연결
    """
    raise HTTPException(status_code=404, detail="페르소나를 찾을 수 없습니다")
