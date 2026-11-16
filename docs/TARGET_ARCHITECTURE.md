# R.U.N.E Target Architecture and Database Schema

Version: 1.0
Status: Proposed target architecture for the locked personal R.U.N.E product
Owner model: One personal owner; personal and business context scopes
Primary clients: iOS, Android, watchOS, macOS, Windows and Web
Optional channels: WhatsApp, Telegram and Discord

## 1. Architecture principles

1. One intelligence core serves every client.
2. Clients never connect directly to privileged provider credentials or internal databases.
3. Every capability has a stable ID, input/output schema, risk class, prerequisites and verification strategy.
4. Authentication, device identity, action authorization and provider consent are separate concepts.
5. Approval is an immutable, action-bound record, not a boolean supplied with an execution request.
6. Every side effect has a durable execution record and auditable outcome.
7. Monitoring and automations are persistent server-side services, not mobile background loops.
8. Device-specific work executes through enrolled nodes with explicit capabilities.
9. Personal and business contexts are separate scopes under one owner.
10. Offline clients queue safe user-originated events and synchronize through versioned event cursors.
11. Unverified outcomes must never be reported as verified success.
12. External content is untrusted data and cannot grant authority or override system policy.

## 2. Logical architecture

```text
iOS / Android / Watch / macOS / Windows / Web / optional channels
                              |
                       Edge API Gateway
                 TLS / rate limits / WAF / routing
                              |
                 Authentication & Device Identity
                              |
                  Communication / Session Service
                              |
                   Conversation & Event Service
                              |
                   R.U.N.E Orchestration Runtime
            +-----------------+--------------------+
            |                 |                    |
       Context & Memory   Model Router        Planner / Workflow
            |                 |                    |
            +-----------------+--------------------+
                              |
                     Policy / Approval Engine
                              |
                      Tool Execution Service
                              |
              +---------------+----------------+
              |               |                |
         Direct APIs          MCP          Device Nodes
              |               |          Mac / Windows /
         Providers       Trusted servers   iOS / Watch
              |
       External services

Monitoring Scheduler -> Event Ingestion -> Rules/Incidents -> Notification Service
                                      |
                              Durable Event Store

PostgreSQL = shared source of truth
Redis = ephemeral coordination/queues/cache
Object Storage = attachments/audio/artifacts
Secret Manager = provider credentials
SQLite = local node cache and offline journal
```

## 3. Service boundaries

### 3.1 Edge API Gateway
- TLS termination and routing.
- Strict CORS allowlist for browser clients.
- Request size and rate limits.
- Authentication middleware.
- Request IDs and trace propagation.
- No provider secrets in client builds.
- Public webhook routes are isolated and signature-verified.

### 3.2 Identity and Device Service
- Single owner account.
- Device enrollment and revocation.
- Device public-key registration.
- Session issuance, rotation and revocation.
- Assurance level and last-seen state.
- Passkey and platform-biometric challenge integration.
- Device registration does not automatically authorize every tool.

### 3.3 Communication and Session Service
- Unified conversations across first-party clients.
- Channel adapters map external channel identities to the owner and a conversation.
- Message ordering, deduplication and delivery state.
- Voice transcripts and audio references with retention policies.
- Reconnect and sync cursors.

### 3.4 Orchestration Runtime
- Intent interpretation.
- Context assembly.
- Model selection and fallback.
- Plan construction.
- Tool selection from a registered capability catalogue.
- Policy checks before every side effect.
- Durable workflow state.
- Verification and user-facing result summaries.

### 3.5 Memory Service
- Episodic, semantic, preference, procedural and project memory.
- Scope-aware retrieval.
- Provenance, confidence, sensitivity, validity and supersession.
- Inspect, correct, export and delete.
- No implicit promotion of model inference into user fact.

### 3.6 Model Router
- Provider adapters for OpenAI, Gemini, Claude, DeepSeek and Ollama.
- Task routing based on capability, latency, privacy, availability and configured cost ceiling.
- Timeouts, circuit breakers and fallback.
- Structured output validation.
- Provider usage/cost records.
- Deterministic provider used only for development and tests.

