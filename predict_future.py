"""
predict_future.py
─────────────────
Generate future predictions with:
  1. Holiday awareness (from holidays.csv / holidays.xlsx)
  2. Employee Leave adjustment (from employee_leaves.csv)
     → If employees are on leave, reduce predicted server allocation accordingly
     → Half Day leaves reduce morning or afternoon intervals only
"""

import pandas as pd
import joblib
import sys
import os
from datetime import datetime, timedelta, date
from load_holidays import load_holidays


# ── Load employee leave adjustments ───────────────────────────────────────────
def load_leave_adjustments(leave_file='employee_leaves.csv'):
    """
    Returns a dict:
      {
        date: {
          'full':      count of full-day leaves,
          'morning':   count of morning-half leaves,
          'afternoon': count of afternoon-half leaves,
        }
      }
    """
    adjustments = {}

    if not os.path.exists(leave_file):
        print("[Leaves] No employee_leaves.csv found. No leave adjustments applied.")
        return adjustments

    df = pd.read_csv(leave_file)
    print(f"[Leaves] Loaded {len(df)} leave record(s) from {leave_file}")

    for _, row in df.iterrows():
        try:
            start = pd.to_datetime(str(row.get('Start Date', ''))).date()
            end   = pd.to_datetime(str(row.get('End Date',   ''))).date()
            hday  = str(row.get('Half Day', 'No')).strip().lower()
        except Exception:
            continue

        current = start
        while current <= end:
            if current not in adjustments:
                adjustments[current] = {'full': 0, 'morning': 0, 'afternoon': 0}

            if 'morning' in hday:
                adjustments[current]['morning'] += 1
            elif 'afternoon' in hday:
                adjustments[current]['afternoon'] += 1
            else:
                adjustments[current]['full'] += 1

            current += timedelta(days=1)

    total_days = sum(
        v['full'] + v['morning'] + v['afternoon']
        for v in adjustments.values()
    )
    print(f"[Leaves] Leave adjustments cover {len(adjustments)} date(s), {total_days} employee-day(s).")
    return adjustments


def apply_leave_adjustment(row, adjustments):
    """
    For a given 15-min interval, return how many users to subtract.
    Full-day leave → subtract all day
    Morning half   → subtract for hours 00–11
    Afternoon half → subtract for hours 12–23
    """
    d    = row['Time Interval'].date()
    hour = row['Hour']
    adj  = adjustments.get(d, None)
    if adj is None:
        return 0

    reduction = adj['full']  # full-day always subtracted

    if hour < 12:
        reduction += adj['morning']
    else:
        reduction += adj['afternoon']

    return reduction


