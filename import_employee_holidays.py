"""
import_employee_holidays.py
───────────────────────────
Reads an HR Excel/CSV file containing employee planned & unplanned holiday
requests and merges them into employee_leaves.csv.

Supported column name variants (case-insensitive):
  Employee Name : 'employee name', 'name', 'emp name', 'employee'
  From Date     : 'from date', 'start date', 'from', 'date from', 'leave from'
  To Date       : 'to date', 'end date', 'to', 'date to', 'leave to'
  Leave Type    : 'leave type', 'type', 'leave category', 'category'
  Status        : 'status', 'approval status', 'state'

Only 'Approved' status rows are imported (if Status column exists).
Duplicate records (same employee + date range) are skipped.
"""

import pandas as pd
import os
import sys
from datetime import date

LEAVE_FILE = 'employee_leaves.csv'
LEAVE_COLS = ['Employee Name', 'Start Date', 'End Date', 'Leave Type',
              'Half Day', 'Description', 'Submitted On']


# ── Column auto-detector ─────────────────────────────────────────────────────
def _find_col(df_cols, candidates):
    """Return first matching column name from candidates (case-insensitive)."""
    lower_map = {c.lower().strip(): c for c in df_cols}
    for c in candidates:
        if c.lower() in lower_map:
            return lower_map[c.lower()]
    return None


def load_existing_leaves():
    if os.path.exists(LEAVE_FILE):
        df = pd.read_csv(LEAVE_FILE)
        for col in LEAVE_COLS:
            if col not in df.columns:
                df[col] = ''
        return df
    return pd.DataFrame(columns=LEAVE_COLS)


