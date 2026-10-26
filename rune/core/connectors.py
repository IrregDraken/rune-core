from __future__ import annotations

"""Provider-neutral connector lifecycle and governed tool execution.

No network client or credential is created here. Concrete MCP and direct-API
adapters implement ConnectorAdapter; tests use deterministic mock adapters.
"""

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Protocol

from .capabilities import ActionRisk, validate_json_schema


class ConnectorStatus(str, Enum):
    DISABLED = "disabled"
    DISCONNECTED = "disconnected"
    NEEDS_AUTH = "needs_auth"
    CONNECTING = "connecting"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    ERROR = "error"


class ExecutionStatus(str, Enum):
    SUCCEEDED = "succeeded"
    SUCCEEDED_UNVERIFIED = "succeeded_unverified"
    AWAITING_APPROVAL = "awaiting_approval"
    BLOCKED = "blocked"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class ToolDefinition:
    id: str
    connector_id: str
    name: str
    description: str
    input_schema: dict[str, Any]
    risk: ActionRisk = ActionRisk.READ
    requires_confirmation: bool = False
    timeout_seconds: float = 30.0
    max_retries: int = 0

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.connector_id.strip() or not self.name.strip():
            raise ValueError("tool id, connector id and name are required")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if not 0 <= self.max_retries <= 3:
            raise ValueError("max_retries must be between 0 and 3")


@dataclass
class ConnectorRecord:
    id: str
    transport: str
    status: ConnectorStatus = ConnectorStatus.DISCONNECTED
    account_label: str | None = None
    granted_scopes: tuple[str, ...] = ()
    credential_env: tuple[str, ...] = ()
    last_health_check: float | None = None
    last_error_code: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionResult:
    execution_id: str
    tool_id: str
    connector_id: str
    status: ExecutionStatus
    output: Any = None
    error_code: str | None = None
    attempts: int = 0
    verified: bool = False
    idempotency_key: str | None = None


@dataclass(frozen=True)
class AuditEvent:
    execution_id: str
    tool_id: str
    connector_id: str
    status: str
    timestamp: float
    arguments_digest: str
    attempts: int
    error_code: str | None = None


class ConnectorAdapter(Protocol):
    async def health_check(self) -> bool: ...
    async def invoke(self, tool_name: str, arguments: dict[str, Any]) -> Any: ...


class ApprovalPolicy(Protocol):
    def is_approved(self, tool: ToolDefinition, arguments: dict[str, Any]) -> bool: ...


class DenyByDefaultApproval:
    """Explicit approval is required for every action marked high impact."""

    def is_approved(self, tool: ToolDefinition, arguments: dict[str, Any]) -> bool:
        return not (
            tool.requires_confirmation
            or tool.risk in {
                ActionRisk.EXTERNAL_COMMUNICATION,
                ActionRisk.FINANCIAL,
                ActionRisk.DESTRUCTIVE,
                ActionRisk.PRIVILEGED,
            }
        )


