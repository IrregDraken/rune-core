from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol

class Capability(str, Enum):
    SYSTEM_LOCK = "system.lock"
    SYSTEM_REBOOT = "system.reboot"
    SYSTEM_SHUTDOWN = "system.shutdown"
    PROCESS_READ = "process.read"
    PROCESS_START = "process.start"
    PROCESS_STOP = "process.stop"
    WINDOW_READ = "window.read"
    WINDOW_CONTROL = "window.control"
    FILE_READ = "file.read"
    FILE_WRITE = "file.write"
    SHELL_EXECUTE = "shell.execute"

@dataclass(frozen=True)
class NodeInfo:
    node_id: str
    platform: str
    hostname: str
    capabilities: frozenset[Capability] = field(default_factory=frozenset)

@dataclass(frozen=True)
class NodeAction:
    capability: Capability
    arguments: dict[str, str] = field(default_factory=dict)
    authorized: bool = False

class RUNEActionNode(Protocol):
    def info(self) -> NodeInfo: ...
    def can(self, capability: Capability) -> bool: ...
    def execute(self, action: NodeAction) -> dict: ...
    def verify(self, action: NodeAction) -> dict: ...
    def observe(self) -> dict: ...

class NullNode:
    def __init__(self, info: NodeInfo) -> None:
        self._info = info

    def info(self) -> NodeInfo:
        return self._info

    def can(self, capability: Capability) -> bool:
        return capability in self._info.capabilities

    def execute(self, action: NodeAction) -> dict:
        if not self.can(action.capability):
            return {"status": "blocked", "reason": "capability_unavailable"}
        return {"status": "not_implemented", "capability": action.capability.value}

    def verify(self, action: NodeAction) -> dict:
        return {"confirmed": False, "status": "unknown"}

    def observe(self) -> dict:
        return {"status": "unavailable", "reason": "node_not_connected"}
