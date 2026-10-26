# R.U.N.E Connector Implementation Status

Last reviewed: 2026-10-27  
Branch: feat/capability-blueprint  
Pull request: #1 (draft, unmerged)

## Executive count

- 37 integration manifests.
- 67 named tool contracts.
- 67 strict, closed input schemas.
- 64 tool contracts have a concrete adapter attached.
- 3 tool contracts are explicitly deferred/restricted: Snapchat public search (1) and Android Companion (2).
- OpenAI and Google AI service manifests have no catalogue tools yet; they belong to the later Intelligence/provider layer.
- MCP is available as a separate transport bridge and may be configured for compatible integrations.

An attached adapter means a real provider-specific implementation exists in code. It does not mean the provider is authenticated, approved, or production-verified.

## Provider coverage matrix

| Integration | Tool operations | Adapter state | Notes |
|---|---:|---|---|
| Google Workspace | 10 | Implemented | Gmail read/search/draft/send; Calendar search/create/update; Drive search/upload; Contacts search |
| Notion | 4 | Implemented | Search, database query, page create/update |
| Brave Search | 1 | Implemented | Web search |
| Tavily | 2 | Implemented | Search and extract |
| GitHub | 3 | Implemented | Repository search, issue create, PR create |
| GitLab | 3 | Implemented | Project search, issue create, merge-request create |
| Figma | 3 | Implemented | File read, comments list/create |
| Linear | 2 | Implemented | Issue search/create |
| Slack | 2 | Implemented | Search uses user token; message send uses bot token |
| Discord | 1 | Implemented | Official bot API only |
| WhatsApp Business | 1 | Implemented with consent gate | Official Cloud API; persistent opt-in and 24-hour customer-service window checks are enforced locally; verified webhook ingestion remains a release gate |
| Instagram | 2 | Implemented | Eligible professional-account publishing and comments read |
| Facebook | 1 | Implemented | Authorised Page publishing |
| Threads | 1 | Implemented | Official Threads publishing flow |
| TikTok | 1 | Implemented | Content Posting API URL-pull flow; app review/creator eligibility required |
| X | 2 | Implemented | Recent search and post creation |
| LinkedIn | 1 | Implemented | Posts API; product approval and version configuration required |
| Telegram | 1 | Implemented | Official bot messaging |
| Reddit | 2 | Implemented | OAuth search and comment creation |
| Pinterest | 1 | Implemented | Pin creation |
| Spotify | 2 | Implemented | Search and playback; account/device policy applies |
| YouTube | 1 | Implemented | Data API search |
| Zotero | 1 | Implemented | Library item search |
| HubSpot | 2 | Implemented | Contact search and deal update |
| Sentry | 1 | Implemented | Issue search |
| Vercel | 2 | Implemented | Deployment list and deployment creation; privileged action approval applies |
| Railway | 1 | Implemented | Deployment log query through GraphQL |
| Microsoft 365 | 1 | Implemented | Outlook message search |
| Dropbox | 1 | Implemented | OAuth refresh and file search |
| Home Assistant | 2 | Implemented | Entity read and service call; privileged service calls require approval |
| Scoped filesystem | 3 | Implemented | Read/write/delete within configured workspace only |
| Playwright browser | 2 | Implemented, disabled by default | Requires host-enforced outbound egress policy before health check succeeds |
| Resend | 1 | Implemented | Transactional email |
| Snapchat | 1 | Restricted/unavailable | No general supported public-search surface established; no scraping or private-session automation |
| Android Companion | 2 | Deferred to device phase | Requires companion app, pairing and OS permissions |
| OpenAI Services | 0 | Deferred to Intelligence | Model/media provider boundary; no catalogue tools in this connector phase |
| Google AI Services | 0 | Deferred to Intelligence | Model/media provider boundary; no catalogue tools in this connector phase |

## Cross-cutting implementation

- Connector lifecycle states and health checks.
- Authenticated API routes for connector health checks and governed tool execution. High-impact calls return awaiting_approval until an authorised client explicitly resubmits with approval.
- Authenticated owner-managed messaging consent opt-in/revocation routes; inbound-window timestamps must be recorded only from a future verified provider webhook.
- Tool schema validation before dispatch.
- Explicit approval gates for external communication, financial, destructive and privileged actions.
- Read-only tools receive bounded retries; side-effecting tools are not automatically retried.
- Idempotency keys are scoped by connector and tool; reusing a key with changed arguments is blocked.
- Audit records store argument digests rather than raw argument payloads.
- Credentials are loaded from environment variables; .env.example contains placeholders only.
- Provider errors are sanitised before being returned to the manager.
- MCP server definitions are administrator-owned configuration in RUNE_MCP_SERVERS_JSON. A model tool call cannot select arbitrary commands or endpoints.
- MCP HTTP endpoints require HTTPS except loopback development endpoints. Stdio subprocesses receive only explicitly allowlisted environment variables.
- Browser actions require RUNE_BROWSER_EGRESS_POLICY=enforced and reject private destinations at navigation/request time.
- WhatsApp Business sends require a persisted opt-in record; free-form text additionally requires an inbound customer message within the 24-hour window. Templates still require provider approval. The durable consent registry exposes record_opt_in, revoke and record_inbound for a verified webhook/consent workflow.
- The existing desktop UI has not been modified.

## Verification

The latest confirmed successful GitHub Actions run before this document was created was run 291, commit eacd18fbb9ee14e46160dc2279a71243f3572c7b: 107 passed, 1 skipped. A newer test batch is being validated separately; do not assume that earlier green run covers subsequent commits.

Offline mock tests cover representative provider routes, OAuth refresh flows, request payloads, auth headers, path validation, filesystem confinement, MCP transport configuration, approval policy and idempotency. Coverage is not yet exhaustive for every provider operation. No real provider credentials or external account calls have been used.

## Remaining connector exit gates

1. Finish provider-by-provider mock coverage for every exposed operation, including pagination, 429/5xx behaviour, auth failures and malformed provider responses.
2. Confirm current API request/response contracts and required OAuth scopes for each provider. Where API access requires review, mark the capability restricted until approval is granted.
3. Add durable consent/webhook state for messaging channels before enabling autonomous inbound-triggered or outbound workflows.
4. Add robust outbound egress isolation for browser execution; keep browser disabled until the host confirms it.
5. Add pagination helpers and consistent provider error classification where APIs paginate.
6. Verify all tests on the latest PR head and keep the PR draft until the coverage report is complete.
7. Keep Snapchat public search unavailable unless a supported official API contract is established. Keep Android Companion in its planned device phase.

Provider credentials are not a blocker for these implementation tasks. They are required later for OAuth consent, account-specific scope checks, app review, and live smoke tests.
