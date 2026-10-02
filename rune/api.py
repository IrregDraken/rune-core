from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from .core.authority import Authority
from .core.model import DeterministicModel
from .core.node import Capability, NodeAction
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
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self._send(204, {})

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
        elif path == "/api/windows":
            observation = self.runtime.node.observe()
            self._send(
                200,
                {
                    "windows": observation.get("windows", []),
                    "status": observation.get("status", "unknown"),
                },
            )
        else:
            self._send(404, {"error": "Not found"})

    def do_POST(self) -> None:
        if self.runtime is None:
            self._send(503, {"error": "RUNE runtime unavailable"})
            return

        request_path = urlparse(self.path).path
        supported = {"/api/chat", "/api/command", "/api/workspace", "/api/window", "/api/action"}
        if request_path not in supported:
            self._send(404, {"error": "Not found"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")

            if request_path == "/api/workspace":
                workspace_id = str(payload.get("workspace_id", "")).strip()
                if self.shell is None or not self.shell.activate_workspace(workspace_id):
                    self._send(404, {"error": "workspace not found"})
                    return
                self.shell.set_mode(ShellMode.WORKING)
                self.shell.island_message = f"workspace: {workspace_id}"
                self._send(
                    200,
                    {
                        "workspace_id": workspace_id,
                        "workspaces": [workspace.__dict__ for workspace in self.shell.workspaces],
                    },
                )
                return

            if request_path == "/api/window":
                operation = str(payload.get("operation", "")).strip().lower()
                hwnd = str(payload.get("hwnd", "")).strip()
                if not operation or not hwnd:
                    self._send(400, {"error": "operation and hwnd are required"})
                    return
                authorized = self.runtime.authority.accepts(
                    self.headers.get("X-RUNE-Session")
                )
                result = self.runtime.execute_action(
                    Capability.WINDOW_CONTROL,
                    {"operation": operation, "hwnd": hwnd},
                    authorized=authorized,
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
                authorized = self.runtime.authority.accepts(
                    self.headers.get("X-RUNE-Session")
                )
                result = self.runtime.execute_action(
                    capability, arguments, authorized=authorized
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
                self._send(
                    200,
                    {
                        "kind": parsed.kind.value,
                        "command": parsed.command.value if parsed.command else None,
                        "raw": parsed.raw,
                    },
                )
                return

            response = self.runtime.receive(text)
            if self.shell is not None:
                self.shell.set_mode(ShellMode.AMBIENT)
                self.shell.island_message = response[:120] if response else "ready"
            self._send(200, {"response": response})
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
