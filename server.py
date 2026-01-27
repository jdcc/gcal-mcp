"""MCP server for Google Calendar."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from mcp.server.fastmcp import FastMCP

SCOPES = ["https://www.googleapis.com/auth/calendar"]
CONFIG_DIR = Path.home() / ".config" / "gcal-mcp"
CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"
TOKEN_FILE = CONFIG_DIR / "token.json"


def get_credentials() -> Credentials:
    """Load or refresh credentials. Raises if no token and not in --auth mode."""
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_FILE.write_text(creds.to_json())
    if not creds or not creds.valid:
        if not CREDENTIALS_FILE.exists():
            raise FileNotFoundError(
                f"No credentials.json found at {CREDENTIALS_FILE}. "
                "Download OAuth Desktop App credentials from Google Cloud Console."
            )
        flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
        creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())
    return creds


def get_service():
    """Build and return the Calendar API service."""
    return build("calendar", "v3", credentials=get_credentials())


def parse_datetime(value: str) -> dict:
    """Return a Google Calendar dateTime or date dict.

    Accepts YYYY-MM-DD (date-only) or any ISO datetime string.
    """
    if len(value) == 10 and value[4] == "-" and value[7] == "-":
        return {"date": value}
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.astimezone()
    return {"dateTime": dt.isoformat(), "timeZone": str(dt.tzinfo)}


# --- MCP Server ---

mcp = FastMCP("gcal-mcp")


@mcp.tool()
def list_calendars() -> str:
    """List all calendars accessible by the authenticated account."""
    try:
        service = get_service()
        result = service.calendarList().list().execute()
        calendars = result.get("items", [])
        return json.dumps(
            [
                {
                    "id": c["id"],
                    "summary": c.get("summary", ""),
                    "primary": c.get("primary", False),
                }
                for c in calendars
            ],
            indent=2,
        )
    except HttpError as e:
        return f"Google API error: {e}"


@mcp.tool()
def list_events(
    calendar_id: str = "primary",
    max_results: int = 25,
    time_min: Optional[str] = None,
    time_max: Optional[str] = None,
    query: Optional[str] = None,
) -> str:
    """List or search events on a calendar.

    Args:
        calendar_id: Calendar ID (default "primary").
        max_results: Maximum number of events to return (default 25).
        time_min: Lower bound (inclusive) as ISO datetime or YYYY-MM-DD.
        time_max: Upper bound (exclusive) as ISO datetime or YYYY-MM-DD.
        query: Free-text search term matched against event fields.
    """
    try:
        service = get_service()
        kwargs: dict = {
            "calendarId": calendar_id,
            "maxResults": max_results,
            "singleEvents": True,
            "orderBy": "startTime",
        }
        if time_min:
            dt = datetime.fromisoformat(time_min)
            if dt.tzinfo is None:
                dt = dt.astimezone()
            kwargs["timeMin"] = dt.isoformat()
        else:
            kwargs["timeMin"] = datetime.now(timezone.utc).isoformat()
        if time_max:
            dt = datetime.fromisoformat(time_max)
            if dt.tzinfo is None:
                dt = dt.astimezone()
            kwargs["timeMax"] = dt.isoformat()
        if query:
            kwargs["q"] = query

        result = service.events().list(**kwargs).execute()
        events = result.get("items", [])
        return json.dumps(
            [
                {
                    "id": e["id"],
                    "summary": e.get("summary", "(no title)"),
                    "start": e.get("start", {}),
                    "end": e.get("end", {}),
                    "location": e.get("location", ""),
                    "description": e.get("description", ""),
                    "htmlLink": e.get("htmlLink", ""),
                }
                for e in events
            ],
            indent=2,
        )
    except HttpError as e:
        return f"Google API error: {e}"


@mcp.tool()
def create_event(
    summary: str,
    start: str,
    end: str,
    calendar_id: str = "primary",
    description: str = "",
    location: str = "",
    attendees: Optional[list[str]] = None,
) -> str:
    """Create a calendar event.

    Args:
        summary: Event title.
        start: Start time as ISO datetime (YYYY-MM-DDTHH:MM) or date (YYYY-MM-DD).
        end: End time as ISO datetime or date.
        calendar_id: Calendar ID (default "primary").
        description: Event description.
        location: Event location.
        attendees: List of email addresses to invite.
    """
    try:
        service = get_service()
        body: dict = {
            "summary": summary,
            "start": parse_datetime(start),
            "end": parse_datetime(end),
        }
        if description:
            body["description"] = description
        if location:
            body["location"] = location
        if attendees:
            body["attendees"] = [{"email": a} for a in attendees]

        event = service.events().insert(calendarId=calendar_id, body=body).execute()
        return json.dumps(
            {
                "id": event["id"],
                "summary": event.get("summary", ""),
                "htmlLink": event.get("htmlLink", ""),
                "start": event.get("start", {}),
                "end": event.get("end", {}),
            },
            indent=2,
        )
    except HttpError as e:
        return f"Google API error: {e}"


@mcp.tool()
def modify_event(
    event_id: str,
    calendar_id: str = "primary",
    summary: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    description: Optional[str] = None,
    location: Optional[str] = None,
) -> str:
    """Modify an existing calendar event. Only provided fields are updated.

    Args:
        event_id: The event ID to modify.
        calendar_id: Calendar ID (default "primary").
        summary: New event title.
        start: New start time as ISO datetime or date.
        end: New end time as ISO datetime or date.
        description: New description.
        location: New location.
    """
    try:
        service = get_service()
        body: dict = {}
        if summary is not None:
            body["summary"] = summary
        if start is not None:
            body["start"] = parse_datetime(start)
        if end is not None:
            body["end"] = parse_datetime(end)
        if description is not None:
            body["description"] = description
        if location is not None:
            body["location"] = location

        event = (
            service.events()
            .patch(calendarId=calendar_id, eventId=event_id, body=body)
            .execute()
        )
        return json.dumps(
            {
                "id": event["id"],
                "summary": event.get("summary", ""),
                "htmlLink": event.get("htmlLink", ""),
                "start": event.get("start", {}),
                "end": event.get("end", {}),
            },
            indent=2,
        )
    except HttpError as e:
        return f"Google API error: {e}"


if __name__ == "__main__":
    if "--auth" in sys.argv:
        print("Running OAuth flow...", file=sys.stderr)
        creds = get_credentials()
        print("Authenticated. Listing calendars:", file=sys.stderr)
        service = build("calendar", "v3", credentials=creds)
        for cal in service.calendarList().list().execute().get("items", []):
            primary = " (primary)" if cal.get("primary") else ""
            print(f"  - {cal['summary']}{primary}", file=sys.stderr)
        print("Token saved to", TOKEN_FILE, file=sys.stderr)
    else:
        mcp.run(transport="stdio")
