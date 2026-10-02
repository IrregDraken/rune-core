"""Desktop surfaces for RUNE.

The desktop package is a lightweight presentation layer. It does not own the
RUNE brain or bypass node authorization. It is a shell surface over the local
runtime/API.
"""

from .windows import WindowsDesktopShell

__all__ = ["WindowsDesktopShell"]
