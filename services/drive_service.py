from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

from config import Config


class DriveService:
    """Thin wrapper around the Google Drive API for a shared folder.

    Authenticates as the user via an Installed App OAuth flow (client secret
    JSON + locally saved token), so uploads use the user's own storage quota.
    All methods fail gracefully (print a message, return a falsy value) so the
    application keeps working when Drive is not configured or unreachable.
    """

    SCOPES = ["https://www.googleapis.com/auth/drive"]

    def __init__(self, client_secrets: Path | None = None, folder_id: str | None = None) -> None:
        self.client_secrets = client_secrets or self._resolve_client_secrets()
        self.folder_id = folder_id or Config.GOOGLE_DRIVE_FOLDER_ID
        self._service = None
        if self.client_secrets is not None and self.client_secrets.exists() and self.folder_id:
            try:
                creds = self._load_or_authorize()
                self._service = build("drive", "v3", credentials=creds, cache_discovery=False)
            except Exception as exc:
                print(f"\n⚠ No se pudo inicializar Google Drive: {exc}")
                self._service = None

    @property
    def enabled(self) -> bool:
        """True when the Drive API service was built successfully."""
        return self._service is not None

    def _resolve_client_secrets(self) -> Path | None:
        raw = Config.GOOGLE_DRIVE_CLIENT_SECRETS
        if not raw:
            return None
        path = Path(raw)
        return path if path.is_absolute() else Path.cwd() / path

    def _token_path(self) -> Path:
        raw = Config.GOOGLE_DRIVE_TOKEN_PATH
        path = Path(raw)
        return path if path.is_absolute() else Path.cwd() / path

    def _load_or_authorize(self) -> Credentials:
        """Load the saved token or run the OAuth flow and persist it."""
        token_path = self._token_path()
        creds = None
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), self.SCOPES)
        if creds is not None and creds.valid:
            return creds
        if creds is not None and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                token_path.write_text(creds.to_json(), encoding="utf-8")
                return creds
            except Exception:
                pass
        creds = self._run_auth_flow()
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json(), encoding="utf-8")
        print(f"\n✓ Token de Google Drive guardado en {token_path}")
        return creds

    def _run_auth_flow(self) -> Credentials:
        """Run the Installed App OAuth flow (browser, or console when headless)."""
        print("\n🔑 Autorizando Google Drive. Se abrirá el navegador con tu cuenta...")
        flow = InstalledAppFlow.from_client_secrets_file(
            str(self.client_secrets), scopes=self.SCOPES
        )
        try:
            return flow.run_local_server(port=0, prompt="consent")
        except Exception:
            return flow.run_console()

    def upload(self, path: Path) -> bool:
        """Upload a file to the shared folder, overwriting it by name if present."""
        if not self.enabled:
            print("ℹ Google Drive no configurado. Archivo guardado solo localmente.")
            return False
        name = path.name
        try:
            media = MediaFileUpload(str(path), mimetype=self._mimetype(path))
            file_id = self._find_file_id(name)
            if file_id is None:
                body = {"name": name, "parents": [self.folder_id]}
                self._service.files().create(body=body, media_body=media, fields="id").execute()
                print(f"\n✓ Subido {name} a Google Drive.")
            else:
                self._service.files().update(fileId=file_id, media_body=media).execute()
                print(f"\n✓ Actualizado {name} en Google Drive.")
            return True
        except HttpError as exc:
            print(f"\n⚠ Error de Google Drive al subir {name}: {exc}")
            return False
        except Exception as exc:
            print(f"\n⚠ Error subiendo {name} a Google Drive: {exc}")
            return False

    def download(self, remote_name: str, dest: Path) -> bool:
        """Download a file by name from the shared folder to a local path."""
        if not self.enabled:
            print("ℹ Google Drive no configurado.")
            return False
        try:
            file_id = self._find_file_id(remote_name)
            if file_id is None:
                print(f"\n⚠ No se encontró {remote_name} en Google Drive.")
                return False
            dest.parent.mkdir(parents=True, exist_ok=True)
            request = self._service.files().get_media(fileId=file_id)
            with open(dest, "wb") as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    _, done = downloader.next_chunk()
            print(f"\n✓ Descargado {remote_name} desde Google Drive a {dest}.")
            return True
        except HttpError as exc:
            print(f"\n⚠ Error de Google Drive al descargar {remote_name}: {exc}")
            return False
        except Exception as exc:
            print(f"\n⚠ Error descargando {remote_name} desde Google Drive: {exc}")
            return False

    def delete(self, remote_name: str) -> bool:
        """Delete a file by name from the shared folder."""
        if not self.enabled:
            print("ℹ Google Drive no configurado.")
            return False
        try:
            file_id = self._find_file_id(remote_name)
            if file_id is None:
                print(f"\n⚠ No se encontró {remote_name} en Google Drive.")
                return False
            self._service.files().delete(fileId=file_id).execute()
            print(f"\n✓ Eliminado {remote_name} de Google Drive.")
            return True
        except HttpError as exc:
            print(f"\n⚠ Error de Google Drive al eliminar {remote_name}: {exc}")
            return False
        except Exception as exc:
            print(f"\n⚠ Error eliminando {remote_name} de Google Drive: {exc}")
            return False

    def list_files(self) -> list[str]:
        """Return the names of files in the shared folder."""
        if not self.enabled:
            return []
        try:
            query = f"'{self.folder_id}' in parents and trashed = false"
            result = (
                self._service.files()
                .list(q=query, fields="files(id, name)", pageSize=1000)
                .execute()
            )
            return [item.get("name") for item in result.get("files") or []]
        except Exception as exc:
            print(f"\n⚠ Error listando archivos de Google Drive: {exc}")
            return []

    def _find_file_id(self, name: str) -> str | None:
        query = (
            f"'{self.folder_id}' in parents and name = '{name}' "
            "and trashed = false"
        )
        result = (
            self._service.files()
            .list(q=query, fields="files(id, name)", pageSize=1)
            .execute()
        )
        files = result.get("files") or []
        return files[0]["id"] if files else None

    @staticmethod
    def _mimetype(path: Path) -> str:
        if path.suffix.lower() == ".xlsx":
            return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        return "text/csv"
