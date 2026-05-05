
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
from datetime import datetime

def generate_report():
    # 1. Daily Summary CSV
    file_path = 'backtest_all_2026-02-01_to_2026-03-20.csv'
    if not os.path.exists(file_path):
        print("Backtest file not found.")
        return
        
    df = pd.read_csv(file_path)
    df['Time Interval'] = pd.to_datetime(df['Time Interval'])
    df['Date'] = df['Time Interval'].dt.date
    
    # Calculate daily totals for actual vs predicted
    daily = df.groupby('Date').agg({
        'Login Count': 'sum',
        'PREDICTED LOGIN COUNT': 'sum'
    }).reset_index()
    
    daily.columns = ['Date', 'Actual Logins', 'Predicted Logins']
    daily['Accuracy (%)'] = (1 - abs(daily['Actual Logins'] - daily['Predicted Logins']) / daily['Actual Logins'].replace(0, 1)) * 100
    daily['Accuracy (%)'] = daily['Accuracy (%)'].clip(lower=0, upper=100)
    
    daily.to_csv('backtest_summary_fixed_blocks.csv', index=False)
    print("Success: backtest_summary_fixed_blocks.csv created.")
    
    # 2. Daily Trend Graph
    plt.figure(figsize=(12, 6))
    plt.plot(daily['Date'], daily['Actual Logins'], label='Actual Total Logins', color='gray', marker='o')
    plt.plot(daily['Date'], daily['Predicted Logins'], label='Predicted Total Logins', color='#8b5cf6', marker='s')
    plt.title('Daily Login Trends (Fixed Blocks Validation)', fontsize=14)
    plt.xlabel('Date')
    plt.ylabel('Total Logins / Day')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('backtest_daily_trend_fixed.png')
    plt.close()
    print("Success: backtest_daily_trend_fixed.png created.")

    # 3. High-Res comparison for the last few days
    # Filter to last 7 days of historical data
    last_date = df['Date'].max()
    week_ago = last_date - pd.Timedelta(days=7)
    subset = df[df['Date'] >= week_ago]
    
    for win, col, pred, color in [('15m', 'Login Count', 'PREDICTED LOGIN COUNT', '#3b82f6'), 
                                   ('30m', 'Login 30m', 'PREDICTED LOGIN 30M', '#f43f5e'), 
                                   ('60m', 'Login 60m', 'PREDICTED LOGIN 60M', '#10b981')]:
        plt.figure(figsize=(15, 7))
        plt.plot(subset['Time Interval'], subset[pred], label=f'Predicted {win}', color=color, linewidth=2)
        plt.plot(subset['Time Interval'], subset[col], label=f'Actual {win}', color='gray', alpha=0.3)
        plt.title(f'Actual vs Predicted ({win} Fixed Blocks) - Last 7 Days', fontsize=16)
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d %b %H:%M'))
        plt.xticks(rotation=45)
        plt.legend()
        plt.grid(True, alpha=0.2)
        plt.tight_layout()
        plt.savefig(f'chart_fixed_{win}.png')
        plt.close()
        print(f"Success: chart_fixed_{win}.png created.")

if __name__ == "__main__":
    generate_report()
