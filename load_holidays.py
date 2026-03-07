"""
load_holidays.py
────────────────
Shared utility: load holiday data from holidays.csv OR holidays.xlsx.

Supported formats — two modes auto-detected:

MODE 1 — Single Date (existing format):
  Date, Description, Type
  2026-01-01, New Year, Mandatory

MODE 2 — Date Range (new format for long leaves/shutdowns):
  Start Date, End Date, Description, Type
  2026-03-01, 2026-04-30, Summer Break, Mandatory

Both modes can exist in the SAME file together.

Type column values:
  'Mandatory' — marks IsHoliday = True
  'Optional'  — marks IsOptionalHoliday = True
  (default: Mandatory if column missing)

Returns:
  mandatory : set of datetime.date
  optional  : set of datetime.date
"""

import os
import pandas as pd
from datetime import timedelta


def _expand_rows(df):
    """
    Expand each row into individual dates.
    Supports both single-date and date-range rows.
    Returns a list of (date, type_str) tuples.
    """
    cols = [c.lower().strip() for c in df.columns]
    df.columns = cols

    has_start = 'start date' in cols or 'start_date' in cols
    has_end   = 'end date'   in cols or 'end_date'   in cols
    has_date  = 'date' in cols
    has_type  = 'type' in cols

    start_col = next((c for c in cols if c in ('start date', 'start_date')), None)
    end_col   = next((c for c in cols if c in ('end date',   'end_date')),   None)
    date_col  = next((c for c in cols if c == 'date'), None)
    type_col  = next((c for c in cols if c == 'type'), None)

    results = []

    for _, row in df.iterrows():
        htype = str(row[type_col]).strip().lower() if type_col else 'mandatory'

        # ── Date Range row ─────────────────────────────────────────────────────
        if has_start and has_end and pd.notna(row.get(start_col)) and pd.notna(row.get(end_col)):
            try:
                start = pd.to_datetime(row[start_col]).date()
                end   = pd.to_datetime(row[end_col]).date()
                current = start
                while current <= end:
                    results.append((current, htype))
                    current += timedelta(days=1)
            except Exception:
                pass

        # ── Single Date row ────────────────────────────────────────────────────
        elif has_date and pd.notna(row.get(date_col)):
            try:
                d = pd.to_datetime(row[date_col]).date()
                results.append((d, htype))
            except Exception:
                pass

    return results


def load_holidays(csv_path='holidays.csv', xlsx_path='holidays.xlsx'):
    """
    Load holidays from CSV or Excel file.
    CSV takes priority if both exist.
    """
    df = None

    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path)
            print(f"[Holidays] Loaded from {csv_path}")
        except Exception as e:
            print(f"[Holidays] Error reading {csv_path}: {e}")

    if df is None and os.path.exists(xlsx_path):
        try:
            df = pd.read_excel(xlsx_path, engine='openpyxl')
            print(f"[Holidays] Loaded from {xlsx_path}")
        except Exception as e:
            print(f"[Holidays] Error reading {xlsx_path}: {e}")

    if df is None:
        print(f"[Holidays] No holiday file found. Proceeding without holidays.")
        return set(), set()

    expanded = _expand_rows(df)

    mandatory = {d for d, t in expanded if t != 'optional'}
    optional  = {d for d, t in expanded if t == 'optional'}

    print(f"[Holidays] {len(mandatory)} Mandatory, {len(optional)} Optional holiday days loaded.")
    return mandatory, optional
