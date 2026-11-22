import json
from urllib.error import HTTPError

import pytest

from rune.core.supabase_auth import (
    SupabaseAuthConfigurationError,
    SupabaseAuthVerifier,
)


class FakeResponse:
    status = 200

    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


def test_verifier_uses_supabase_user_endpoint_and_returns_server_identity():
    seen = {}

    def opener(request, timeout):
        seen["url"] = request.full_url
        seen["authorization"] = request.get_header("Authorization")
        seen["apikey"] = request.get_header("Apikey")
        seen["timeout"] = timeout
        return FakeResponse({"id": "owner-123", "email": "owner@example.test"})

    verifier = SupabaseAuthVerifier(
        "https://project.supabase.co", "publishable-key", opener=opener
    )

    assert verifier.verify("access-token") == {
        "id": "owner-123",
        "email": "owner@example.test",
    }
    assert seen == {
        "url": "https://project.supabase.co/auth/v1/user",
        "authorization": "Bearer access-token",
        "apikey": "publishable-key",
        "timeout": 5.0,
    }


def test_verifier_rejects_missing_or_oversized_tokens_without_network_call():
    def opener(*_args, **_kwargs):
        raise AssertionError("network must not be called")

    verifier = SupabaseAuthVerifier(
        "https://project.supabase.co", "publishable-key", opener=opener
    )
    assert verifier.verify(None) is None
    assert verifier.verify("x" * 16_385) is None


def test_verifier_rejects_auth_errors():
    def opener(*_args, **_kwargs):
        raise HTTPError("https://project.supabase.co/auth/v1/user", 401, "invalid", {}, None)

    verifier = SupabaseAuthVerifier(
        "https://project.supabase.co", "publishable-key", opener=opener
    )
    assert verifier.verify("expired-token") is None


def test_verifier_fails_closed_when_auth_service_is_unavailable():
    def opener(*_args, **_kwargs):
        raise OSError("network unavailable")

    verifier = SupabaseAuthVerifier(
        "https://project.supabase.co", "publishable-key", opener=opener
    )
    assert verifier.verify("access-token") is None


def test_verifier_requires_configuration():
    verifier = SupabaseAuthVerifier("", "")
    assert not verifier.configured
    with pytest.raises(SupabaseAuthConfigurationError):
        verifier.verify("access-token")


def test_verifier_rejects_response_without_subject():
    verifier = SupabaseAuthVerifier(
        "https://project.supabase.co",
        "publishable-key",
        opener=lambda *_args, **_kwargs: FakeResponse({"email": "owner@example.test"}),
    )
    assert verifier.verify("access-token") is None
