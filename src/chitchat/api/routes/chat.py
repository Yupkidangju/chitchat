# src/chitchat/api/routes/chat.py
# [v1.0.0] 채팅 세션 REST API + WebSocket 스트리밍
#
# 채팅 세션 CRUD와 WebSocket을 통한 실시간 스트리밍 응답을 제공한다.
# 동적 상태 엔진(DynamicStateEngine)이 매 AI 응답 후 캐릭터 상태를 갱신한다.

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()


# --- 요청/응답 스키마 ---

class SessionCreateRequest(BaseModel):
    """채팅 세션 생성 요청."""
    title: str = Field(min_length=1, max_length=120)
    chat_profile_id: str
    user_persona_id: str


class SessionResponse(BaseModel):
    """채팅 세션 응답."""
    id: str
    title: str
    status: str
    created_at: str


class SendMessageRequest(BaseModel):
    """메시지 전송 요청."""
    content: str = Field(min_length=1)


# --- 엔드포인트 ---

@router.get("/sessions")
async def list_sessions(request: Request) -> list[SessionResponse]:
    """모든 채팅 세션을 반환한다.

    TODO: ChatService 연결
    """
    return []


@router.post("/sessions", status_code=201)
async def create_session(
    body: SessionCreateRequest, request: Request,
) -> SessionResponse:
    """새 채팅 세션을 생성한다.

    TODO: ChatService 연결
    """
    raise HTTPException(status_code=501, detail="채팅 세션 생성 미구현")


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, request: Request) -> dict[str, Any]:
    """세션 상세 + 메시지 목록을 반환한다.

    TODO: ChatService 연결
    """
    raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")


@router.get("/sessions/{session_id}/dynamic-state")
async def get_dynamic_state(session_id: str, request: Request) -> dict[str, Any]:
    """세션 내 캐릭터의 현재 동적 상태를 반환한다.

    관계 변수, 기억 목록, 감정 상태, 이벤트 로그를 포함한다.

    TODO: DynamicStateEngine 연결
    """
    raise HTTPException(status_code=404, detail="동적 상태를 찾을 수 없습니다")


@router.websocket("/ws/chat/{session_id}")
async def chat_websocket(websocket: WebSocket, session_id: str) -> None:
    """WebSocket 채팅 스트리밍.

    클라이언트가 메시지를 전송하면:
    1. 프롬프트 어셈블러 v2가 동적 상태를 주입하여 프롬프트를 조립한다.
    2. Provider adapter가 스트리밍 응답을 생성한다.
    3. 각 청크를 WebSocket으로 실시간 전송한다.
    4. 응답 완료 후 DynamicStateEngine이 상태를 갱신한다.

    TODO: ChatService + DynamicStateEngine 연결
    """
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            # 임시 에코 응답
            await websocket.send_json({
                "type": "chunk",
                "content": f"[에코] {data}",
            })
            await websocket.send_json({
                "type": "done",
                "content": "",
            })
    except WebSocketDisconnect:
        logger.info("WebSocket 연결 종료: 세션 %s", session_id)