### 3.7 Policy and Approval Service
- Central policy evaluation before connector or node execution.
- Risk class and user-configured permission policy.
- Approval record bound to exact arguments and tool version.
- One-time approval consumption.
- Expiry, revocation and replay protection.
- High-impact actions always require explicit approval.
- Critical financial, destructive and security actions require strong re-authentication.

### 3.8 Tool Execution Service
- Tool schema validation.
- Connector health verification.
- Execution IDs and idempotency.
- Bounded timeout and retry.
- No automatic retry for non-idempotent side effects.
- Output sanitization.
- Durable audit and execution attempts.
- Verification evidence stored separately from raw provider output.

### 3.9 Connector and MCP Service
- Provider-specific direct API adapters preferred where stable.
- MCP used as a transport for trusted, preconfigured servers.
- Model/user input cannot supply arbitrary MCP URLs, commands or environment variables.
- Least-privilege scopes.
- Health state distinguishes disconnected, needs-auth, configured, healthy, degraded and disabled.
- Configured does not mean live-verified.

### 3.10 Device Node Service
- Windows and macOS local execution nodes.
- Mobile and watch capabilities only through supported OS APIs.
- Node capability advertisement and health.
- Device pairing and short-lived node credentials.
- Local operations are sandboxed and permission-scoped.
- Offline actions are queued only when safe and re-authorized at execution time.

### 3.11 Monitoring and Notification Services
- Scheduled checks and provider webhooks.
- Event normalization and deduplication.
- Severity and alert policy.
- Incident lifecycle.
- Notification routing, retries and delivery receipts.
- Quiet hours and escalation configuration.
- Mobile push uses APNs/FCM; watch delivery follows paired-device and OS behavior.

### 3.12 Automation Service
- Durable scheduled and event-triggered workflows.
- Versioned workflow definitions.
- Approval checkpoints.
- Retry and compensation policies.
- Pause, cancel and resume.
- Every step references a registered capability and execution record.

## 4. Platform mapping

| Client | Responsibilities |
|---|---|
| iOS (SwiftUI) | Main mobile experience, chat, voice, approvals, notifications, pairing |
| Android (Flutter initially) | Main mobile experience, chat, voice, approvals, notifications, pairing |
| watchOS (SwiftUI) | Briefings, short voice turns, quick commands, haptics, notifications |
| macOS | Local node, desktop assistant, computer interaction and development workflows |
| Windows | Existing desktop node and command center, expanded toward parity |
| Web (React/TypeScript) | Full command center, configuration, monitoring, audit and workflow management |
| WhatsApp/Telegram/Discord | Optional channel adapters, not primary product surfaces |

All clients use the same gateway and user identity. They do not maintain independent memory stores.

## 5. Recommended deployment topology

### Initial production topology
- API gateway and application services in a managed container environment.
- PostgreSQL managed database with point-in-time recovery.
- Redis for queues, ephemeral state and distributed locks when needed.
- Object storage for attachments, recordings and generated artifacts.
- Managed secret storage for OAuth refresh tokens and provider credentials.
- Worker process for scheduled monitoring and automation.
- OpenTelemetry-compatible traces, metrics and structured logs.

Do not deploy the current local HTTP server directly as the public production gateway. Introduce a hardened ASGI/API service boundary (for example FastAPI/Starlette) or equivalent, preserving the Python domain core.

### Local-first nodes
Each desktop node keeps:
- SQLite cache.
- Encrypted local event journal.
- Device key material in OS secure storage.
- Node capability registry.
- Pending sync queue.

PostgreSQL remains the shared source of truth for synced state. Local SQLite is not a second conflicting authority.

## 6. PostgreSQL database schema

Use PostgreSQL with UUID primary keys, timestamptz and JSONB where structured provider payloads are necessary. The initial product is single-owner, not multi-tenant SaaS. Keep owner_id on owner-scoped records for integrity and future migration, but do not implement arbitrary tenant administration.

### 6.1 Identity and devices

