# src/chitchat/api/routes/chat.py
# [v1.0.0] 채팅 세션 REST API + WebSocket 스트리밍
#
# [v1.0.0 Phase 5 변경사항]
# - WebSocket 에코 모드 → ChatService.start_stream() 실제 AI 스트리밍 연결
# - ChatProfile 미설정 세션은 에코 모드로 폴백
# - chunk/done/error 3종 메시지 프로토콜 구현

from __future__ import annotations

import asyncio
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


class MessageResponse(BaseModel):
    """채팅 메시지 응답."""
    id: str
    role: str
    content: str
    created_at: str
    # [v1.0.0] 프롬프트 Inspector — assistant 메시지에만 스냅샷 포함
    prompt_snapshot_json: str | None = None


class SendMessageRequest(BaseModel):
    """메시지 전송 요청."""
    content: str = Field(min_length=1)


# --- 서비스 접근 헬퍼 ---

def _get_chat_service(request: Request) -> Any:
    """요청에서 ChatService를 가져온다."""
    return request.app.state.chat_service


# --- 엔드포인트 ---

@router.get("/sessions")
async def list_sessions(request: Request) -> list[SessionResponse]:
    """모든 채팅 세션을 반환한다."""
    svc = _get_chat_service(request)
    rows = svc.get_all_sessions()
    return [
        SessionResponse(
            id=r.id,
            title=r.title,
            status=r.status,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.post("/sessions", status_code=201)
async def create_session(
    body: SessionCreateRequest, request: Request,
) -> SessionResponse:
    """새 채팅 세션을 생성한다."""
    svc = _get_chat_service(request)
    row = svc.create_session(
        title=body.title,
        chat_profile_id=body.chat_profile_id,
        user_persona_id=body.user_persona_id,
    )
    return SessionResponse(
        id=row.id,
        title=row.title,
        status=row.status,
        created_at=row.created_at,
    )


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, request: Request) -> dict[str, Any]:
    """세션 상세 + 메시지 목록을 반환한다."""
    svc = _get_chat_service(request)
    session = svc.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")

    messages = svc.get_session_messages(session_id)
    return {
        "id": session.id,
        "title": session.title,
        "status": session.status,
        "created_at": session.created_at,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at,
                # [v1.0.0] 프롬프트 Inspector — 스냅샷 JSON 포함
                "prompt_snapshot_json": m.prompt_snapshot_json,
            }
            for m in messages
        ],
    }


