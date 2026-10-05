from __future__ import annotations

import ctypes
import os
import platform
import socket
import subprocess
from pathlib import Path
from typing import Any

from rune.core.node import Capability, NodeAction, NodeInfo


class WindowsNode:
    """Controlled Windows device node for RUNE.

    This adapter uses Windows' native command surfaces and standard-library APIs.
    Destructive actions require an explicit authorization flag and are never
    implicitly granted by recognizing a force command.
    """

    _CAPABILITIES = frozenset({
        Capability.SYSTEM_LOCK,
        Capability.SYSTEM_REBOOT,
        Capability.SYSTEM_SHUTDOWN,
        Capability.PROCESS_READ,
        Capability.PROCESS_START,
        Capability.PROCESS_STOP,
        Capability.WINDOW_READ,
        Capability.WINDOW_CONTROL,
        Capability.FILE_READ,
        Capability.FILE_WRITE,
    })

    def __init__(self, *, node_id: str = "windows-local") -> None:
        if os.name != "nt":
            raise RuntimeError("WindowsNode can only run on Windows.")
        self._info = NodeInfo(
            node_id=node_id,
            platform=platform.system().lower(),
            hostname=socket.gethostname(),
            capabilities=self._CAPABILITIES,
        )

    def info(self) -> NodeInfo:
        return self._info

    def can(self, capability: Capability) -> bool:
        return capability in self._CAPABILITIES

    def execute(self, action: NodeAction) -> dict[str, Any]:
        if not self.can(action.capability):
            return {"status": "blocked", "reason": "capability_unavailable"}

        if action.capability in {
            Capability.SYSTEM_LOCK,
            Capability.SYSTEM_REBOOT,
            Capability.SYSTEM_SHUTDOWN,
        } and not action.authorized:
            return {"status": "blocked", "reason": "authorization_required"}

        try:
            if action.capability is Capability.SYSTEM_LOCK:
                ctypes.windll.user32.LockWorkStation()
                return {"status": "attempted", "operation": "lock"}

            if action.capability is Capability.SYSTEM_REBOOT:
                self._system_command("shutdown", "/r", "/t", "0")
                return {"status": "attempted", "operation": "reboot"}

            if action.capability is Capability.SYSTEM_SHUTDOWN:
                self._system_command("shutdown", "/s", "/t", "0")
                return {"status": "attempted", "operation": "shutdown"}

            if action.capability is Capability.PROCESS_READ:
                return {"status": "succeeded", "processes": self._processes()}

            if action.capability is Capability.WINDOW_CONTROL:
                if not action.authorized:
                    return {"status": "blocked", "reason": "authorization_required"}
                operation = action.arguments.get("operation", "").strip().lower()
                hwnd = int(action.arguments.get("hwnd", "0"))
                if not hwnd:
                    return {"status": "failed", "reason": "hwnd_required"}
                return self._control_window(hwnd, operation)

            if action.capability is Capability.PROCESS_STOP:
                if not action.authorized:
                    return {"status": "blocked", "reason": "authorization_required"}
                pid = str(action.arguments.get("pid", "")).strip()
                if not pid.isdigit() or int(pid) <= 0:
                    return {"status": "failed", "reason": "pid_required"}
                self._system_command("taskkill", "/PID", pid, "/T", "/F")
                return {"status": "attempted", "operation": "process_stop", "pid": int(pid)}

            if action.capability is Capability.PROCESS_START:
                if not action.authorized:
                    return {"status": "blocked", "reason": "authorization_required"}
                executable = action.arguments.get("executable", "").strip()
                if not executable:
                    return {"status": "failed", "reason": "executable_required"}
                process = subprocess.Popen(executable, shell=False)
                return {"status": "succeeded", "pid": process.pid, "executable": executable}

            if action.capability is Capability.FILE_READ:
                if not action.authorized:
                    return {"status": "blocked", "reason": "authorization_required"}
                path = self._safe_path(action.arguments.get("path", ""))
                if path is None:
                    return {"status": "blocked", "reason": "path_outside_user_home"}
                try:
                    data = path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    return {"status": "failed", "reason": "file_is_not_utf8_text"}
                return {
                    "status": "succeeded",
                    "path": str(path),
                    "content": data[:262144],
                    "truncated": len(data) > 262144,
                }

            if action.capability is Capability.FILE_WRITE:
                if not action.authorized:
                    return {"status": "blocked", "reason": "authorization_required"}
                path = self._safe_path(action.arguments.get("path", ""))
                if path is None:
                    return {"status": "blocked", "reason": "path_outside_user_home"}
                content = action.arguments.get("content", "")
                encoded = content.encode("utf-8")
                if len(encoded) > 262144:
                    return {"status": "failed", "reason": "content_too_large"}
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(encoded)
                return {"status": "attempted", "path": str(path), "bytes": len(encoded)}

            return {"status": "blocked", "reason": "unsupported_capability"}
        except (OSError, subprocess.SubprocessError) as exc:
            return {"status": "failed", "reason": str(exc)}

    def observe(self) -> dict[str, Any]:
        """Return a bounded, non-destructive snapshot of the Windows node."""
        try:
            processes = self._processes()
            windows = self._windows()
            return {
                "status": "succeeded",
                "platform": platform.platform(),
                "hostname": socket.gethostname(),
                "process_count": len(processes),
                "processes": processes[:200],
                "window_count": len(windows),
                "windows": windows[:100],
                "system": self._system_telemetry(),
            }
        except (OSError, subprocess.SubprocessError) as exc:
            return {"status": "failed", "reason": str(exc)}

    def verify(self, action: NodeAction) -> dict[str, Any]:
        if action.capability in {Capability.SYSTEM_REBOOT, Capability.SYSTEM_SHUTDOWN}:
            return {"confirmed": False, "status": "awaiting_reconnect"}
        if action.capability is Capability.SYSTEM_LOCK:
            return {"confirmed": False, "status": "requires_desktop_observer"}
        if action.capability in {Capability.PROCESS_READ, Capability.WINDOW_READ, Capability.FILE_READ}:
            return {"confirmed": True, "status": "observable"}
        if action.capability is Capability.FILE_WRITE:
            path = self._safe_path(action.arguments.get("path", ""))
            expected = action.arguments.get("content", "").encode("utf-8")
            if path is None or not path.is_file():
                return {"confirmed": False, "status": "file_missing"}
            try:
                actual = path.read_bytes()
                return {
                    "confirmed": actual == expected,
                    "status": "verified",
                    "bytes": len(actual),
                }
            except OSError:
                return {"confirmed": False, "status": "readback_failed"}
        if action.capability is Capability.PROCESS_STOP:
            pid = str(action.arguments.get("pid", "")).strip()
            if pid.isdigit():
                exists = any(row.get("pid") == pid for row in self._processes())
                return {"confirmed": not exists, "status": "verified"}
        return {"confirmed": False, "status": "unknown"}

    @staticmethod
    def _safe_path(raw_path: str) -> Path | None:
        """Confine file capabilities to the current user's home directory."""
        raw = raw_path.strip()
        if not raw:
            return None
        try:
            home = Path.home().resolve()
            candidate = Path(raw).expanduser().resolve()
            if os.path.commonpath((str(home), str(candidate))) != str(home):
                return None
            return candidate
        except (OSError, RuntimeError, ValueError):
            return None

    @staticmethod
    def _windows() -> list[dict[str, Any]]:
        """Return visible top-level windows with titles and owning PIDs."""
        user32 = ctypes.windll.user32
        windows: list[dict[str, Any]] = []
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        def callback(hwnd: int, _lparam: int) -> bool:
            if not user32.IsWindowVisible(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True
            title = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, title, length + 1)
            if not title.value.strip():
                return True
            pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            windows.append({"hwnd": int(hwnd), "pid": int(pid.value), "title": title.value})
            return True

        user32.EnumWindows(EnumWindowsProc(callback), 0)
        foreground = int(user32.GetForegroundWindow())
        for window in windows:
            window["foreground"] = window["hwnd"] == foreground
        return windows

    @staticmethod
    def _control_window(hwnd: int, operation: str) -> dict[str, Any]:
        user32 = ctypes.windll.user32
        commands = {"minimize": 6, "maximize": 3, "restore": 9}
        if operation in commands:
            ok = bool(user32.ShowWindow(hwnd, commands[operation]))
            return {"status": "succeeded" if ok else "failed", "operation": operation, "hwnd": hwnd}
        if operation in {"focus", "activate"}:
            ok = bool(user32.SetForegroundWindow(hwnd))
            return {"status": "succeeded" if ok else "failed", "operation": "focus", "hwnd": hwnd}
        return {"status": "failed", "reason": "unsupported_window_operation", "operation": operation}

    @staticmethod
    def _system_telemetry() -> dict[str, int]:
        """Read bounded host memory telemetry without third-party dependencies."""
        try:
            class MemoryStatus(ctypes.Structure):
                _fields_ = [
                    ("length", ctypes.c_ulong),
                    ("memory_load", ctypes.c_ulong),
                    ("total_phys", ctypes.c_ulonglong),
                    ("avail_phys", ctypes.c_ulonglong),
                    ("total_page", ctypes.c_ulonglong),
                    ("avail_page", ctypes.c_ulonglong),
                    ("total_virtual", ctypes.c_ulonglong),
                    ("avail_virtual", ctypes.c_ulonglong),
                    ("avail_extended", ctypes.c_ulonglong),
                ]

            status = MemoryStatus()
            status.length = ctypes.sizeof(MemoryStatus)
            if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return {}
            return {
                "memory_load_percent": int(status.memory_load),
                "memory_total_mb": int(status.total_phys // (1024 * 1024)),
                "memory_available_mb": int(status.avail_phys // (1024 * 1024)),
            }
        except (AttributeError, OSError):
            return {}

    @staticmethod
    def _system_command(*args: str) -> None:
        subprocess.Popen(list(args), shell=False)

    @staticmethod
    def _processes() -> list[dict[str, str]]:
        completed = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            check=True,
        )
        rows: list[dict[str, str]] = []
        for line in completed.stdout.splitlines():
            parts = [part.strip('"') for part in line.split('","')]
            if len(parts) >= 2:
                rows.append({"name": parts[0], "pid": parts[1]})
        return rows
