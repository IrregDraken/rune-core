from rune.core.integration_catalogue import (
    IntegrationState, integration_catalogue, snapshot, tool_catalogue,
)


def test_integration_catalogue_contains_requested_services():
    ids = {item.id for item in integration_catalogue()}
    assert {"google_workspace", "notion", "brave_search", "tavily", "figma",
            "snapchat", "instagram", "whatsapp", "discord", "android_companion"} <= ids


def test_social_integrations_are_explicit_about_restrictions():
    items = {item.id: item for item in integration_catalogue()}
    assert items["snapchat"].state is IntegrationState.PROVIDER_REVIEW_REQUIRED
    assert "not a general personal-chat API" in " ".join(items["snapchat"].notes)
    assert items["instagram"].state is IntegrationState.PROVIDER_REVIEW_REQUIRED
    assert items["whatsapp"].state is IntegrationState.PROVIDER_REVIEW_REQUIRED


def test_tool_catalogue_marks_external_actions_for_confirmation():
    tools = {item.id: item for item in tool_catalogue()}
    assert tools["instagram.media.publish"].confirmation is True
    assert tools["whatsapp.message.send"].confirmation is True
    assert tools["gmail.send"].confirmation is True
    assert tools["brave.search"].risk == "read"


def test_catalogue_snapshot_is_json_serializable():
    import json
    data = snapshot()
    json.dumps(data)
    assert len(data["integrations"]) >= 30
    assert len(data["tools"]) >= 50



def test_every_manifest_credential_has_an_env_example_placeholder():
    from pathlib import Path
    from rune.core.integration_catalogue import integration_catalogue
    example = Path(__file__).resolve().parents[1] / ".env.example"
    content = example.read_text(encoding="utf-8")
    names = {name for item in integration_catalogue() for name in item.auth_env}
    missing = sorted(name for name in names if f"{name}=" not in content)
    assert not missing, f"Missing environment placeholders: {missing}"



def test_tool_availability_reflects_device_and_review_restrictions():
    from rune.core.integration_catalogue import tool_catalogue
    tools = {item.id: item for item in tool_catalogue()}
    assert tools["android.alarm.create"].availability == "device_dependent"
    assert tools["snapchat.public.search"].availability == "restricted_or_review_required"