```sql
CREATE TABLE owners (
  id UUID PRIMARY KEY,
  display_name TEXT NOT NULL,
  email CITEXT UNIQUE,
  status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active','locked','deleted')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE devices (
  id UUID PRIMARY KEY,
  owner_id UUID NOT NULL REFERENCES owners(id),
  device_key_id TEXT NOT NULL UNIQUE,
  platform TEXT NOT NULL CHECK (platform IN
    ('ios','android','watchos','macos','windows','web','channel')),
  display_name TEXT NOT NULL,
  public_key TEXT,
  assurance TEXT NOT NULL DEFAULT 'observed'
    CHECK (assurance IN ('observed','paired','verified','strong')),
  capabilities JSONB NOT NULL DEFAULT '[]',
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending','active','revoked','lost')),
  last_seen_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  revoked_at TIMESTAMPTZ
);
CREATE INDEX devices_owner_status_idx ON devices(owner_id,status);

CREATE TABLE sessions (
  id UUID PRIMARY KEY,
  owner_id UUID NOT NULL REFERENCES owners(id),
  device_id UUID REFERENCES devices(id),
  token_hash TEXT NOT NULL UNIQUE,
  audience TEXT NOT NULL,
  scopes TEXT[] NOT NULL DEFAULT '{}',
  issued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL,
  revoked_at TIMESTAMPTZ
);
CREATE INDEX sessions_owner_expiry_idx ON sessions(owner_id,expires_at);
```

Store only token hashes. Provider refresh tokens and API keys belong in a secret manager; database rows store secret references and metadata, never plaintext secrets.

### 6.2 Contexts and conversations

```sql
CREATE TABLE contexts (
  id UUID PRIMARY KEY,
  owner_id UUID NOT NULL REFERENCES owners(id),
  scope TEXT NOT NULL CHECK (scope IN ('personal','business','project')),
  name TEXT NOT NULL,
  description TEXT,
  parent_context_id UUID REFERENCES contexts(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  archived_at TIMESTAMPTZ
);
CREATE INDEX contexts_owner_scope_idx ON contexts(owner_id,scope);

CREATE TABLE conversations (
  id UUID PRIMARY KEY,
  owner_id UUID NOT NULL REFERENCES owners(id),
  context_id UUID REFERENCES contexts(id),
  title TEXT,
  status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active','archived','deleted')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX conversations_owner_updated_idx
  ON conversations(owner_id,updated_at DESC);

CREATE TABLE messages (
  id UUID PRIMARY KEY,
  conversation_id UUID NOT NULL REFERENCES conversations(id),
  owner_id UUID NOT NULL REFERENCES owners(id),
  device_id UUID REFERENCES devices(id),
  channel TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('user','assistant','tool','system')),
  content TEXT,
  content_type TEXT NOT NULL DEFAULT 'text',
  attachment_refs JSONB NOT NULL DEFAULT '[]',
  metadata JSONB NOT NULL DEFAULT '{}',
  client_message_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(device_id,client_message_id)
);
CREATE INDEX messages_conversation_created_idx
  ON messages(conversation_id,created_at);
```

Message metadata must not be used as an unvalidated authority source. Inbound messages from email, web pages and connected channels are untrusted content.

### 6.3 Memory and provenance

```sql
CREATE TABLE memories (
  id UUID PRIMARY KEY,
  owner_id UUID NOT NULL REFERENCES owners(id),
  context_id UUID REFERENCES contexts(id),
  memory_type TEXT NOT NULL CHECK (memory_type IN
    ('episodic','semantic','preference','procedural','goal','project')),
  key TEXT,
  value JSONB NOT NULL,
  confidence NUMERIC(4,3) NOT NULL DEFAULT 1.0
    CHECK (confidence >= 0 AND confidence <= 1),
  salience NUMERIC(4,3) NOT NULL DEFAULT 0.5
    CHECK (salience >= 0 AND salience <= 1),
  sensitivity TEXT NOT NULL DEFAULT 'normal'
    CHECK (sensitivity IN ('normal','sensitive','restricted')),
  source_type TEXT NOT NULL,
  source_ref TEXT,
  valid_from TIMESTAMPTZ,
  valid_until TIMESTAMPTZ,
  supersedes_id UUID REFERENCES memories(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);
CREATE INDEX memories_owner_type_idx ON memories(owner_id,memory_type);
CREATE INDEX memories_context_idx ON memories(context_id);
CREATE INDEX memories_value_gin_idx ON memories USING GIN(value);

CREATE TABLE memory_sources (
  id UUID PRIMARY KEY,
  memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
  source_kind TEXT NOT NULL,
  source_uri TEXT,
  excerpt TEXT,
  observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  confidence NUMERIC(4,3)
);
```

