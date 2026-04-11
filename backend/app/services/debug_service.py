import time
import uuid
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass, field, asdict
from collections import deque
import threading

MAX_REQUESTS = 500
MAX_AI_CALLS = 1000


@dataclass
class RequestRecord:
    id: str
    method: str
    path: str
    query_params: dict
    user_id: Optional[str]
    status_code: int
    started_at: str
    duration_ms: float
    request_body: Optional[str] = None
    response_body: Optional[str] = None
    headers: dict = field(default_factory=dict)


@dataclass
class AICallRecord:
    id: str
    started_at: str
    duration_ms: float
    model: str
    function_name: str
    messages: list
    response: str
    error: Optional[str] = None


class DebugService:
    _instance: Optional["DebugService"] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._requests: deque[RequestRecord] = deque(maxlen=MAX_REQUESTS)
        self._ai_calls: deque[AICallRecord] = deque(maxlen=MAX_AI_CALLS)
        self._request_lock = threading.Lock()
        self._ai_lock = threading.Lock()

    def clear_all(self):
        with self._request_lock:
            self._requests.clear()
        with self._ai_lock:
            self._ai_calls.clear()

    def record_request(
        self,
        method: str,
        path: str,
        query_params: dict,
        user_id: Optional[str],
        request_body: Optional[str] = None,
        headers: dict = None,
    ) -> str:
        record_id = str(uuid.uuid4())[:8]
        now = datetime.now(timezone.utc).isoformat()
        record = RequestRecord(
            id=record_id,
            method=method,
            path=path,
            query_params=query_params,
            user_id=user_id,
            status_code=0,
            started_at=now,
            duration_ms=0,
            request_body=request_body,
            headers=headers or {},
        )
        with self._request_lock:
            self._requests.append(record)
        return record_id

    def finish_request(
        self,
        record_id: str,
        status_code: int,
        duration_ms: float,
        response_body: Optional[str] = None,
    ):
        with self._request_lock:
            for record in self._requests:
                if record.id == record_id:
                    record.status_code = status_code
                    record.duration_ms = duration_ms
                    record.response_body = response_body
                    break

    def record_ai_call(
        self,
        function_name: str,
        model: str,
        messages: list,
        response: str,
        duration_ms: float,
        error: Optional[str] = None,
    ) -> str:
        record_id = str(uuid.uuid4())[:8]
        now = datetime.now(timezone.utc).isoformat()
        record = AICallRecord(
            id=record_id,
            started_at=now,
            duration_ms=duration_ms,
            model=model,
            function_name=function_name,
            messages=messages,
            response=response,
            error=error,
        )
        with self._ai_lock:
            self._ai_calls.append(record)
        return record_id

    def get_requests(self) -> list[dict]:
        with self._request_lock:
            return [asdict(r) for r in reversed(list(self._requests))]

    def get_ai_calls(self) -> list[dict]:
        with self._ai_lock:
            return [asdict(r) for r in reversed(list(self._ai_calls))]

    def get_stats(self) -> dict:
        with self._request_lock:
            requests_list = list(self._requests)
        with self._ai_lock:
            ai_list = list(self._ai_calls)

        total_requests = len(requests_list)
        avg_request_duration = (
            sum(r.duration_ms for r in requests_list if r.duration_ms > 0)
            / total_requests
            if total_requests > 0
            else 0
        )

        total_ai_calls = len(ai_list)
        avg_ai_duration = (
            sum(c.duration_ms for c in ai_list) / total_ai_calls
            if total_ai_calls > 0
            else 0
        )

        return {
            "total_requests": total_requests,
            "avg_request_duration_ms": round(avg_request_duration, 2),
            "total_ai_calls": total_ai_calls,
            "avg_ai_duration_ms": round(avg_ai_duration, 2),
            "requests_per_minute": round(
                total_requests
                / max(1, len(set(r.started_at[:16] for r in requests_list))),
                1,
            ),
        }


_debug_service: Optional[DebugService] = None


def get_debug_service() -> DebugService:
    global _debug_service
    if _debug_service is None:
        _debug_service = DebugService()
    return _debug_service


class TrackingSession:
    def __init__(self):
        self.request_id: Optional[str] = None
        self.start_time: Optional[float] = None


def track_request(
    method: str,
    path: str,
    query_params: dict,
    user_id: Optional[str] = None,
    request_body: Optional[str] = None,
    headers: dict = None,
) -> TrackingSession:
    session = TrackingSession()
    service = get_debug_service()
    session.request_id = service.record_request(
        method=method,
        path=path,
        query_params=query_params,
        user_id=user_id,
        request_body=request_body,
        headers=headers,
    )
    session.start_time = time.perf_counter()
    return session


def finish_request(
    session: TrackingSession,
    status_code: int,
    response_body: Optional[str] = None,
):
    if session.start_time is not None:
        duration_ms = (time.perf_counter() - session.start_time) * 1000
        service = get_debug_service()
        service.finish_request(
            record_id=session.request_id,
            status_code=status_code,
            duration_ms=duration_ms,
            response_body=response_body,
        )


def track_ai_call(
    function_name: str,
    model: str,
    messages: list,
    response: str,
    duration_ms: float,
    error: Optional[str] = None,
) -> str:
    service = get_debug_service()
    return service.record_ai_call(
        function_name=function_name,
        model=model,
        messages=messages,
        response=response,
        duration_ms=duration_ms,
        error=error,
    )


def patch_minimax_service():
    import time
    from . import minimax

    original_chatcompletion = minimax.chatcompletion
    original_chatcompletion_text = minimax.chatcompletion_text

    def tracked_chatcompletion(messages: list, model: str = "MiniMax-M2.7", **kwargs):
        start = time.perf_counter()
        error = None
        response = None
        try:
            response = original_chatcompletion(messages, model, **kwargs)
            return response
        except Exception as e:
            error = str(e)
            raise
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            response_text = ""
            if response and hasattr(response, "choices"):
                response_text = response.choices[0].message.content or ""
            track_ai_call(
                function_name="chatcompletion",
                model=model,
                messages=messages,
                response=response_text,
                duration_ms=duration_ms,
                error=error,
            )

    def tracked_chatcompletion_text(
        messages: list, model: str = "MiniMax-M2.7", **kwargs
    ) -> str:
        start = time.perf_counter()
        error = None
        response = ""
        try:
            response = original_chatcompletion_text(messages, model, **kwargs)
            return response
        except Exception as e:
            error = str(e)
            raise
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            track_ai_call(
                function_name="chatcompletion_text",
                model=model,
                messages=messages,
                response=response,
                duration_ms=duration_ms,
                error=error,
            )

    minimax.chatcompletion = tracked_chatcompletion
    minimax.chatcompletion_text = tracked_chatcompletion_text
