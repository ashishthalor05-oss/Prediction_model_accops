import pandas as pd
from datetime import timedelta, datetime
import os
from load_holidays import load_holidays

def calculate_concurrency():
    """
    Reconstructs user sessions and aggregates logins for 15, 30, and 60 minute windows.
    """
    print("Loading Login & Logout Logs...")
    if not os.path.exists('login_logs.csv') or not os.path.exists('disconnect_logs.csv'):
        print("Error: login_logs.csv or disconnect_logs.csv not found.")
        return

    # Load Holidays
    mandatory_holidays, optional_holidays = load_holidays()

    # Load Logs
    logins = pd.read_csv('login_logs.csv')
    logouts = pd.read_csv('disconnect_logs.csv')

    logins['Timestamp'] = pd.to_datetime(logins['Timestamp'], format='mixed', errors='coerce')
    logouts['Timestamp'] = pd.to_datetime(logouts['Timestamp'], format='mixed', errors='coerce')
    
    logins = logins.dropna(subset=['Timestamp']).sort_values('Timestamp')
    logouts = logouts.dropna(subset=['Timestamp']).sort_values('Timestamp')

    if logins.empty:
        print("No valid login logs found.")
        return

    # 1. Reconstruct Sessions (3-hour timeout)
    sessions = []
    logins_by_user = {u: group.sort_values('Timestamp') for u, group in logins.groupby('Username')}
    logouts_by_user = {u: group.sort_values('Timestamp') for u, group in logouts.groupby('Username')}

    print("Reconstructing sessions with 3-hour timeout...")
    for user, u_logins in logins_by_user.items():
        u_logouts = logouts_by_user.get(user, pd.DataFrame(columns=['Timestamp']))
        for i in range(len(u_logins)):
            login_time = u_logins.iloc[i]['Timestamp']
            next_logout = u_logouts[u_logouts['Timestamp'] > login_time]
            end_logout = next_logout.iloc[0]['Timestamp'] if not next_logout.empty else None
            end_login = u_logins.iloc[i+1]['Timestamp'] if i+1 < len(u_logins) else None
            timeout_end = login_time + timedelta(hours=3)
            
            candidates = [timeout_end]
            if end_logout: candidates.append(end_logout)
            if end_login: candidates.append(end_login)
            logout_time = min(candidates)
            sessions.append({'Start': login_time, 'End': logout_time})

    # 2. Aggregation
    start_all = logins['Timestamp'].min().replace(hour=0, minute=0, second=0, microsecond=0)
    end_all = logins['Timestamp'].max().replace(hour=23, minute=59, second=59, microsecond=0)
    time_slots = pd.date_range(start=start_all, end=end_all, freq='15min')
    
    results = []
    print(f"Aggregating {len(time_slots)} intervals...")
    
    # Pre-calculate simple counts per slot for speed
    slot_counts = {slot: 0 for slot in time_slots}
    block_30m   = {}
    block_60m   = {}
    
    for t in logins['Timestamp']:
        floored_15 = t.floor('15min')
        floored_30 = t.floor('30min')
        floored_60 = t.floor('60min')
        
        if floored_15 in slot_counts:
            slot_counts[floored_15] += 1
            
        block_30m[floored_30] = block_30m.get(floored_30, 0) + 1
        block_60m[floored_60] = block_60m.get(floored_60, 0) + 1

    for idx, slot in enumerate(time_slots):
        slot_end = slot + timedelta(minutes=15)
        
        # 15m Login Count (Current 15m window)
        login_15m = slot_counts.get(slot, 0)
        
        # 30m Login Count (Fixed Block: e.g. 12:00-12:30 or 12:30-13:00)
        login_30m = block_30m.get(slot.floor('30min'), 0)
        
        # 60m Login Count (Fixed Block: e.g. 12:00-13:00)
        login_60m = block_60m.get(slot.floor('60min'), 0)
        
        # Active Users
        active_count = 0
        for s in sessions:
            if s['Start'] < slot_end and s['End'] > slot:
                active_count += 1
        
        results.append({
            'Time Interval': slot,
            'Login Count': login_15m,
            'Login 30m': login_30m,
            'Login 60m': login_60m,
            'Active Users': active_count
        })

    full_df = pd.DataFrame(results)
    full_df['Date']      = full_df['Time Interval'].dt.date
    full_df['Hour']      = full_df['Time Interval'].dt.hour
    full_df['DayOfWeek'] = full_df['Time Interval'].dt.dayofweek
    full_df['IsWeekend'] = full_df['DayOfWeek'] >= 5
    full_df['Month']     = full_df['Time Interval'].dt.month
    full_df['Day']       = full_df['Time Interval'].dt.day
    full_df['IsHoliday']         = full_df['Date'].apply(lambda d: d in mandatory_holidays)
    full_df['IsOptionalHoliday'] = full_df['Date'].apply(lambda d: d in optional_holidays)

    full_df.to_csv('processed_data.csv', index=False)
    print(f"Success: processed_data.csv created with 15/30/60m targets.")

if __name__ == "__main__":
    calculate_concurrency()