Use a vector extension only after retrieval evaluation demonstrates the need. Start with indexed metadata and lexical/full-text retrieval. Every retrieval path must respect context scope and sensitivity.

### 6.4 Goals, tasks and plans

```sql
CREATE TABLE goals (
  id UUID PRIMARY KEY,
  owner_id UUID NOT NULL REFERENCES owners(id),
  context_id UUID REFERENCES contexts(id),
  title TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  priority SMALLINT NOT NULL DEFAULT 3,
  target_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE tasks (
  id UUID PRIMARY KEY,
  owner_id UUID NOT NULL REFERENCES owners(id),
  context_id UUID REFERENCES contexts(id),
  goal_id UUID REFERENCES goals(id),
  title TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL DEFAULT 'open',
  priority SMALLINT NOT NULL DEFAULT 3,
  due_at TIMESTAMPTZ,
  source_message_id UUID REFERENCES messages(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ
);
CREATE INDEX tasks_owner_status_due_idx ON tasks(owner_id,status,due_at);

CREATE TABLE plans (
  id UUID PRIMARY KEY,
  owner_id UUID NOT NULL REFERENCES owners(id),
  context_id UUID REFERENCES contexts(id),
  goal_id UUID REFERENCES goals(id),
  title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'proposed',
  plan_version INTEGER NOT NULL DEFAULT 1,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE plan_steps (
  id UUID PRIMARY KEY,
  plan_id UUID NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
  sequence INTEGER NOT NULL,
  capability_id TEXT,
  title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'proposed',
  input JSONB NOT NULL DEFAULT '{}',
  output JSONB,
  execution_id UUID,
  verification JSONB,
  UNIQUE(plan_id,sequence)
);
```

### 6.5 Integrations, tools and approvals

```sql
CREATE TABLE integrations (
  id UUID PRIMARY KEY,
  owner_id UUID NOT NULL REFERENCES owners(id),
  provider_key TEXT NOT NULL,
  account_label TEXT,
  status TEXT NOT NULL DEFAULT 'disconnected',
  granted_scopes TEXT[] NOT NULL DEFAULT '{}',
  secret_ref TEXT,
  last_verified_at TIMESTAMPTZ,
  last_error_code TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(owner_id,provider_key,account_label)
);

CREATE TABLE tool_definitions (
  id TEXT PRIMARY KEY,
  connector_key TEXT NOT NULL,
  version INTEGER NOT NULL,
  input_schema JSONB NOT NULL,
  risk_class TEXT NOT NULL,
  requires_approval BOOLEAN NOT NULL DEFAULT false,
  enabled BOOLEAN NOT NULL DEFAULT false,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE approvals (
  id UUID PRIMARY KEY,
  owner_id UUID NOT NULL REFERENCES owners(id),
  device_id UUID REFERENCES devices(id),
  session_id UUID REFERENCES sessions(id),
  tool_id TEXT NOT NULL REFERENCES tool_definitions(id),
  tool_version INTEGER NOT NULL,
  connector_key TEXT NOT NULL,
  arguments_digest TEXT NOT NULL,
  risk_class TEXT NOT NULL,
  explanation TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending','approved','rejected','expired','consumed','revoked')),
  nonce_hash TEXT NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL,
  decided_at TIMESTAMPTZ,
  consumed_at TIMESTAMPTZ
);
CREATE INDEX approvals_owner_status_expiry_idx
  ON approvals(owner_id,status,expires_at);
```

An approval cannot be reused for different arguments, a different tool version, a different connector or a different execution. Approval consumption must be atomic.

### 6.6 Executions and audit

