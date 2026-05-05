import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.ensemble import HistGradientBoostingRegressor
import warnings
import sys
import os

warnings.filterwarnings('ignore')

def run_backtest(train_start, train_end, test_start, test_end):
    print(f"Loading data from processed_data.csv...")
    if not os.path.exists('processed_data.csv'):
        print("ERROR: processed_data.csv not found.")
        sys.exit(1)
        
    df = pd.read_csv('processed_data.csv')
    df['Time Interval'] = pd.to_datetime(df['Time Interval'])
    
    # Feature Engineering
    df['HourFraction'] = df['Time Interval'].dt.hour + (df['Time Interval'].dt.minute / 60.0)
    df['Hour_sin'] = np.sin(2 * np.pi * df['HourFraction']/24.0)
    df['Hour_cos'] = np.cos(2 * np.pi * df['HourFraction']/24.0)
    df['DayOfWeek_sin'] = np.sin(2 * np.pi * df['DayOfWeek']/7.0)
    df['DayOfWeek_cos'] = np.cos(2 * np.pi * df['DayOfWeek']/7.0)

    # Split Data: Train on [train_start, train_end], Test on [test_start, test_end]
    train_df = df[(df['Time Interval'] >= train_start) & (df['Time Interval'] <= train_end)].copy()
    test_df  = df[(df['Time Interval'] >= test_start) & (df['Time Interval'] <= test_end)].copy()
    
    if len(train_df) == 0 or len(test_df) == 0:
        print("ERROR: Not enough data for backtest.")
        sys.exit(1)

    features = ['HourFraction', 'DayOfWeek', 'Hour_sin', 'Hour_cos', 'DayOfWeek_sin', 'DayOfWeek_cos', 
                'IsWeekend', 'IsHoliday', 'IsOptionalHoliday', 'Month', 'Day']
    
    target = 'Login Count'
    print(f"Training backtest model for {target}...")
    model = HistGradientBoostingRegressor(max_iter=300, random_state=42)
    model.fit(train_df[features], train_df[target])
    
    test_df['Predicted Logins'] = model.predict(test_df[features]).clip(0).astype(int)
    
    # Metrics
    actual = test_df[target]
    pred = test_df['Predicted Logins']
    mae = mean_absolute_error(actual, pred)
    rmse = np.sqrt(mean_squared_error(actual, pred))
    
    print(f"\nGUI_METRIC:MAE:{mae:.2f}")
    print(f"GUI_METRIC:RMSE:{rmse:.2f}")
    print(f"GUI_METRIC:PEAK_ACTUAL:{actual.max()}")
    print(f"GUI_METRIC:PEAK_PREDICTED:{pred.max()}")
    
    # Visualization
    plt.figure(figsize=(15, 6))
    plt.plot(test_df['Time Interval'], actual, label='Actual Logins', alpha=0.7)
    plt.plot(test_df['Time Interval'], pred, label='Predicted Logins', linestyle='--', alpha=0.8)
    plt.title(f'Backtest: Predicted vs Actual Logins ({test_start} to {test_end})')
    plt.xlabel('Time')
    plt.ylabel('Login Count')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig('app_backtest_chart.png')
    plt.close()
    
    # Save results
    test_df[['Time Interval', target, 'Predicted Logins']].to_csv('app_backtest_results.csv', index=False)
    print("SUCCESS: Backtest complete.")

if __name__ == "__main__":
    if len(sys.argv) >= 5:
        run_backtest(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        print("Usage: python test_model_accuracy.py <ts> <te> <vs> <ve>")
