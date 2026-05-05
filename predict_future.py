"""
predict_future.py
─────────────────
Predicts Logins for a specific window (15m, 30m, 60m).
Interval frequency matches the chosen window size.
"""

import pandas as pd
import joblib
import sys
import os
import numpy as np
import matplotlib.pyplot as plt
import argparse
from datetime import datetime, timedelta, date
from load_holidays import load_holidays

def load_leave_adjustments(leave_file='employee_leaves.csv'):
    adjustments = {}
    if not os.path.exists(leave_file): return adjustments
    df = pd.read_csv(leave_file)
    for _, row in df.iterrows():
        try:
            start = pd.to_datetime(str(row.get('Start Date', ''))).date()
            end   = pd.to_datetime(str(row.get('End Date',   ''))).date()
            hday  = str(row.get('Half Day', 'No')).strip().lower()
        except: continue
        curr = start
        while curr <= end:
            if curr not in adjustments: adjustments[curr] = {'full': 0, 'morning': 0, 'afternoon': 0}
            if 'morning' in hday: adjustments[curr]['morning'] += 1
            elif 'afternoon' in hday: adjustments[curr]['afternoon'] += 1
            else: adjustments[curr]['full'] += 1
            curr += timedelta(days=1)
    return adjustments

def apply_leave_adjustment(row, adjustments):
    d, hr = row['Time Interval'].date(), row['Hour']
    adj = adjustments.get(d)
    if not adj: return 0
    red = adj['full']
    if hr < 12: red += adj['morning']
    else: red += adj['afternoon']
    return red

def run_prediction():
    parser = argparse.ArgumentParser()
    parser.add_argument('start', help="Start date YYYY-MM-DD")
    parser.add_argument('end', nargs='?', help="End date YYYY-MM-DD")
    parser.add_argument('--window', default='15m', choices=['15m', '30m', '60m', 'all'], help="Prediction window")
    args = parser.parse_args()

    start_date = datetime.strptime(args.start, "%Y-%m-%d").date()
    end_date   = datetime.strptime(args.end, "%Y-%m-%d").date() if args.end else start_date
    window     = args.window

    # Map windows to models
    window_map = {
        '15m': [('Login Count', 'rf_model_login_count.joblib')],
        '30m': [('Login 30m', 'rf_model_login_30m.joblib')],
        '60m': [('Login 60m', 'rf_model_login_60m.joblib')],
        'all': [('Login Count', 'rf_model_login_count.joblib'), 
                ('Login 30m', 'rf_model_login_30m.joblib'),
                ('Login 60m', 'rf_model_login_60m.joblib')]
    }
    targets_to_run = window_map[window]
    
    # Always include Active Users
    targets_to_run.append(('Active Users', 'rf_model_active_users.joblib'))

    # Set interval frequency
    freq_map = {'15m': 15, '30m': 30, '60m': 60, 'all': 15}
    interval_minutes = freq_map[window]

    print(f"Backtest Prediction: {start_date} to {end_date} | Window: {window} | Frequency: {interval_minutes}m")

    # Build intervals
    intervals = []
    curr = start_date
    while curr <= end_date:
        t, t_end = datetime.combine(curr, datetime.min.time()), datetime.combine(curr, datetime.max.time())
        while t <= t_end:
            intervals.append(t)
            t += timedelta(minutes=interval_minutes)
        curr += timedelta(days=1)

    df = pd.DataFrame({'Time Interval': intervals})
    df['HourFraction'] = df['Time Interval'].dt.hour + (df['Time Interval'].dt.minute / 60.0)
    df['DayOfWeek'] = df['Time Interval'].dt.dayofweek
    df['Hour'], df['Month'], df['Day'] = df['Time Interval'].dt.hour, df['Time Interval'].dt.month, df['Time Interval'].dt.day
    df['Hour_sin'] = np.sin(2 * np.pi * df['HourFraction']/24.0)
    df['Hour_cos'] = np.cos(2 * np.pi * df['HourFraction']/24.0)
    df['DayOfWeek_sin'] = np.sin(2 * np.pi * df['DayOfWeek']/7.0)
    df['DayOfWeek_cos'] = np.cos(2 * np.pi * df['DayOfWeek']/7.0)
    df['IsWeekend'] = df['DayOfWeek'] >= 5
    
    mandatory, optional = load_holidays()
    df['IsHoliday'] = df['Time Interval'].dt.date.apply(lambda x: x in mandatory)
    df['IsOptionalHoliday'] = df['Time Interval'].dt.date.apply(lambda x: x in optional)

    features = ['HourFraction', 'DayOfWeek', 'Hour_sin', 'Hour_cos', 'DayOfWeek_sin', 'DayOfWeek_cos', 
                'IsWeekend', 'IsHoliday', 'IsOptionalHoliday', 'Month', 'Day']

    for target, path in targets_to_run:
        if os.path.exists(path):
            model = joblib.load(path)
            col = f"PREDICTED {target.upper()}"
            df[col] = model.predict(df[features]).clip(0).astype(int)
        else:
            print(f"Warning: Model {path} missing.")

    # ── Logical Consistency Check ─────────────────────────────────────────────
    # Active Users MUST be at least >= current interval logins
    login_cols = [c for c in df.columns if 'LOGIN' in c]
    if 'PREDICTED ACTIVE USERS' in df.columns and login_cols:
        # We take the max across all predicted login windows to be safe
        max_login = df[login_cols].max(axis=1)
        df['PREDICTED ACTIVE USERS'] = np.maximum(df['PREDICTED ACTIVE USERS'], max_login)

    # Load Actuals
    if os.path.exists('processed_data.csv'):
        actuals = pd.read_csv('processed_data.csv')
        actuals['Time Interval'] = pd.to_datetime(actuals['Time Interval'])
        cols_to_merge = ['Time Interval'] + [t[0] for t in targets_to_run]
        df = df.merge(actuals[cols_to_merge], on='Time Interval', how='left')

    adjustments = load_leave_adjustments()
    df['Employees on Leave'] = df.apply(lambda r: apply_leave_adjustment(r, adjustments), axis=1) if adjustments else 0

    # Save
    out_name = f"backtest_{window}_{start_date}_to_{end_date}.csv"
    df.to_csv(out_name, index=False)
    
    # Graphs
    for target, _ in targets_to_run:
        if target == 'Active Users': continue
        plt.figure(figsize=(12, 6))
        p_col = f"PREDICTED {target.upper()}"
        plt.plot(df['Time Interval'], df[p_col], label=f'Predicted {target}', color='#f43f5e', linewidth=2)
        if target in df.columns and not df[target].isnull().all():
            plt.plot(df['Time Interval'], df[target], label=f'Actual {target}', color='#3b82f6', alpha=0.4)
        plt.title(f"Prediction: {target} ({start_date})")
        plt.legend(); plt.grid(True, alpha=0.3)
        plt.savefig(f'chart_{target.replace(" ", "_")}.png'); plt.close()

    print(f"Success: Results saved to {out_name}")

if __name__ == "__main__":
    run_prediction()
