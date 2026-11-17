from __future__ import annotations

import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from .core.authority import Authority
from .core.model import DeterministicModel
from .core.providers import configured_model_provider
from .core.remote import RemoteBackendClient
from .core.orchestrator import RUNEOrchestrator
from .core.node import Capability
from .runtime import RUNERuntime
from .core.voice import Speech, VoiceInput
from .shell.state import ShellMode, ShellState


class RUNERequestHandler(BaseHTTPRequestHandler):
    runtime: RUNERuntime | None = None
    shell: ShellState | None = None

    def _cors_headers(self) -> None:
        origin = self.headers.get("Origin")
        allowed = {
            item.strip()
            for item in os.environ.get(
                "RUNE_LOCAL_ALLOWED_ORIGINS",
                "http://localhost:3000,http://127.0.0.1:3000",
            ).split(",")
            if item.strip()
        }
        if origin and origin in allowed:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-RUNE-Session")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")

    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self._cors_headers()
        self.end_headers()
        if status != 204:
            self.wfile.write(body)

    def _send_audio(self, status: int, audio: bytes, content_type: str = "audio/mpeg") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(audio)))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(audio)

    def do_OPTIONS(self) -> None:
        self._send(204, {})

    def _authorized(self) -> bool:
        return self.runtime is not None and self.runtime.authority.accepts(
            self.headers.get("X-RUNE-Session")
        )

    @staticmethod
    def _auth_required() -> bool:
        return os.environ.get("RUNE_API_AUTH_REQUIRED", "false").strip().lower() in {"1", "true", "yes"}

    def do_GET(self) -> None:
        if self.runtime is None:
            self._send(503, {"error": "RUNE runtime unavailable"})
            return
        path = urlparse(self.path).path
        if path != "/api/health" and self._auth_required() and not self._authorized():
            self._send(403, {"error": "privileged session required"})
            return
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
                "wake_phrase": "Hey RUNE",
                "session_state": self.runtime.voice_session.state.value,
                "inactivity_seconds": self.runtime.voice_session.inactivity_seconds,
                "confirmation_seconds": self.runtime.voice_session.confirmation_seconds,
                "wake_word_engine": voice.wake_word is not None,
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
            "/api/remote/propose",
            "/api/remote/submit",
            "/api/remote/approve",
            "/api/voice/synthesize",
            "/api/voice/transcribe",
            "/api/voice/session",
        }
        if request_path not in supported:
            self._send(404, {"error": "Not found"})
            return
        if self._auth_required() and not self._authorized():
            self._send(403, {"error": "privileged session required"})
            return

        try:
            if request_path == "/api/voice/transcribe":
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > 25 * 1024 * 1024:
                    self._send(400, {"error": "audio payload must be between 1 byte and 25 MB"})
                    return
                audio = self.rfile.read(length)
                content_type = self.headers.get("Content-Type", "audio/wav").split(";")[0].strip().lower()
                audio_format = {
                    "audio/wav": "wav", "audio/x-wav": "wav", "audio/mpeg": "mp3",
                    "audio/mp3": "mp3", "audio/mp4": "m4a", "audio/ogg": "ogg",
                    "audio/webm": "webm", "audio/flac": "flac",
                }.get(content_type)
                if audio_format is None:
                    self._send(415, {"error": "unsupported audio content type"})
                    return
                try:
                    transcript = self.runtime.voice.transcribe(
                        VoiceInput(audio=audio, sample_rate=16000, audio_format=audio_format)
                    )
                except ValueError as exc:
                    self._send(400, {"error": str(exc)})
                    return
                except Exception:
                    self._send(503, {"error": "speech recognition provider unavailable"})
                    return
                self._send(200, {"text": transcript.text, "confidence": transcript.confidence})
                return

            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")

            if request_path in {"/api/memory", "/api/goal", "/api/plan", "/api/plan/verify",
                                "/api/remote/propose", "/api/remote/submit", "/api/remote/approve",
                                "/api/voice/synthesize", "/api/voice/transcribe",
                                "/api/voice/session"} and not self._authorized():
                self._send(403, {"error": "privileged session required"})
                return

            if request_path == "/api/voice/session":
                controller = self.runtime.voice_session
                action = str(payload.get("action", "")).strip()
                now = time.time()
                if action == "wake":
                    controller.wake_detected(now)
                elif action == "activity":
                    controller.user_activity(now)
                elif action == "processing":
                    controller.processing_started(now)
                elif action == "speech_started":
                    controller.speech_started(now)
                elif action == "speech_finished":
                    controller.speech_finished(now)
                elif action in {"stop", "interrupt"}:
                    controller.interrupt(now)
                elif action == "confirmation":
                    controller.answer_confirmation(payload.get("continue") is True, now)
                elif action == "tick":
                    prompt = controller.tick(now)
                    self._send(200, {"state": controller.state.value, "prompt": prompt})
                    return
                elif action == "close":
                    controller.close()
                else:
                    self._send(400, {"error": "unsupported voice session action"})
                    return
                self._send(200, {"state": controller.state.value})
                return

            if request_path == "/api/voice/synthesize":
                text = str(payload.get("text", "")).strip()
                if not text:
                    self._send(400, {"error": "text is required"})
                    return
                try:
                    audio = self.runtime.voice.synthesize(Speech(text))
                except ValueError as exc:
                    self._send(400, {"error": str(exc)})
                    return
                except Exception:
                    self._send(503, {"error": "voice provider unavailable"})
                    return
                self._send_audio(200, audio)
                return

            if request_path == "/api/remote/propose":
                request_text = str(payload.get("message", "")).strip()
                if not request_text:
                    self._send(400, {"error": "message is required"})
                    return
                remote = RemoteBackendClient()
                try:
                    proposal = RUNEOrchestrator(self.runtime.engine.model, remote).propose(request_text)
                    self._send(200, {"proposal": proposal})
                finally:
                    remote.close()
                return

            if request_path == "/api/remote/submit":
                proposal = payload.get("proposal")
                if not isinstance(proposal, dict):
                    self._send(400, {"error": "proposal object is required"})
                    return
                remote = RemoteBackendClient()
                try:
                    tasks = RUNEOrchestrator(self.runtime.engine.model, remote).submit_proposal(proposal)
                    self._send(202, {"tasks": tasks, "status": "awaiting_owner_approval"})
                finally:
                    remote.close()
                return

            if request_path == "/api/remote/approve":
                task_id = str(payload.get("task_id", "")).strip()
                if not task_id:
                    self._send(400, {"error": "task_id is required"})
                    return
                remote = RemoteBackendClient()
                try:
                    task = RUNEOrchestrator(self.runtime.engine.model, remote).approve(task_id)
                    self._send(200, {"task": task})
                finally:
                    remote.close()
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
        except Exception:
            self._send(500, {"error": "internal_error"})


def serve(
    host: str = "127.0.0.1",
    port: int = 8765,
    runtime: RUNERuntime | None = None,
) -> None:
    host = os.environ.get("RUNE_API_HOST", host)
    port = int(os.environ.get("PORT", os.environ.get("RUNE_API_PORT", str(port))))
    if runtime is not None:
        active_runtime = runtime
    else:
        model_mode = os.environ.get("RUNE_MODEL_MODE", "development").strip().lower()
        if model_mode == "live":
            model = configured_model_provider()
        elif model_mode == "development":
            model = DeterministicModel()
        else:
            raise ValueError("RUNE_MODEL_MODE must be 'development' or 'live'")
        active_runtime = RUNERuntime(
            model,
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