class ConnectorManager:
    def __init__(self, approval_policy: ApprovalPolicy | None = None) -> None:
        self.records: dict[str, ConnectorRecord] = {}
        self.adapters: dict[str, ConnectorAdapter] = {}
        self.tools: dict[str, ToolDefinition] = {}
        self.audit_log: list[AuditEvent] = []
        self._idempotency: dict[str, ExecutionResult] = {}
        self.approval_policy = approval_policy or DenyByDefaultApproval()

    def register_connector(
        self, record: ConnectorRecord, adapter: ConnectorAdapter | None = None
    ) -> None:
        key = record.id.strip().lower()
        if not key or key in self.records:
            raise ValueError(f"invalid or duplicate connector id: {key}")
        record.id = key
        self.records[key] = record
        if adapter is not None:
            self.adapters[key] = adapter

    def register_tool(self, tool: ToolDefinition) -> None:
        key = tool.id.strip().lower()
        if not key or key in self.tools:
            raise ValueError(f"invalid or duplicate tool id: {key}")
        if tool.connector_id.strip().lower() not in self.records:
            raise ValueError(f"unknown connector: {tool.connector_id}")
        self.tools[key] = tool

    async def health_check(self, connector_id: str) -> ConnectorStatus:
        key = connector_id.strip().lower()
        record = self.records.get(key)
        adapter = self.adapters.get(key)
        if record is None or adapter is None:
            raise KeyError(f"connector unavailable: {key}")
        if record.status is ConnectorStatus.DISABLED:
            return record.status
        record.status = ConnectorStatus.CONNECTING
        try:
            healthy = await asyncio.wait_for(adapter.health_check(), timeout=10)
            record.status = ConnectorStatus.HEALTHY if healthy else ConnectorStatus.NEEDS_AUTH
            record.last_error_code = None if healthy else "credentials_missing_or_health_check_failed"
        except Exception:
            record.status = ConnectorStatus.ERROR
            record.last_error_code = "health_check_error"
        record.last_health_check = time.time()
        return record.status

    async def execute(
        self,
        tool_id: str,
        arguments: dict[str, Any],
        *,
        execution_id: str,
        approved: bool = False,
        idempotency_key: str | None = None,
    ) -> ExecutionResult:
        key = tool_id.strip().lower()
        tool = self.tools.get(key)
        if tool is None:
            return ExecutionResult(execution_id, key, "", ExecutionStatus.UNAVAILABLE,
                                   error_code="tool_not_registered")
        connector_id = tool.connector_id.strip().lower()
        record = self.records[connector_id]
        adapter = self.adapters.get(connector_id)
        if record.status is not ConnectorStatus.HEALTHY or adapter is None:
            return ExecutionResult(execution_id, key, connector_id,
                                   ExecutionStatus.UNAVAILABLE, error_code="connector_not_healthy")
        try:
            validate_json_schema(tool.input_schema, arguments)
        except (TypeError, ValueError) as exc:
            return ExecutionResult(execution_id, key, connector_id,
                                   ExecutionStatus.BLOCKED, error_code="invalid_arguments")
        if not approved and not self.approval_policy.is_approved(tool, arguments):
            return ExecutionResult(execution_id, key, connector_id,
                                   ExecutionStatus.AWAITING_APPROVAL, error_code="approval_required")
        if idempotency_key and idempotency_key in self._idempotency:
            return self._idempotency[idempotency_key]

        attempts = 0
        output: Any = None
        error_code = None
        for attempt in range(tool.max_retries + 1):
            attempts = attempt + 1
            try:
                output = await asyncio.wait_for(
                    adapter.invoke(tool.id, arguments), timeout=tool.timeout_seconds
                )
                result = ExecutionResult(
                    execution_id, key, connector_id, ExecutionStatus.SUCCEEDED_UNVERIFIED,
                    output=output, attempts=attempts, verified=False,
                    idempotency_key=idempotency_key,
                )
                if idempotency_key:
                    self._idempotency[idempotency_key] = result
                self._audit(tool, arguments, result)
                return result
            except asyncio.TimeoutError:
                error_code = "tool_timeout"
            except Exception:
                error_code = "tool_invocation_failed"
            if attempt < tool.max_retries:
                await asyncio.sleep(min(0.1 * (2 ** attempt), 0.5))

        result = ExecutionResult(execution_id, key, connector_id,
                                 ExecutionStatus.FAILED, error_code=error_code,
                                 attempts=attempts, idempotency_key=idempotency_key)
        self._audit(tool, arguments, result)
        return result

    def _audit(self, tool: ToolDefinition, arguments: dict[str, Any],
               result: ExecutionResult) -> None:
        digest = hashlib.sha256(
            json.dumps(arguments, sort_keys=True, default=str).encode()
        ).hexdigest()
        self.audit_log.append(AuditEvent(
            result.execution_id, tool.id, tool.connector_id, result.status.value,
            time.time(), digest, result.attempts, result.error_code,
        ))

    def snapshot(self) -> dict[str, Any]:
        return {
            "connectors": [
                {
                    "id": r.id, "transport": r.transport, "status": r.status.value,
                    "account_label": r.account_label,
                    "granted_scopes": list(r.granted_scopes),
                    "credential_env": list(r.credential_env),
                    "last_health_check": r.last_health_check,
                    "last_error_code": r.last_error_code,
                }
                for r in self.records.values()
            ],
            "tools": [
                {"id": t.id, "connector_id": t.connector_id, "name": t.name,
                 "risk": t.risk.value, "requires_confirmation": t.requires_confirmation}
                for t in self.tools.values()
            ],
            "audit_events": len(self.audit_log),
        }


def build_initial_connector_manager() -> ConnectorManager:
    """Register every planned integration and named tool without activating them."""
    from .integration_catalogue import integration_catalogue, tool_catalogue, tool_schema

    manager = ConnectorManager()
    for item in integration_catalogue():
        manager.register_connector(ConnectorRecord(
            id=item.id,
            transport=item.transport,
            status=ConnectorStatus.DISCONNECTED,
            credential_env=item.auth_env,
            metadata={"category": item.category, "activation_state": item.state.value},
        ))

    risk_map = {
        "read": ActionRisk.READ,
        "write": ActionRisk.WRITE,
        "external_communication": ActionRisk.EXTERNAL_COMMUNICATION,
        "financial": ActionRisk.FINANCIAL,
        "destructive": ActionRisk.DESTRUCTIVE,
        "privileged": ActionRisk.PRIVILEGED,
        "device": ActionRisk.PRIVILEGED,
    }
    # Concrete, allowlisted adapters; no network call occurs during registration.
    from ..adapters.http_connectors import BraveSearchAdapter, FigmaAdapter, GoogleWorkspaceAdapter, NotionAdapter, ResendAdapter, TavilyAdapter, TelegramBotAdapter
    manager.adapters["brave_search"] = BraveSearchAdapter()
    manager.adapters["google_workspace"] = GoogleWorkspaceAdapter()
    manager.adapters["figma"] = FigmaAdapter()
    manager.adapters["notion"] = NotionAdapter()
    manager.adapters["tavily"] = TavilyAdapter()
    manager.adapters["email_delivery"] = ResendAdapter()
    manager.adapters["telegram"] = TelegramBotAdapter()

    for item in tool_catalogue():
        manager.register_tool(ToolDefinition(
            id=item.id,
            connector_id=item.integration_id,
            name=item.name,
            description=item.description,
            input_schema=tool_schema(item.id),
            risk=risk_map.get(item.risk, ActionRisk.READ),
            requires_confirmation=item.confirmation,
        ))
    return manager
