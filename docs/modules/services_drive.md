# `services/drive_service.py` — DriveService

## Purpose

The **only** Google Drive integration in the project. It shares the `match_ids_*.csv` between the home machine and the Tecsup (institute) machine. It authenticates as the user via an Installed App OAuth flow (client secret JSON + locally saved token), so uploads use the user's own storage quota. Excel/chat/kill exports, the rampage ranking, the replay JSONs, and `parse_jobs_*.csv` stay local.

## Public functions

### `class DriveService`

#### `__init__(client_secrets: Path | None = None, folder_id: str | None = None)`

Builds the Drive API v3 service from the OAuth client secret JSON and the shared folder ID. Falls back to `Config.GOOGLE_DRIVE_CLIENT_SECRETS` and `Config.GOOGLE_DRIVE_FOLDER_ID`. Loads the saved token (or runs the interactive OAuth flow on first use) and stores it at `Config.GOOGLE_DRIVE_TOKEN_PATH`. When the client secrets file is missing or the service cannot be built, it prints a Spanish warning and disables itself.

#### `enabled -> bool`

True when the Drive API service was built successfully.

#### `upload(path: Path) -> bool`

Uploads a file to the shared folder, creating or overwriting it by name. Returns `False` gracefully when Drive is disabled or the request fails.

#### `download(remote_name: str, dest: Path) -> bool`

Downloads a file by name from the shared folder to a local path.

#### `delete(remote_name: str) -> bool`

Deletes a file by name from the shared folder.

#### `list_files() -> list[str]`

Returns the names of the non-trashed files in the shared folder.

## Internal flow

- `_find_file_id(name)` — looks up a file ID by exact name within the folder.
- `_resolve_client_secrets()` — resolves `Config.GOOGLE_DRIVE_CLIENT_SECRETS` relative to the working directory.
- `_token_path()` — resolves `Config.GOOGLE_DRIVE_TOKEN_PATH` relative to the working directory.
- `_load_or_authorize()` — loads the saved token, refreshes it when expired, or runs the OAuth flow and persists the token.
- `_run_auth_flow()` — `InstalledAppFlow.run_local_server()` (browser); falls back to `run_console()` when there is no display.
- `_mimetype(path)` — returns `text/csv` or the xlsx mimetype.

## Dependencies

- `google_auth_oauthlib.flow.InstalledAppFlow` — interactive user OAuth flow.
- `google.oauth2.credentials.Credentials` — token loading/refreshing.
- `google.auth.transport.requests.Request` — token refresh.
- `googleapiclient.discovery.build` — Drive API v3 service.
- `googleapiclient.http` — `MediaFileUpload`, `MediaIoBaseDownload`.
- `config.Config` — client secrets path, token path and folder ID.

## Inputs

- Environment: `GOOGLE_DRIVE_CLIENT_SECRETS`, `GOOGLE_DRIVE_TOKEN_PATH`, `GOOGLE_DRIVE_FOLDER_ID`.
- On first use per machine: a browser authorization with the user's Google account.

## Outputs

- Files uploaded/downloaded/deleted in the shared Drive folder.
- `data/drive_token.json` (gitignored) written after the first authorization.
- Spanish console messages on success and failure.

## Usage example

```python
from services.drive_service import DriveService

drive = DriveService()
if drive.enabled:
    names = drive.list_files()
    drive.upload(Path("exports/match_ids_2026-08-16.csv"))
    drive.download("match_ids_2026-08-16.csv", Path("exports/match_ids_2026-08-16.csv"))
    drive.delete("match_ids_2026-08-16.csv")
```

## Notes

- Authenticates as the user, so the folder must be owned by (or shared with) that account; no `supportsAllDrives` logic is needed.
- Publish the OAuth app ("In production") so the refresh token does not expire every ~7 days.
- Every method degrades gracefully (prints a Spanish message, returns a falsy value) so the application keeps working without Drive.
- Only `match_ids_*.csv` should ever be shared through this service.
