from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

class CommandKind(str, Enum):
    NATURAL = "natural"
    FORCE = "force"

class ForceCommand(str, Enum):
    WAKE = "wake"
    SLEEP = "sleep"
    LOCK = "lock"
    REBOOT = "reboot"
    SHUTDOWN = "shutdown"
    PAUSE = "pause"
    RESUME = "resume"
    QUIET = "quiet"
    EMERGENCY_STOP = "emergency_stop"

@dataclass(frozen=True)
class ParsedCommand:
    kind: CommandKind
    command: ForceCommand | None = None
    raw: str = ""

_ALIASES = {
    ForceCommand.WAKE: ("wake", "wake up", "wakeup"),
    ForceCommand.SLEEP: ("sleep", "go to sleep"),
    ForceCommand.LOCK: ("lock", "lock computer", "lock the computer"),
    ForceCommand.REBOOT: ("reboot", "restart", "restart computer", "restart the computer"),
    ForceCommand.SHUTDOWN: ("shutdown", "shut down", "shutdown computer", "shut down the computer"),
    ForceCommand.PAUSE: ("pause", "pause rune"),
    ForceCommand.RESUME: ("resume", "resume rune"),
    ForceCommand.QUIET: ("quiet mode", "be quiet", "go quiet"),
    ForceCommand.EMERGENCY_STOP: ("emergency stop", "full stop", "stop everything"),
}

def parse_command(text: str) -> ParsedCommand:
    normalized = " ".join(text.strip().lower().split())
    if normalized.startswith("rune "):
        normalized = normalized[5:].strip()
    for command, aliases in _ALIASES.items():
        if normalized in aliases:
            return ParsedCommand(CommandKind.FORCE, command, text)
    return ParsedCommand(CommandKind.NATURAL, raw=text)
