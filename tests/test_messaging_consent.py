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
