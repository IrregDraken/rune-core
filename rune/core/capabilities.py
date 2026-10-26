from __future__ import annotations

"""Declarative capability and connector catalogue for R.U.N.E.

This module describes what R.U.N.E can support independently of model providers,
channels, credentials, and concrete service adapters. A catalogue entry is not
proof that an integration is configured or an action is executable.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable


class CapabilityStatus(str, Enum):
    FOUNDATION = "foundation"
    PLANNED = "planned"
    PROVIDER_DEPENDENT = "provider_dependent"
    DEVICE_DEPENDENT = "device_dependent"
    RESTRICTED = "restricted"
    MANUAL_FALLBACK = "manual_fallback"


class IntegrationTransport(str, Enum):
    DIRECT_API = "direct_api"
    MCP = "mcp"
    BROWSER = "browser"
    LOCAL = "local"
    DEVICE = "device"
    MANUAL = "manual"


class ActionRisk(str, Enum):
    READ = "read"
    WRITE = "write"
    EXTERNAL_COMMUNICATION = "external_communication"
    FINANCIAL = "financial"
    DESTRUCTIVE = "destructive"
    PRIVILEGED = "privileged"


@dataclass(frozen=True)
class CapabilitySpec:
    id: str
    name: str
    category: str
    description: str
    status: CapabilityStatus = CapabilityStatus.PLANNED
    transports: tuple[IntegrationTransport, ...] = ()
    integrations: tuple[str, ...] = ()
    risk: ActionRisk = ActionRisk.READ
    requires_confirmation: bool = False
    prerequisites: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class ConnectorSpec:
    id: str
    name: str
    purpose: str
    transport: IntegrationTransport
    priority: str
    services: tuple[str, ...] = ()
    required_scopes: tuple[str, ...] = ()
    credential_env: tuple[str, ...] = ()
    status: CapabilityStatus = CapabilityStatus.PLANNED
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ConnectorState:
    connector_id: str
    configured: bool = False
    healthy: bool = False
    account_label: str | None = None
    granted_scopes: tuple[str, ...] = ()
    last_checked_at: str | None = None
    error_code: str | None = None


class CapabilityCatalogue:
    """Read-only catalogue with stable IDs and duplicate protection."""

    def __init__(
        self,
        capabilities: Iterable[CapabilitySpec] = (),
        connectors: Iterable[ConnectorSpec] = (),
    ) -> None:
        self._capabilities: dict[str, CapabilitySpec] = {}
        self._connectors: dict[str, ConnectorSpec] = {}
        for item in capabilities:
            self.register_capability(item)
        for item in connectors:
            self.register_connector(item)

    def register_capability(self, spec: CapabilitySpec) -> None:
        key = spec.id.strip().lower()
        if not key:
            raise ValueError("capability id is required")
        if key in self._capabilities:
            raise ValueError(f"capability already registered: {key}")
        self._capabilities[key] = spec

    def register_connector(self, spec: ConnectorSpec) -> None:
        key = spec.id.strip().lower()
        if not key:
            raise ValueError("connector id is required")
        if key in self._connectors:
            raise ValueError(f"connector already registered: {key}")
        self._connectors[key] = spec

    def capability(self, capability_id: str) -> CapabilitySpec | None:
        return self._capabilities.get(capability_id.strip().lower())

    def connector(self, connector_id: str) -> ConnectorSpec | None:
        return self._connectors.get(connector_id.strip().lower())

    def capabilities(
        self,
        *,
        category: str | None = None,
        status: CapabilityStatus | None = None,
    ) -> list[CapabilitySpec]:
        items = self._capabilities.values()
        if category is not None:
            items = (item for item in items if item.category == category)
        if status is not None:
            items = (item for item in items if item.status is status)
        return sorted(items, key=lambda item: (item.category, item.name))

    def connectors(self, *, priority: str | None = None) -> list[ConnectorSpec]:
        items = self._connectors.values()
        if priority is not None:
            items = (item for item in items if item.priority == priority)
        return sorted(items, key=lambda item: (item.priority, item.name))

    def snapshot(self) -> dict[str, Any]:
        return {
            "capabilities": [
                {
                    "id": item.id,
                    "name": item.name,
                    "category": item.category,
                    "description": item.description,
                    "status": item.status.value,
                    "transports": [value.value for value in item.transports],
                    "integrations": list(item.integrations),
                    "risk": item.risk.value,
                    "requires_confirmation": item.requires_confirmation,
                    "prerequisites": list(item.prerequisites),
                    "tags": list(item.tags),
                }
                for item in self.capabilities()
            ],
            "connectors": [
                {
                    "id": item.id,
                    "name": item.name,
                    "purpose": item.purpose,
                    "transport": item.transport.value,
                    "priority": item.priority,
                    "services": list(item.services),
                    "required_scopes": list(item.required_scopes),
                    "status": item.status.value,
                    "notes": list(item.notes),
                }
                for item in self.connectors()
            ],
        }


def validate_json_schema(schema: dict[str, Any], value: Any, path: str = "$") -> None:
    """Validate the safe JSON Schema subset needed by the initial tool boundary.

    Supports object, array, string, number, integer, boolean, null, required,
    properties, additionalProperties, items, enum, minimum/maximum, minLength,
    maxLength, minItems and maxItems. Unsupported schema keywords fail closed.
    """
    supported = {
        "type", "required", "properties", "additionalProperties", "items",
        "enum", "minimum", "maximum", "minLength", "maxLength",
        "minItems", "maxItems",
    }
    unknown = set(schema) - supported
    if unknown:
        raise ValueError(f"unsupported schema keywords at {path}: {sorted(unknown)}")

    expected = schema.get("type")
    type_checks = {
        "object": lambda v: isinstance(v, dict),
        "array": lambda v: isinstance(v, list),
        "string": lambda v: isinstance(v, str),
        "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
        "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
        "boolean": lambda v: isinstance(v, bool),
        "null": lambda v: v is None,
    }
    if expected is not None:
        if expected not in type_checks:
            raise ValueError(f"unsupported schema type at {path}: {expected}")
        if not type_checks[expected](value):
            raise ValueError(f"expected {expected} at {path}")

    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(f"value is not an allowed enum member at {path}")

    if isinstance(value, dict):
        required = schema.get("required", [])
        missing = [key for key in required if key not in value]
        if missing:
            raise ValueError(f"missing required properties at {path}: {missing}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties", True) is False:
            extra = set(value) - set(properties)
            if extra:
                raise ValueError(f"additional properties are not allowed at {path}: {sorted(extra)}")
        for key, item in value.items():
            if key in properties:
                validate_json_schema(properties[key], item, f"{path}.{key}")

    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            raise ValueError(f"too few items at {path}")
        if len(value) > schema.get("maxItems", float("inf")):
            raise ValueError(f"too many items at {path}")
        if "items" in schema:
            for index, item in enumerate(value):
                validate_json_schema(schema["items"], item, f"{path}[{index}]")

    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            raise ValueError(f"string too short at {path}")
        if len(value) > schema.get("maxLength", float("inf")):
            raise ValueError(f"string too long at {path}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if value < schema.get("minimum", float("-inf")):
            raise ValueError(f"value below minimum at {path}")
        if value > schema.get("maximum", float("inf")):
            raise ValueError(f"value above maximum at {path}")


def build_default_catalogue() -> CapabilityCatalogue:
    """Return the initial capability map and planned connector inventory."""
    api = IntegrationTransport.DIRECT_API
    mcp = IntegrationTransport.MCP
    browser = IntegrationTransport.BROWSER
    local = IntegrationTransport.LOCAL
    device = IntegrationTransport.DEVICE
    manual = IntegrationTransport.MANUAL
    read = ActionRisk.READ
    write = ActionRisk.WRITE
    external = ActionRisk.EXTERNAL_COMMUNICATION
    financial = ActionRisk.FINANCIAL
    destructive = ActionRisk.DESTRUCTIVE
    privileged = ActionRisk.PRIVILEGED

    capability_rows = [
        ("communication.email.read", "Read and search email", "communication", "Search messages, threads and attachments.", CapabilityStatus.PROVIDER_DEPENDENT, (api, mcp), ("gmail", "microsoft365"), read, False),
        ("communication.email.draft", "Draft email", "communication", "Create and revise email drafts.", CapabilityStatus.PROVIDER_DEPENDENT, (api, mcp), ("gmail", "microsoft365"), write, False),
        ("communication.email.send", "Send email", "communication", "Send or forward authorised email.", CapabilityStatus.PROVIDER_DEPENDENT, (api, mcp), ("gmail", "microsoft365"), external, True),
        ("communication.contacts.manage", "Manage contacts", "communication", "Read and update authorised contacts.", CapabilityStatus.PLANNED, (api, mcp), ("google_contacts", "microsoft365"), write, True),
        ("calendar.read", "Read calendar", "productivity", "Read events and availability.", CapabilityStatus.PROVIDER_DEPENDENT, (api, mcp), ("google_calendar", "microsoft365"), read, False),
        ("calendar.write", "Manage calendar events", "productivity", "Create, move, update and cancel events.", CapabilityStatus.PLANNED, (api, mcp), ("google_calendar", "microsoft365"), write, True),
        ("tasks.manage", "Manage tasks and reminders", "productivity", "Create, update, prioritise and complete tasks.", CapabilityStatus.PLANNED, (api, mcp, local), ("notion", "linear", "todoist"), write, False),
        ("projects.coordinate", "Coordinate projects", "projects", "Track goals, milestones, dependencies and blockers.", CapabilityStatus.PLANNED, (api, mcp), ("notion", "linear", "github"), write, True),
        ("web.research", "Web research", "web", "Search, read, compare and summarise public sources.", CapabilityStatus.PLANNED, (api, mcp, browser), ("search", "browser"), read, False),
        ("web.browser.operate", "Operate browser", "web", "Navigate websites and complete approved browser tasks.", CapabilityStatus.PLANNED, (browser, mcp), ("browser",), write, True),
        ("files.create", "Create files", "files", "Generate documents, spreadsheets, presentations and data files.", CapabilityStatus.PLANNED, (local,), ("filesystem",), write, False),
        ("files.read_search", "Read and search files", "files", "Extract and search authorised files.", CapabilityStatus.PLANNED, (local, mcp), ("filesystem", "google_drive", "onedrive"), read, False),
        ("files.organise", "Organise files", "files", "Move, rename and organise files in approved locations.", CapabilityStatus.PLANNED, (local, mcp), ("filesystem", "google_drive", "onedrive"), write, True),
        ("files.delete", "Delete files", "files", "Delete files in explicitly approved scopes.", CapabilityStatus.PLANNED, (local, mcp), ("filesystem", "google_drive", "onedrive"), destructive, True),
        ("developer.github", "GitHub operations", "development", "Inspect repositories, issues, pull requests, code and workflows.", CapabilityStatus.PROVIDER_DEPENDENT, (api, mcp), ("github",), write, True),
        ("developer.code.execute", "Execute code and tests", "development", "Run code in an isolated, resource-limited environment.", CapabilityStatus.PLANNED, (local,), ("sandbox",), privileged, True),
        ("knowledge.manage", "Manage knowledge base", "knowledge", "Ingest, index, cite and maintain approved knowledge.", CapabilityStatus.FOUNDATION, (local, mcp), ("sqlite", "notion", "google_drive"), write, False),
        ("creative.image.generate", "Generate images", "creative", "Generate or edit images through an authorised provider.", CapabilityStatus.PROVIDER_DEPENDENT, (api,), ("image_provider",), write, False),
        ("creative.audio.transcribe", "Transcribe audio", "creative", "Transcribe user-provided or authorised audio.", CapabilityStatus.PROVIDER_DEPENDENT, (api,), ("speech_provider",), read, False),
        ("creative.audio.speak", "Generate speech", "creative", "Create spoken audio from text.", CapabilityStatus.PROVIDER_DEPENDENT, (api,), ("tts_provider",), write, False),
        ("media.spotify.search", "Search Spotify", "media", "Search catalogue and playlists through supported Spotify APIs.", CapabilityStatus.PROVIDER_DEPENDENT, (api,), ("spotify",), read, False),
        ("media.spotify.playback", "Control Spotify playback", "media", "Control playback where policy, account and active-device requirements permit.", CapabilityStatus.RESTRICTED, (api, device), ("spotify", "android_companion"), privileged, True),
        ("media.streaming.open", "Open streaming services", "media", "Find content and open supported streaming destinations.", CapabilityStatus.PLANNED, (api, device), ("browser", "device"), read, False),
        ("finance.analyse", "Analyse financial records", "finance", "Analyse explicitly connected financial data.", CapabilityStatus.PLANNED, (api,), ("financial_provider",), read, False),
        ("finance.transact", "Make payments or purchases", "finance", "Initiate transactions only through approved provider flows.", CapabilityStatus.RESTRICTED, (api,), ("payment_provider",), financial, True),
        ("business.crm.manage", "Manage CRM records", "business", "Read and update authorised CRM contacts, companies and deals.", CapabilityStatus.PLANNED, (api, mcp), ("hubspot", "salesforce"), write, True),
        ("automation.schedule", "Schedule automations", "automation", "Create recurring and scheduled workflows.", CapabilityStatus.PLANNED, (local,), ("scheduler",), write, False),
        ("automation.monitor", "Monitor conditions", "automation", "Check explicit user-defined conditions and notify on changes.", CapabilityStatus.PLANNED, (api, local), ("scheduler", "webhooks"), read, False),
        ("device.alarms", "Set device alarms", "device", "Set alarms on an authorised Android device.", CapabilityStatus.DEVICE_DEPENDENT, (device,), ("android_companion",), privileged, True),
        ("device.notifications", "Manage device notifications", "device", "Deliver or read notifications with granted permissions.", CapabilityStatus.DEVICE_DEPENDENT, (device,), ("android_companion",), privileged, True),
        ("smarthome.control", "Control smart-home devices", "device", "Operate authorised smart-home devices and scenes.", CapabilityStatus.DEVICE_DEPENDENT, (api, mcp), ("home_assistant",), privileged, True),
    ]
    capabilities = [
        CapabilitySpec(
            id=row[0], name=row[1], category=row[2], description=row[3],
            status=row[4], transports=row[5], integrations=row[6], risk=row[7],
            requires_confirmation=row[8],
        )
        for row in capability_rows
    ]

    connectors = [
        ConnectorSpec("github", "GitHub", "Repository and developer workflow access.", mcp, "A", ("repositories", "issues", "pull requests", "actions"), ("repo", "read:user"), status=CapabilityStatus.PROVIDER_DEPENDENT),
        ConnectorSpec("google_workspace", "Google Workspace", "Gmail, Calendar, Drive and contacts through Google APIs; MCP where appropriate.", api, "A", ("gmail", "calendar", "drive", "contacts"), ("least-privilege OAuth scopes",), status=CapabilityStatus.PROVIDER_DEPENDENT),
        ConnectorSpec("microsoft365", "Microsoft 365", "Outlook, Calendar, OneDrive and SharePoint.", mcp, "A", ("mail", "calendar", "files"), ("least-privilege Graph scopes",), status=CapabilityStatus.PROVIDER_DEPENDENT),
        ConnectorSpec("notion", "Notion", "Pages, databases and project knowledge through the Notion API or vetted MCP server.", api, "A", ("pages", "databases", "search"), ("read/write only where granted",), status=CapabilityStatus.PROVIDER_DEPENDENT),
        ConnectorSpec("filesystem", "Scoped filesystem", "RUNE-managed workspace files only.", local, "A", ("read", "write", "search"), (), status=CapabilityStatus.FOUNDATION, notes=("Never expose unrestricted host filesystem access.",)),
        ConnectorSpec("brave_search", "Brave Search", "Independent web search provider for public-web research.", api, "A", ("web search",), ("BRAVE_SEARCH_API_KEY",), status=CapabilityStatus.PROVIDER_DEPENDENT),
        ConnectorSpec("tavily_search", "Tavily", "Research-oriented web search and extraction provider.", api, "A", ("search", "extract"), ("TAVILY_API_KEY",), status=CapabilityStatus.PROVIDER_DEPENDENT),
        ConnectorSpec("browser_search", "Browser automation", "Isolated browser navigation and page interaction, separate from search providers.", browser, "A", ("fetch", "browser"), (), status=CapabilityStatus.PLANNED, notes=("Web content is untrusted input.",)),
        ConnectorSpec("linear", "Linear", "Issue and project tracking.", mcp, "B", ("issues", "projects", "cycles"), ("workspace scopes",), status=CapabilityStatus.PLANNED),
        ConnectorSpec("slack", "Slack", "Search and authorised workspace messaging.", mcp, "B", ("search", "messages", "channels"), ("least-privilege OAuth scopes",), status=CapabilityStatus.PLANNED),
        ConnectorSpec("discord", "Discord", "Later communication channel and approved bot integration.", api, "B", ("messages", "servers", "commands"), ("bot scopes and intents",), status=CapabilityStatus.PLANNED),
        ConnectorSpec("hubspot", "HubSpot", "CRM contacts, companies, deals and tickets.", mcp, "B", ("contacts", "companies", "deals", "tickets"), ("CRM scopes",), status=CapabilityStatus.PLANNED),
        ConnectorSpec("spotify", "Spotify", "Music catalogue and permitted playback operations.", api, "C", ("search", "playlists", "playback"), ("Spotify OAuth scopes",), status=CapabilityStatus.RESTRICTED, notes=("Review current Spotify developer policy before enabling playback control.",)),
        ConnectorSpec("home_assistant", "Home Assistant", "Later smart-home automation.", mcp, "C", ("entities", "scenes", "services"), ("instance token",), status=CapabilityStatus.DEVICE_DEPENDENT),
        ConnectorSpec("zotero", "Zotero", "Research library and references.", mcp, "C", ("library", "collections", "items"), ("library access",), status=CapabilityStatus.PLANNED),
        ConnectorSpec("sentry", "Sentry", "Error monitoring and issue triage.", mcp, "C", ("issues", "events", "projects"), ("project scopes",), status=CapabilityStatus.PLANNED),
        ConnectorSpec("cloud_deploy", "Deployment platforms", "Approved deployment and operations actions.", api, "C", ("deployments", "logs", "domains"), ("provider-specific scopes",), status=CapabilityStatus.PLANNED, notes=("Production deployments and rollback require explicit approval.",)),
    ]
    return CapabilityCatalogue(capabilities, connectors)
