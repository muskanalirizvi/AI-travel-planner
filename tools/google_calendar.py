"""Google Calendar event-creation tool using an installed-app OAuth2 flow.

One-time setup (personal/single-user project -- see .env.example for the
matching env vars):
1. In Google Cloud Console, create a project, enable the Google Calendar
   API, and create an OAuth client ID of type "Desktop app". Download its
   JSON and point GOOGLE_CALENDAR_CREDENTIALS_FILE at it.
2. Run `python scripts/authorize_google_calendar.py` once. It opens a
   browser for you to sign in and grant calendar access, then saves a
   token file at GOOGLE_CALENDAR_TOKEN_FILE that's reused (and silently
   refreshed) on every later run.
"""

import os
from datetime import datetime, timedelta
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from langchain_core.tools import tool

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

_SETUP_INSTRUCTIONS = (
    "Google Calendar isn't set up yet. To enable it: (1) In Google Cloud "
    "Console, enable the Google Calendar API and create an OAuth client ID "
    "of type 'Desktop app'. (2) Download its JSON and set "
    "GOOGLE_CALENDAR_CREDENTIALS_FILE in .env to its path. (3) Run "
    "`python scripts/authorize_google_calendar.py` once to grant access "
    "(opens a browser) -- see .env.example for details."
)

_service = None
_init_error: Optional[str] = None


def _get_service():
    """Lazily build and cache the Calendar API client.

    Reads the token file directly rather than running the interactive
    OAuth flow here, since a tool call happens inside an HTTP request and
    can't pop open a browser. The one-time browser consent step lives in
    scripts/authorize_google_calendar.py instead.
    """
    global _service, _init_error

    if _service is not None:
        return _service
    if _init_error is not None:
        raise RuntimeError(_init_error)

    token_file = os.getenv("GOOGLE_CALENDAR_TOKEN_FILE", "google_calendar_token.json")
    if not os.path.exists(token_file):
        _init_error = _SETUP_INSTRUCTIONS
        raise RuntimeError(_init_error)

    creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_file, "w") as f:
                f.write(creds.to_json())
        else:
            _init_error = _SETUP_INSTRUCTIONS
            raise RuntimeError(_init_error)

    _service = build("calendar", "v3", credentials=creds)
    return _service


@tool
def create_event(title: str, date: str, time: str, duration_minutes: int = 60) -> str:
    """Create an event on the user's Google Calendar for an itinerary item.

    Use this to schedule trip-planning items like flights, hotel
    check-ins, or activities, e.g. create_event("Flight to Dubai",
    "2026-09-10", "14:30"). `date` must be "YYYY-MM-DD" and `time` must be
    24-hour "HH:MM". Defaults to a 1-hour event; pass duration_minutes to
    change that. Requires one-time Google Calendar OAuth setup (see
    .env.example) -- if that hasn't been done, returns setup instructions
    instead of failing.
    """
    try:
        start_dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    except ValueError as exc:
        return f"Error: invalid date/time ({exc}). Use date='YYYY-MM-DD' and time='HH:MM'."

    end_dt = start_dt + timedelta(minutes=duration_minutes)
    timezone = os.getenv("GOOGLE_CALENDAR_TIMEZONE", "UTC")

    try:
        service = _get_service()
        event = (
            service.events()
            .insert(
                calendarId="primary",
                body={
                    "summary": title,
                    "start": {"dateTime": start_dt.isoformat(), "timeZone": timezone},
                    "end": {"dateTime": end_dt.isoformat(), "timeZone": timezone},
                },
            )
            .execute()
        )
    except RuntimeError as exc:
        return f"Error: {exc}"
    except HttpError as exc:
        return f"Error creating calendar event: {exc}"

    link = event.get("htmlLink", "")
    return f"Created event '{title}' on {date} at {time} ({timezone}). {link}".strip()
