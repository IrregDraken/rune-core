from rune.core.integration_catalogue import tool_schema
from rune.core.capabilities import validate_json_schema


def test_core_tool_schemas_reject_missing_and_unknown_arguments():
    schema = tool_schema("gmail.search")
    validate_json_schema(schema, {"q": "from:team"})
    try:
        validate_json_schema(schema, {})
    except (TypeError, ValueError):
        pass
    else:
        raise AssertionError("missing required query must be rejected")
    try:
        validate_json_schema(schema, {"q": "hello", "arbitrary": True})
    except (TypeError, ValueError):
        pass
    else:
        raise AssertionError("unknown arguments must be rejected")


def test_notion_page_create_has_required_parent_and_properties():
    schema = tool_schema("notion.page.create")
    validate_json_schema(schema, {"parent": {"page_id": "abc"}, "properties": {}})
    try:
        validate_json_schema(schema, {"parent": {}})
    except (TypeError, ValueError):
        pass
    else:
        raise AssertionError("Notion page create must require properties")


def test_every_catalogue_tool_has_a_closed_schema():
    from rune.core.integration_catalogue import tool_catalogue
    for item in tool_catalogue():
        schema = tool_schema(item.id)
        assert schema.get("type") == "object"
        assert schema.get("additionalProperties") is False
