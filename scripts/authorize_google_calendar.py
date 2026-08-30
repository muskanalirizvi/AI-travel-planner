"""One-time interactive setup: authorize this app to access your Google Calendar.

Run once locally: `python scripts/authorize_google_calendar.py`

It opens a browser for you to sign in and grant calendar access, then saves
a reusable token file so tools/google_calendar.py never needs to open a
browser itself. Re-run this if you ever revoke access and need to
re-authorize.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow

from tools.google_calendar import SCOPES

load_dotenv()


def main() -> None:
    credentials_file = os.getenv("GOOGLE_CALENDAR_CREDENTIALS_FILE")
    if not credentials_file or not os.path.exists(credentials_file):
        raise SystemExit(
            "GOOGLE_CALENDAR_CREDENTIALS_FILE is not set in .env or the file "
            "it points to doesn't exist. See .env.example for setup steps."
        )

    token_file = os.getenv("GOOGLE_CALENDAR_TOKEN_FILE", "google_calendar_token.json")

    flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
    creds = flow.run_local_server(port=0)

    with open(token_file, "w") as f:
        f.write(creds.to_json())

    print(f"Authorization complete. Token saved to {token_file}.")


if __name__ == "__main__":
    main()
