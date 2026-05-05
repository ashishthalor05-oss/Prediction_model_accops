import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import pandas as pd
from datetime import date, timedelta
from load_holidays import load_holidays

username = 'tushar.komawar'

df  = pd.read_csv('login_logs.csv')
udf = df[df['Username'].str.lower().str.strip() == username].copy()
udf['Timestamp'] = pd.to_datetime(udf['Timestamp'], errors='coerce')
udf = udf.dropna(subset=['Timestamp'])
udf['DayName'] = udf['Timestamp'].dt.day_name()
udf['Hour']    = udf['Timestamp'].dt.hour

print(f"=== User: {username} ===")

print(f"Total Login Events : {len(udf)}")
print(f"Date Range         : {udf['Timestamp'].min().date()} to {udf['Timestamp'].max().date()}")

day_order  = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
day_counts = udf['DayName'].value_counts().reindex(day_order, fill_value=0)
max_d      = max(day_counts.max(), 1)
print("\n--- Login by Day ---")
for day, cnt in day_counts.items():
    bar = '#' * int((cnt / max_d) * 20)
    print(f"  {day[:3]}  {bar:<20}  {cnt}")

hour_counts = udf['Hour'].value_counts().sort_index()
max_h       = max(hour_counts.max(), 1)
print("\n--- Login by Hour ---")
for hr, cnt in hour_counts.items():
    ampm = 'AM' if hr < 12 else 'PM'
    hr12 = hr % 12 or 12
    bar  = '#' * int((cnt / max_h) * 20)
    print(f"  {hr12:2d}:00 {ampm}  {bar:<20}  {cnt}")

mean_hr = udf['Hour'].mean()
std_hr  = udf['Hour'].std() if len(udf) > 1 else 1.0
ws = max(0,  int(mean_hr - max(std_hr, 0.5)))
we = min(23, int(mean_hr + max(std_hr, 0.5)) + 1)

def fh(h):
    a   = 'AM' if h < 12 else 'PM'
    h12 = h % 12 or 12
    return f"{h12}:00 {a}"

days_active = set(udf['DayName'].unique())

print(f"\n--- Next 7 Days Prediction ---")
print(f"  Expected Login Window: {fh(ws)} - {fh(we)}")
print(f"  Most Active Day      : {day_counts.idxmax()}")
print()
print(f"  {'Date':<12} {'Day':<12} {'Login?':<8} Window")
print(f"  {'-'*12} {'-'*12} {'-'*8} {'-'*20}")
mandatory, optional = load_holidays()
holidays = mandatory.union(optional)

# Load personal leaves for this user
on_leave_dates = set()
if os.path.exists('employee_leaves.csv'):
    try:
        ldf = pd.read_csv('employee_leaves.csv')
        # Check both naming conventions (HR Excel vs Manual)
        u_col = 'UserId' if 'UserId' in ldf.columns else 'Employee Name'
        user_leaves = ldf[ldf[u_col].astype(str).str.lower().str.strip() == username.lower()]
        for _, row in user_leaves.iterrows():
            s = pd.to_datetime(row.get('From Date' if 'From Date' in ldf.columns else 'Start Date')).date()
            e = pd.to_datetime(row.get('To Date' if 'To Date' in ldf.columns else 'End Date')).date()
            curr = s
            while curr <= e:
                on_leave_dates.add(curr)
                curr += timedelta(days=1)
    except: pass

for i in range(1, 8):
    d      = date.today() + timedelta(days=i)
    dn     = d.strftime('%A')
    
    on_leave = d in on_leave_dates
    is_holiday = d in holidays

    if is_holiday:
        likely = False
        win    = "Holiday"
        flag   = "No"
    elif on_leave:
        likely = False
        win    = "On Leave"
        flag   = "No"
    else:
        likely = dn in days_active
        win    = f"{fh(ws)} - {fh(we)}" if likely else "-"
        flag   = "YES <<" if likely else "No"
        
    print(f"  {str(d):<12} {dn:<12} {flag:<8} {win}")

'''analyze user'''