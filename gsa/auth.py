import os
import json
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/photoslibrary.readonly",
]

TOKEN_PATH = Path.home() / ".gsa" / "token.json"
CREDS_PATH = Path.home() / ".gsa" / "credentials.json"


def get_credentials() -> Credentials:
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    creds = None

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDS_PATH.exists():
                raise FileNotFoundError(
                    f"Google API credentials not found at {CREDS_PATH}\n"
                    "Download OAuth 2.0 credentials from Google Cloud Console and save them there."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)

        TOKEN_PATH.write_text(creds.to_json())

    return creds
