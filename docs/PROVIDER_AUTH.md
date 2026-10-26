# R.U.N.E Provider Authentication Preparation

This document is a deployment checklist, not a request to supply credentials now. Connector implementation and offline testing do not require provider accounts or API keys. Keep real secrets in a secret manager or local ignored environment file; never paste them into chat, commit them, or place them in tool arguments.

The canonical placeholder list is .env.example. The integration catalogue currently declares 65 provider/configuration environment variables, and each declared variable has a placeholder there.

## Productivity and knowledge

| Provider | Environment variables | Setup required later |
|---|---|---|
| Google Workspace | GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN | Create OAuth client, configure consent screen, obtain refresh token with only the Gmail, Calendar, Drive and People scopes actually used. Re-consent if a later write scope is added. |
| Microsoft 365 | MICROSOFT_CLIENT_ID, MICROSOFT_CLIENT_SECRET, MICROSOFT_REFRESH_TOKEN | Register Entra application, configure delegated Graph permissions for Outlook mail search, complete consent and refresh-token flow. |
| Notion | NOTION_API_TOKEN | Create an internal integration and explicitly share the required pages/databases with it. |
| Dropbox | DROPBOX_APP_KEY, DROPBOX_APP_SECRET, DROPBOX_REFRESH_TOKEN | Create app, choose least-privilege file scopes, complete OAuth and obtain refresh token. |
| Linear | LINEAR_API_KEY | Create a workspace API key with the minimum issue read/write access. |

## Research, design and developer platforms

| Provider | Environment variables | Setup required later |
|---|---|---|
| Brave Search | BRAVE_SEARCH_API_KEY | Create an API subscription/key. |
| Tavily | TAVILY_API_KEY | Create an API key and select an appropriate plan. |
| GitHub | GITHUB_TOKEN | Create a fine-grained token restricted to selected repositories and only required metadata, issues and pull-request permissions. |
| GitLab | GITLAB_TOKEN, optional GITLAB_API_URL | Create a token with only project read and issue/merge-request write scopes. |
| Figma | FIGMA_ACCESS_TOKEN | Create a token for the required team/files and verify file/comment permissions. |
| Zotero | ZOTERO_API_KEY, ZOTERO_USER_ID | Create an API key and select the required library permissions. |
| Sentry | SENTRY_AUTH_TOKEN | Create an auth token with issue read access for selected organisations/projects. |
| Vercel | VERCEL_TOKEN | Create a token scoped to the intended team/projects. Production deploys remain privileged and approval-gated. |
| Railway | RAILWAY_API_TOKEN | Create a project/workspace token with only the required deployment/log access. |

## Messaging and social platforms

| Provider | Environment variables | Setup required later |
|---|---|---|
| Resend | RESEND_API_KEY | Verify a sending domain and configure SPF/DKIM/DMARC before production delivery. |
| Slack | SLACK_BOT_TOKEN, SLACK_USER_TOKEN, SLACK_SIGNING_SECRET | Install a bot with required channel permissions. Search uses a user token; messaging uses a bot token. Configure signing secret when webhooks are enabled. |
| Discord | DISCORD_BOT_TOKEN | Create/install a bot and grant only the required server/channel permissions. |
| Telegram | TELEGRAM_BOT_TOKEN | Create a bot and explicitly add it to intended chats. |
| WhatsApp Business | WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_VERIFY_TOKEN, WHATSAPP_APP_SECRET, WHATSAPP_API_VERSION | Configure Meta Business/WhatsApp Cloud API, business verification, phone number, webhook verification, approved templates and required permissions. The local consent registry requires recorded opt-in; free-form text additionally requires an inbound message within 24 hours. |
| Meta Graph (Instagram/Facebook/Threads) | META_APP_ID, META_APP_SECRET, META_ACCESS_TOKEN, META_GRAPH_VERSION | Configure the relevant products, eligible professional/Page accounts, scopes, app review and long-lived token strategy. Personal-account DM automation is not assumed. |
| TikTok | TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, TIKTOK_ACCESS_TOKEN | Apply for Content Posting API access, pass app review, obtain creator-authorised scopes and satisfy URL-pull/domain requirements. |
| X | X_CLIENT_ID, X_CLIENT_SECRET, X_ACCESS_TOKEN | Configure OAuth user context and an API tier that supports the requested search/write operations. |
| LinkedIn | LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET, LINKEDIN_ACCESS_TOKEN, LINKEDIN_API_VERSION | Apply for the relevant LinkedIn product/Community Management permissions and obtain an authorised member or organisation token. |
| Reddit | REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_REFRESH_TOKEN | Register an application, obtain user consent for read/comment scopes and set an appropriate User-Agent. |
| Pinterest | PINTEREST_APP_ID, PINTEREST_APP_SECRET, PINTEREST_ACCESS_TOKEN | Register an app, obtain approved scopes and a user-authorised access token. |

## Media and AI services

| Provider | Environment variables | Setup required later |
|---|---|---|
| Spotify | SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REFRESH_TOKEN | Register an app, complete OAuth and verify account/device eligibility for playback control. |
| YouTube | YOUTUBE_API_KEY, YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET | Enable YouTube Data API v3 and configure quota. OAuth client values are reserved for future account actions; current search uses the API key. |
| OpenAI | OPENAI_API_KEY | Reserved for the later Intelligence/model-provider and media layer. |
| Google AI | GOOGLE_AI_API_KEY | Reserved for the later Intelligence/model-provider and media layer. |

## Local capabilities and MCP

- RUNE_WORKSPACE_DIR: absolute path to the restricted workspace root.
- RUNE_CONSENT_DB: optional path for the local SQLite messaging-consent ledger. SQLite database/WAL files are ignored by Git.
- RUNE_BROWSER_EGRESS_POLICY: must be set to enforced only after the host has configured network-level egress filtering. Browser tools remain unavailable otherwise.
- RUNE_MCP_SERVERS_JSON: administrator-owned JSON configuration for MCP servers. Do not place provider secrets directly in this JSON; list only environment-variable names in env_names. Remote endpoints must use HTTPS; plain HTTP is limited to loopback. Stdio subprocesses receive only explicitly allowlisted environment variables.
- Android Companion: no credentials yet. Pairing, app signing and OS permissions belong to the later device phase.

## Release-time verification

When credentials are eventually configured, perform a read-only health check first, inspect granted scopes, then run one harmless read operation. Verify writes only in a test workspace/account. Do not enable production sends, deployments, smart-home controls or destructive operations until the corresponding approval and consent controls have been reviewed. Provider app approval, OAuth consent, quotas and account eligibility are external prerequisites and cannot be replaced by adding a key.
