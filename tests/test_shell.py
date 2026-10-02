from rune.shell.state import ShellMode, ShellState


def test_shell_starts_ambient():
    shell = ShellState()
    assert shell.mode is ShellMode.AMBIENT
    assert shell.workspaces[0].active is True


def test_shell_switches_workspace():
    shell = ShellState()
    shell.activate_workspace("work")
    assert shell.workspaces[1].active is True
    assert shell.workspaces[0].active is False
