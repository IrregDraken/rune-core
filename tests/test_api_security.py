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


def test_voice_and_remote_mutation_routes_require_a_session_even_in_local_mode():
    privileged = (
        "/api/voice/transcribe",
        "/api/voice/synthesize",
        "/api/voice/session",
        "/api/remote/submit",
        "/api/memory",
    )
    for path in privileged:
        assert RUNERequestHandler._requires_session(path) is True


def test_read_only_health_and_state_routes_are_not_privileged_by_default():
    assert RUNERequestHandler._requires_session("/api/health") is False
    assert RUNERequestHandler._requires_session("/api/state") is False
