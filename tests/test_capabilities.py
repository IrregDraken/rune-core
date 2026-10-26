import pytest

from rune.core.capabilities import (
    ActionRisk,
    CapabilityStatus,
    IntegrationTransport,
    build_default_catalogue,
    validate_json_schema,
)


def test_default_catalogue_contains_capabilities_and_connectors():
    catalogue = build_default_catalogue()
    assert catalogue.capability("communication.email.send") is not None
    assert catalogue.capability("device.alarms").status is CapabilityStatus.DEVICE_DEPENDENT
    assert catalogue.connector("github").priority == "A"
    assert len(catalogue.capabilities()) >= 25
    assert len(catalogue.connectors()) >= 10


def test_catalogue_filters_by_category_and_status():
    catalogue = build_default_catalogue()
    media = catalogue.capabilities(category="media")
    assert media
    assert all(item.category == "media" for item in media)
    restricted = catalogue.capabilities(status=CapabilityStatus.RESTRICTED)
    assert any(item.risk is ActionRisk.FINANCIAL for item in restricted)


def test_catalogue_rejects_duplicate_ids():
    from rune.core.capabilities import CapabilityCatalogue, CapabilitySpec
    item = CapabilitySpec("test.one", "One", "test", "Test")
    with pytest.raises(ValueError):
        CapabilityCatalogue([item, item])


def test_schema_validation_accepts_valid_object():
    validate_json_schema(
        {
            "type": "object",
            "required": ["recipient", "subject"],
            "properties": {
                "recipient": {"type": "string", "minLength": 3},
                "subject": {"type": "string", "maxLength": 120},
            },
            "additionalProperties": False,
        },
        {"recipient": "user@example.com", "subject": "Hello"},
    )


@pytest.mark.parametrize(
    "value",
    [
        {},
        {"recipient": "x", "subject": "Hello"},
        {"recipient": "user@example.com", "subject": "Hello", "extra": True},
    ],
)
def test_schema_validation_rejects_invalid_object(value):
    schema = {
        "type": "object",
        "required": ["recipient", "subject"],
        "properties": {
            "recipient": {"type": "string", "minLength": 3},
            "subject": {"type": "string", "maxLength": 120},
        },
        "additionalProperties": False,
    }
    with pytest.raises(ValueError):
        validate_json_schema(schema, value)


def test_schema_validation_checks_array_items_and_numeric_bounds():
    schema = {
        "type": "object",
        "properties": {
            "count": {"type": "integer", "minimum": 1, "maximum": 5},
            "tags": {"type": "array", "items": {"type": "string"}, "maxItems": 2},
        },
    }
    validate_json_schema(schema, {"count": 3, "tags": ["a", "b"]})
    with pytest.raises(ValueError):
        validate_json_schema(schema, {"count": 8, "tags": ["a"]})
    with pytest.raises(ValueError):
        validate_json_schema(schema, {"count": 2, "tags": ["a", 2]})


def test_schema_validator_fails_closed_for_unknown_keywords():
    with pytest.raises(ValueError):
        validate_json_schema({"type": "string", "pattern": "^[a-z]+$"}, "abc")
