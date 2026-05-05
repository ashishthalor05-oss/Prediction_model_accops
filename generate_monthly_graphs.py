import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.ensemble import HistGradientBoostingRegressor
import warnings
warnings.filterwarnings('ignore')

def generate_monthly_backtest(train_end_date, test_start_date, test_end_date, month_name):
    print(f"\n--- Generating Backtest for {month_name} ---")
    df = pd.read_csv('processed_data.csv')
    df['Time Interval'] = pd.to_datetime(df['Time Interval'])
    
    df['HourFraction'] = df['Time Interval'].dt.hour + (df['Time Interval'].dt.minute / 60.0)
    df['Hour_sin'] = np.sin(2 * np.pi * df['HourFraction']/24.0)
    df['Hour_cos'] = np.cos(2 * np.pi * df['HourFraction']/24.0)
    df['DayOfWeek_sin'] = np.sin(2 * np.pi * df['DayOfWeek']/7.0)
    df['DayOfWeek_cos'] = np.cos(2 * np.pi * df['DayOfWeek']/7.0)

    train_df = df[(df['Time Interval'] < train_end_date)].copy()
    test_df  = df[(df['Time Interval'] >= test_start_date) & (df['Time Interval'] <= test_end_date)].copy()
    
    if len(train_df) == 0 or len(test_df) == 0:
        print(f"Skipping {month_name} due to lack of data.")
        return

    base_features = ['HourFraction', 'DayOfWeek', 'Hour_sin', 'Hour_cos', 'DayOfWeek_sin', 'DayOfWeek_cos', 'IsWeekend', 'IsHoliday', 'IsOptionalHoliday', 'Month', 'Day']
    
    model_sl = HistGradientBoostingRegressor(max_iter=150, random_state=42)
    model_ml = HistGradientBoostingRegressor(max_iter=150, random_state=42)
    model_al = HistGradientBoostingRegressor(max_iter=150, random_state=42)
    
    model_sl.fit(train_df[base_features], train_df['Single Session Logins'])
    model_ml.fit(train_df[base_features], train_df['Multi Session Logins'])
    model_al.fit(train_df[base_features], train_df['Active User Logins'])
    
    test_df['Pred_SL'] = model_sl.predict(test_df[base_features]).clip(0)
    test_df['Pred_ML'] = model_ml.predict(test_df[base_features]).clip(0)
    test_df['Pred_AL'] = model_al.predict(test_df[base_features]).clip(0)
    
    train_df['Pred_SL'] = model_sl.predict(train_df[base_features]).clip(0)
    train_df['Pred_ML'] = model_ml.predict(train_df[base_features]).clip(0)
    train_df['Pred_AL'] = model_al.predict(train_df[base_features]).clip(0)

    ext_features = base_features + ['Pred_SL', 'Pred_ML', 'Pred_AL']

    model_au = HistGradientBoostingRegressor(max_iter=400, learning_rate=0.05, max_depth=12, min_samples_leaf=2, l2_regularization=0.1, random_state=42)
    model_au.fit(train_df[ext_features], train_df['Active Users'])
    
    test_df['Predicted_Active_Users'] = model_au.predict(test_df[ext_features]).clip(0).astype(int)
    
    plt.figure(figsize=(18, 7))
    plt.plot(test_df['Time Interval'], test_df['Active Users'], label='Actual Active Users', color='blue', alpha=0.7)
    plt.plot(test_df['Time Interval'], test_df['Predicted_Active_Users'], label='Predicted Active Users', color='green', linestyle='--', alpha=0.8)
    plt.title(f'Blind Backtest: Predicted vs Actual Active Users ({month_name})')
    plt.xlabel('Date')
    plt.ylabel('Concurrent Active Users')
    plt.xticks(rotation=45)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    chart_file = f'backtest_{month_name.lower()}.png'
    plt.savefig(chart_file, dpi=150)
    print(f"[{month_name}] Saved graph to {chart_file}")

if __name__ == "__main__":
    # JAN: Train Dec, Test Jan
    generate_monthly_backtest('2026-01-01', '2026-01-01', '2026-01-31 23:59:59', 'Jan_2026')
    # FEB: Train Dec+Jan, Test Feb
    generate_monthly_backtest('2026-02-01', '2026-02-01', '2026-02-28 23:59:59', 'Feb_2026')
    # MAR: Train Dec+Jan+Feb, Test Mar (up to Mar 16)
    generate_monthly_backtest('2026-03-01', '2026-03-01', '2026-03-16 23:59:59', 'Mar_2026')
