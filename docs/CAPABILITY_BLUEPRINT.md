# R.U.N.E Capability Blueprint

Status: master capability specification, version 1.0  
Scope: R.U.N.E core capabilities and external integrations, before intelligence-provider, channel, and device-companion implementation.

## Product boundary

R.U.N.E is a persistent personal intelligence and action system. It must be able to understand a request, discover whether a capability exists, check feasibility and permissions, execute through an approved adapter, observe the result, verify the outcome, and remember the result. A listed capability is a target, not a claim that it is already implemented.

The capability layer is independent of model providers and communication channels. WhatsApp, Discord, and a future Android companion are clients of the same core, not separate assistants.

## Capability lifecycle and status vocabulary

- **foundation**: generic runtime support exists or is being implemented in core.
- **planned**: target capability, not yet implemented.
- **provider-dependent**: requires a supported external service/API and credentials.
- **device-dependent**: requires a later device node/companion and user-granted OS permissions.
- **restricted**: limited by platform policy, licensing, safety, or unavailable public APIs.
- **manual-fallback**: R.U.N.E can prepare instructions/content but cannot honestly claim to perform the final action.

Every execution must return one of: succeeded-and-verified, attempted-unverified, awaiting-approval, blocked, failed, or unavailable. Never report an attempted action as successful.

## Capability catalogue

### 1. Conversation, communication and correspondence
- Draft, revise, summarise, translate and classify email.
- Search/read email, inspect threads and attachments, label/archive messages.
- Send email, reply, forward, schedule email, manage drafts.
- Draft messages for supported messaging platforms; send only through an authorised integration.
- Summarise conversations and extract tasks, decisions, dates and commitments.
- Manage contacts and contact groups where supported.
- Prepare meeting agendas, follow-ups and status updates.
- Detect suspicious or untrusted instructions in inbound content; treat content as data, never as authority.
Integrations: Gmail API, Microsoft Graph, SMTP only where appropriate, provider-specific messaging APIs. MCP candidates: Gmail, Microsoft 365, Slack, Discord, Telegram where supported. Sending and external publication require explicit authority; high-impact recipients/actions may require confirmation.

### 2. Calendar, time and personal organisation
- Read calendars, list events, find free/busy windows.
- Create, update, move, cancel and invite attendees to events.
- Create reminders, recurring reminders, tasks and checklists.
- Summarise daily/weekly schedules and detect conflicts.
- Convert time zones and plan schedules.
Integrations: Google Calendar, Microsoft Graph Calendar, CalDAV where practical. MCP candidates: Google Calendar, Microsoft 365, Notion. Invitations, cancellations and changes affecting others require confirmation.

### 3. Tasks, projects and knowledge work
- Create, assign, update, prioritise and close tasks.
- Track goals, milestones, dependencies, blockers and progress.
- Generate project plans, briefs, reports, meeting notes and decision logs.
- Search and update project workspaces.
- Relate information across projects and organisations while preserving source/provenance.
Integrations/MCP: Notion, Linear, Jira, Asana, Trello, ClickUp, GitHub Projects. Prefer a small set of user-selected systems rather than connecting every task app at once.

### 4. Web research and browser operations
- Search the web, open and extract pages, compare sources, summarise findings.
- Research products, services, people, organisations and technical topics.
- Fill forms, navigate websites, download and upload files.
- Monitor user-specified pages or conditions and report changes.
- Operate browser sessions through approved automation.
Integrations: search APIs and Playright/browser automation; MCP candidates: browser/Playwright, search provider, fetch/read-page tools. Treat web pages as untrusted input. Purchases, submissions, account changes and publication require confirmation. CAPTCHA, MFA and access controls must not be bypassed.

### 5. Files, documents and data
- Create, read, edit, search, classify, organise and convert common files.
- Generate PDF, DOCX, XLSX, PPTX, CSV, TXT and Markdown.
- Extract tables and structured data from supported documents.
- Analyse spreadsheets, produce charts and reports.
- Manage files in approved cloud storage and user-authorised local folders.
Integrations/MCP: filesystem (strictly scoped), Google Drive, OneDrive/SharePoint, Dropbox. Local filesystem access must be sandboxed and path-scoped. Deletion and overwrites require confirmation and recoverability checks.

