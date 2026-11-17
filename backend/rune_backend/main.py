from __future__ import annotations
from uuid import uuid4
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from rune_backend.config import get_settings
from rune_backend.routes import router

settings=get_settings()
app=FastAPI(title="RUNE Backend",description="Identity, trusted-device and remote task boundary for RUNE.",
            version="0.2.0",docs_url="/docs" if settings.backend_env=="development" else None,redoc_url=None)
app.add_middleware(CORSMiddleware,allow_origins=settings.backend_allowed_origins,allow_credentials=True,
    allow_methods=["GET","POST","PATCH","DELETE","OPTIONS"],
    allow_headers=["Authorization","Content-Type","X-Request-ID","X-RUNE-Device-Token"])
app.include_router(router)

@app.middleware("http")
async def attach_request_id(request:Request,call_next):
    request_id=request.headers.get("X-Request-ID") or str(uuid4())
    request.state.request_id=request_id
    response=await call_next(request)
    response.headers["X-Request-ID"]=request_id
    return response

@app.get("/health",tags=["system"])
async def health(request:Request)->JSONResponse:
    return JSONResponse(status_code=200,content={"status":"ok","service":"rune-backend","request_id":request.state.request_id})

@app.get("/ready",tags=["system"])
async def readiness(request:Request)->JSONResponse:
    identity=bool(settings.supabase_url and settings.supabase_publishable_key)
    database=bool(settings.supabase_url and settings.supabase_secret_key)
    ready=identity and database
    return JSONResponse(status_code=200 if ready else 503,content={
        "status":"ready" if ready else "not_ready","identity_configured":identity,
        "database_configured":database,"request_id":request.state.request_id})
