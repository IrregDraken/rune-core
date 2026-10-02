import os

import pytest

from rune.desktop.windows import WindowsDesktopShell


def test_windows_desktop_shell_is_platform_gated() -> None:
    if os.name == "nt":
        pytest.skip("Windows-specific runtime")
    with pytest.raises(RuntimeError):
        WindowsDesktopShell()
