# gcal-mcp

MCP server for Google Calendar. Provides four tools: list calendars, list/search events, create events, and modify events.

## Prerequisites

- [uv](https://docs.astral.sh/uv/)
- A Google Cloud project with the Calendar API enabled

## Google Cloud Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project (or select an existing one)
3. Enable the **Google Calendar API**
4. Go to **APIs & Services > Credentials**
5. Create an **OAuth 2.0 Client ID** of type **Desktop App**
6. Download the credentials JSON and save it to `~/.config/gcal-mcp/credentials.json`
7. Go to **OAuth consent screen** and add your Google account as a test user

## Install & Authenticate

```bash
make install    # install dependencies
make auth       # opens browser for OAuth consent, prints calendars on success
```

## Register with Claude Code

```bash
make register   # adds gcal-mcp as a user-scoped MCP server
make unregister # removes it
```

## Tools

| Tool | Description |
|------|-------------|
| `list_calendars` | List all accessible calendars |
| `list_events` | List or search events (supports time range, free-text query) |
| `create_event` | Create an event (supports attendees, location, description) |
| `modify_event` | Patch an existing event (only provided fields are updated) |

Date/time values accept `YYYY-MM-DD` for all-day events or ISO datetime (`YYYY-MM-DDTHH:MM`) for timed events.

## File Locations

- Credentials: `~/.config/gcal-mcp/credentials.json`
- OAuth token: `~/.config/gcal-mcp/token.json`
