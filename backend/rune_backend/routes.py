from __future__ import annotations
import hashlib, secrets, re
from datetime import datetime, timedelta, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException
from rune_backend.auth import Owner, require_owner
from rune_backend.schemas import DeviceHeartbeat, DeviceRegistration, TaskCreate, TaskResultInput
from rune_backend.store import owner_filter, store

router = APIRouter(prefix="/v1", tags=["RUNE remote operations"])

def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()

def _reject_secret_fields(value, path: str = "arguments", depth: int = 0) -> None:
    if depth > 8:
        raise HTTPException(400, "Task arguments are nested too deeply")
    forbidden = {"password", "passwd", "pin", "passcode", "secret", "secret_key",
                 "api_key", "access_token", "refresh_token", "session_cookie",
                 "private_key", "authorization", "credential"}
    if isinstance(value, dict):
        if len(value) > 32:
            raise HTTPException(400, "Too many task argument fields")
        for key, item in value.items():
            normalized = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(key)).lower().replace("-", "_")
            if normalized in forbidden or normalized.endswith(("_password", "_token", "_secret", "_api_key")):
                raise HTTPException(400, f"Sensitive field is not accepted in {path}")
            _reject_secret_fields(item, f"{path}.{key}", depth + 1)
    elif isinstance(value, list):
        if len(value) > 100:
            raise HTTPException(400, "Task argument list is too large")
        for index, item in enumerate(value):
            _reject_secret_fields(item, f"{path}[{index}]", depth + 1)
    elif isinstance(value, str) and len(value) > 4096:
        raise HTTPException(400, "Task argument text is too long")


def _validate_capability_arguments(capability: str, arguments: dict) -> None:
    if capability in {"app.list", "ui.observe"}:
        if arguments:
            raise HTTPException(400, f"{capability} does not accept arguments")
        return
    if capability == "app.launch":
        package_name = arguments.get("packageName", arguments.get("package_name"))
        if not isinstance(package_name, str) or not package_name.strip() or len(package_name) > 255:
            raise HTTPException(400, "app.launch requires a valid packageName")
        return
    if capability == "ui.interact":
        action = arguments.get("action")
        if action == "tap":
            x, y = arguments.get("x"), arguments.get("y")
            if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
                raise HTTPException(400, "tap requires numeric x and y coordinates")
            if not (0 <= x <= 10000 and 0 <= y <= 10000):
                raise HTTPException(400, "tap coordinates are outside the allowed range")
        elif action == "scroll":
            if arguments.get("direction", "down") not in {"up", "down"}:
                raise HTTPException(400, "scroll direction must be up or down")
        elif action == "type":
            value = arguments.get("text")
            if not isinstance(value, str) or not value or len(value) > 4000:
                raise HTTPException(400, "type requires text up to 4000 characters")
        else:
            raise HTTPException(400, "unsupported ui.interact action")
        return
    raise HTTPException(400, "capability is not implemented by the current device agent")

async def _audit(owner_id: UUID, event_type: str, outcome: str, *, device_id=None, task_id=None, metadata=None):
    await store.request("POST", "rune_audit_events", body={
        "owner_id": str(owner_id), "device_id": str(device_id) if device_id else None,
        "task_id": str(task_id) if task_id else None, "event_type": event_type,
        "outcome": outcome, "metadata": metadata or {},
    })

async def _device(device_id: UUID, token: str):
    if len(token) < 32:
        raise HTTPException(401, "Device credential required")
    rows = await store.request("GET", "rune_devices", params={
        "id": f"eq.{device_id}", "token_hash": f"eq.{_hash(token)}",
        "status": "not.eq.revoked", "select": "*", "limit": "1",
    })
    if not rows:
        raise HTTPException(401, "Invalid or revoked device credential")
    return rows[0]

@router.get("/me")
async def me(owner: Owner = Depends(require_owner)):
    return {"owner_id": str(owner.id), "email": owner.email}

@router.post("/devices/register", status_code=201)
async def register_device(body: DeviceRegistration, owner: Owner = Depends(require_owner)):
    token = secrets.token_urlsafe(48)
    rows = await store.request("POST", "rune_devices", body={
        "owner_id": str(owner.id), "device_name": body.device_name, "platform": body.platform,
        "app_version": body.app_version, "capabilities": body.capabilities,
        "public_key": body.public_key, "token_hash": _hash(token), "status": "offline",
    }, prefer="return=representation")
    device = rows[0]
    await _audit(owner.id, "device.registered", "success", device_id=UUID(device["id"]),
                 metadata={"platform": body.platform})
    return {"device": {k:v for k,v in device.items() if k != "token_hash"}, "device_token": token}

