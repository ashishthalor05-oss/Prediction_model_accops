"""Final cleanup: keep only known HR column names, drop all junk."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pandas as pd

LEAVE_FILE = 'employee_leaves.csv'

# The known real columns from HR leave export
HR_COLS = [
    'Employee Number', 'Employee Name', 'UserId', 'Job Title',
    'Business Unit', 'Department', 'Sub Department', 'Location',
    'Cost Center', 'Reporting Manager', 'Leave Types',
    'From Date', 'From Session', 'To Date', 'To Session',
    'Total Duration', 'Unit', 'Requested On', 'Requested By',
    'Note', 'Reason', 'Status', 'Last Action Taken by',
    'Last Action Taken on', 'Next Approver'
]
HEADER_KEYS = {'userid', 'employee name', 'from date', 'status'}

raw = pd.read_csv(LEAVE_FILE, header=None, encoding='utf-8', on_bad_lines='skip')

header_row = None
for i, row in raw.iterrows():
    vals = {str(v).strip().lower() for v in row.values}
    if HEADER_KEYS.issubset(vals):
        header_row = i
        print(f'Header row at index: {i}')
        break

if header_row is None:
    print('ERROR: Could not find header row'); sys.exit(1)

df = pd.read_csv(LEAVE_FILE, header=header_row, encoding='utf-8', on_bad_lines='skip')
df.columns = df.columns.str.strip()

# Keep ONLY known HR columns that exist in the file
keep_cols = [c for c in HR_COLS if c in df.columns]
df = df[keep_cols]
print(f'Keeping {len(keep_cols)} HR columns: {keep_cols}')

# Drop repeat-header and empty UserId rows
df = df[df['UserId'].astype(str).str.strip().str.lower() != 'userid']
df = df[df['UserId'].notna() & (df['UserId'].astype(str).str.strip() != 'nan')]
df = df.reset_index(drop=True)
print(f'Data rows: {len(df)}')

# Preview
print()
print(df[['Employee Name','UserId','From Date','To Date','Status','Last Action Taken by']].to_string())

df.to_csv(LEAVE_FILE, index=False)
print(f'\nClean CSV saved!')
