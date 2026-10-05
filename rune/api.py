from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from .core.authority import Authority
from .core.model import DeterministicModel
from .core.node import Capability
from .runtime import RUNERuntime
from .shell.state import ShellMode, ShellState


class RUNERequestHandler(BaseHTTPRequestHandler):
    runtime: RUNERuntime | None = None
    shell: ShellState | None = None

    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-RUNE-Session")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self._send(204, {})

    def _authorized(self) -> bool:
        return self.runtime is not None and self.runtime.authority.accepts(
            self.headers.get("X-RUNE-Session")
        )

    def do_GET(self) -> None:
        if self.runtime is None:
            self._send(503, {"error": "RUNE runtime unavailable"})
            return
        path = urlparse(self.path).path
        if path == "/api/health":
            self._send(200, {"status": "online"})
        elif path == "/api/state":
            state = self.runtime.snapshot()
            if self.shell is not None:
                state["shell"] = {
                    "mode": self.shell.mode.value,
                    "island_message": self.shell.island_message,
                    "workspaces": [workspace.__dict__ for workspace in self.shell.workspaces],
                }
            self._send(200, state)
        elif path == "/api/activity":
            self._send(200, {"events": self.runtime.recent_events()})
        elif path == "/api/tools":
            self._send(200, {"tools": [spec.__dict__ for spec in self.runtime.tools.specs()]})
        elif path == "/api/voice":
            voice = self.runtime.voice
            self._send(200, {
                "wake_word": voice.wake_word is not None,
                "speech_to_text": voice.speech_to_text is not None,
                "text_to_speech": voice.text_to_speech is not None,
                "speaker_verifier": voice.speaker_verifier is not None,
            })
        elif path == "/api/windows":
            observation = self.runtime.node.observe()
            self._send(200, {
                "windows": observation.get("windows", []),
                "status": observation.get("status", "unknown"),
            })
        else:
            self._send(404, {"error": "Not found"})

    def do_POST(self) -> None:
        if self.runtime is None:
            self._send(503, {"error": "RUNE runtime unavailable"})
            return

        request_path = urlparse(self.path).path
        supported = {
            "/api/chat",
            "/api/command",
            "/api/workspace",
            "/api/window",
            "/api/action",
            "/api/memory",
            "/api/goal",
            "/api/plan",
            "/api/plan/verify",
        }
        if request_path not in supported:
            self._send(404, {"error": "Not found"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")

            if request_path in {"/api/memory", "/api/goal"} and not self._authorized():
                self._send(403, {"error": "privileged session required"})
                return

            if request_path == "/api/memory":
                key = str(payload.get("key", "")).strip()
                value = payload.get("value")
                if not key or value is None:
                    self._send(400, {"error": "key and value are required"})
                    return
                record = self.runtime.remember(
                    key,
                    value,
                    kind=str(payload.get("kind", "semantic")),
                    salience=float(payload.get("salience", 0.8)),
                    tags=tuple(str(tag) for tag in payload.get("tags", [])),
                )
                self._send(200, {"memory": record})
                return

            if request_path == "/api/goal":
                goal = str(payload.get("goal", "")).strip()
                if not goal:
                    self._send(400, {"error": "goal is required"})
                    return
                self._send(200, {"goal": self.runtime.set_goal(goal)})
                return

            if request_path == "/api/plan":
                goal = str(payload.get("goal", "")).strip()
                steps = payload.get("steps", [])
                if not isinstance(steps, list):
                    self._send(400, {"error": "steps must be an array"})
                    return
                self._send(200, {"plan": self.runtime.create_plan(goal, steps)})
                return

            if request_path == "/api/plan/verify":
                step_id = str(payload.get("step_id", "")).strip()
                evidence = payload.get("evidence", {})
                if not step_id or not isinstance(evidence, dict):
                    self._send(400, {"error": "step_id and evidence are required"})
                    return
                self._send(200, {"plan": self.runtime.verify_plan_step(step_id, evidence)})
                return

            if request_path == "/api/workspace":
                workspace_id = str(payload.get("workspace_id", "")).strip()
                if self.shell is None or not self.shell.activate_workspace(workspace_id):
                    self._send(404, {"error": "workspace not found"})
                    return
                self.shell.set_mode(ShellMode.WORKING)
                self.shell.island_message = f"workspace: {workspace_id}"
                self._send(200, {
                    "workspace_id": workspace_id,
                    "workspaces": [workspace.__dict__ for workspace in self.shell.workspaces],
                })
                return

            if request_path == "/api/window":
                operation = str(payload.get("operation", "")).strip().lower()
                hwnd = str(payload.get("hwnd", "")).strip()
                if not operation or not hwnd:
                    self._send(400, {"error": "operation and hwnd are required"})
                    return
                result = self.runtime.execute_action(
                    Capability.WINDOW_CONTROL,
                    {"operation": operation, "hwnd": hwnd},
                    authorized=self._authorized(),
                )
                self._send(200, result)
                return

            if request_path == "/api/action":
                capability_name = str(payload.get("capability", "")).strip()
                try:
                    capability = Capability(capability_name)
                except ValueError:
                    self._send(400, {"error": "unknown capability"})
                    return
                arguments = {
                    str(key): str(value)
                    for key, value in dict(payload.get("arguments", {})).items()
                }
                result = self.runtime.execute_action(
                    capability, arguments, authorized=self._authorized()
                )
                self._send(200, result)
                return

            text = str(payload.get("message", "")).strip()
            if not text:
                self._send(400, {"error": "message is required"})
                return

            if request_path == "/api/command":
                parsed = self.runtime.parse_command(text)
                if self.shell is not None:
                    self.shell.set_mode(ShellMode.COMMAND)
                    self.shell.island_message = parsed.command.value if parsed.command else None
                self._send(200, {
                    "kind": parsed.kind.value,
                    "command": parsed.command.value if parsed.command else None,
                    "raw": parsed.raw,
                })
                return

            response = self.runtime.receive(text)
            if self.shell is not None:
                self.shell.set_mode(ShellMode.AMBIENT)
                self.shell.island_message = response[:120] if response else "ready"
            self._send(200, {"response": response})
        except (TypeError, ValueError) as exc:
            self._send(400, {"error": str(exc)})
        except Exception as exc:
            self._send(500, {"error": str(exc)})


def serve(
    host: str = "127.0.0.1",
    port: int = 8765,
    runtime: RUNERuntime | None = None,
) -> None:
    active_runtime = runtime or RUNERuntime(
        DeterministicModel(),
        authority=Authority(os.environ.get("RUNE_SESSION_TOKEN")),
    )
    RUNERequestHandler.runtime = active_runtime
    RUNERequestHandler.shell = ShellState()
    server = ThreadingHTTPServer((host, port), RUNERequestHandler)
    print(f"RUNE API listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        active_runtime.close()


if __name__ == "__main__":
    serve()
