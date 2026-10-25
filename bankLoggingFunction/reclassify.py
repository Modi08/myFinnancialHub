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
    
    # Align column positions
    tx_idx = headers.index("Transaction ID") if "Transaction ID" in headers else 0
    party_idx = headers.index("Party") if "Party" in headers else 2
    amount_idx = headers.index("Amount") if "Amount" in headers else 3
    cat_idx = headers.index("Category") if "Category" in headers else 5
    note_idx = headers.index("Asset Note") if "Asset Note" in headers else 6

    updated_count = 0
    duplicates_removed = 0
    
    seen_ids = set()
    cleaned_data = [headers] # Build a fresh list to avoid list-modification bugs

    for row in data[1:]:
        # Pad row if missing trailing columns
        while len(row) <= max(note_idx, tx_idx):
            row.append("")
            
        tx_id = row[tx_idx]
        
        # 1. Duplicate Check: Skip if we've already logged this Transaction ID
        if tx_id and tx_id in seen_ids:
            duplicates_removed += 1
            continue
            
        if tx_id:
            seen_ids.add(tx_id)

        party = row[party_idx]
        try:
            amount_val = float(str(row[amount_idx]).replace(",", ".").replace("€", "").strip())
        except ValueError:
            amount_val = 0.0

        is_credit = amount_val > 0
        raw_amount = abs(amount_val)

        new_cat, _, new_note = classify_transaction(party, raw_amount, is_credit)

        # 2. Filtering: Drop rows explicitly returning None from rules.py
        if new_cat is None:
            continue

        # 3. Categorization Update
        if row[cat_idx] != new_cat or row[note_idx] != new_note:
            row[cat_idx] = new_cat
            row[note_idx] = new_note
            updated_count += 1
            
        cleaned_data.append(row)

    # 4. Wipe the sheet clean before writing to ensure deleted rows disappear
    sheet.clear()
    
    # 5. Overwrite the sheet with the cleaned matrix in a single batch request
    sheet.update(values=cleaned_data, range_name="A1")
    
    print(f"Reclassification complete. Processed {len(data) - 1} rows.")
    print(f"Removed {duplicates_removed} duplicates.")
    print(f"Updated {updated_count} entries.")

if __name__ == "__main__":
    target_sheet = sys.argv[1] if len(sys.argv) > 1 else None
    reclassify_sheet(target_sheet)