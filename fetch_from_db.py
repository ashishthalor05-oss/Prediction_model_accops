"""
fetch_from_db.py — Fetch raw log data from SQL Server Express into log_data.csv
────────────────────────────────────────────────────────────────────────────────
Usage:
    python fetch_from_db.py --server ".\\SQLEXPRESS" --database "HyWorksDB"
                             --table "Logs" --auth windows
                             --from "2025-11-01" --to "2026-03-02"

    # SQL Auth:
    python fetch_from_db.py --server ".\\SQLEXPRESS" --database "HyWorksDB"
                             --table "Logs" --auth sql --user sa --password ****
                             --from "2025-11-01" --to "2026-03-02"

    # Test connection only (no data fetch):
    python fetch_from_db.py --server ".\\SQLEXPRESS" --database "HyWorksDB"
                             --auth windows --test
"""

import argparse
import sys
import os

# Force UTF-8 output so special chars don't crash on Windows cp1252 subprocess pipes
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ── Try importing pyodbc ───────────────────────────────────────────────────────
try:
    import pyodbc
except ImportError:
    print("ERROR: pyodbc is not installed. Run:  pip install pyodbc")
    sys.exit(1)

import pandas as pd

# ── ODBC Driver detection ──────────────────────────────────────────────────────
PREFERRED_DRIVERS = [
    'ODBC Driver 18 for SQL Server',
    'ODBC Driver 17 for SQL Server',
    'ODBC Driver 13 for SQL Server',
    'SQL Server Native Client 11.0',
    'SQL Server',
]

def get_driver():
    available = pyodbc.drivers()
    for d in PREFERRED_DRIVERS:
        if d in available:
            return d
    # Fallback: pick any SQL Server driver
    sql_drivers = [d for d in available if 'SQL Server' in d]
    if sql_drivers:
        return sql_drivers[0]
    return None


def build_connection_string(server, database, auth, user=None, password=None):
    driver = get_driver()
    if not driver:
        raise RuntimeError(
            "No SQL Server ODBC driver found on this machine.\n"
            "Install 'ODBC Driver 17 for SQL Server' from Microsoft."
        )
    if auth == 'windows':
        return (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            "Trusted_Connection=yes;"
            "TrustServerCertificate=yes;"
        )
    else:
        if not user or not password:
            raise ValueError("SQL Auth requires --user and --password.")
        return (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={user};"
            f"PWD={password};"
            "TrustServerCertificate=yes;"
        )


def test_connection(conn_str):
    """Test connection only. Prints SUCCESS or ERROR."""
    try:
        conn = pyodbc.connect(conn_str, timeout=10)
        conn.close()
        print("SUCCESS: Connected to SQL Server successfully.")
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


# ── Timestamp column auto-detection ───────────────────────────────────────────
TIMESTAMP_CANDIDATES = ['Timestamp', 'LogTime', 'EventTime', 'CreatedAt',
                         'DateTime', 'Date', 'time', 'log_time']


def format_table(table):
    """
    Safely quote a table name for SQL Server.
    Handles both plain names ('Log') and schema-prefixed names ('dbo.Log').
    Returns e.g. [dbo].[Log]  or  [Log]
    """
    parts = table.split('.')
    return '.'.join(f'[{p.strip("[]").strip()}]' for p in parts)


def detect_timestamp_column(cursor, table):
    tbl = format_table(table)
    cursor.execute(f"SELECT TOP 0 * FROM {tbl}")
    cols = [desc[0] for desc in cursor.description]
    for candidate in TIMESTAMP_CANDIDATES:
        for col in cols:
            if col.lower() == candidate.lower():
                return col
    return None


def fetch_data(conn_str, table, date_from, date_to, output_file='log_data.csv'):
    print("INFO: Connecting to SQL Server...")
    try:
        conn = pyodbc.connect(conn_str, timeout=15)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    cursor = conn.cursor()

    # Format table name safely (handles schema.table like dbo.Log)
    tbl = format_table(table)

    # Detect timestamp column
    ts_col = detect_timestamp_column(cursor, table)

    if ts_col:
        query = f"""
            SELECT *
            FROM {tbl}
            WHERE [{ts_col}] >= ? AND [{ts_col}] < DATEADD(day, 1, ?)
            ORDER BY [{ts_col}]
        """
        params = (date_from, date_to)
        print(f"INFO: Querying table {tbl} on column [{ts_col}]"
              f" from {date_from} to {date_to}...")
    else:
        # No timestamp column found -- fetch everything
        query  = f"SELECT * FROM {tbl}"
        params = ()
        print(f"WARNING: No timestamp column detected. Fetching ALL rows from {tbl}.")

    try:
        cursor.execute(query, params)
    except Exception as e:
        print(f"ERROR: Query failed — {e}")
        conn.close()
        sys.exit(1)

    # ── Stream rows in chunks directly to CSV (avoids memory crash) ──────────
    CHUNK    = 10_000
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), output_file)
    total    = 0

    print(f"INFO: Streaming rows to {output_file} in chunks of {CHUNK:,}...")

    try:
        import csv
        with open(out_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # No header row — log_data.csv is a headerless raw log file
            while True:
                rows = cursor.fetchmany(CHUNK)
                if not rows:
                    break
                writer.writerows(rows)
                total += len(rows)
                print(f"INFO: {total:,} rows written...")
    except Exception as e:
        print(f"ERROR: Writing CSV failed — {e}")
        conn.close()
        sys.exit(1)

    conn.close()

    if total == 0:
        print("WARNING: Query returned 0 rows. Check date range or table name.")
        sys.exit(0)

    print(f"SUCCESS: {total:,} rows fetched -> saved to {output_file}")



# ── CLI entry ──────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description='Fetch log data from SQL Server Express.')
    parser.add_argument('--server',   required=True,  help='SQL Server instance, e.g. .\\SQLEXPRESS')
    parser.add_argument('--database', required=True,  help='Database name')
    parser.add_argument('--table',    default='Logs', help='Table name (default: Logs)')
    parser.add_argument('--auth',     default='windows', choices=['windows', 'sql'],
                        help='Authentication type')
    parser.add_argument('--user',     default='',     help='SQL Auth username')
    parser.add_argument('--password', default='',     help='SQL Auth password')
    parser.add_argument('--from',     dest='date_from', default='',
                        help='Start date YYYY-MM-DD')
    parser.add_argument('--to',       dest='date_to',   default='',
                        help='End date YYYY-MM-DD')
    parser.add_argument('--output',   default='log_data.csv',
                        help='Output CSV filename (default: log_data.csv)')
    parser.add_argument('--test',     action='store_true',
                        help='Test connection only, do not fetch data')
    args = parser.parse_args()

    try:
        conn_str = build_connection_string(
            args.server, args.database, args.auth, args.user, args.password
        )
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    if args.test:
        test_connection(conn_str)
        return

    if not args.date_from or not args.date_to:
        print("ERROR: --from and --to dates are required for data fetch.")
        sys.exit(1)

    fetch_data(conn_str, args.table, args.date_from, args.date_to, args.output)


if __name__ == '__main__':
    main()
