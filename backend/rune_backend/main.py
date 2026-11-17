from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from rune_backend.config import get_settings

settings = get_settings()

app = FastAPI(
    title="RUNE Backend",
    description="Private remote API boundary for RUNE clients.",
    version="0.1.0",
    docs_url="/docs" if settings.backend_env == "development" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)


@app.middleware("http")
async def attach_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/health", tags=["system"])
async def health(request: Request) -> JSONResponse:
    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "service": "rune-backend",
            "request_id": request.state.request_id,
        },
    )


@app.get("/ready", tags=["system"])
async def readiness(request: Request) -> JSONResponse:
    # Database/auth readiness checks will be added after the dedicated
    # RUNE Supabase project is provisioned and its schema is installed.
    return JSONResponse(
        status_code=503,
        content={
            "status": "not_ready",
            "reason": "identity and database services are not configured",
            "request_id": request.state.request_id,
        },
    )
