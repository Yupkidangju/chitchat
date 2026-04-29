# src/chitchat/ui/async_bridge.py
# [v0.1.0b0] asyncio ↔ Qt 스레드 안전 브리지
#
# worker 스레드에서 asyncio 코루틴을 실행하고,
# 결과를 Qt Signal/Slot으로 메인 스레드에 전달한다.
# 모든 UI 갱신은 반드시 Signal.emit()을 통해 메인 스레드에서 수행된다.
#
# [v0.1.0b0 Hardening] 공용 비동기 실행 패턴:
#   - run_coroutine_in_thread: 단발성 비동기 작업 (연결 테스트, 모델 패치, Validate 등)
#   - run_stream_in_thread: 스트리밍 작업 (채팅 응답)
#   - cancel_stream: loop.call_soon_threadsafe(task.cancel)로 thread-safe 취소
#   - task_finished: finally에서 항상 발생 → busy 상태 해제용
from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import Callable, Coroutine
from typing import Any

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


class AsyncSignalBridge(QObject):
    """asyncio 결과를 Qt 메인 스레드로 전달하는 Signal 브리지.

    모든 비동기 작업의 결과는 Signal/Slot으로 메인 스레드에서 처리된다.
    UI 계층은 이 브리지만 사용하고, threading을 직접 관리하지 않는다.

    Signals:
        chunk_received(str): 스트리밍 delta 텍스트.
        stream_finished(str, object): 스트리밍 완료 (full_text, usage_dict_or_None).
        stream_error(str): 스트리밍 에러 메시지.
        task_result(object): 범용 비동기 작업 결과.
        task_error(str): 범용 비동기 작업 에러.
        task_finished(): 비동기 작업 종료 (성공/실패 무관). busy 해제용.
    """

    # 스트리밍 전용 시그널
    chunk_received = Signal(str)
    stream_finished = Signal(str, object)  # (full_text, usage_dict_or_None)
    stream_error = Signal(str)

    # 범용 비동기 작업 시그널
    task_result = Signal(object)  # 결과 객체
    task_error = Signal(str)
    task_finished = Signal()  # finally — 성공/실패 무관하게 항상 발생

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._current_loop: asyncio.AbstractEventLoop | None = None
        self._current_task: asyncio.Task[Any] | None = None
        self._busy = False

    @property
    def is_busy(self) -> bool:
        """현재 비동기 작업이 실행 중인지 반환한다."""
        return self._busy

    # --- 범용 비동기 작업 ---

    def run_coroutine_in_thread(self, coro: Coroutine[Any, Any, Any]) -> None:
        """코루틴을 별도 스레드의 asyncio 이벤트 루프에서 실행한다.

        결과는 task_result / task_error Signal로 메인 스레드에 전달된다.
        작업 종료 시 task_finished Signal이 항상 발생한다.

        사용 예:
            bridge.run_coroutine_in_thread(provider_service.test_connection(pid))
            bridge.run_coroutine_in_thread(provider_service.fetch_models(pid))
        """
        if self._busy:
            logger.warning("이전 작업이 실행 중. 새 작업 무시됨.")
            return

        self._busy = True

        def _worker() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._current_loop = loop
            try:
                result = loop.run_until_complete(coro)
                self.task_result.emit(result)
            except Exception as e:
                logger.error("비동기 작업 실패: %s", e)
                self.task_error.emit(str(e))
            finally:
                self._current_loop = None
                self._busy = False
                loop.close()
                self.task_finished.emit()

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

    # --- 스트리밍 ---

    def run_stream_in_thread(
        self,
        stream_coro_factory: Callable[
            [Callable[[str], None], Callable[[str, dict[str, Any] | None], None], Callable[[str], None]],
            Coroutine[Any, Any, Any],
        ],
    ) -> None:
        """스트리밍 코루틴을 별도 스레드에서 실행한다.

        콜백을 Signal.emit으로 래핑하여 thread-safe하게 UI에 전달한다.
        작업 종료 시 task_finished Signal이 항상 발생한다.

        Args:
            stream_coro_factory: (on_chunk, on_finish, on_error) → 코루틴을 반환하는 팩토리.
        """
        if self._busy:
            logger.warning("이전 작업이 실행 중. 스트리밍 요청 무시됨.")
            return

        self._busy = True

        def _on_chunk(delta: str) -> None:
            self.chunk_received.emit(delta)

        def _on_finish(full_text: str, usage: dict[str, Any] | None) -> None:
            self.stream_finished.emit(full_text, usage)

        def _on_error(msg: str) -> None:
            self.stream_error.emit(msg)

        def _worker() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._current_loop = loop
            try:
                coro = stream_coro_factory(_on_chunk, _on_finish, _on_error)
                task = loop.create_task(coro)
                self._current_task = task
                loop.run_until_complete(task)
            except asyncio.CancelledError:
                logger.info("스트리밍 Task 취소됨.")
            except Exception as e:
                logger.error("스트리밍 스레드 에러: %s", e)
                self.stream_error.emit(str(e))
            finally:
                self._current_task = None
                self._current_loop = None
                self._busy = False
                loop.close()
                self.task_finished.emit()

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

    def cancel_stream(self) -> None:
        """현재 스트리밍을 thread-safe하게 취소한다.

        loop.call_soon_threadsafe(task.cancel)로 올바른 이벤트 루프에서 취소한다.
        """
        task = self._current_task
        loop = self._current_loop
        if task and loop and not task.done():
            loop.call_soon_threadsafe(task.cancel)
            logger.info("스트리밍 취소 요청 (thread-safe).")