### 6. Software engineering and developer operations
- Read repositories, explain code, plan changes, implement code and tests.
- Create branches, commits, pull requests and issues.
- Review diffs, run tests, inspect CI and diagnose failures.
- Manage deployments and release workflows through approved providers.
- Maintain project documentation and technical decisions.
Integrations/MCP: GitHub, GitLab, Bitbucket, Linear/Jira, Sentry, Vercel, Railway, cloud provider tools. Production deploys, merges, secret changes and destructive operations require explicit approval. Code execution must be isolated.

### 7. Research, learning and personal knowledge
- Maintain personal facts, preferences, goals, decisions and commitments.
- Maintain project, organisation and domain knowledge bases.
- Ingest user-provided documents and approved external sources.
- Track provenance, timestamps, confidence, sensitivity and supersession.
- Search across knowledge and cite supporting sources.
Foundations: R.U.N.E-owned memory and retrieval. MCP candidates: Notion, Google Drive, OneDrive, Obsidian/local filesystem, Zotero. Memory controls must support inspect, correct, export and delete.

### 8. Entertainment and media
- Search music, artists, albums and playlists.
- Open supported media apps and deep links.
- Control playback where an official API and account tier permit it.
- Manage playlists and saved items where permitted.
- Find films/shows and open supported streaming destinations.
Integrations: Spotify Web API/SDK where policy permits; Apple Music and YouTube Music only through supported interfaces. Netflix and similar streaming platforms have restricted public control surfaces; do not promise unrestricted playback/account control. Phone-level media control is device-dependent and belongs to the later companion phase.

### 9. Creative production
- Draft and edit text, scripts, presentations and structured content.
- Generate and edit images through authorised image services.
- Transcribe and summarise audio; generate speech where configured.
- Create diagrams, charts and multimedia deliverables.
Integrations: image-generation APIs, transcription/TTS providers, document-generation libraries. Paid provider credentials can be added later; development must support mocks.

### 10. Finance, shopping and transactions
- Read connected financial data only through explicitly authorised, supported providers.
- Categorise transactions and prepare budgets/reports.
- Compare products and prepare shopping lists.
- Prepare purchase flows and invoices.
- Initiate payments or purchases only with strong user confirmation and provider-supported controls.
No credential scraping, card storage, financial transfers or purchases without explicit authority. Payment execution is a later, separately reviewed capability.

### 11. Business and operations
- Coordinate projects, tasks, people and operational workflows.
- Prepare reports, proposals, briefs and internal communications.
- Maintain customer and supplier records through authorised CRM integrations.
- Summarise operational metrics and identify exceptions.
- Trigger approved workflows and notifications.
Integrations/MCP: HubSpot, Salesforce, Notion, Linear/Jira, Slack, Microsoft 365, Google Workspace. Treat business data as confidential and enforce workspace-level access.

### 12. Automation and monitoring
- Run scheduled jobs and recurring workflows.
- Trigger actions from approved events/webhooks.
- Monitor specific user-defined conditions, deadlines and statuses.
- Retry transient failures with bounded backoff and idempotency.
- Keep execution history, audit logs and cancellation controls.
Foundations: scheduler, durable job queue, event store, policy engine. Automation must be opt-in, bounded, observable and easy to pause.

### 13. Device and smart-home capabilities (later device phase)
- Set alarms/timers, open apps, share files and display notifications.
- Control media sessions and supported device settings.
- Interact with smart-home devices and routines.
- Use approved accessibility or automation interfaces only where platform policy permits.
Integrations: future Android companion, Android intents/notification/media APIs, Home Assistant. Not part of the current implementation phase.

## MCP and integration plan

MCP is a protocol for exposing tools/resources to R.U.N.E; it is not itself a capability, AI model, memory store or mandatory integration method. Build a provider-neutral connector layer with MCP support. Prefer official direct APIs when they offer better authentication, reliability, scopes, webhooks or policy compliance. Do not create MCP servers for services that do not offer a supported API merely to force an MCP integration.

