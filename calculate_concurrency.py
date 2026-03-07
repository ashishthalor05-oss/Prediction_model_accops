import pandas as pd
from datetime import timedelta
import os
from load_holidays import load_holidays

def calculate_concurrency():
    # Load the data
    print("Loading data...")
    try:
        resource_df = pd.read_csv('resource_logs.csv')
    except FileNotFoundError:
        print("Error: resource_logs.csv not found. Please run filter_logs.py first.")
        return

    # Load Holidays from holidays.csv or holidays.xlsx
    mandatory_holidays, optional_holidays = load_holidays()

    # Convert timestamps to datetime
    print("Processing timestamps...")
    resource_df['Timestamp'] = pd.to_datetime(resource_df['Timestamp'])

    # Function to reconstruct sessions from a DataFrame of events
    def reconstruct_sessions(events_df, resource_type_name):
        sessions = []
        grouped = events_df.groupby('Username')
        
        for user, group in grouped:
            group = group.sort_values(by='Timestamp')
            current_start = None
            
            for index, row in group.iterrows():
                if row['Event'] == 'Start':
                    # If already started, update start time (assume restart)
                    current_start = row['Timestamp']
                
                elif row['Event'] == 'End':
                    if current_start is not None:
                        sessions.append({
                            'Username': user,
                            'Start': current_start,
                            'End': row['Timestamp'],
                            'Type': resource_type_name
                        })
                        current_start = None
            
            # Handle active sessions at end of log
            if current_start is not None:
                last_time = events_df['Timestamp'].max()
                sessions.append({
                    'Username': user,
                    'Start': current_start,
                    'End': last_time,
                    'Type': resource_type_name
                })
        return pd.DataFrame(sessions)

    print("Reconstructing sessions...")
    # Split by Resource Type
    single_events = resource_df[resource_df['ResourceType'] == 'Single']
    multi_events  = resource_df[resource_df['ResourceType'] == 'Multi']
    user_events   = resource_df[resource_df['ResourceType'] == 'UserSession']

    single_sessions = reconstruct_sessions(single_events, 'Single')
    multi_sessions  = reconstruct_sessions(multi_events,  'Multi')
    user_sessions   = reconstruct_sessions(user_events,   'UserSession')

    # Pre-filter only Start events for login counts
    single_starts = single_events[single_events['Event'] == 'Start'].copy()
    multi_starts  = multi_events[multi_events['Event']   == 'Start'].copy()
    
    # Combine for interval range calculation
    all_sessions_list = [df for df in [single_sessions, multi_sessions, user_sessions] if not df.empty]
    
    if not all_sessions_list:
        print("No sessions found.")
        return
        
    all_sessions = pd.concat(all_sessions_list)

    print(f"Reconstructed: {len(single_sessions)} Single, {len(multi_sessions)} Multi, {len(user_sessions)} User sessions.")

    # Define 15-minute intervals
    min_time = all_sessions['Start'].min().floor('15min')
    max_time = all_sessions['End'].max().ceil('15min')
    
    print(f"Calculating concurrency from {min_time} to {max_time}...")
    
    intervals = pd.date_range(start=min_time, end=max_time, freq='15min')
    
    concurrency_counts = []
    
    for interval_start in intervals:
        interval_end = interval_start + timedelta(minutes=15)
        
        # Helper to count overlaps (concurrent sessions)
        def count_overlaps(session_df):
            if session_df.empty: return 0
            mask = (session_df['Start'] < interval_end) & (session_df['End'] > interval_start)
            return session_df[mask].shape[0]

        # Helper to count new logins in this interval (Start events)
        def count_logins(starts_df):
            if starts_df.empty: return 0
            mask = (starts_df['Timestamp'] >= interval_start) & (starts_df['Timestamp'] < interval_end)
            return starts_df[mask].shape[0]

        single_count       = count_overlaps(single_sessions)
        multi_count        = count_overlaps(multi_sessions)
        user_count         = count_overlaps(user_sessions)
        single_login_count = count_logins(single_starts)
        multi_login_count  = count_logins(multi_starts)
        
        # Check Holiday
        current_date = interval_start.date()
        is_mandatory = current_date in mandatory_holidays
        is_optional  = current_date in optional_holidays
        holiday_flag = 'Mandatory' if is_mandatory else ('Optional' if is_optional else 'No')

        concurrency_counts.append({
            'Time Interval':          interval_start,
            'Single Session Users':   single_count,
            'Multi Session Users':    multi_count,
            'Active Users':           user_count,
            'Single Session Logins':  single_login_count,
            'Multi Session Logins':   multi_login_count,
            'Holiday':                holiday_flag
        })
        
    result_df = pd.DataFrame(concurrency_counts)
    
    # Save to CSV
    output_file = 'concurrency_report.csv'
    result_df.to_csv(output_file, index=False)
    print(f"\nConcurrency report saved to {output_file}")
    
    print("\n--- Concurrency Preview (Top 10) ---")
    print(result_df.head(10))
    
    print("\n--- Concurrency Preview (Peak Active Users) ---")
    print(result_df.sort_values(by='Active Users', ascending=False).head(5))

    # Remind user how to manage holidays
    if not os.path.exists('holidays.csv') and not os.path.exists('holidays.xlsx'):
        print("\nNote: No holidays.csv or holidays.xlsx found.")
        print("Create a file with columns: Date, Description, Type (Mandatory/Optional)")

if __name__ == "__main__":
    calculate_concurrency()