@router.get("/sessions/{session_id}/messages/{message_id}/snapshot")
async def get_message_snapshot(
    session_id: str, message_id: str, request: Request,
) -> dict[str, Any]:
    """[v1.0.0] 단일 메시지의 프롬프트 스냅샷을 반환한다.

    designs.md §9.9 프롬프트 Inspector에서 사용한다.
    assistant 메시지에만 스냅샷이 존재하며, 없으면 404를 반환한다.
    """
    import json
    svc = _get_chat_service(request)
    messages = svc.get_session_messages(session_id)
    target = next((m for m in messages if m.id == message_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="메시지를 찾을 수 없습니다")
    if not target.prompt_snapshot_json:
        raise HTTPException(status_code=404, detail="이 메시지에는 프롬프트 스냅샷이 없습니다")
    return json.loads(target.prompt_snapshot_json)


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, request: Request) -> dict[str, bool]:
    """채팅 세션을 삭제한다."""
    svc = _get_chat_service(request)
    ok = svc.delete_session(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
    return {"deleted": True}


@router.get("/sessions/{session_id}/dynamic-state")
async def get_dynamic_state(session_id: str, request: Request) -> dict[str, Any]:
    """세션의 캐릭터 동적 상태를 반환한다.

    [v1.0.0 Phase 7] DynamicStateEngine으로 ZSTD blob을 해동하여 JSON으로 반환한다.
    """
    repos = request.app.state.repos
    dse = request.app.state.dynamic_state_engine

    ds_row = repos.dynamic_states.get_by_session(session_id)
    if not ds_row:
        return {
            "exists": False,
            "session_id": session_id,
            "message": "이 세션에 동적 상태가 아직 없습니다.",
        }

    state = dse.decompress_state(ds_row.state_blob)
    return {
        "exists": True,
        "session_id": session_id,
        "character_id": state.character_id,
        "turn_count": state.turn_count,
        "version": state.version,
        "updated_at": state.updated_at_iso,
        "relationship": {
            "trust": state.relationship_state.trust,
            "familiarity": state.relationship_state.familiarity,
            "emotional_reliance": state.relationship_state.emotional_reliance,
            "comfort_with_silence": state.relationship_state.comfort_with_silence,
            "willingness_to_initiate": state.relationship_state.willingness_to_initiate,
            "fear_of_rejection": state.relationship_state.fear_of_rejection,
            "boundary_sensitivity": state.relationship_state.boundary_sensitivity,
            "repair_ability": state.relationship_state.repair_ability,
        },
        "emotional_state": state.current_emotional_state,
        "defense_strategy": state.active_defense_strategy,
        "memories": [
            {
                "id": m.id,
                "trigger": m.trigger_type,
                "content": m.content,
                "impact": m.emotional_impact,
                "turn": m.turn_number,
            }
            for m in state.memories[-10:]
        ],
        "events": [
            {
                "id": e.id,
                "type": e.event_type,
                "description": e.description,
                "turn": e.turn_number,
            }
            for e in state.events[-5:]
        ],
    }


@router.websocket("/ws/chat/{session_id}")
async def chat_websocket(websocket: WebSocket, session_id: str) -> None:
    """WebSocket 채팅 스트리밍.

    [v1.0.0 Phase 5] 실제 AI 스트리밍 연결:
    1. 사용자 메시지를 DB에 저장한다.
    2. ChatService.start_stream()이 프롬프트를 조립하고 Provider 스트리밍을 실행한다.
    3. 각 청크를 WebSocket JSON으로 실시간 전송한다.
    4. 완료 시 "done" 타입을 전송한다.

    ChatProfile/UserPersona가 미설정된 세션은 에코 모드로 폴백한다.

    WebSocket 메시지 프로토콜:
    - {"type": "chunk", "content": "..."} — 스트리밍 청크
    - {"type": "done", "content": "", "usage": {...}} — 스트리밍 완료
    - {"type": "error", "content": "에러 메시지"} — 스트리밍 에러
    """
    # ChatService 접근
    chat_service = websocket.app.state.chat_service

    # 세션 존재 확인
    session = chat_service.get_session(session_id)
    if not session:
        await websocket.close(code=4004, reason="세션을 찾을 수 없습니다")
        return

    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()

            # 사용자 메시지 저장
            chat_service.save_user_message(session_id, data)

            # ChatProfile 존재 여부에 따라 AI 스트리밍 또는 에코 모드 결정
            session = chat_service.get_session(session_id)
            has_profile = bool(
                session
                and session.chat_profile_id
                and session.user_persona_id
            )

            if has_profile:
                # [v1.0.0] 실제 AI 스트리밍
                await _stream_ai_response(websocket, chat_service, session_id)
            else:
                # ChatProfile 미설정 시 에코 모드 폴백
                echo_response = f"[에코] {data}"
                chat_service.save_assistant_message(session_id, echo_response)
                await websocket.send_json({
                    "type": "chunk",
                    "content": echo_response,
                })
                await websocket.send_json({
                    "type": "done",
                    "content": "",
                })
    except WebSocketDisconnect:
        logger.info("WebSocket 연결 종료: 세션 %s", session_id)


async def _stream_ai_response(
    websocket: WebSocket,
    chat_service: Any,
    session_id: str,
) -> None:
    """ChatService.start_stream()을 WebSocket 콜백으로 연결한다.

    chunk 콜백에서 각 delta를 WebSocket JSON으로 전송하고,
    완료/에러 시 적절한 메시지를 전송한다.
    """
    # 완료/에러 상태를 추적하는 이벤트
    done_event = asyncio.Event()
    result: dict[str, Any] = {"error": None}

    # 현재 이벤트 루프 참조 — 콜백에서 안전한 전송을 위해 사용
    loop = asyncio.get_running_loop()

    def on_chunk(delta: str) -> None:
        """스트리밍 청크를 WebSocket으로 전송한다."""
        asyncio.run_coroutine_threadsafe(
            websocket.send_json({"type": "chunk", "content": delta}),
            loop,
        )

    def on_finish(full_text: str, usage: dict[str, object] | None, message_id: str) -> None:
        """스트리밍 완료 시 done 메시지를 전송한다.

        [v1.0.0] message_id를 포함하여 프론트엔드가 Inspector 스냅샷을 조회할 수 있게 한다.
        """
        asyncio.run_coroutine_threadsafe(
            websocket.send_json({
                "type": "done", "content": "", "usage": usage,
                "message_id": message_id,
            }),
            loop,
        )
        done_event.set()

    def on_error(error_msg: str) -> None:
        """스트리밍 에러 시 error 메시지를 전송한다."""
        result["error"] = error_msg
        asyncio.run_coroutine_threadsafe(
            websocket.send_json({"type": "error", "content": error_msg}),
            loop,
        )
        done_event.set()

    # 스트리밍 실행 — start_stream은 async이므로 직접 await
    try:
        await chat_service.start_stream(session_id, on_chunk, on_finish, on_error)
    except Exception as e:
        logger.error("AI 스트리밍 예외: %s", e)
        await websocket.send_json({"type": "error", "content": str(e)})


