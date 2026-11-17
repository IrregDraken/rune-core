import os
import sqlite3
import httpx

from rune.core.remote import OwnerSession


def test_owner_session_refreshes_and_encrypts_rotating_refresh_token(tmp_path):
    seen = {}
    def handler(request):
        seen["refresh_token"] = request.read().decode()
        return httpx.Response(200, json={
            "access_token": "new-access-token",
            "refresh_token": "rotated-refresh-token",
            "expires_in": 3600,
            "token_type": "bearer",
        })

    db = tmp_path / "owner.db"
    key = os.urandom(32)
    session = OwnerSession(
        supabase_url="https://project.supabase.co",
        publishable_key="publishable",
        refresh_token="initial-refresh-token",
        store_path=str(db),
        encryption_key=key,
        transport=httpx.MockTransport(handler),
    )
    assert session.get_access_token() == "new-access-token"
    assert "initial-refresh-token" not in str(seen["refresh_token"])
    session.close()

    connection = sqlite3.connect(db)
    stored = connection.execute("select ciphertext from owner_session where id=1").fetchone()[0]
    connection.close()
    assert b"rotated-refresh-token" not in stored

    restored = OwnerSession(
        supabase_url="https://project.supabase.co",
        publishable_key="publishable",
        refresh_token="initial-refresh-token",
        store_path=str(db),
        encryption_key=key,
        transport=httpx.MockTransport(handler),
    )
    assert restored.refresh_token == "rotated-refresh-token"
    restored.close()


def test_owner_session_requires_encryption_key_for_refresh_token(tmp_path):
    try:
        OwnerSession(
            supabase_url="https://project.supabase.co",
            publishable_key="publishable",
            refresh_token="refresh",
            store_path=str(tmp_path / "owner.db"),
        )
    except ValueError as exc:
        assert "encryption key" in str(exc)
    else:
        raise AssertionError("refresh token persistence must be encrypted")
