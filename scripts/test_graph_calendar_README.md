# Microsoft Graph CalendarView Test Script

This folder contains a Python test script that authenticates a Microsoft user account and calls Microsoft Graph over HTTP:

- Endpoint: `GET /me/calendarView`
- Script: `test_graph_calendar.py`
- Purpose: prove delegated calendar access end-to-end and print the API response body

## What the script does

1. Authenticates with Microsoft identity using MSAL (device code flow)
2. Requests delegated scopes:
   - `Calendars.Read`
   - `User.Read`
3. Calls Graph API:
   - `https://graph.microsoft.com/v1.0/me/calendarView`
4. Sends query parameters for a 7-day time window from current UTC time
5. Prints:
   - HTTP status and content type
   - Full JSON response body
   - Event count summary
6. Caches tokens in `.token_cache.json` so future runs can be silent

## Prerequisites

### 1. Azure app registration

Create an app registration in Azure Portal:

1. Go to `Azure Portal -> App registrations -> New registration`
2. Set **Supported account types** to one of:
   - `Personal Microsoft accounts only`
   - `Accounts in any organizational directory and personal Microsoft accounts`
3. Create the app and copy the **Application (client) ID**

### 2. Add a public client redirect URI

In your app registration:

1. Go to `Authentication (Preview)` (or `Authentication` in non-preview UI)
2. Add platform: `Mobile and desktop applications`
3. Add redirect URI:
   - `https://login.microsoftonline.com/common/oauth2/nativeclient`
4. In `Advanced settings`, set `Allow public client flows` to `Yes`

### 3. Add Microsoft Graph delegated permissions

In your app registration:

1. Go to `API permissions -> Add a permission -> Microsoft Graph -> Delegated permissions`
2. Add:
   - `Calendars.Read`
   - `User.Read`
3. Grant consent:
   - Use **Grant admin consent** if your tenant requires it
   - Otherwise user consent will occur during first sign-in

### 4. Python dependencies

Install required packages:

```bash
pip install msal requests
```

## Configuration

Set your app client ID as an environment variable:

```bash
export AZURE_CLIENT_ID=<your-client-id>
```

Optional: override authority endpoint (default is `common`):

```bash
export AZURE_AUTHORITY=https://login.microsoftonline.com/consumers
```

Use `consumers` when your app registration is configured for Microsoft personal accounts only.

You can also hard-code `CLIENT_ID` in `test_graph_calendar.py`, but environment variable usage is recommended.

## Run

From repository root:

```bash
python scripts/test_graph_calendar.py
```

On first run, the script displays a device-code message. Complete sign-in at:

- `https://aka.ms/devicelogin`

After successful auth, the script calls Graph and prints the response.

## Expected success output

You should see:

- `HTTP 200 OK`
- A JSON body containing `value` with calendar event items (possibly empty)
- A summary line with event count

## Common issues

- `Could not obtain token`:
  - Confirm `AZURE_CLIENT_ID` is correct
  - Verify app supports the account type you are signing in with
- `AADSTS9002346` on device flow creation:
   - This means the app is configured for Microsoft Account users only
   - The script now auto-retries with `/consumers` authority
   - You can also explicitly set:
      - `AZURE_AUTHORITY=https://login.microsoftonline.com/consumers`
- `AADSTS70002` on device flow creation:
   - The app is not configured as a public/mobile client for device code flow
   - In app `Authentication (Preview)` (or `Authentication`), add `Mobile and desktop applications`
   - Add redirect URI `https://login.microsoftonline.com/common/oauth2/nativeclient`
   - Set `Allow public client flows` to `Yes`
- `HTTP 401/403`:
  - Confirm delegated permissions include `Calendars.Read`
  - Ensure consent has been granted
- Empty `value` array:
  - Authentication and Graph access still succeeded; it may simply mean no events in the selected window

## Files in this folder

- `test_graph_calendar.py`: script implementation
- `README.md`: setup and usage instructions
