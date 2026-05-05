# src/chitchat/api/routes/health.py
# [v1.0.0] 헬스체크 엔드포인트
#
# 서버 상태 확인 및 기본 정보 반환을 담당한다.

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """서버 상태 확인 엔드포인트."""
    return {"status": "ok", "version": "1.0.0", "app": "chitchat"}
