from contextlib import asynccontextmanager
import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException
from jose import jwt, JWTError
from .routes.holdings import router as holdings_router
from .routes.digest import router as digest_router
from .routes.dashboard import router as dashboard_router
from .routes.positions import router as positions_router
from .routes.trigger import router as trigger_router
from .routes.analysis_runs import router as analysis_runs_router
from .routes.alerts import router as alerts_router
from .routes.preferences import router as preferences_router
from .routes.prices import router as prices_router
from .routes.scheduler import router as scheduler_router
from .routes.test_push import router as test_push_router
from .routes.debug import router as debug_router
from .pipeline.scheduler import start_scheduler
from .services.apns import validate_apns_configuration
import base64
import json

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    apns_status = validate_apns_configuration()
    if apns_status["configured"]:
        logger.info("APNs configuration validated successfully")
    else:
        logger.warning(
            "APNs configuration is incomplete", extra={"issues": apns_status["issues"]}
        )
    start_scheduler()
    yield


app = FastAPI(title="Clavynx API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def decode_token_payload(token: str) -> dict:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        payload = parts[1]
        padded = payload + "=" * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(padded)
        return json.loads(decoded)
    except Exception:
        return None


@app.middleware("http")
async def validate_jwt_middleware(request: Request, call_next):
    if request.url.path in ["/health", "/docs", "/openapi.json", "/redoc"]:
        return await call_next(request)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        if any(
            request.url.path.startswith(p)
            for p in [
                "/holdings",
                "/digest",
                "/dashboard",
                "/positions",
                "/trigger-analysis",
                "/analysis-runs",
                "/alerts",
                "/preferences",
                "/prices",
                "/scheduler",
                "/test-push",
            ]
        ):
            raise HTTPException(401, "Missing Authorization header")
        return await call_next(request)

    token = auth_header[7:]

    try:
        from .config import get_settings

        settings = get_settings()

        payload = decode_token_payload(token)
        if not payload:
            raise HTTPException(401, "Invalid token format")

        if "sub" not in payload:
            raise HTTPException(401, "Please sign in again - no user ID in token")

        # Get user ID from payload (payload is already decoded and validated by Supabase)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(401, "Please sign in again - no user ID in token")

        request.state.user_id = user_id

    except HTTPException:
        raise
    except JWTError as e:
        print(f"JWT Error: {e}")
        raise HTTPException(401, f"Invalid token")
    except Exception as e:
        print(f"Auth error: {e}")
        raise HTTPException(401, "Authentication failed")

    return await call_next(request)


@app.middleware("http")
async def debug_middleware(request: Request, call_next):
    from .services.debug_service import track_request, finish_request
    import json

    if request.url.path.startswith("/debug"):
        return await call_next(request)

    query_params = dict(request.query_params)
    headers = dict(request.headers)
    body = None

    if request.method in ["POST", "PATCH", "PUT"]:
        body_bytes = await request.body()
        if body_bytes:
            try:
                body = body_bytes.decode("utf-8")
                json_body = json.loads(body)
                body = json.dumps(json_body, indent=2)
            except:
                body = body_bytes.decode("utf-8", errors="replace")
        request._body = body_bytes

    user_id = getattr(request.state, "user_id", None)

    session = track_request(
        method=request.method,
        path=request.url.path,
        query_params=query_params,
        user_id=user_id,
        request_body=body,
        headers={
            k: v
            for k, v in headers.items()
            if k.lower() not in ["authorization", "cookie"]
        },
    )

    start_time = time.perf_counter()
    try:
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000
        response_body = None
        if hasattr(response, "body"):
            response_body = (
                response.body.decode("utf-8", errors="replace")
                if hasattr(response.body, "decode")
                else str(response.body)
            )
        elif hasattr(response, "stream_content"):
            response_body = "[streamed]"
        finish_request(session, response.status_code, response_body)
        return response
    except HTTPException as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        finish_request(session, e.status_code, str(e.detail))
        raise
    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        finish_request(session, 500, str(e))
        raise


@app.get("/health")
async def health():
    return {"status": "ok"}


app.include_router(holdings_router, prefix="/holdings", tags=["holdings"])
app.include_router(digest_router, prefix="/digest", tags=["digest"])
app.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
app.include_router(positions_router, prefix="/positions", tags=["positions"])
app.include_router(trigger_router, prefix="/trigger-analysis", tags=["analysis"])
app.include_router(
    analysis_runs_router, prefix="/analysis-runs", tags=["analysis-runs"]
)
app.include_router(alerts_router, prefix="/alerts", tags=["alerts"])
app.include_router(preferences_router, prefix="/preferences", tags=["preferences"])
app.include_router(prices_router, prefix="/prices", tags=["prices"])
app.include_router(scheduler_router, prefix="/scheduler", tags=["scheduler"])
app.include_router(test_push_router, prefix="/test-push", tags=["test-push"])
app.include_router(debug_router, prefix="/debug", tags=["debug"])
