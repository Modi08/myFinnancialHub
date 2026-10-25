import os
from pathlib import Path
import gspread
import google.auth
from google.oauth2 import service_account

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_sheet(spreadsheet_id: str = None):
    """Initializes Google Sheets client using local key if present, otherwise Cloud Default Credentials."""
    target_id = spreadsheet_id or os.environ.get("SPREADSHEET_ID")
    if not target_id:
        raise ValueError("Missing SPREADSHEET_ID. Set it in environment variables or pass as an argument.")

    local_key_file = Path(__file__).parent / "local_key.json"

    # In Google Cloud, K_SERVICE is always set; locally, use local_key.json if it exists
    if not os.environ.get("K_SERVICE") and local_key_file.exists():
        creds = service_account.Credentials.from_service_account_file(
            str(local_key_file), scopes=SCOPES
        )
    else:
        creds, _ = google.auth.default(scopes=SCOPES)

    gc = gspread.authorize(creds)
    return gc.open_by_key(target_id).sheet1