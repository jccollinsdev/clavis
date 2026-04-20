from contextlib import asynccontextmanager
import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from jose import jwt, JWTError
from .routes.holdings import router as holdings_router
from .routes.digest import router as digest_router
from .routes.dashboard import router as dashboard_router
from .routes.positions import router as positions_router
from .routes.trigger import router as trigger_router
from .routes.analysis_runs import router as analysis_runs_router
from .routes.alerts import router as alerts_router
from .routes.news import router as news_router
from .routes.preferences import router as preferences_router
from .routes.prices import router as prices_router
from .routes.account import router as account_router
from .routes.admin import router as admin_router
from .routes.scheduler import router as scheduler_router
from .routes.push_test_route import router as test_push_router
from .routes.debug import router as debug_router
from .routes.tickers import router as tickers_router
from .routes.watchlists import router as watchlists_router
from .routes.brokerage import router as brokerage_router
from .pipeline.scheduler import start_scheduler
from .services.apns import validate_apns_configuration
from .config import get_settings
from .services.supabase import get_supabase
import json

logger = logging.getLogger(__name__)
settings = get_settings()
allowed_origins = [
    origin.strip()
    for origin in settings.cors_allowed_origins.split(",")
    if origin.strip()
]
public_paths = {"/health", "/admin", "/admin/login", "/admin/logout"}
public_doc_paths = {"/docs", "/openapi.json", "/redoc"}


def _is_public_path(path: str) -> bool:
    if path in public_paths:
        return True
    if settings.enable_public_docs and path in public_doc_paths:
        return True
    return False


def configure_sentry() -> None:
    dsn = settings.sentry_dsn.strip()
    if not dsn:
        log_event(logging.INFO, "sentry_disabled")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration

        sentry_sdk.init(
            dsn=dsn,
            environment=settings.sentry_environment,
            integrations=[FastApiIntegration()],
            traces_sample_rate=settings.sentry_traces_sample_rate,
            profiles_sample_rate=settings.sentry_profiles_sample_rate,
            send_default_pii=False,
        )
        log_event(
            logging.INFO,
            "sentry_initialized",
            environment=settings.sentry_environment,
            traces_sample_rate=settings.sentry_traces_sample_rate,
            profiles_sample_rate=settings.sentry_profiles_sample_rate,
        )
    except Exception as exc:
        log_event(logging.WARNING, "sentry_init_failed", error=str(exc))


def log_event(level: int, event: str, **fields) -> None:
    payload = {"event": event, **fields}
    logger.log(level, json.dumps(payload, default=str, sort_keys=True))


configure_sentry()


@asynccontextmanager
async def lifespan(app: FastAPI):
    apns_status = validate_apns_configuration()
    if apns_status["configured"]:
        log_event(logging.INFO, "startup_apns_configured")
    else:
        log_event(
            logging.WARNING,
            "startup_apns_incomplete",
            issues=apns_status["issues"],
        )
    start_scheduler()
    yield


app = FastAPI(
    title="Clavynx API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.enable_public_docs else None,
    redoc_url="/redoc" if settings.enable_public_docs else None,
    openapi_url="/openapi.json" if settings.enable_public_docs else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def validate_jwt_middleware(request: Request, call_next):
    if request.method == "OPTIONS" or _is_public_path(request.url.path):
        return await call_next(request)

    if request.url.path.startswith("/admin/"):
        return await call_next(request)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        log_event(
            logging.WARNING,
            "auth_missing",
            method=request.method,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=401,
            content={"detail": "Missing Authorization header"},
        )

    token = auth_header[7:]

    try:
        user_response = get_supabase().auth.get_user(token)
        user = getattr(user_response, "user", None)
        user_id = getattr(user, "id", None)
        if not user_id:
            return JSONResponse(
                status_code=401,
                content={"detail": "Please sign in again - no user ID in token"},
            )

        request.state.user_id = str(user_id)

    except JWTError as e:
        log_event(
            logging.WARNING,
            "auth_invalid",
            method=request.method,
            path=request.url.path,
            error=str(e),
        )
        return JSONResponse(status_code=401, content={"detail": "Invalid token"})
    except HTTPException:
        raise
    except Exception as e:
        log_event(
            logging.ERROR,
            "auth_error",
            method=request.method,
            path=request.url.path,
            error=str(e),
        )
        return JSONResponse(
            status_code=401,
            content={"detail": "Authentication failed"},
        )

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
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
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
        log_event(
            logging.INFO,
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            user_id=user_id,
        )
        return response
    except HTTPException as e:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        finish_request(session, e.status_code, str(e.detail))
        log_event(
            logging.WARNING,
            "request_failed",
            method=request.method,
            path=request.url.path,
            status_code=e.status_code,
            duration_ms=duration_ms,
            error=str(e.detail),
            user_id=user_id,
        )
        raise
    except Exception as e:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        finish_request(session, 500, str(e))
        log_event(
            logging.ERROR,
            "request_exception",
            method=request.method,
            path=request.url.path,
            status_code=500,
            duration_ms=duration_ms,
            error=str(e),
            user_id=user_id,
        )
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
app.include_router(news_router, prefix="/news", tags=["news"])
app.include_router(preferences_router, prefix="/preferences", tags=["preferences"])
app.include_router(tickers_router, prefix="/tickers", tags=["tickers"])
app.include_router(watchlists_router, prefix="/watchlists", tags=["watchlists"])
app.include_router(brokerage_router, prefix="/brokerage", tags=["brokerage"])
app.include_router(prices_router, prefix="/prices", tags=["prices"])
app.include_router(account_router, prefix="/account", tags=["account"])
app.include_router(scheduler_router, prefix="/scheduler", tags=["scheduler"])
app.include_router(test_push_router, prefix="/test-push", tags=["test-push"])
app.include_router(debug_router, prefix="/debug", tags=["debug"])
app.include_router(admin_router, prefix="/admin", tags=["admin"])
