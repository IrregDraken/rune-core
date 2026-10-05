import os
from pathlib import Path

import pytest

from rune.core.node import Capability
from rune.nodes.windows import WindowsNode


def test_windows_node_exposes_file_capabilities():
    if os.name != "nt":
        pytest.skip("Windows-only capability adapter")
    node = WindowsNode()
    assert node.can(Capability.FILE_READ)
    assert node.can(Capability.FILE_WRITE)


def test_windows_file_path_guard():
    home = Path.home().resolve()
    assert WindowsNode._safe_path(str(home / "rune-test.txt")) == home / "rune-test.txt"
    outside = Path(home.anchor) / "rune-outside.txt"
    if outside.resolve() != home / "rune-outside.txt":
        assert WindowsNode._safe_path(str(outside)) is None
