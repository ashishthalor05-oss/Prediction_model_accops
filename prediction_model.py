import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
import joblib
import sys
import os

def train_and_evaluate(cutoff_date="2026-02-01"):
    if not os.path.exists('processed_data.csv'):
        print("Error: processed_data.csv not found. Run calculate_concurrency.py first.")
        return

    df = pd.read_csv('processed_data.csv')
    df['Time Interval'] = pd.to_datetime(df['Time Interval'])
    
    # Feature Engineering
    df['HourFraction'] = df['Time Interval'].dt.hour + (df['Time Interval'].dt.minute / 60.0)
    df['Hour_sin'] = np.sin(2 * np.pi * df['HourFraction']/24.0)
    df['Hour_cos'] = np.cos(2 * np.pi * df['HourFraction']/24.0)
    df['DayOfWeek_sin'] = np.sin(2 * np.pi * df['DayOfWeek']/7.0)
    df['DayOfWeek_cos'] = np.cos(2 * np.pi * df['DayOfWeek']/7.0)

    # ── Date Cutoff for Backtesting ───────────────────────────────────────
    # Train only on data BEFORE the cutoff date
    cutoff = pd.to_datetime(cutoff_date).date()
    train_df = df[df['Date'].apply(lambda d: pd.to_datetime(d).date() < cutoff)]
    
    if train_df.empty:
        print(f"Error: No data found before {cutoff_date}. Using all data instead.")
        train_df = df
    else:
        print(f"Training on data up to {cutoff_date} (Rows: {len(train_df)})")

    features = ['HourFraction', 'DayOfWeek', 'Hour_sin', 'Hour_cos', 'DayOfWeek_sin', 'DayOfWeek_cos', 
                'IsWeekend', 'IsHoliday', 'IsOptionalHoliday', 'Month', 'Day']
    
    targets = {
        'Login Count': 'rf_model_login_count.joblib',
        'Login 30m': 'rf_model_login_30m.joblib',
        'Login 60m': 'rf_model_login_60m.joblib',
        'Active Users': 'rf_model_active_users.joblib'
    }

    metrics_text = f"Training Cutoff: {cutoff_date}\n\n"
    for target, model_name in targets.items():
        if target not in train_df.columns:
            continue

        print(f"Training Model for {target}...")
        X_train = train_df[features]
        y_train = train_df[target]

        model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
        model.fit(X_train, y_train)

        # Basic Validation on Train set (for reference)
        preds = model.predict(X_train).clip(0)
        mae = mean_absolute_error(y_train, preds)
        metrics_text += f"{target}: Train MAE={mae:.2f}\n"

        joblib.dump(model, model_name)
        print(f"Success: {model_name} saved.")

    with open('model_metrics.txt', 'w') as f:
        f.write(metrics_text)

if __name__ == "__main__":
    # Default to Feb 1st cutoff for Feb/March prediction
    cutoff = sys.argv[1] if len(sys.argv) > 1 else "2026-02-01"
    train_and_evaluate(cutoff)