@router.get("/devices")
async def list_devices(owner: Owner = Depends(require_owner)):
    rows = await store.request("GET", "rune_devices", params={
        **owner_filter(owner.id),
        "select": "id,device_name,platform,app_version,capabilities,status,last_seen_at,created_at,revoked_at",
        "order": "created_at.desc",
    })
    now = datetime.now(timezone.utc)
    for device in rows:
        last_seen = device.get("last_seen_at")
        if device.get("status") != "revoked" and last_seen:
            try:
                seen = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
                if now - seen > timedelta(seconds=90):
                    device["status"] = "offline"
            except (TypeError, ValueError):
                device["status"] = "offline"
        elif device.get("status") != "revoked" and not last_seen:
            device["status"] = "offline"
    return rows

@router.delete("/devices/{device_id}")
async def revoke_device(device_id: UUID, owner: Owner = Depends(require_owner)):
    rows = await store.request("PATCH", "rune_devices", params={
        **owner_filter(owner.id), "id": f"eq.{device_id}", "select": "id",
    }, body={"status":"revoked","revoked_at":datetime.now(timezone.utc).isoformat()},
       prefer="return=representation")
    if not rows: raise HTTPException(404, "Device not found")
    cancelled = await store.request("PATCH", "rune_tasks", params={
        **owner_filter(owner.id),
        "device_id": f"eq.{device_id}",
        "status": "in.(awaiting_approval,queued,running)",
        "select": "id",
    }, body={"status": "cancelled", "finished_at": datetime.now(timezone.utc).isoformat()},
       prefer="return=representation")
    await _audit(owner.id, "device.revoked", "success", device_id=device_id,
                 metadata={"tasks_cancelled": len(cancelled or [])})
    return {"device_id":str(device_id),"status":"revoked",
            "tasks_cancelled":len(cancelled or [])}

@router.post("/devices/{device_id}/heartbeat")
async def heartbeat(device_id: UUID, body: DeviceHeartbeat, x_rune_device_token: str = Header(default="")):
    device = await _device(device_id, x_rune_device_token)
    patch = {"status":body.status,"last_seen_at":datetime.now(timezone.utc).isoformat()}
    if body.app_version is not None: patch["app_version"] = body.app_version
    if body.capabilities is not None: patch["capabilities"] = body.capabilities
    await store.request("PATCH","rune_devices",params={"id":f"eq.{device_id}"},body=patch)
    return {"device_id":str(device_id),"status":body.status,"owner_id":device["owner_id"]}

@router.post("/tasks", status_code=201)
async def create_task(body: TaskCreate, owner: Owner = Depends(require_owner)):
    _reject_secret_fields(body.arguments)
    _validate_capability_arguments(body.capability, body.arguments)
    devices = await store.request("GET","rune_devices",params={
        **owner_filter(owner.id),"id":f"eq.{body.device_id}","status":"not.eq.revoked",
        "select":"id,capabilities","limit":"1",
    })
    if not devices: raise HTTPException(404,"Registered device not found")
    if body.capability not in (devices[0].get("capabilities") or []):
        raise HTTPException(409,"Device has not advertised this capability")
    # Until a server-owned risk/authority policy exists, never let a client
    # downgrade an operation to unattended execution.
    now=datetime.now(timezone.utc)
    rows=await store.request("POST","rune_tasks",body={
        "owner_id":str(owner.id),"device_id":str(body.device_id),"capability":body.capability,
        "arguments":body.arguments,"status":"awaiting_approval",
        "requires_approval":True,"created_at":now.isoformat(),
        "execution_ttl_seconds":body.expires_in_seconds,
        # Approval can take time; execution expiry begins only after approval.
        "expires_at":(now+timedelta(hours=24)).isoformat(),
    },prefer="return=representation")
    task=rows[0]
    await _audit(owner.id,"task.created",task["status"],device_id=body.device_id,
                 task_id=UUID(task["id"]),metadata={"capability":body.capability})
    return {"task":task}



@router.get("/tasks")
async def list_tasks(status: str = "awaiting_approval", owner: Owner = Depends(require_owner)):
    allowed = {"awaiting_approval", "queued", "running", "completed", "failed", "blocked", "uncertain", "expired", "cancelled"}
    if status not in allowed:
        raise HTTPException(400, "Unsupported task status")
    return await store.request("GET", "rune_tasks", params={
        **owner_filter(owner.id), "status": f"eq.{status}", "select": "*",
        "order": "created_at.desc", "limit": "100",
    })

@router.get("/tasks/{task_id}")
async def task_status(task_id: UUID, owner: Owner = Depends(require_owner)):
    rows = await store.request("GET", "rune_tasks", params={
        **owner_filter(owner.id), "id": f"eq.{task_id}", "select": "*", "limit": "1",
    })
    if not rows:
        raise HTTPException(404, "Task not found")
    task = rows[0]
    return {"task": task, "evidence_present": bool(task.get("evidence"))}

