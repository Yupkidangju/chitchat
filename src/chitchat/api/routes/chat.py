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

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from chitchat.api.dependencies import (
    get_chat_service,
    get_dynamic_state_engine,
    get_repos,
)
from chitchat.db.repositories import RepositoryRegistry
from chitchat.services.chat_service import ChatService
from chitchat.services.dynamic_state_engine import DynamicStateEngine

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


# --- 엔드포인트 ---

@router.get("/sessions")
async def list_sessions(svc: ChatService = Depends(get_chat_service)) -> list[SessionResponse]:
    """모든 채팅 세션을 반환한다."""
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
    body: SessionCreateRequest, svc: ChatService = Depends(get_chat_service),
) -> SessionResponse:
    """새 채팅 세션을 생성한다."""
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
async def get_session(
    session_id: str, svc: ChatService = Depends(get_chat_service),
) -> dict[str, Any]:
    """세션 상세 + 메시지 목록을 반환한다."""
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
    session_id: str, message_id: str,
    svc: ChatService = Depends(get_chat_service),
) -> dict[str, Any]:
    """[v1.0.0] 단일 메시지의 프롬프트 스냅샷을 반환한다.

    designs.md §9.9 프롬프트 Inspector에서 사용한다.
    assistant 메시지에만 스냅샷이 존재하며, 없으면 404를 반환한다.
    """
    import json
    messages = svc.get_session_messages(session_id)
    target = next((m for m in messages if m.id == message_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="메시지를 찾을 수 없습니다")
    if not target.prompt_snapshot_json:
        raise HTTPException(status_code=404, detail="이 메시지에는 프롬프트 스냅샷이 없습니다")
    result: dict[str, Any] = json.loads(target.prompt_snapshot_json)
    return result


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str, svc: ChatService = Depends(get_chat_service),
) -> dict[str, bool]:
    """채팅 세션을 삭제한다."""
    ok = svc.delete_session(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
    return {"deleted": True}


@router.get("/sessions/{session_id}/dynamic-state")
async def get_dynamic_state(
    session_id: str,
    repos: RepositoryRegistry = Depends(get_repos),
    dse: DynamicStateEngine = Depends(get_dynamic_state_engine),
) -> dict[str, Any]:
    """세션의 캐릭터 동적 상태를 반환한다.

    [v1.0.0 Phase 7] DynamicStateEngine으로 ZSTD blob을 해동하여 JSON으로 반환한다.
    """
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
async def chat_websocket(
    websocket: WebSocket,
    session_id: str,
    chat_service: ChatService = Depends(get_chat_service),
) -> None:
    """WebSocket 채팅 스트리밍.

    [v1.0.0 Phase 5] 실제 AI 스트리밍 연결:
    1. 사용자 메시지를 DB에 저장한다.
    2. ChatService.start_stream()이 프롬프트를 조립하고 Provider 스트리밍을 실행한다.
    3. 각 청크를 WebSocket JSON으로 실시간 전송한다.
    4. 완료 시 "done" 타입을 전송한다.

    [v1.1.1] SC-09 스트리밍 취소:
    - 스트리밍 중에도 receive loop를 유지하여 cancel 메시지 수신 가능
    - 클라이언트가 {"type": "cancel"} 전송 시 streaming Task를 취소

    ChatProfile/UserPersona가 미설정된 세션은 에코 모드로 폴백한다.

    WebSocket 메시지 프로토콜:
    - {"type": "chunk", "content": "..."} — 스트리밍 청크
    - {"type": "done", "content": "", "usage": {...}} — 스트리밍 완료
    - {"type": "error", "content": "에러 메시지"} — 스트리밍 에러
    - 수신: {"type": "cancel"} — 스트리밍 취소 요청 (v1.1.1)
    """
    import json

    # 세션 존재 확인
    session = chat_service.get_session(session_id)
    if not session:
        await websocket.close(code=4004, reason="세션을 찾을 수 없습니다")
        return

    await websocket.accept()

    # [v1.1.1] 현재 스트리밍 태스크 추적
    streaming_task: asyncio.Task[None] | None = None

    try:
        while True:
            # [v1.1.1] 스트리밍 중이면 receive와 streaming을 동시 대기
            # 스트리밍 중이 아니면 receive만 대기 (일반 메시지 수신 루프)
            if streaming_task and not streaming_task.done():
                # 스트리밍 진행 중 — cancel 메시지를 받기 위해 receive도 대기
                receive_task = asyncio.create_task(websocket.receive_text())
                done_tasks, _ = await asyncio.wait(
                    {receive_task, streaming_task},
                    return_when=asyncio.FIRST_COMPLETED,
                )

                if streaming_task in done_tasks:
                    # 스트리밍 완료 — 예외 전파 체크
                    streaming_task.result()  # 예외가 있으면 여기서 raise
                    streaming_task = None
                    # receive_task가 아직 대기 중이면 취소 (다음 루프에서 새로 받음)
                    if not receive_task.done():
                        receive_task.cancel()
                        try:
                            await receive_task
                        except (asyncio.CancelledError, Exception):
                            pass
                    continue

                if receive_task in done_tasks:
                    # 스트리밍 중 메시지 수신 — cancel인지 확인
                    data = receive_task.result()
                    try:
                        msg = json.loads(data)
                        if isinstance(msg, dict) and msg.get("type") == "cancel":
                            # [v1.1.1] 스트리밍 취소 요청
                            streaming_task.cancel()
                            logger.info("스트리밍 취소 요청: 세션 %s", session_id)
                            try:
                                await streaming_task
                            except asyncio.CancelledError:
                                pass
                            streaming_task = None
                            continue
                    except (json.JSONDecodeError, TypeError):
                        pass  # 스트리밍 중 일반 메시지 — 무시 (동시 전송 방지)
                    continue

            else:
                # 스트리밍 중이 아님 — 일반 receive loop
                streaming_task = None  # 완료된 task 정리
                data = await websocket.receive_text()

                # [v1.1.1] cancel 메시지가 스트리밍 종료 후 도착했으면 무시
                try:
                    msg = json.loads(data)
                    if isinstance(msg, dict) and msg.get("type") == "cancel":
                        continue
                except (json.JSONDecodeError, TypeError):
                    pass

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
                    # [v1.1.1] 실제 AI 스트리밍 — Task로 생성 후 다음 루프에서 동시 대기
                    streaming_task = asyncio.create_task(
                        _stream_ai_response(websocket, chat_service, session_id),
                    )
                    # Task를 await하지 않고 루프 상단의 동시 대기로 넘어감
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
    finally:
        # [v1.1.1] 진행 중인 스트리밍이 있으면 확실하게 취소 — 좀비 Task 방지
        if streaming_task and not streaming_task.done():
            streaming_task.cancel()
            try:
                await streaming_task
            except (asyncio.CancelledError, Exception):
                pass
            logger.debug("스트리밍 태스크 정리 완료: 세션 %s", session_id)


async def _stream_ai_response(
    websocket: WebSocket,
    chat_service: Any,
    session_id: str,
) -> None:
    """ChatService.start_stream()을 WebSocket 콜백으로 연결한다.

    chunk 콜백에서 각 delta를 WebSocket JSON으로 전송하고,
    완료/에러 시 적절한 메시지를 전송한다.

    [v1.1.1] asyncio.CancelledError를 전파하여 cancel 프로토콜을 지원한다.
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
    except asyncio.CancelledError:
        # [v1.1.1] 스트리밍 취소 시 stopped 메시지 전송
        logger.info("스트리밍 취소 완료: 세션 %s", session_id)
        await websocket.send_json({
            "type": "error",
            "content": "스트리밍이 취소되었습니다.",
        })
        raise  # CancelledError 전파하여 상위에서 정리
    except Exception as e:
        logger.error("AI 스트리밍 예외: %s", e)
        await websocket.send_json({"type": "error", "content": str(e)})

