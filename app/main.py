"""
Secure ML inference service — Milestone 3 (Secure Deployment).
Owner: Ali Yasser — Security & DevSecOps Engineer

Security controls implemented in this file:
  1. Explicit CORS allow-list (never "*")
  2. Security response headers (HSTS, X-Content-Type-Options, X-Frame-Options, CSP)
  3. Global rate limiting (SlowAPI) to blunt brute-force / abuse (OWASP API4)
  4. Structured, PII-free audit logging
  5. No debug/reload in production, no stack traces leaked to clients
"""
import logging
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import (
    get_redoc_html,
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.auth import router as auth_router
from app.api.inference import router as inference_router
from app.core.config import get_settings
from app.core.limiter import limiter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("fraud_api")

settings = get_settings()

# Docs UI is always disabled in production (unchanged). In non-production,
# it's served through the custom routes below instead of FastAPI's built-in
# docs_url/redoc_url, which point at a CDN by default -- see the docs/redoc
# routes near the bottom of this file for why.
_DOCS_ENABLED = settings.ENVIRONMENT != "production"

app = FastAPI(
    title=settings.APP_NAME,
    docs_url=None,
    redoc_url=None,
)

# --- Rate limiting ---------------------------------------------------------
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# --- CORS: explicit allow-list only ----------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS or ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


# --- Security headers middleware -------------------------------------------
# Paths that serve an interactive HTML UI (not JSON) and therefore need a
# CSP that actually allows a script/stylesheet/inline-script to run. Every
# other path is a JSON API response, which has no legitimate need to load
# any resource at all -- those keep the strict `default-src 'none'`.
_DOCS_UI_PATH_PREFIXES = ("/docs", "/redoc", "/static/")


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start) * 1000

    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    if request.url.path.startswith(_DOCS_UI_PATH_PREFIXES):
        # Swagger UI / ReDoc need to run an inline bootstrap script and load
        # their own script/stylesheet; those assets are served from this
        # same origin (app/static/, mounted below) rather than a third-party
        # CDN, so 'self' covers them -- no wildcard needed. ReDoc's own font
        # stylesheet is still Google Fonts-hosted, so that one host (not a
        # wildcard) is allow-listed too. Found this after the previous
        # `default-src 'none'` silently blank-paged /docs even though the
        # CDN it used to point at was reachable -- the CSP, not the network,
        # was blocking it.
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "img-src 'self' data:; font-src 'self' https://fonts.gstatic.com"
        )
    else:
        response.headers["Content-Security-Policy"] = "default-src 'none'"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    # NOTE: the "Server: uvicorn" header cannot be stripped from middleware —
    # uvicorn sets it after the ASGI app returns. It is disabled at the
    # server level instead: see `--no-server-header` in Dockerfile CMD
    # (found during Milestone 3 pentest, remediated at the correct layer).

    logger.info(
        "request method=%s path=%s status=%s duration_ms=%.2f",
        request.method, request.url.path, response.status_code, duration_ms,
    )
    return response


# --- Global error handler: never leak stack traces to clients --------------
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("unhandled_error path=%s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please contact support."},
    )


# --- Routers -----------------------------------------------------------
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(inference_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["health"])
def health_check():
    """Liveness/readiness probe for AKS. Returns no sensitive information."""
    return {"status": "ok", "environment": settings.ENVIRONMENT}


# --- API documentation UI: self-hosted, not CDN-hosted ----------------------
# FastAPI's built-in docs_url/redoc_url pull swagger-ui/redoc's JS+CSS from
# cdn.jsdelivr.net at page-load time. That's a silent single point of failure
# in an otherwise fully local dev setup (blocked CDN, offline machine, or --
# as found here -- this file's own strict CSP -- all produce the same blank
# page with no visible error). Serving the same vendored files from this
# origin instead removes that dependency entirely; disabled in production
# exactly as the CDN-backed version was.
if _DOCS_ENABLED:
    _STATIC_DIR = Path(__file__).resolve().parent / "static"
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

    @app.get("/docs", include_in_schema=False)
    def custom_swagger_ui_html():
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} - Swagger UI",
            oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
            swagger_js_url="/static/swagger-ui-bundle.js",
            swagger_css_url="/static/swagger-ui.css",
            swagger_favicon_url="/static/favicon.png",
        )

    @app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
    def swagger_ui_redirect():
        return get_swagger_ui_oauth2_redirect_html()

    @app.get("/redoc", include_in_schema=False)
    def custom_redoc_html():
        return get_redoc_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} - ReDoc",
            redoc_js_url="/static/redoc.standalone.js",
            redoc_favicon_url="/static/favicon.png",
        )