```sql
CREATE TABLE executions (
  id UUID PRIMARY KEY,
  owner_id UUID NOT NULL REFERENCES owners(id),
  context_id UUID REFERENCES contexts(id),
  plan_step_id UUID REFERENCES plan_steps(id),
  tool_id TEXT NOT NULL REFERENCES tool_definitions(id),
  connector_key TEXT NOT NULL,
  approval_id UUID REFERENCES approvals(id),
  arguments_digest TEXT NOT NULL,
  idempotency_key TEXT,
  status TEXT NOT NULL,
  result JSONB,
  error_code TEXT,
  verified BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  UNIQUE(connector_key,tool_id,idempotency_key)
);

CREATE TABLE execution_attempts (
  id UUID PRIMARY KEY,
  execution_id UUID NOT NULL REFERENCES executions(id) ON DELETE CASCADE,
  attempt_number INTEGER NOT NULL,
  status TEXT NOT NULL,
  provider_request_id TEXT,
  error_code TEXT,
  started_at TIMESTAMPTZ NOT NULL,
  finished_at TIMESTAMPTZ,
  UNIQUE(execution_id,attempt_number)
);

CREATE TABLE audit_events (
  id UUID PRIMARY KEY,
  owner_id UUID NOT NULL REFERENCES owners(id),
  actor_device_id UUID REFERENCES devices(id),
  session_id UUID REFERENCES sessions(id),
  event_type TEXT NOT NULL,
  resource_type TEXT NOT NULL,
  resource_id TEXT NOT NULL,
  arguments_digest TEXT,
  outcome TEXT NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX audit_owner_created_idx ON audit_events(owner_id,created_at DESC);
```

Do not persist raw secrets or unnecessary personal content in audit metadata. Retention and export policies must be configurable.

### 6.7 Monitoring and notifications

```sql
CREATE TABLE monitors (
  id UUID PRIMARY KEY,
  owner_id UUID NOT NULL REFERENCES owners(id),
  context_id UUID REFERENCES contexts(id),
  name TEXT NOT NULL,
  source_type TEXT NOT NULL,
  source_config JSONB NOT NULL,
  rule_config JSONB NOT NULL,
  schedule TEXT,
  severity TEXT NOT NULL DEFAULT 'normal',
  enabled BOOLEAN NOT NULL DEFAULT true,
  last_checked_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE monitor_events (
  id UUID PRIMARY KEY,
  monitor_id UUID NOT NULL REFERENCES monitors(id),
  dedupe_key TEXT NOT NULL,
  severity TEXT NOT NULL,
  event_type TEXT NOT NULL,
  summary TEXT NOT NULL,
  evidence JSONB NOT NULL DEFAULT '{}',
  observed_at TIMESTAMPTZ NOT NULL,
  acknowledged_at TIMESTAMPTZ,
  UNIQUE(monitor_id,dedupe_key)
);

CREATE TABLE notifications (
  id UUID PRIMARY KEY,
  owner_id UUID NOT NULL REFERENCES owners(id),
  source_event_id UUID,
  channel TEXT NOT NULL,
  severity TEXT NOT NULL,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued',
  scheduled_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  delivered_at TIMESTAMPTZ,
  acknowledged_at TIMESTAMPTZ,
  attempt_count INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX notifications_owner_schedule_idx
  ON notifications(owner_id,status,scheduled_at);
```

### 6.8 Automations and synchronization

