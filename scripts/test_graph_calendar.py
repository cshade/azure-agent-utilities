#!/usr/bin/env python3
"""
Test script: Sign in to Microsoft account and call GET /me/calendarView via Microsoft Graph.

Prerequisites:
  pip install msal requests

App registration (Azure Portal > App registrations):
  - Supported account types: "Personal Microsoft accounts" or "Any Azure AD + personal"
  - Platform: "Mobile and desktop applications"
    - Allow public client flows: Enabled (Yes)
  - Redirect URI: https://login.microsoftonline.com/common/oauth2/nativeclient
  - Required delegated permissions: Calendars.Read

Set your Client ID below, or export it as AZURE_CLIENT_ID.
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone

import msal
import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CLIENT_ID = os.environ.get("AZURE_CLIENT_ID", "YOUR_CLIENT_ID_HERE")

# "common"  → work/school + personal accounts
# "consumers" → personal Microsoft accounts only
AUTHORITY = os.environ.get(
    "AZURE_AUTHORITY", "https://login.microsoftonline.com/common"
)

SCOPES = ["Calendars.Read", "User.Read"]

GRAPH_BASE = "https://graph.microsoft.com/v1.0"

# calendarView window (next 7 days)
_now = datetime.now(timezone.utc)
START = _now.strftime("%Y-%m-%dT%H:%M:%SZ")
END = (_now + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")

# ---------------------------------------------------------------------------
# Token cache (persists across runs so you only auth once)
# ---------------------------------------------------------------------------
CACHE_FILE = os.path.join(os.path.dirname(__file__), ".token_cache.json")


def _load_cache() -> msal.SerializableTokenCache:
    cache = msal.SerializableTokenCache()
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            cache.deserialize(f.read())
    return cache


def _save_cache(cache: msal.SerializableTokenCache) -> None:
    if cache.has_state_changed:
        with open(CACHE_FILE, "w") as f:
            f.write(cache.serialize())


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
def _exit_device_flow_error(flow: dict) -> None:
    error_codes = flow.get("error_codes", [])
    if 70002 in error_codes:
        sys.exit(
            "[auth] Failed to create device flow: app is not enabled as a public/mobile client.\n"
            "\n"
            "Fix your Azure app registration:\n"
            "  1) Azure Portal -> App registrations -> <your app> -> Authentication\n"
            "  2) Add platform: Mobile and desktop applications\n"
            "  3) Add redirect URI: https://login.microsoftonline.com/common/oauth2/nativeclient\n"
            "  4) Enable 'Allow public client flows' (set to Yes)\n"
            "\n"
            "Then re-run this script. Original error payload:\n"
            f"{flow}"
        )

    sys.exit(f"[auth] Failed to create device flow: {flow}")


def acquire_token() -> str:
    if CLIENT_ID == "YOUR_CLIENT_ID_HERE":
        sys.exit(
            "\nERROR: Set your Azure app Client ID.\n"
            "  export AZURE_CLIENT_ID=<your-client-id>\n"
            "or edit CLIENT_ID in this script.\n"
        )

    cache = _load_cache()

    app = msal.PublicClientApplication(
        client_id=CLIENT_ID,
        authority=AUTHORITY,
        token_cache=cache,
    )

    # Try silent auth first (cached token)
    accounts = app.get_accounts()
    result = None
    if accounts:
        print(
            f"[auth] Found cached account: {accounts[0].get('username', '(unknown)')}"
        )
        result = app.acquire_token_silent(SCOPES, account=accounts[0])

    # Fall back to device code flow (works in any terminal, no browser redirect needed)
    if not result:
        flow = app.initiate_device_flow(scopes=SCOPES)

        # If the app is configured as Microsoft Account (MSA) only,
        # Azure AD requires the /consumers authority endpoint.
        if flow.get("error_codes") and 9002346 in flow.get("error_codes", []):
            print(
                "[auth] App appears to be MSA-only; retrying with /consumers authority"
            )
            app = msal.PublicClientApplication(
                client_id=CLIENT_ID,
                authority="https://login.microsoftonline.com/consumers",
                token_cache=cache,
            )
            flow = app.initiate_device_flow(scopes=SCOPES)

        if "user_code" not in flow:
            _exit_device_flow_error(flow)

        print("\n" + "=" * 60)
        print(flow["message"])  # Tells the user to visit aka.ms/devicelogin
        print("=" * 60 + "\n")

        result = app.acquire_token_by_device_flow(
            flow
        )  # blocks until user authenticates

    _save_cache(cache)

    if "access_token" not in result:
        error = result.get("error_description") or result.get("error") or str(result)
        sys.exit(f"[auth] Could not obtain token: {error}")

    print(
        f"[auth] Authenticated as: {result.get('id_token_claims', {}).get('preferred_username', '(unknown)')}\n"
    )
    return result["access_token"]


# ---------------------------------------------------------------------------
# Graph call
# ---------------------------------------------------------------------------
def get_calendar_view(token: str) -> dict:
    url = f"{GRAPH_BASE}/me/calendarView"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    params = {
        "startDateTime": START,
        "endDateTime": END,
        "$orderby": "start/dateTime",
        "$select": "subject,start,end,location,organizer,isOnlineMeeting",
        "$top": "20",
    }

    print(f"GET {url}")
    print(f"    startDateTime = {START}")
    print(f"    endDateTime   = {END}\n")

    response = requests.get(url, headers=headers, params=params, timeout=30)

    print(f"HTTP {response.status_code} {response.reason}")
    print(f"Content-Type: {response.headers.get('Content-Type', '')}\n")

    return response.status_code, response.json() if response.content else {}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    token = acquire_token()
    status, body = get_calendar_view(token)

    print("=" * 60)
    print("Response body:")
    print("=" * 60)
    print(json.dumps(body, indent=2))

    events = body.get("value", [])
    print(f"\n[summary] {len(events)} event(s) returned in the next 7 days.")

    if status >= 400:
        sys.exit(f"\n[error] Graph returned HTTP {status}")


if __name__ == "__main__":
    main()
