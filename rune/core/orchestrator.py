from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from .model import ModelProvider
from .remote import RemoteBackendClient


IDENTITY_POLICY = """You are R.U.N.E., one persistent personal executive assistant.
Be clear, calm, capable and honest. Never claim an action succeeded without device
evidence. Separate intent, proposal, approval, attempt, outcome and verification.
Never request or place passwords, PINs, API keys, cookies, access tokens, private
keys or biometric material in task arguments or model context. Respect app and OS
authentication. Prefer the smallest safe action sequence. Do not invent capabilities.
Return only valid JSON matching the requested schema."""


class OrchestrationError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProposedAction:
    device_id: str
    capability: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ProposedTask:
    summary: str
    actions: tuple[ProposedAction, ...]
    status: str = "awaiting_owner_approval"


class RemoteClient(Protocol):
    def list_devices(self) -> list[dict[str, Any]]: ...
    def create_task(self, device_id: UUID | str, capability: str,
                    arguments: dict[str, Any], *, expires_in_seconds: int = 60) -> dict[str, Any]: ...
    def approve_task(self, task_id: UUID | str) -> dict[str, Any]: ...


class RUNEOrchestrator:
    """Turns natural-language intent into capability-checked, approval-gated tasks."""

    def __init__(self, model: ModelProvider, remote: RemoteClient) -> None:
        self.model = model
        self.remote = remote

    def propose(self, request: str) -> dict[str, Any]:
        clean = request.strip()
        if not clean:
            raise ValueError("request cannot be empty")
        devices = self.remote.list_devices()
        available = [
            {"id": d.get("id"), "name": d.get("device_name"),
             "platform": d.get("platform"), "status": d.get("status"),
             "capabilities": d.get("capabilities", [])}
            for d in devices if d.get("status") in {"online", "idle"}
        ]
        prompt = (
            f"{IDENTITY_POLICY}\n\n"
            "Convert the user's request into a safe executable proposal. Do not execute. "
            "Only select capabilities explicitly advertised by a device. If no action is "
            "needed, return an empty actions array. Do not guess device IDs.\n"
            "JSON schema: {\"summary\": string, \"actions\": "
            "[{\"device_id\": string, \"capability\": string, \"arguments\": object}]}\n"
            f"Registered devices and capabilities: {json.dumps(available, separators=(',', ':'))}\n"
            f"User request: {clean}"
        )
        raw = self.model.respond(prompt).content
        try:
            payload = json.loads(raw)
        except (TypeError, ValueError) as exc:
            raise OrchestrationError("model did not return valid proposal JSON") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("actions"), list):
            raise OrchestrationError("model proposal has an invalid shape")
        summary = str(payload.get("summary", "")).strip()
        if not summary:
            raise OrchestrationError("model proposal is missing a summary")
        device_map = {str(d.get("id")): d for d in available}
        actions: list[ProposedAction] = []
        for item in payload["actions"]:
            if not isinstance(item, dict):
                raise OrchestrationError("action proposal must be an object")
            device_id = str(item.get("device_id", ""))
            capability = str(item.get("capability", ""))
            arguments = item.get("arguments", {})
            device = device_map.get(device_id)
            if device is None:
                raise OrchestrationError("proposal references an unregistered device")
            if capability not in (device.get("capabilities") or []):
                raise OrchestrationError("proposal references an unavailable capability")
            if not isinstance(arguments, dict):
                raise OrchestrationError("action arguments must be an object")
            _reject_sensitive(arguments)
            _validate_capability_arguments(capability, arguments)
            actions.append(ProposedAction(device_id, capability, arguments))
        return {
            "summary": summary,
            "status": "proposed_not_executed",
            "actions": [a.__dict__ for a in actions],
            "approval_required": bool(actions),
        }

    def submit_proposal(self, proposal: dict[str, Any]) -> list[dict[str, Any]]:
        if proposal.get("status") != "proposed_not_executed":
            raise OrchestrationError("only an unsubmitted proposal can be submitted")
        tasks = []
        for action in proposal.get("actions", []):
            task = self.remote.create_task(
                action["device_id"], action["capability"], action["arguments"]
            )
            tasks.append(task.get("task", task))
        return tasks

    def approve(self, task_id: UUID | str) -> dict[str, Any]:
        return self.remote.approve_task(task_id)


def _reject_sensitive(value: Any, path: str = "arguments") -> None:
    forbidden = {
        "password", "passwd", "pin", "passcode", "secret", "secret_key",
        "api_key", "access_token", "refresh_token", "session_cookie",
        "private_key", "authorization", "credential",
    }
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(key)).lower().replace("-", "_")
            if normalized in forbidden or normalized.endswith(("_password", "_token", "_secret", "_api_key")):
                raise OrchestrationError(f"sensitive field rejected at {path}.{key}")
            _reject_sensitive(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_sensitive(child, f"{path}[{index}]")


def _validate_capability_arguments(capability: str, arguments: dict[str, Any]) -> None:
    if capability in {"app.list", "ui.observe"}:
        if arguments:
            raise OrchestrationError(f"{capability} does not accept arguments")
        return
    if capability == "app.launch":
        package_name = arguments.get("packageName", arguments.get("package_name"))
        if not isinstance(package_name, str) or not package_name.strip() or len(package_name) > 255:
            raise OrchestrationError("app.launch requires a valid packageName")
        return
    if capability == "ui.interact":
        action = arguments.get("action")
        if action == "tap":
            if not isinstance(arguments.get("x"), (int, float)) or not isinstance(arguments.get("y"), (int, float)):
                raise OrchestrationError("ui.interact tap requires numeric x and y coordinates")
            if not (0 <= arguments["x"] <= 10000 and 0 <= arguments["y"] <= 10000):
                raise OrchestrationError("tap coordinates are outside the allowed range")
        elif action == "scroll":
            if arguments.get("direction", "down") not in {"up", "down"}:
                raise OrchestrationError("scroll direction must be up or down")
        elif action == "type":
            value = arguments.get("text")
            if not isinstance(value, str) or not value or len(value) > 4000:
                raise OrchestrationError("ui.interact type requires text up to 4000 characters")
        else:
            raise OrchestrationError("unsupported ui.interact action")
        return
    raise OrchestrationError("capability has no registered execution schema")