```sql
CREATE TABLE automations (
  id UUID PRIMARY KEY,
  owner_id UUID NOT NULL REFERENCES owners(id),
  context_id UUID REFERENCES contexts(id),
  name TEXT NOT NULL,
  trigger_type TEXT NOT NULL,
  trigger_config JSONB NOT NULL,
  workflow_definition JSONB NOT NULL,
  version INTEGER NOT NULL DEFAULT 1,
  enabled BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE automation_runs (
  id UUID PRIMARY KEY,
  automation_id UUID NOT NULL REFERENCES automations(id),
  status TEXT NOT NULL,
  current_step INTEGER,
  trigger_event_id UUID,
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  error_code TEXT
);

CREATE TABLE sync_cursors (
  device_id UUID NOT NULL REFERENCES devices(id),
  stream_name TEXT NOT NULL,
  last_sequence BIGINT NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY(device_id,stream_name)
);

CREATE TABLE event_outbox (
  id UUID PRIMARY KEY,
  owner_id UUID NOT NULL REFERENCES owners(id),
  aggregate_type TEXT NOT NULL,
  aggregate_id UUID NOT NULL,
  event_type TEXT NOT NULL,
  sequence BIGINT NOT NULL,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  published_at TIMESTAMPTZ,
  UNIQUE(aggregate_type,aggregate_id,sequence)
);

CREATE TABLE webhook_inbox (
  provider TEXT NOT NULL,
  provider_event_id TEXT NOT NULL,
  received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  processed_at TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'received',
  payload_digest TEXT NOT NULL,
  PRIMARY KEY(provider,provider_event_id)
);
```

## 7. API surface

Version external API under /v1.

- POST /v1/auth/session
- POST /v1/devices/enroll
- GET /v1/devices
- DELETE /v1/devices/{device_id}
- GET/POST /v1/conversations
- GET/POST /v1/conversations/{id}/messages
- GET/POST /v1/memories
- PATCH/DELETE /v1/memories/{id}
- GET/POST /v1/goals
- GET/POST /v1/tasks
- GET/POST /v1/plans
- GET /v1/capabilities
- GET /v1/integrations
- POST /v1/integrations/{id}/verify
- POST /v1/tools/{tool_id}/prepare
- POST /v1/approvals
- POST /v1/approvals/{id}/decision
- POST /v1/executions
- GET /v1/executions/{id}
- POST /v1/monitors
- GET /v1/monitor-events
- POST /v1/automations
- POST /v1/sync/pull
- POST /v1/sync/push
- Provider webhooks under isolated signed routes.

Every endpoint must declare authentication, scope, permission and rate-limit requirements.

## 8. Event model

Use a durable event envelope:
- event_id
- event_type
- owner_id
- context_id
- aggregate_type
- aggregate_id
- sequence
- occurred_at
- source_device_id
- correlation_id
- causation_id
- schema_version
- payload

Events are append-only. State projections can be rebuilt. Use an outbox transaction for database changes that must publish events. Consumers must be idempotent.

## 9. Approval lifecycle

1. Orchestrator prepares a tool call.
2. Policy engine classifies risk and evaluates current permissions.
3. If approval is required, create a pending approval record with canonical argument digest and expiry.
4. Client displays the exact action, destination, affected data and reversibility.
5. Owner approves or rejects through an authenticated session, with re-authentication for critical actions.
6. Executor atomically consumes approval and validates digest, tool version, session, expiry and device status.
7. Execution and attempts are persisted.
8. Verification evidence is recorded.
9. User receives outcome; unverified is not described as complete.

Routine low-risk reads may run without interactive approval. Routine writes may run autonomously only under explicit owner-configured policies with narrow scope and revocation.

## 10. Delivery phases

1. Stabilize and safely integrate PR #1.
2. Harden API security and create identity/device/session foundation.
3. Implement PostgreSQL persistence, event outbox and sync.
4. Implement action-bound approval and durable execution/audit.
5. Implement model provider routing and voice.
6. Implement iOS/Android clients and notification delivery.
7. Implement monitoring and automation workers.
8. Implement desktop nodes and computer control.
9. Implement watchOS and macOS clients.
10. Expand optional channels and advanced intelligence.

## 11. Architecture acceptance criteria

- No privileged secret is shipped in a web/mobile client.
- All private APIs require authenticated, scoped sessions.
- Revoked devices cannot act or sync.
- Approval cannot be replayed or reused with changed arguments.
- Execution and idempotency survive process restart.
- Cross-device conversation and memory state converge.
- Context scope is enforced in retrieval and APIs.
- Provider health distinguishes configured from live verified.
- Monitor events deduplicate and notify according to severity/quiet hours.
- Voice works end-to-end with explicit microphone permissions.
- Every consequential action has an auditable, verifiable outcome.
