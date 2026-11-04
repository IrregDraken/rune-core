import time

from rune.core.messaging_consent import MessagingConsentRegistry


def test_whatsapp_requires_opt_in_for_all_outbound_messages(tmp_path):
    registry = MessagingConsentRegistry(str(tmp_path / "consent.sqlite3"))
    assert not registry.can_send("whatsapp", "+2348000000000", "template")
    registry.record_opt_in("whatsapp", "+2348000000000", "explicit user opt-in")
    assert registry.can_send("whatsapp", "+2348000000000", "template")
    assert not registry.can_send("whatsapp", "+2348000000000", "text")


def test_whatsapp_text_requires_recent_inbound_message(tmp_path):
    registry = MessagingConsentRegistry(str(tmp_path / "consent.sqlite3"))
    registry.record_opt_in("whatsapp", "2348000000000", "explicit user opt-in")
    now = time.time()
    assert not registry.can_send("whatsapp", "2348000000000", "text", now=now)
    registry.record_inbound("whatsapp", "2348000000000", timestamp=now - 60)
    assert registry.can_send("whatsapp", "2348000000000", "text", now=now)
    assert not registry.can_send("whatsapp", "2348000000000", "text", now=now + 25 * 60 * 60)


def test_revoke_removes_send_permission(tmp_path):
    registry = MessagingConsentRegistry(str(tmp_path / "consent.sqlite3"))
    registry.record_opt_in("whatsapp", "2348000000000", "user opt-in")
    registry.revoke("whatsapp", "2348000000000", "user requested stop")
    assert not registry.can_send("whatsapp", "2348000000000", "template")


def test_whatsapp_webhook_signature_and_inbound_window(tmp_path):
    import hashlib
    import hmac
    import json
    from rune.core.messaging_consent import WhatsAppWebhookVerifier

    secret = "test-app-secret"
    registry = MessagingConsentRegistry(str(tmp_path / "consent.sqlite3"))
    now = time.time()
    payload = {"entry": [{"changes": [{"value": {"messages": [
        {"from": "2348000000000", "timestamp": str(now), "text": {"body": "START"}}
    ]}}]}]}
    raw = json.dumps(payload).encode()
    signature = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    assert WhatsAppWebhookVerifier.verify_signature(raw, signature, secret)
    assert not WhatsAppWebhookVerifier.verify_signature(raw, "sha256=bad", secret)
    result = WhatsAppWebhookVerifier.ingest(payload, registry)
    assert result == {"inbound_recorded": 1, "opted_in": 1, "revoked": 0}
    assert registry.can_send("whatsapp", "2348000000000", "text", now=now + 30)


def test_whatsapp_verified_stop_revokes_consent(tmp_path):
    from rune.core.messaging_consent import WhatsAppWebhookVerifier

    registry = MessagingConsentRegistry(str(tmp_path / "consent.sqlite3"))
    registry.record_opt_in("whatsapp", "2348000000000", "previous verified opt-in")
    payload = {"entry": [{"changes": [{"value": {"messages": [
        {"from": "2348000000000", "timestamp": str(time.time()), "text": {"body": "STOP"}}
    ]}}]}]}
    result = WhatsAppWebhookVerifier.ingest(payload, registry)
    assert result["revoked"] == 1
    assert not registry.can_send("whatsapp", "2348000000000", "template")


def test_whatsapp_webhook_ignores_invalid_timestamps_and_malformed_entries(tmp_path):
    from rune.core.messaging_consent import WhatsAppWebhookVerifier

    registry = MessagingConsentRegistry(str(tmp_path / "consent.sqlite3"))
    result = WhatsAppWebhookVerifier.ingest({"entry": [
        {"changes": [{"value": {"messages": [
            {"from": "2348000000000", "timestamp": "not-a-time", "text": {"body": "START"}}
        ]}}]},
        {"changes": "malformed"},
    ]}, registry)
    assert result == {"inbound_recorded": 0, "opted_in": 0, "revoked": 0}
