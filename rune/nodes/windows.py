from __future__ import annotations

import ctypes
import os
import platform
import socket
import subprocess
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
        Capability.WINDOW_READ,
        Capability.WINDOW_CONTROL,
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

            if action.capability is Capability.PROCESS_START:
                executable = action.arguments.get("executable", "").strip()
                if not executable:
                    return {"status": "failed", "reason": "executable_required"}
                process = subprocess.Popen(executable, shell=False)
                return {"status": "succeeded", "pid": process.pid, "executable": executable}

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
        # Reboot/shutdown terminate the current process, so immediate positive
        # verification is not possible from this node. The core must observe a
        # later heartbeat to confirm those transitions.
        if action.capability in {Capability.SYSTEM_REBOOT, Capability.SYSTEM_SHUTDOWN}:
            return {"confirmed": False, "status": "awaiting_reconnect"}
        if action.capability is Capability.SYSTEM_LOCK:
            return {"confirmed": False, "status": "requires_desktop_observer"}
        if action.capability in {Capability.PROCESS_READ, Capability.WINDOW_READ}:
            return {"confirmed": True, "status": "observable"}
        return {"confirmed": False, "status": "unknown"}

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
            import ctypes

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