### Priority A: core productivity and development
1. **GitHub MCP**: repositories, issues, pull requests, code search and workflows. Use official GitHub APIs where direct integration is stronger.
2. **Google Workspace MCP**: Gmail, Calendar and Drive, subject to OAuth scopes.
3. **Microsoft 365 MCP**: Outlook, Calendar, OneDrive and SharePoint via Microsoft Graph.
4. **Notion MCP**: pages, databases and workspace search.
5. **Filesystem MCP**: only a restricted, sandboxed workspace, never unrestricted host access.
6. **Browser/search MCP**: web search and controlled browser navigation; browser execution remains isolated.

### Priority B: project and collaboration
7. **Linear MCP** or Jira integration: issues, projects, cycles and roadmaps.
8. **Slack MCP**: search and authorised messaging.
9. **Discord integration/MCP**: later channel phase; Discord is a communication surface as well as a possible tool integration.
10. **Trello/Asana/ClickUp**: select based on the user's actual workspace; do not install all by default.
11. **HubSpot MCP**: CRM contacts, companies, deals and tickets if adopted.

### Priority C: media and specialist services
12. **Spotify integration**: official Spotify APIs and OAuth; check current developer policy and account/device requirements before enabling playback control.
13. **YouTube integration**: supported search and account actions; playback control may be device-dependent.
14. **Home Assistant MCP**: later smart-home/device automation.
15. **Sentry MCP**: error monitoring and issue triage.
16. **Vercel/Railway/cloud integrations**: deployment and operational management with explicit production approvals.
17. **Zotero MCP**: research libraries and citations where useful.

### Integration decision rule
For each service, record: official API availability, MCP server maturity/maintenance, OAuth scopes, data sensitivity, rate limits, cost, webhook support, user value, and fallback. Use an MCP server only when it is maintained, auditable, scoped and materially improves interoperability. R.U.N.E must be able to use a direct adapter instead.

## Selected first-wave integrations

The initial provider selection is fixed as follows:

1. **Google Workspace**: Gmail, Calendar, Drive and Contacts. Prefer Google OAuth and official APIs for reliable scope control; use a vetted MCP server only where it adds clear value.
2. **Notion**: pages, databases and project/task tracking. Start with the official Notion API; retain MCP compatibility behind the same adapter boundary.
3. **Brave Search + Tavily**: both are independent research-provider targets. RUNE can query either or both, compare overlap, and retain source URLs/provenance. API keys remain environment references, never stored in the connector registry.
4. **GitHub, scoped filesystem and browser automation**: core development/runtime support alongside the selected services.

All first-wave connectors are registered in a disconnected state. Registration is not account authorisation, and no network call is made until an adapter is configured and health-checked.

## Connector implementation boundary

`rune.core.connectors` defines connector lifecycle state, tool definitions, adapter and approval-policy protocols, schema-validated invocation, bounded retries/timeouts, idempotency keys, audit digests and explicit result states. The runtime exposes connector status through `GET /api/connectors`. The current registry contains no live adapters or credentials; tests use deterministic mocks.

## Core implementation requirements before model intelligence

1. Capability catalogue with stable IDs, categories, descriptions, status, prerequisites, transports, risk and confirmation policy.
2. Connector registry with connection state, health, authentication metadata (never secrets), granted scopes and service identity.
3. MCP client boundary: discover servers/tools/resources, validate schemas, invoke tools, handle timeouts and protocol errors.
4. Direct API adapter boundary for services that should not use MCP.
5. Unified execution envelope: request ID, actor, capability ID, arguments, policy decision, approval state, attempt, result, evidence and audit record.
6. Permission policy: read, write, external communication, financial, destructive and privileged-device action classes.
7. JSON Schema input validation and bounded outputs.
8. Idempotency, timeout, retry and cancellation semantics.
9. Audit trail and verified outcome semantics.
10. Mock connectors and deterministic tests so the framework can be built without paid credentials.
11. No API keys committed to source. Use environment variables or later secret manager integration.
12. No live external actions until a real connector is configured and tested.

## Current implementation boundary

This phase builds the catalogue, registry contracts, validation and execution governance. It does not yet implement model-provider routing, memory redesign, WhatsApp, Discord, Android companion, or paid service integrations. Those follow the agreed roadmap.
