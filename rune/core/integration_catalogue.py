from __future__ import annotations

"""Complete integration and tool inventory for RUNE.

This is executable configuration, not a claim that every vendor API is available.
Each integration records its preferred transport, auth environment references,
capabilities, policy limits and activation state. Credentials are never stored.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class IntegrationState(str, Enum):
    READY_FOR_CONFIGURATION = "ready_for_configuration"
    PROVIDER_REVIEW_REQUIRED = "provider_review_required"
    DEVICE_PHASE = "device_phase"
    MANUAL_FALLBACK = "manual_fallback"


@dataclass(frozen=True)
class IntegrationManifest:
    id: str
    name: str
    category: str
    transport: str
    auth_env: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    state: IntegrationState = IntegrationState.READY_FOR_CONFIGURATION
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ToolManifest:
    id: str
    integration_id: str
    name: str
    description: str
    risk: str = "read"
    confirmation: bool = False
    availability: str = "provider_dependent"


# Provider IDs are stable configuration keys. Multiple providers may satisfy
# one capability, and the runtime must not assume that a browser login grants
# API access or permission to automate a platform.
INTEGRATIONS: tuple[IntegrationManifest, ...] = (
    IntegrationManifest("google_workspace", "Google Workspace", "productivity", "direct_api",
        ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN"),
        ("gmail", "calendar", "drive", "contacts", "tasks")),
    IntegrationManifest("notion", "Notion", "productivity", "direct_api_or_mcp",
        ("NOTION_API_TOKEN",), ("pages", "databases", "tasks", "projects")),
    IntegrationManifest("brave_search", "Brave Search", "research", "direct_api",
        ("BRAVE_SEARCH_API_KEY",), ("web_search",)),
    IntegrationManifest("tavily", "Tavily", "research", "direct_api",
        ("TAVILY_API_KEY",), ("web_search", "research_extract")),
    IntegrationManifest("github", "GitHub", "developer", "direct_api_or_mcp",
        ("GITHUB_TOKEN",), ("repositories", "issues", "pull_requests", "actions")),
    IntegrationManifest("gitlab", "GitLab", "developer", "direct_api",
        ("GITLAB_TOKEN",), ("repositories", "issues", "merge_requests", "pipelines")),
    IntegrationManifest("figma", "Figma", "design", "direct_api_or_mcp",
        ("FIGMA_ACCESS_TOKEN",), ("files", "projects", "comments", "components"),
        notes=("Design file access is governed by the connected account's permissions.",)),
    IntegrationManifest("linear", "Linear", "productivity", "direct_api_or_mcp",
        ("LINEAR_API_KEY",), ("issues", "projects", "cycles")),
    IntegrationManifest("slack", "Slack", "communication", "direct_api_or_mcp",
        ("SLACK_BOT_TOKEN", "SLACK_USER_TOKEN", "SLACK_SIGNING_SECRET"), ("search", "messages", "channels")),
    IntegrationManifest("discord", "Discord", "communication", "official_bot_api",
        ("DISCORD_BOT_TOKEN",), ("guilds", "channels", "messages"),
        notes=("Bot permissions and server installation are required; not arbitrary personal-account automation.",)),
    IntegrationManifest("whatsapp", "WhatsApp", "communication", "official_business_api",
        ("WHATSAPP_ACCESS_TOKEN", "WHATSAPP_PHONE_NUMBER_ID", "WHATSAPP_VERIFY_TOKEN", "WHATSAPP_APP_SECRET", "WHATSAPP_API_VERSION"),
        ("business_messaging", "templates", "webhooks"), IntegrationState.PROVIDER_REVIEW_REQUIRED,
        ("WhatsApp Business Platform, opt-in, templates and messaging windows apply. Personal-account web automation is not assumed.",)),
    IntegrationManifest("instagram", "Instagram", "social", "official_graph_api",
        ("META_APP_ID", "META_APP_SECRET", "META_ACCESS_TOKEN", "META_GRAPH_VERSION"),
        ("professional_account_publish", "comments", "insights"), IntegrationState.PROVIDER_REVIEW_REQUIRED,
        ("Official API features depend on account type, permissions and review. Personal DM automation is not assumed.",)),
    IntegrationManifest("facebook", "Facebook", "social", "official_graph_api",
        ("META_APP_ID", "META_APP_SECRET", "META_ACCESS_TOKEN"),
        ("pages", "publishing", "comments", "insights"), IntegrationState.PROVIDER_REVIEW_REQUIRED,
        ("Page and app permissions apply; not unrestricted personal-profile automation.",)),
    IntegrationManifest("threads", "Threads", "social", "official_api",
        ("META_APP_ID", "META_APP_SECRET", "META_ACCESS_TOKEN"),
        ("publishing", "replies", "insights"), IntegrationState.PROVIDER_REVIEW_REQUIRED),
    IntegrationManifest("snapchat", "Snapchat", "social", "official_api_or_manual",
        ("SNAPCHAT_CLIENT_ID", "SNAPCHAT_CLIENT_SECRET"),
        ("marketing_ads", "public_profile_if_eligible"), IntegrationState.PROVIDER_REVIEW_REQUIRED,
        ("Public APIs are not a general personal-chat API. No scraping, session-cookie reuse or private DM automation.",)),
    IntegrationManifest("tiktok", "TikTok", "social", "official_api",
        ("TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_ACCESS_TOKEN"),
        ("content_publish_if_approved", "public_data_if_eligible"), IntegrationState.PROVIDER_REVIEW_REQUIRED,
        ("Scopes, app review and creator eligibility apply.",)),
    IntegrationManifest("x", "X", "social", "official_api",
        ("X_CLIENT_ID", "X_CLIENT_SECRET", "X_ACCESS_TOKEN"),
        ("posts", "search", "account_actions"), IntegrationState.PROVIDER_REVIEW_REQUIRED,
        ("API tier, rate limits and paid access may apply.",)),
    IntegrationManifest("linkedin", "LinkedIn", "social", "official_api",
        ("LINKEDIN_CLIENT_ID", "LINKEDIN_CLIENT_SECRET", "LINKEDIN_ACCESS_TOKEN", "LINKEDIN_API_VERSION"),
        ("profile", "organisation_posts", "approved_messaging"), IntegrationState.PROVIDER_REVIEW_REQUIRED,
        ("Most permissions require product approval; messaging is not generally open.",)),
    IntegrationManifest("telegram", "Telegram", "communication", "official_bot_api",
        ("TELEGRAM_BOT_TOKEN",), ("messages", "files", "commands")),
    IntegrationManifest("reddit", "Reddit", "social_research", "official_api",
        ("REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_REFRESH_TOKEN"),
        ("search", "posts", "comments"), IntegrationState.PROVIDER_REVIEW_REQUIRED),
    IntegrationManifest("pinterest", "Pinterest", "social", "official_api",
        ("PINTEREST_APP_ID", "PINTEREST_APP_SECRET", "PINTEREST_ACCESS_TOKEN"), ("boards", "pins"),
        IntegrationState.PROVIDER_REVIEW_REQUIRED),
    IntegrationManifest("spotify", "Spotify", "media", "official_api",
        ("SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET", "SPOTIFY_REFRESH_TOKEN"),
        ("search", "library", "playlists", "playback_if_eligible"),
        IntegrationState.PROVIDER_REVIEW_REQUIRED,
        ("Playback control depends on current Spotify developer policy, account and active-device requirements.",)),
    IntegrationManifest("youtube", "YouTube", "media", "official_api",
        ("YOUTUBE_API_KEY", "YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET"), ("search", "channels", "videos", "uploads")),
    IntegrationManifest("zotero", "Zotero", "research", "official_api",
        ("ZOTERO_API_KEY", "ZOTERO_USER_ID"), ("libraries", "items", "collections")),
    IntegrationManifest("hubspot", "HubSpot", "business", "official_api",
        ("HUBSPOT_ACCESS_TOKEN",), ("contacts", "companies", "deals", "tickets")),
    IntegrationManifest("sentry", "Sentry", "developer_ops", "official_api",
        ("SENTRY_AUTH_TOKEN",), ("issues", "projects", "events")),
    IntegrationManifest("vercel", "Vercel", "developer_ops", "official_api",
        ("VERCEL_TOKEN",), ("projects", "deployments", "domains")),
    IntegrationManifest("railway", "Railway", "developer_ops", "official_api_or_mcp",
        ("RAILWAY_API_TOKEN",), ("projects", "deployments", "logs")),
    IntegrationManifest("microsoft365", "Microsoft 365", "productivity", "graph_api",
        ("MICROSOFT_CLIENT_ID", "MICROSOFT_CLIENT_SECRET", "MICROSOFT_REFRESH_TOKEN"),
        ("outlook", "calendar", "onedrive", "sharepoint")),
    IntegrationManifest("dropbox", "Dropbox", "files", "official_api",
        ("DROPBOX_APP_KEY", "DROPBOX_APP_SECRET", "DROPBOX_REFRESH_TOKEN"), ("files", "sharing")),
    IntegrationManifest("home_assistant", "Home Assistant", "device_smart_home", "local_api",
        ("HOME_ASSISTANT_URL", "HOME_ASSISTANT_TOKEN"), ("entities", "scenes", "automations"),
        notes=("Requires an explicitly configured Home Assistant instance and long-lived access token.",)),
    IntegrationManifest("android_companion", "Android Companion", "device", "device_bridge",
        (), ("alarms", "notifications", "open_apps", "media_sessions", "share"),
        IntegrationState.DEVICE_PHASE,
        ("Requires a later Android app, pairing and explicit OS permissions.",)),
    IntegrationManifest("filesystem", "Scoped Filesystem", "files", "local",
        (), ("read", "write", "search", "organise"),
        notes=("Sandboxed workspace only; destructive changes require approval.",)),
    IntegrationManifest("browser", "Playwright Browser", "web_automation", "browser",
        (), ("navigate", "extract", "download", "upload", "form_fill"),
        notes=("Isolated browser profile. Respect site terms, robots, CAPTCHA and MFA; no access-control bypass.",)),
    IntegrationManifest("email_delivery", "Resend", "communication", "official_api",
        ("RESEND_API_KEY",), ("transactional_email", "delivery_events")),
    IntegrationManifest("openai", "OpenAI Services", "ai_services", "official_api",
        ("OPENAI_API_KEY",), ("image_generation", "speech", "transcription")),
    IntegrationManifest("google_ai", "Google AI Services", "ai_services", "official_api",
        ("GOOGLE_AI_API_KEY",), ("image", "speech", "transcription")),
)


# Tool catalogues are explicit, inspectable contracts. High-impact operations
# are confirmation-gated by the execution policy before any adapter call.
_TOOL_ROWS = (
    ("google_workspace", "gmail.search", "Search email", "read", False),
    ("google_workspace", "gmail.read", "Read an email thread", "read", False),
    ("google_workspace", "gmail.draft", "Create an email draft", "write", False),
    ("google_workspace", "gmail.send", "Send an email", "external_communication", True),
    ("google_workspace", "calendar.search", "Find calendar events and availability", "read", False),
    ("google_workspace", "calendar.create", "Create a calendar event", "write", True),
    ("google_workspace", "calendar.update", "Update or cancel a calendar event", "write", True),
    ("google_workspace", "drive.search", "Search Drive files", "read", False),
    ("google_workspace", "drive.upload", "Upload a file to Drive", "write", True),
    ("google_workspace", "contacts.search", "Search contacts", "read", False),
    ("notion", "notion.search", "Search Notion workspace", "read", False),
    ("notion", "notion.page.create", "Create a Notion page", "write", False),
    ("notion", "notion.page.update", "Update a Notion page", "write", False),
    ("notion", "notion.database.query", "Query a Notion database", "read", False),
    ("brave_search", "brave.search", "Search the public web with Brave", "read", False),
    ("tavily", "tavily.search", "Search the web with Tavily", "read", False),
    ("tavily", "tavily.extract", "Extract content from research URLs", "read", False),
    ("github", "github.repo.search", "Search repositories", "read", False),
    ("github", "github.issue.create", "Create a GitHub issue", "write", True),
    ("github", "github.pull_request.create", "Create a pull request", "write", True),
    ("gitlab", "gitlab.project.search", "Search GitLab projects", "read", False),
    ("gitlab", "gitlab.issue.create", "Create a GitLab issue", "write", True),
    ("gitlab", "gitlab.merge_request.create", "Create a GitLab merge request", "write", True),
    ("linear", "linear.issue.search", "Search Linear issues", "read", False),
    ("linear", "linear.issue.create", "Create a Linear issue", "write", True),
    ("figma", "figma.file.get", "Read a Figma file", "read", False),
    ("figma", "figma.comments.list", "List Figma comments", "read", False),
    ("figma", "figma.comment.create", "Post a Figma comment", "external_communication", True),
    ("slack", "slack.search", "Search Slack messages", "read", False),
    ("slack", "slack.message.send", "Send a Slack message", "external_communication", True),
    ("discord", "discord.message.send", "Send a message through an authorised bot", "external_communication", True),
    ("whatsapp", "whatsapp.message.send", "Send an approved WhatsApp Business message", "external_communication", True),
    ("instagram", "instagram.media.publish", "Publish approved Instagram professional-account media", "external_communication", True),
    ("instagram", "instagram.comments.read", "Read eligible Instagram comments", "read", False),
    ("facebook", "facebook.page.publish", "Publish to an authorised Facebook Page", "external_communication", True),
    ("threads", "threads.post.publish", "Publish a Threads post", "external_communication", True),
    ("snapchat", "snapchat.public.search", "Search eligible public Snapchat content", "read", False),
    ("tiktok", "tiktok.content.publish", "Publish content with approved TikTok permissions", "external_communication", True),
    ("x", "x.search", "Search public X posts", "read", False),
    ("x", "x.post.create", "Publish an X post", "external_communication", True),
    ("linkedin", "linkedin.post.create", "Publish to an authorised LinkedIn identity or organisation", "external_communication", True),
    ("telegram", "telegram.message.send", "Send a Telegram bot message", "external_communication", True),
    ("reddit", "reddit.search", "Search Reddit", "read", False),
    ("reddit", "reddit.comment.create", "Publish a Reddit comment", "external_communication", True),
    ("pinterest", "pinterest.pin.create", "Create a Pinterest pin", "external_communication", True),
    ("spotify", "spotify.search", "Search Spotify catalog", "read", False),
    ("spotify", "spotify.playback.start", "Start eligible Spotify playback", "write", True),
    ("youtube", "youtube.search", "Search YouTube", "read", False),
    ("zotero", "zotero.items.search", "Search Zotero library", "read", False),
    ("hubspot", "hubspot.contacts.search", "Search CRM contacts", "read", False),
    ("hubspot", "hubspot.deal.update", "Update a CRM deal", "write", True),
    ("sentry", "sentry.issues.search", "Search Sentry issues", "read", False),
    ("vercel", "vercel.deployments.list", "List Vercel deployments", "read", False),
    ("vercel", "vercel.production.deploy", "Deploy to production", "privileged", True),
    ("railway", "railway.logs.read", "Read deployment logs", "read", False),
    ("microsoft365", "outlook.search", "Search Outlook mail", "read", False),
    ("dropbox", "dropbox.files.search", "Search Dropbox files", "read", False),
    ("home_assistant", "home_assistant.entity.read", "Read smart-home entity state", "read", False),
    ("home_assistant", "home_assistant.service.call", "Control a smart-home entity", "privileged", True),
    ("android_companion", "android.alarm.create", "Create a device alarm", "device", True),
    ("android_companion", "android.app.open", "Open an installed Android app", "device", True),
    ("browser", "browser.navigate", "Navigate an authorised browser session", "read", False),
    ("browser", "browser.form.submit", "Submit a web form", "external_communication", True),
    ("filesystem", "filesystem.file.read", "Read a file in the RUNE workspace", "read", False),
    ("filesystem", "filesystem.file.write", "Write a file in the RUNE workspace", "write", False),
    ("filesystem", "filesystem.file.delete", "Delete a workspace file", "destructive", True),
    ("email_delivery", "email.send", "Send transactional email", "external_communication", True),
)


def integration_catalogue() -> tuple[IntegrationManifest, ...]:
    return INTEGRATIONS


_TOOL_SCHEMAS: dict[str, dict] = {
    "gmail.search": {"type": "object", "required": ["q"], "properties": {
        "q": {"type": "string", "minLength": 1, "maxLength": 500},
        "maxResults": {"type": "integer", "minimum": 1, "maximum": 100}}, "additionalProperties": False},
    "gmail.read": {"type": "object", "required": ["message_id"], "properties": {
        "message_id": {"type": "string", "minLength": 1, "maxLength": 256}}, "additionalProperties": False},
    "gmail.draft": {"type": "object", "required": ["to", "subject", "body"], "properties": {
        "to": {"type": "string", "minLength": 3, "maxLength": 320},
        "subject": {"type": "string", "maxLength": 998},
        "body": {"type": "string", "maxLength": 100000}}, "additionalProperties": False},
    "gmail.send": {"type": "object", "required": ["to", "subject", "body"], "properties": {
        "to": {"type": "string", "minLength": 3, "maxLength": 320},
        "subject": {"type": "string", "maxLength": 998},
        "body": {"type": "string", "maxLength": 100000}}, "additionalProperties": False},
    "calendar.search": {"type": "object", "properties": {
        "timeMin": {"type": "string", "maxLength": 64}, "timeMax": {"type": "string", "maxLength": 64},
        "q": {"type": "string", "maxLength": 500}, "maxResults": {"type": "integer", "minimum": 1, "maximum": 2500}},
        "additionalProperties": False},
    "calendar.create": {"type": "object", "required": ["summary", "start", "end"], "properties": {
        "summary": {"type": "string", "minLength": 1, "maxLength": 1024},
        "description": {"type": "string", "maxLength": 8192},
        "start": {"type": "object"}, "end": {"type": "object"},
        "attendees": {"type": "array", "items": {"type": "object"}, "maxItems": 100}},
        "additionalProperties": False},
    "calendar.update": {"type": "object", "required": ["event_id"], "properties": {
        "event_id": {"type": "string", "minLength": 1, "maxLength": 256},
        "summary": {"type": "string", "maxLength": 1024}, "description": {"type": "string", "maxLength": 8192},
        "start": {"type": "object"}, "end": {"type": "object"}, "status": {"type": "string", "enum": ["confirmed", "cancelled"]}},
        "additionalProperties": False},
    "drive.search": {"type": "object", "properties": {
        "q": {"type": "string", "maxLength": 1000}, "pageSize": {"type": "integer", "minimum": 1, "maximum": 1000},
        "orderBy": {"type": "string", "maxLength": 100}, "fields": {"type": "string", "maxLength": 1000}},
        "additionalProperties": False},
    "contacts.search": {"type": "object", "properties": {
        "pageSize": {"type": "integer", "minimum": 1, "maximum": 1000},
        "personFields": {"type": "string", "maxLength": 500}}, "additionalProperties": False},
    "notion.search": {"type": "object", "properties": {
        "query": {"type": "string", "maxLength": 500}, "page_size": {"type": "integer", "minimum": 1, "maximum": 100},
        "start_cursor": {"type": "string", "maxLength": 256}}, "additionalProperties": False},
    "notion.database.query": {"type": "object", "required": ["database_id"], "properties": {
        "database_id": {"type": "string", "minLength": 1, "maxLength": 64},
        "filter": {"type": "object"}, "sorts": {"type": "array", "items": {"type": "object"}, "maxItems": 10},
        "page_size": {"type": "integer", "minimum": 1, "maximum": 100},
        "start_cursor": {"type": "string", "maxLength": 256}}, "additionalProperties": False},
    "notion.page.create": {"type": "object", "required": ["parent", "properties"], "properties": {
        "parent": {"type": "object"}, "properties": {"type": "object"},
        "children": {"type": "array", "items": {"type": "object"}, "maxItems": 100},
        "icon": {"type": "object"}, "cover": {"type": "object"}}, "additionalProperties": False},
    "notion.page.update": {"type": "object", "required": ["page_id"], "properties": {
        "page_id": {"type": "string", "minLength": 1, "maxLength": 64},
        "properties": {"type": "object"}, "archived": {"type": "boolean"},
        "in_trash": {"type": "boolean"}, "icon": {"type": "object"}, "cover": {"type": "object"}},
        "additionalProperties": False},
    "brave.search": {"type": "object", "required": ["q"], "properties": {
        "q": {"type": "string", "minLength": 1, "maxLength": 500},
        "count": {"type": "integer", "minimum": 1, "maximum": 20},
        "country": {"type": "string", "maxLength": 2}, "search_lang": {"type": "string", "maxLength": 10},
        "freshness": {"type": "string", "maxLength": 10}}, "additionalProperties": False},
    "tavily.search": {"type": "object", "required": ["query"], "properties": {
        "query": {"type": "string", "minLength": 1, "maxLength": 1000},
        "search_depth": {"type": "string", "enum": ["basic", "advanced"]},
        "topic": {"type": "string", "enum": ["general", "news", "finance"]},
        "max_results": {"type": "integer", "minimum": 1, "maximum": 20},
        "include_answer": {"type": "boolean"}, "include_raw_content": {"type": "boolean"},
        "include_domains": {"type": "array", "items": {"type": "string"}, "maxItems": 50},
        "exclude_domains": {"type": "array", "items": {"type": "string"}, "maxItems": 50}},
        "additionalProperties": False},
    "tavily.extract": {"type": "object", "required": ["urls"], "properties": {
        "urls": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 20},
        "include_images": {"type": "boolean"}, "extract_depth": {"type": "string", "enum": ["basic", "advanced"]},
        "format": {"type": "string", "enum": ["markdown", "text"]}}, "additionalProperties": False},
    "figma.file.get": {"type": "object", "required": ["file_key"], "properties": {
        "file_key": {"type": "string", "minLength": 1, "maxLength": 128},
        "depth": {"type": "integer", "minimum": 1, "maximum": 10}}, "additionalProperties": False},
    "figma.comments.list": {"type": "object", "required": ["file_key"], "properties": {
        "file_key": {"type": "string", "minLength": 1, "maxLength": 128}}, "additionalProperties": False},
    "figma.comment.create": {"type": "object", "required": ["file_key", "message"], "properties": {
        "file_key": {"type": "string", "minLength": 1, "maxLength": 128},
        "message": {"type": "string", "minLength": 1, "maxLength": 10000},
        "client_meta": {"type": "object"}}, "additionalProperties": False},
    "github.repo.search": {"type": "object", "required": ["q"],
        "properties": {"q": {"type": "string", "minLength": 1, "maxLength": 256},
            "sort": {"type": "string", "enum": ["stars", "forks", "help-wanted-issues", "updated"]},
            "order": {"type": "string", "enum": ["asc", "desc"]},
            "per_page": {"type": "integer", "minimum": 1, "maximum": 100},
            "page": {"type": "integer", "minimum": 1}},
        "additionalProperties": False},
    "github.issue.create": {"type": "object", "required": ["owner", "repo", "title"],
        "properties": {"owner": {"type": "string", "minLength": 1, "maxLength": 100},
            "repo": {"type": "string", "minLength": 1, "maxLength": 100},
            "title": {"type": "string", "minLength": 1, "maxLength": 256},
            "body": {"type": "string", "maxLength": 65536},
            "assignees": {"type": "array", "items": {"type": "string"}, "maxItems": 10},
            "labels": {"type": "array", "items": {"type": "string"}, "maxItems": 100},
            "milestone": {"type": "integer", "minimum": 1}},
        "additionalProperties": False},
    "github.pull_request.create": {"type": "object", "required": ["owner", "repo", "title", "head", "base"],
        "properties": {"owner": {"type": "string", "minLength": 1, "maxLength": 100},
            "repo": {"type": "string", "minLength": 1, "maxLength": 100},
            "title": {"type": "string", "minLength": 1, "maxLength": 256},
            "head": {"type": "string", "minLength": 1, "maxLength": 256},
            "base": {"type": "string", "minLength": 1, "maxLength": 256},
            "body": {"type": "string", "maxLength": 65536},
            "draft": {"type": "boolean"}, "maintainer_can_modify": {"type": "boolean"}},
        "additionalProperties": False},
    "gitlab.project.search": {"type": "object", "required": ["search"], "properties": {"search": {"type": "string", "minLength": 1, "maxLength": 256}, "per_page": {"type": "integer", "minimum": 1, "maximum": 100}}, "additionalProperties": False},
    "gitlab.issue.create": {"type": "object", "required": ["project_id", "title"], "properties": {"project_id": {"type": "integer", "minimum": 1}, "title": {"type": "string", "minLength": 1, "maxLength": 255}, "description": {"type": "string", "maxLength": 100000}, "labels": {"type": "string", "maxLength": 1000}}, "additionalProperties": False},
    "gitlab.merge_request.create": {"type": "object", "required": ["project_id", "source_branch", "target_branch", "title"], "properties": {"project_id": {"type": "integer", "minimum": 1}, "source_branch": {"type": "string", "minLength": 1}, "target_branch": {"type": "string", "minLength": 1}, "title": {"type": "string", "minLength": 1, "maxLength": 255}, "description": {"type": "string", "maxLength": 100000}}, "additionalProperties": False},
    "linear.issue.search": {"type": "object", "required": ["query"], "properties": {"query": {"type": "string", "minLength": 1, "maxLength": 256}}, "additionalProperties": False},
    "linear.issue.create": {"type": "object", "required": ["team_id", "title"], "properties": {"team_id": {"type": "string", "minLength": 1}, "title": {"type": "string", "minLength": 1, "maxLength": 255}, "description": {"type": "string", "maxLength": 100000}, "assignee_id": {"type": "string"}}, "additionalProperties": False},
    "telegram.message.send": {"type": "object", "required": ["chat_id", "text"],
        "properties": {
            "chat_id": {"type": "string", "minLength": 1, "maxLength": 128},
            "text": {"type": "string", "minLength": 1, "maxLength": 4096},
            "parse_mode": {"type": "string", "enum": ["Markdown", "MarkdownV2", "HTML"]},
            "disable_notification": {"type": "boolean"}},
        "additionalProperties": False},
    "email.send": {"type": "object", "required": ["from", "to", "subject"],
        "properties": {
            "from": {"type": "string", "minLength": 3, "maxLength": 320},
            "to": {"type": "array", "items": {"type": "string", "minLength": 3, "maxLength": 320}, "minItems": 1, "maxItems": 50},
            "subject": {"type": "string", "minLength": 1, "maxLength": 998},
            "html": {"type": "string", "maxLength": 100000},
            "text": {"type": "string", "maxLength": 100000},
            "reply_to": {"type": "string", "maxLength": 320},
            "cc": {"type": "array", "items": {"type": "string"}, "maxItems": 50},
            "bcc": {"type": "array", "items": {"type": "string"}, "maxItems": 50},
            "tags": {"type": "array", "items": {"type": "object"}, "maxItems": 20}},
        "additionalProperties": False},
    "drive.upload": {"type": "object", "required": ["file_name", "mime_type", "content_base64"], "properties": {"file_name": {"type": "string"}, "mime_type": {"type": "string"}, "content_base64": {"type": "string"}, "parent_id": {"type": "string"}}, "additionalProperties": False},
    "slack.search": {"type": "object", "required": ["query"], "properties": {"query": {"type": "string"}, "count": {"type": "integer"}}, "additionalProperties": False},
    "slack.message.send": {"type": "object", "required": ["channel", "text"], "properties": {"channel": {"type": "string"}, "text": {"type": "string"}}, "additionalProperties": False},
    "discord.message.send": {"type": "object", "required": ["channel_id", "content"], "properties": {"channel_id": {"type": "string"}, "content": {"type": "string"}}, "additionalProperties": False},
    "whatsapp.message.send": {"type": "object", "required": ["to", "type"], "properties": {"to": {"type": "string"}, "type": {"type": "string"}, "text": {"type": "object"}, "template": {"type": "object"}}, "additionalProperties": False},
    "instagram.media.publish": {"type": "object", "required": ["ig_user_id", "image_url"], "properties": {"ig_user_id": {"type": "string"}, "image_url": {"type": "string"}, "caption": {"type": "string"}}, "additionalProperties": False},
    "instagram.comments.read": {"type": "object", "required": ["ig_user_id", "media_id"], "properties": {"ig_user_id": {"type": "string"}, "media_id": {"type": "string"}}, "additionalProperties": False},
    "facebook.page.publish": {"type": "object", "required": ["page_id", "message"], "properties": {"page_id": {"type": "string"}, "message": {"type": "string"}, "link": {"type": "string"}}, "additionalProperties": False},
    "threads.post.publish": {"type": "object", "required": ["user_id", "text"], "properties": {"user_id": {"type": "string"}, "text": {"type": "string"}, "media_url": {"type": "string"}}, "additionalProperties": False},
    "snapchat.public.search": {"type": "object", "required": ["query"], "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}}, "additionalProperties": False},
    "tiktok.content.publish": {"type": "object", "required": ["video_url", "title", "privacy_level"], "properties": {"video_url": {"type": "string", "format": "uri"}, "title": {"type": "string", "maxLength": 2200}, "privacy_level": {"type": "string", "enum": ["PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS", "FOLLOWER_OF_CREATOR", "SELF_ONLY"]}}, "additionalProperties": False},
    "x.search": {"type": "object", "required": ["query"], "properties": {"query": {"type": "string"}, "max_results": {"type": "integer"}}, "additionalProperties": False},
    "x.post.create": {"type": "object", "required": ["text"], "properties": {"text": {"type": "string"}, "reply_to_id": {"type": "string"}}, "additionalProperties": False},
    "linkedin.post.create": {"type": "object", "required": ["author", "commentary"], "properties": {"author": {"type": "string"}, "commentary": {"type": "string"}, "visibility": {"type": "string"}}, "additionalProperties": False},
    "reddit.search": {"type": "object", "required": ["query"], "properties": {"query": {"type": "string"}, "subreddit": {"type": "string"}, "sort": {"type": "string"}, "limit": {"type": "integer"}}, "additionalProperties": False},
    "reddit.comment.create": {"type": "object", "required": ["parent_id", "text"], "properties": {"parent_id": {"type": "string"}, "text": {"type": "string"}}, "additionalProperties": False},
    "pinterest.pin.create": {"type": "object", "required": ["board_id", "title", "media_source"], "properties": {"board_id": {"type": "string"}, "title": {"type": "string"}, "description": {"type": "string"}, "link": {"type": "string"}, "media_source": {"type": "object"}}, "additionalProperties": False},
    "spotify.search": {"type": "object", "required": ["q"], "properties": {"q": {"type": "string"}, "type": {"type": "string"}, "limit": {"type": "integer"}}, "additionalProperties": False},
    "spotify.playback.start": {"type": "object", "required": ["uri"], "properties": {"uri": {"type": "string"}, "device_id": {"type": "string"}}, "additionalProperties": False},
    "youtube.search": {"type": "object", "required": ["q"], "properties": {"q": {"type": "string"}, "type": {"type": "string"}, "maxResults": {"type": "integer"}}, "additionalProperties": False},
    "zotero.items.search": {"type": "object", "required": ["q"], "properties": {"q": {"type": "string"}, "limit": {"type": "integer"}}, "additionalProperties": False},
    "hubspot.contacts.search": {"type": "object", "required": [], "properties": {"q": {"type": "string"}, "limit": {"type": "integer"}}, "additionalProperties": False},
    "hubspot.deal.update": {"type": "object", "required": ["deal_id", "properties"], "properties": {"deal_id": {"type": "string"}, "properties": {"type": "object"}}, "additionalProperties": False},
    "sentry.issues.search": {"type": "object", "required": [], "properties": {"query": {"type": "string"}, "project": {"type": "string"}, "limit": {"type": "integer"}}, "additionalProperties": False},
    "vercel.deployments.list": {"type": "object", "required": [], "properties": {"projectId": {"type": "string"}, "limit": {"type": "integer"}}, "additionalProperties": False},
    "vercel.production.deploy": {"type": "object", "required": ["projectId", "name", "gitSource"], "properties": {"projectId": {"type": "string", "minLength": 1}, "name": {"type": "string", "minLength": 1}, "target": {"type": "string", "enum": ["production", "preview"]}, "gitSource": {"type": "object"}}, "additionalProperties": False},
    "railway.logs.read": {"type": "object", "required": ["deploymentId"], "properties": {"deploymentId": {"type": "string"}, "lines": {"type": "integer"}}, "additionalProperties": False},
    "outlook.search": {"type": "object", "required": ["query"], "properties": {"query": {"type": "string"}, "top": {"type": "integer"}}, "additionalProperties": False},
    "dropbox.files.search": {"type": "object", "required": ["query"], "properties": {"query": {"type": "string"}, "path": {"type": "string"}}, "additionalProperties": False},
    "home_assistant.entity.read": {"type": "object", "required": ["entity_id"], "properties": {"entity_id": {"type": "string"}}, "additionalProperties": False},
    "home_assistant.service.call": {"type": "object", "required": ["domain", "service", "entity_id"], "properties": {"domain": {"type": "string"}, "service": {"type": "string"}, "entity_id": {"type": "string"}, "service_data": {"type": "object"}}, "additionalProperties": False},
    "android.alarm.create": {"type": "object", "required": ["hour", "minute"], "properties": {"hour": {"type": "integer"}, "minute": {"type": "integer"}, "label": {"type": "string"}}, "additionalProperties": False},
    "android.app.open": {"type": "object", "required": ["package_name"], "properties": {"package_name": {"type": "string"}}, "additionalProperties": False},
    "browser.navigate": {"type": "object", "required": ["url"], "properties": {"url": {"type": "string"}}, "additionalProperties": False},
    "browser.form.submit": {"type": "object", "required": ["url", "fields"], "properties": {"url": {"type": "string"}, "fields": {"type": "object"}}, "additionalProperties": False},
    "filesystem.file.read": {"type": "object", "required": ["path"], "properties": {"path": {"type": "string"}}, "additionalProperties": False},
    "filesystem.file.write": {"type": "object", "required": ["path", "content"], "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "additionalProperties": False},
    "filesystem.file.delete": {"type": "object", "required": ["path"], "properties": {"path": {"type": "string"}}, "additionalProperties": False},
}
_DEFAULT_SCHEMA = {"type": "object", "additionalProperties": False}


def _integration_availability(integration_id: str) -> str:
    state = next((item.state for item in INTEGRATIONS if item.id == integration_id),
                 IntegrationState.READY_FOR_CONFIGURATION)
    if state is IntegrationState.DEVICE_PHASE:
        return "device_dependent"
    if state is IntegrationState.MANUAL_FALLBACK:
        return "manual_fallback"
    if state is IntegrationState.PROVIDER_REVIEW_REQUIRED:
        return "restricted_or_review_required"
    return "provider_dependent"


def tool_catalogue() -> tuple[ToolManifest, ...]:
    return tuple(
        ToolManifest(
            id=tool_id,
            integration_id=integration_id,
            name=tool_id.rsplit(".", 1)[-1],
            description=description,
            risk=risk,
            confirmation=confirmation,
            availability=_integration_availability(integration_id),
        )
        for integration_id, tool_id, description, risk, confirmation in _TOOL_ROWS
    )


def tool_schema(tool_id: str) -> dict:
    """Return a defensive copy of the strict schema for a known tool."""
    import copy
    if tool_id not in {row[1] for row in _TOOL_ROWS}:
        raise KeyError(tool_id)
    return copy.deepcopy(_TOOL_SCHEMAS.get(tool_id, _DEFAULT_SCHEMA))


def snapshot() -> dict:
    return {
        "integrations": [
            {
                "id": item.id, "name": item.name, "category": item.category,
                "transport": item.transport, "auth_env": list(item.auth_env),
                "capabilities": list(item.capabilities), "state": item.state.value,
                "notes": list(item.notes),
            }
            for item in INTEGRATIONS
        ],
        "tools": [
            {
                "id": item.id, "integration_id": item.integration_id,
                "name": item.name, "description": item.description,
                "risk": item.risk, "confirmation": item.confirmation,
                "availability": item.availability,
            }
            for item in tool_catalogue()
        ],
    }
