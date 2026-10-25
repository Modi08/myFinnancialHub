import os
import time
import jwt
import requests
import traceback
import functions_framework
from datetime import datetime, timedelta

from rules import classify_transaction
from sheetClient import get_sheet

APP_ID = os.environ.get("EB_APP_ID")
ACCOUNT_ID = os.environ.get("EB_ACCOUNT_ID")
PEM_KEY = os.environ.get("EB_PRIVATE_KEY", "").replace("\\n", "\n")

def get_jwt():
    now = int(time.time())
    payload = {
        "iss": "enablebanking.com",
        "aud": "api.enablebanking.com",
        "iat": now,
        "exp": now + 600
    }
    return jwt.encode(payload, PEM_KEY.encode("utf-8"), algorithm="RS256", headers={"kid": APP_ID})

@functions_framework.http
def sync_revolut(request):
    try:
        # 1. Fetch recent transactions (last 3 days to capture clearing delays)
        token = get_jwt()
        date_from = (datetime.utcnow() - timedelta(days=3)).strftime("%Y-%m-%d")
        url = f"https://api.enablebanking.com/accounts/{ACCOUNT_ID}/transactions?date_from={date_from}"
        res = requests.get(url, headers={"Authorization": f"Bearer {token}"})
        res.raise_for_status()
        transactions = res.json().get("transactions", [])

        # 2. Access Google Sheet
        sheet = get_sheet()
        existing_ids = set(sheet.col_values(1))
        if not existing_ids:
            headers = ["Transaction ID", "Date", "Party", "Amount", "Currency", "Category", "Asset Note"]
            sheet.append_row(headers)
            existing_ids.add("Transaction ID")

        # 3. Classify and collect new entries
        new_rows = []
        for tx in transactions:
            tx_id = tx.get("entry_reference") or tx.get("transaction_id")
            if tx_id and tx_id not in existing_ids:
                date = tx.get("booking_date") or tx.get("value_date", "")
                raw_amount = float(tx.get("transaction_amount", {}).get("amount", 0))
                currency = tx.get("transaction_amount", {}).get("currency", "EUR")
                is_credit = tx.get("credit_debit_indicator") == "CRDT"

                remittance = tx.get("remittance_information", [""])
                party = (
                    tx.get("creditor", {}).get("name")
                    or tx.get("debtor", {}).get("name")
                    or (remittance[0] if remittance else "Unknown")
                )

                category, signed_amount, note = classify_transaction(party, raw_amount, is_credit)
                new_rows.append([tx_id, date, party, signed_amount, currency, category, note])
                existing_ids.add(tx_id)

        if new_rows:
            sheet.append_rows(new_rows, value_input_option="USER_ENTERED")
            return f"Synced {len(new_rows)} transactions.", 200

        return "No new transactions found.", 200

    except Exception as e:
        print(f"CRITICAL ERROR REVEALED: {traceback.format_exc()}")
        return f"Sync failed: {str(e)}", 500