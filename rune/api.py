from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from .core.model import DeterministicModel
from .runtime import RUNERuntime

class RUNERequestHandler(BaseHTTPRequestHandler):
    runtime: RUNERuntime | None = None

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
            self._send(200, self.runtime.snapshot())
        elif path == "/api/activity":
            self._send(200, {"events": self.runtime.recent_events()})
        else:
            self._send(404, {"error": "Not found"})

    def do_POST(self) -> None:
        if self.runtime is None:
            self._send(503, {"error": "RUNE runtime unavailable"})
            return
        if urlparse(self.path).path not in ("/api/chat", "/api/command"):
            self._send(404, {"error": "Not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            text = str(payload.get("message", "")).strip()
            if not text:
                self._send(400, {"error": "message is required"})
                return
            if urlparse(self.path).path == "/api/command":
                parsed = self.runtime.parse_command(text)
                self._send(200, {
                    "kind": parsed.kind.value,
                    "command": parsed.command.value if parsed.command else None,
                    "raw": parsed.raw,
                })
                return
            response = self.runtime.receive(text)
            self._send(200, {"response": response})
        except Exception as exc:
            self._send(500, {"error": str(exc)})

def serve(host: str = "127.0.0.1", port: int = 8765, runtime: RUNERuntime | None = None) -> None:
    active_runtime = runtime or RUNERuntime(DeterministicModel())
    RUNERequestHandler.runtime = active_runtime
    server = ThreadingHTTPServer((host, port), RUNERequestHandler)
    print(f"RUNE API listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        active_runtime.close()
