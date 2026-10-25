import os
import sys
from rules import classify_transaction
from sheetClient import get_sheet

DEFAULT_SPREADSHEET_ID = "1aXMltRbpBeBOJjXJCwlKIMweqg54CsCPVwtT8HrH5_Q"

def reclassify_sheet(spreadsheet_id: str = None):
    sheet = get_sheet(spreadsheet_id or DEFAULT_SPREADSHEET_ID)
    data = sheet.get_all_values()

    if not data or len(data) < 2:
        print("Sheet has no transaction rows to classify.")
        return

    headers = data[0]
    expected_headers = ["Transaction ID", "Date", "Party", "Amount", "Currency", "Category", "Asset Note"]

    # Align column positions
    party_idx = headers.index("Party") if "Party" in headers else 2
    amount_idx = headers.index("Amount") if "Amount" in headers else 3
    cat_idx = headers.index("Category") if "Category" in headers else 5
    note_idx = headers.index("Asset Note") if "Asset Note" in headers else 6

    updated_count = 0

    for row in data[1:]:
        # Pad row if missing trailing columns
        while len(row) <= note_idx:
            row.append("")

        party = row[party_idx]
        try:
            amount_val = float(str(row[amount_idx]).replace(",", ".").replace("€", "").strip())
        except ValueError:
            amount_val = 0.0

        is_credit = amount_val > 0
        raw_amount = abs(amount_val)

        new_cat, _, new_note = classify_transaction(party, raw_amount, is_credit)
        if new_cat == None:
            data.remove(row)
        if row[cat_idx] != new_cat or row[note_idx] != new_note:
            row[cat_idx] = new_cat
            row[note_idx] = new_note
            updated_count += 1

    # Overwrite the sheet with the reclassified matrix in a single batch request
    sheet.update(values=data, range_name="A1")
    print(f"Reclassification complete. Processed {len(data) - 1} rows. Updated {updated_count} entries.")

if __name__ == "__main__":
    target_sheet = sys.argv[1] if len(sys.argv) > 1 else None
    reclassify_sheet(target_sheet)