from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ShellMode(str, Enum):
    AMBIENT = "ambient"
    COMMAND = "command"
    WORKING = "working"
    QUIET = "quiet"
    ATTENTION = "attention"


@dataclass(frozen=True)
class Workspace:
    id: str
    name: str
    app_ids: tuple[str, ...] = ()
    active: bool = False


@dataclass
class ShellState:
    mode: ShellMode = ShellMode.AMBIENT
    island_message: str | None = None
    workspaces: list[Workspace] = field(default_factory=lambda: [
        Workspace("home", "Home", active=True),
        Workspace("work", "Work"),
    ])

    def set_mode(self, mode: ShellMode) -> None:
        self.mode = mode

    def activate_workspace(self, workspace_id: str) -> bool:
        if not any(workspace.id == workspace_id for workspace in self.workspaces):
            return False
        updated: list[Workspace] = []
        for workspace in self.workspaces:
            updated.append(
                Workspace(
                    workspace.id,
                    workspace.name,
                    workspace.app_ids,
                    active=workspace.id == workspace_id,
                )
            )
        self.workspaces = updated
        return True
