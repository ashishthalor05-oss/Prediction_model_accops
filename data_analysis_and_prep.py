import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from load_holidays import load_holidays

def analyze_and_prep_data():
    input_file = 'concurrency_report.csv'
    output_file = 'processed_data.csv'
    
    print(f"Loading data from {input_file}...")
    try:
        df = pd.read_csv(input_file)
    except FileNotFoundError:
        print(f"Error: {input_file} not found.")
        return

    # specific parsing for timestamps - assuming standard format from previous step
    df['Time Interval'] = pd.to_datetime(df['Time Interval'])
    
    # Feature Engineering
    print("Feature Engineering...")
    df['Hour'] = df['Time Interval'].dt.hour
    df['DayOfWeek'] = df['Time Interval'].dt.dayofweek
    df['IsWeekend'] = df['DayOfWeek'] >= 5
    df['Month'] = df['Time Interval'].dt.month
    df['Day'] = df['Time Interval'].dt.day
    df['Date'] = df['Time Interval'].dt.date

    # Load Holidays from holidays.csv or holidays.xlsx
    print("Loading holidays...")
    all_mandatory, all_optional = load_holidays()

    df['IsHoliday']         = df['Date'].apply(lambda x: x in all_mandatory)
    df['IsOptionalHoliday'] = df['Date'].apply(lambda x: x in all_optional)

    # Save processed data
    df.to_csv(output_file, index=False)
    print(f"Propcessed data saved to {output_file}")
    
    # Visualization
    print("Generating visualizations...")
    plt.figure(figsize=(15, 6))
    sns.lineplot(data=df, x='Time Interval', y='Active Users', label='Active Users')
    if 'Single Session Users' in df.columns:
        sns.lineplot(data=df, x='Time Interval', y='Single Session Users', label='Single Session Users')
    if 'Multi Session Users' in df.columns:
        sns.lineplot(data=df, x='Time Interval', y='Multi Session Users', label='Multi Session Users')
        
    plt.title('Active Users vs Resource Usage Over Time')
    plt.xlabel('Time')
    plt.ylabel('Count')
    plt.legend()
    plt.savefig('active_users_vs_resource.png')
    print("Saved active_users_vs_resource.png")

    # Average Daily Profile
    plt.figure(figsize=(12, 6))
    avg_daily = df.groupby('Hour')['Active Users'].mean().reset_index()
    sns.lineplot(data=avg_daily, x='Hour', y='Active Users')
    plt.title('Average Daily User Profile')
    plt.xlabel('Hour of Day')
    plt.ylabel('Average Active Users')
    plt.grid(True)
    plt.xticks(range(0, 24))
    plt.savefig('average_daily_profile.png')
    print("Saved average_daily_profile.png")

    # Day of Week Profile
    plt.figure(figsize=(12, 6))
    sns.boxplot(data=df, x='DayOfWeek', y='Active Users')
    plt.title('User Activity by Day of Week (0=Mon, 6=Sun)')
    plt.xlabel('Day of Week')
    plt.ylabel('Active Users')
    plt.savefig('day_of_week_profile.png')
    print("Saved day_of_week_profile.png")

if __name__ == "__main__":
    analyze_and_prep_data()
