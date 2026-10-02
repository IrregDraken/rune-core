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

            if action.capability is Capability.PROCESS_START:
                executable = action.arguments.get("executable", "").strip()
                if not executable:
                    return {"status": "failed", "reason": "executable_required"}
                process = subprocess.Popen(executable, shell=False)
                return {"status": "succeeded", "pid": process.pid, "executable": executable}

            return {"status": "blocked", "reason": "unsupported_capability"}
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
        if action.capability is Capability.PROCESS_READ:
            return {"confirmed": True, "status": "observable"}
        return {"confirmed": False, "status": "unknown"}

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