# ── Main prediction function ───────────────────────────────────────────────────
def predict_future_range(start_date_str, end_date_str=None):

    # Load Models
    try:
        model_resource = joblib.load('rf_model_resource_users.joblib')
        model_active   = joblib.load('rf_model_active_users.joblib')
    except FileNotFoundError:
        print("Error: Models not found. Run 'run_project.py' or 'prediction_model.py' first.")
        return

    # Optional login-count models
    model_single_logins = joblib.load('rf_model_single_session_logins.joblib') \
        if os.path.exists('rf_model_single_session_logins.joblib') else None
    model_multi_logins  = joblib.load('rf_model_multi_session_logins.joblib') \
        if os.path.exists('rf_model_multi_session_logins.joblib') else None

    # Parse Dates
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date   = datetime.strptime(end_date_str,   "%Y-%m-%d").date() if end_date_str else start_date
    except ValueError:
        print("Error: Invalid date format. Use YYYY-MM-DD.")
        return

    print(f"\nGenerating prediction from {start_date} to {end_date}...")

    # Build 15-minute intervals
    all_intervals = []
    current_date  = start_date
    while current_date <= end_date:
        current_time  = datetime.combine(current_date, datetime.min.time())
        day_end_time  = datetime.combine(current_date, datetime.max.time())
        while current_time <= day_end_time:
            all_intervals.append(current_time)
            current_time += timedelta(minutes=15)
        current_date += timedelta(days=1)

    df = pd.DataFrame({'Time Interval': all_intervals})

    # Time features
    df['Hour']      = df['Time Interval'].dt.hour
    df['DayOfWeek'] = df['Time Interval'].dt.dayofweek
    df['IsWeekend'] = df['DayOfWeek'] >= 5
    df['Month']     = df['Time Interval'].dt.month
    df['Day']       = df['Time Interval'].dt.day

    # Load holidays from file (not hardcoded)
    mandatory_holidays, optional_holidays = load_holidays()
    df['IsHoliday']         = df['Time Interval'].dt.date.apply(lambda x: x in mandatory_holidays)
    df['IsOptionalHoliday'] = df['Time Interval'].dt.date.apply(lambda x: x in optional_holidays)

    # Model predictions
    features = ['Hour', 'DayOfWeek', 'IsWeekend', 'IsHoliday', 'IsOptionalHoliday', 'Month', 'Day']
    X = df[features]

    df['Predicted Resource Users'] = model_resource.predict(X).astype(int)
    df['Predicted Active Users']   = model_active.predict(X).astype(int)

    # Predict login counts if models exist
    if model_single_logins:
        df['Predicted Single Logins'] = model_single_logins.predict(X).clip(0).astype(int)
    if model_multi_logins:
        df['Predicted Multi Logins']  = model_multi_logins.predict(X).clip(0).astype(int)

    # ── Apply employee leave adjustments ──────────────────────────────────────
    adjustments = load_leave_adjustments()
    if adjustments:
        df['Leave Reduction'] = df.apply(
            lambda row: apply_leave_adjustment(row, adjustments), axis=1
        )
        # Subtract leaves from predictions (floor at 0)
        df['Adjusted Active Users']   = (df['Predicted Active Users']   - df['Leave Reduction']).clip(lower=0).astype(int)
        df['Adjusted Resource Users'] = (df['Predicted Resource Users'] - df['Leave Reduction']).clip(lower=0).astype(int)

        print("\n[Leaves] Applied leave adjustments to predictions.")
        print("         Column 'Adjusted Active Users' = Model Prediction - Employees on Leave")
    else:
        df['Leave Reduction']         = 0
        df['Adjusted Active Users']   = df['Predicted Active Users']
        df['Adjusted Resource Users'] = df['Predicted Resource Users']

    # Server allocation recommendation (10% buffer + 5 users)
    df['Servers Needed'] = ((df['Adjusted Active Users'] * 1.10) + 5).astype(int)

    # ── Display ───────────────────────────────────────────────────────────────
    print("\n--- Prediction Output (First 10 rows) ---")
    print(df[['Time Interval',
              'Predicted Active Users', 'Leave Reduction',
              'Adjusted Active Users', 'Servers Needed']].head(10).to_string(index=False))

    # Leave-impacted days summary
    if adjustments:
        leave_days = df[df['Leave Reduction'] > 0].copy()
        if not leave_days.empty:
            daily = leave_days.groupby(leave_days['Time Interval'].dt.date).agg(
                Employees_on_Leave=('Leave Reduction', 'max'),
                Avg_Adjusted_Users=('Adjusted Active Users', 'mean'),
                Max_Servers_Needed=('Servers Needed', 'max')
            ).reset_index()
            daily.columns = ['Date', 'Employees on Leave', 'Avg Adjusted Users', 'Max Servers Needed']
            print("\n--- Leave-Adjusted Days Summary ---")
            print(daily.to_string(index=False))

    # Peak stats
    peak_adj  = df['Adjusted Active Users'].max()
    peak_pred = df['Predicted Active Users'].max()
    peak_time = df.loc[df['Adjusted Active Users'].idxmax(), 'Time Interval']
    saved     = peak_pred - peak_adj

    print(f"\n--- Summary: {start_date} to {end_date} ---")
    print(f"Peak Predicted Active Users  (without leaves): {peak_pred}")
    print(f"Peak Adjusted Active Users   (with leaves):    {peak_adj}  (saved {saved} servers at peak)")
    print(f"Peak at: {peak_time}")

    # Save
    out = f"prediction_{start_date}_to_{end_date}.csv" if start_date != end_date else f"prediction_{start_date}.csv"
    df.to_csv(out, index=False)
    print(f"\nDetailed prediction saved to {out}")
    return df


if __name__ == "__main__":
    if len(sys.argv) > 2:
        predict_future_range(sys.argv[1], sys.argv[2])
    elif len(sys.argv) > 1:
        predict_future_range(sys.argv[1])
    else:
        date_input = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        predict_future_range(date_input)