def import_holiday_excel(file_path, status_filter=True):
    """
    Read the HR Excel/CSV, parse, deduplicate, and merge into employee_leaves.csv.

    Parameters
    ----------
    file_path     : str  — absolute path to the Excel/CSV file
    status_filter : bool — if True, only import rows with Status == 'Approved'
                          (or 'Approve') variants; False imports all rows.

    Returns
    -------
    (added, skipped) counts
    """
    print(f"[Import] Reading: {file_path}")

    # ── Read file ─────────────────────────────────────────────────────────────
    try:
        if file_path.lower().endswith(('.xlsx', '.xls')):
            # Try reading; if multiple sheets, read all and concat
            xl = pd.ExcelFile(file_path, engine='openpyxl')
            frames = []
            for sheet in xl.sheet_names:
                try:
                    sh = xl.parse(sheet, header=0)
                    if not sh.empty:
                        frames.append(sh)
                except Exception:
                    pass
            if not frames:
                print("[Import] ERROR: No readable sheets found.")
                return 0, 0
            raw = pd.concat(frames, ignore_index=True)
        else:
            raw = pd.read_csv(file_path)
    except Exception as e:
        print(f"[Import] ERROR reading file: {e}")
        return 0, 0

    print(f"[Import] Rows read: {len(raw)}  |  Columns: {list(raw.columns)}")

    # ── Map columns ───────────────────────────────────────────────────────────
    col_name   = _find_col(raw.columns, ['employee name', 'name', 'emp name', 'employee name', 'employeename'])
    col_from   = _find_col(raw.columns, ['from date', 'start date', 'from', 'date from', 'leave from', 'fromdate'])
    col_to     = _find_col(raw.columns, ['to date', 'end date', 'to', 'date to', 'leave to', 'todate'])
    col_type   = _find_col(raw.columns, ['leave type', 'type', 'leave category', 'category', 'leavetype'])
    col_status = _find_col(raw.columns, ['status', 'approval status', 'state', 'approval'])

    if not col_name:
        print("[Import] ERROR: Could not find 'Employee Name' column.")
        print(f"         Available columns: {list(raw.columns)}")
        return 0, 0
    if not col_from or not col_to:
        print("[Import] ERROR: Could not find 'From Date' / 'To Date' columns.")
        print(f"         Available columns: {list(raw.columns)}")
        return 0, 0

    # ── Filter by status ──────────────────────────────────────────────────────
    if status_filter and col_status:
        approved_keywords = ['approved', 'approve', 'accepted', 'confirmed']
        mask = raw[col_status].astype(str).str.strip().str.lower().apply(
            lambda s: any(kw in s for kw in approved_keywords)
        )
        before = len(raw)
        raw = raw[mask].copy()
        print(f"[Import] Status filter: {before} → {len(raw)} approved rows kept.")
    else:
        print("[Import] No status filter applied — importing all rows.")

    if raw.empty:
        print("[Import] No rows to import after filtering.")
        return 0, 0

    # ── Build standardised records ────────────────────────────────────────────
    existing = load_existing_leaves()
    # Create a dedup key from existing data
    existing_keys = set(
        zip(existing['Employee Name'].astype(str).str.strip().str.lower(),
            existing['Start Date'].astype(str),
            existing['End Date'].astype(str))
    )

    new_rows = []
    skipped  = 0

    for _, row in raw.iterrows():
        try:
            emp_name  = str(row[col_name]).strip()
            from_date = pd.to_datetime(row[col_from], dayfirst=False, errors='coerce')
            to_date   = pd.to_datetime(row[col_to],   dayfirst=False, errors='coerce')

            if pd.isna(from_date) or pd.isna(to_date) or not emp_name or emp_name.lower() in ('nan', ''):
                skipped += 1
                continue

            start_str = from_date.strftime('%Y-%m-%d')
            end_str   = to_date.strftime('%Y-%m-%d')
            leave_type = str(row[col_type]).strip() if col_type else 'Personal Leave'

            # Map company leave types to standard types
            lt_lower = leave_type.lower()
            if 'unplanned' in lt_lower or 'sick' in lt_lower or 'medical' in lt_lower:
                std_type = 'Sick Leave'
            elif 'planned' in lt_lower or 'annual' in lt_lower or 'earned' in lt_lower:
                std_type = 'Annual Leave'
            elif 'maternity' in lt_lower or 'paternity' in lt_lower:
                std_type = 'Maternity / Paternity'
            elif 'compensat' in lt_lower or 'comp off' in lt_lower:
                std_type = 'Compensatory Off'
            else:
                std_type = 'Personal Leave'

            # Deduplication check
            key = (emp_name.lower(), start_str, end_str)
            if key in existing_keys:
                skipped += 1
                continue

            new_rows.append({
                'Employee Name': emp_name,
                'Start Date':    start_str,
                'End Date':      end_str,
                'Leave Type':    std_type,
                'Half Day':      'No',
                'Description':   f'Imported: {leave_type}',
                'Submitted On':  str(date.today()),
            })
            existing_keys.add(key)

        except Exception as ex:
            print(f"[Import] Skipping row due to error: {ex}")
            skipped += 1

    # ── Merge & Save ──────────────────────────────────────────────────────────
    added = len(new_rows)
    if added > 0:
        new_df  = pd.DataFrame(new_rows)
        combined = pd.concat([existing, new_df], ignore_index=True)
        combined.to_csv(LEAVE_FILE, index=False)
        print(f"[Import] ✅ Added {added} new record(s) to {LEAVE_FILE}")
    else:
        print(f"[Import] No new records to add (all duplicates or filtered out).")

    print(f"[Import] Skipped {skipped} row(s).")
    return added, skipped


# ── CLI entry point ───────────────────────────────────────────────────────────
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python import_employee_holidays.py <path_to_excel_file>")
        print("       python import_employee_holidays.py <path_to_excel_file> --all")
        sys.exit(1)

    path = sys.argv[1]
    filter_status = '--all' not in sys.argv

    if not os.path.exists(path):
        print(f"ERROR: File not found: {path}")
        sys.exit(1)

    added, skipped = import_holiday_excel(path, status_filter=filter_status)
    print(f"\nDone. Added: {added}  |  Skipped: {skipped}")
