from rune.api import RUNERequestHandler


def test_remote_api_authentication_can_be_enabled(monkeypatch):
    monkeypatch.setenv("RUNE_API_AUTH_REQUIRED", "true")
    assert RUNERequestHandler._auth_required() is True


def test_local_api_authentication_remains_opt_in_for_local_desktop(monkeypatch):
    monkeypatch.delenv("RUNE_API_AUTH_REQUIRED", raising=False)
    assert RUNERequestHandler._auth_required() is False


def test_api_authentication_flag_accepts_common_boolean_values(monkeypatch):
    for value in ("1", "true", "TRUE", "yes"):
        monkeypatch.setenv("RUNE_API_AUTH_REQUIRED", value)
        assert RUNERequestHandler._auth_required() is True