@router.post("/tasks/{task_id}/approve")
async def approve_task(task_id: UUID, owner: Owner = Depends(require_owner)):
    now = datetime.now(timezone.utc)
    pending = await store.request("GET", "rune_tasks", params={
        **owner_filter(owner.id),
        "id": f"eq.{task_id}",
        "status": "eq.awaiting_approval",
        "expires_at": f"gt.{now.isoformat()}",
        "select": "id,device_id,execution_ttl_seconds",
        "limit": "1",
    })
    if not pending:
        raise HTTPException(409, "Task unavailable, expired or already decided")
    task = pending[0]
    execution_expiry = now + timedelta(seconds=int(task["execution_ttl_seconds"]))
    rows = await store.request("PATCH", "rune_tasks", params={
        **owner_filter(owner.id),
        "id": f"eq.{task_id}",
        "status": "eq.awaiting_approval",
        "expires_at": f"gt.{now.isoformat()}",
        "select": "*",
    }, body={
        "status": "queued",
        "approval_at": now.isoformat(),
        "expires_at": execution_expiry.isoformat(),
    }, prefer="return=representation")
    if not rows:
        raise HTTPException(409, "Task was already decided")
    approved = rows[0]
    await _audit(owner.id, "task.approved", "success",
                 device_id=UUID(approved["device_id"]), task_id=task_id)
    return {"task": approved}

@router.post("/tasks/{task_id}/cancel")
async def cancel_task(task_id: UUID, owner: Owner = Depends(require_owner)):
    now = datetime.now(timezone.utc).isoformat()
    rows = await store.request("PATCH", "rune_tasks", params={
        **owner_filter(owner.id),
        "id": f"eq.{task_id}",
        "status": "eq.awaiting_approval",
        "select": "id,device_id",
    }, body={"status": "cancelled", "finished_at": now},
       prefer="return=representation")
    if not rows:
        raise HTTPException(409, "Only a task awaiting approval can be cancelled here")
    task = rows[0]
    await _audit(owner.id, "task.cancelled", "success",
                 device_id=UUID(task["device_id"]), task_id=task_id)
    return {"task_id": str(task_id), "status": "cancelled"}


@router.get("/devices/{device_id}/tasks/next")
async def next_task(device_id: UUID, x_rune_device_token: str = Header(default="")):
    device = await _device(device_id, x_rune_device_token)
    now = datetime.now(timezone.utc).isoformat()
    await store.request("PATCH", "rune_tasks", params={
        "device_id": f"eq.{device_id}",
        "status": "in.(queued,running)",
        "expires_at": f"lte.{now}",
    }, body={"status": "expired", "finished_at": now})
    # A single Postgres UPDATE ... FOR UPDATE SKIP LOCKED claim prevents two
    # pollers from receiving the same queued task.
    claimed = await store.rpc("claim_next_rune_task", body={"p_device_id": str(device_id)})
    if not claimed:
        return {"task": None}
    task = claimed[0]
    await _audit(
        UUID(device["owner_id"]), "task.claimed", "running",
        device_id=device_id, task_id=UUID(task["id"]),
    )
    return {"task": task}


@router.post("/devices/{device_id}/tasks/{task_id}/result")
async def task_result(device_id: UUID, task_id: UUID, body: TaskResultInput,
                      x_rune_device_token: str = Header(default="")):
    device = await _device(device_id, x_rune_device_token)
    now = datetime.now(timezone.utc).isoformat()
    current = await store.request("GET", "rune_tasks", params={
        "id": f"eq.{task_id}",
        "device_id": f"eq.{device_id}",
        "owner_id": f"eq.{device['owner_id']}",
        "status": "eq.running",
        "expires_at": f"gt.{now}",
        "select": "id,capability",
        "limit": "1",
    })
    if not current:
        raise HTTPException(409, "Task is not running or does not belong to this device")

    capability = current[0]["capability"]
    if body.status == "completed" and not body.evidence:
        raise HTTPException(400, "Completed tasks require verification evidence")
    if capability == "app.launch" and body.status == "completed" and body.evidence.get("confirmed") is not True:
        raise HTTPException(400, "App launch cannot be completed without active-window confirmation")

    rows = await store.request("PATCH", "rune_tasks", params={
        "id": f"eq.{task_id}",
        "device_id": f"eq.{device_id}",
        "owner_id": f"eq.{device['owner_id']}",
        "status": "eq.running",
        "expires_at": f"gt.{now}",
        "select": "id",
    }, body={
        "status": body.status,
        "result": body.output,
        "evidence": body.evidence,
        "error_code": body.error_code,
        "finished_at": now,
    }, prefer="return=representation")
    if not rows:
        raise HTTPException(409, "Task was already finalized")
    await _audit(
        UUID(device["owner_id"]), "task.result", body.status,
        device_id=device_id, task_id=task_id,
        metadata={"has_evidence": bool(body.evidence), "error_code": body.error_code},
    )
    return {
        "task_id": str(task_id),
        "status": body.status,
        "evidence_present": bool(body.evidence),
    }
