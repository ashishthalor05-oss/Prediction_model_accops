import pandas as pd
from datetime import timedelta
import calculate_concurrency # Import to reuse session logic if needed, but easier to copy-paste core logic for debug

def debug_interval():
    target_time_str = "2025-11-27 12:15:00"
    target_time = pd.to_datetime(target_time_str)
    interval_end = target_time + timedelta(minutes=15)
    
    print(f"Debugging Interval: {target_time} to {interval_end}")

    # Load Logs
    login_df = pd.read_csv('login_logs.csv')
    disconnect_df = pd.read_csv('disconnect_logs.csv')
    resource_df = pd.read_csv('resource_logs.csv')
    
    # Standardize
    login_df['Username'] = login_df['Username'].str.lower().str.strip()
    disconnect_df['Username'] = disconnect_df['Username'].str.lower().str.strip()
    resource_df['Username'] = resource_df['Username'].str.lower().str.strip()
    
    login_df['Timestamp'] = pd.to_datetime(login_df['Timestamp'])
    disconnect_df['Timestamp'] = pd.to_datetime(disconnect_df['Timestamp'])
    resource_df['Timestamp'] = pd.to_datetime(resource_df['Timestamp'])

    # Reconstruct Login Sessions
    login_df['Event'] = 'Login'
    disconnect_df['Event'] = 'Disconnect'
    cols = ['Timestamp', 'Username', 'Event']
    
    all_events = pd.concat([login_df[cols], disconnect_df[cols]]).sort_values(by='Timestamp')
    login_sessions = reconstruct_sessions(all_events, 'Login', 'Disconnect')
    sessions_df = pd.DataFrame(login_sessions)
    
    # Reconstruct Resource Sessions
    resource_df['Event'] = 'Resource_Start'
    res_starts = resource_df[cols].copy()
    res_starts['Event'] = 'Resource_Start'
    
    res_ends = disconnect_df[cols].copy()
    res_ends['Event'] = 'Resource_End'
    
    res_events = pd.concat([res_starts, res_ends]).sort_values(by='Timestamp')
    resource_sessions = reconstruct_sessions(res_events, 'Resource_Start', 'Resource_End')
    res_sessions_df = pd.DataFrame(resource_sessions)

    # Check Overlap
    login_mask = (sessions_df['Start'] < interval_end) & (sessions_df['End'] > target_time)
    active_logins = sessions_df[login_mask]
    
    res_mask = (res_sessions_df['Start'] < interval_end) & (res_sessions_df['End'] > target_time)
    active_resources = res_sessions_df[res_mask]
    
    print(f"\nActive Login Users ({len(active_logins)}):")
    print(active_logins[['Username', 'Start', 'End']])
    
    print(f"\nActive Resource Users ({len(active_resources)}):")
    print(active_resources[['Username', 'Start', 'End']])
    
    # Intersection
    login_users = set(active_logins['Username'])
    res_users = set(active_resources['Username'])
    
    only_res = res_users - login_users
    print(f"\nUsers in Resource but NOT in Login ({len(only_res)}):")
    for user in only_res:
        print(f"User: {user}")
        # Find why they are not in login
        # Check their sessions
        user_sess = sessions_df[sessions_df['Username'] == user]
        print("  Login Sessions for this user:")
        print(user_sess)

def reconstruct_sessions(input_events, start_event, end_event):
    sessions = []
    grouped = input_events.groupby('Username')
    
    for user, group in grouped:
        group = group.sort_values(by='Timestamp')
        current_start = None
        
        for index, row in group.iterrows():
            if row['Event'] == start_event:
                current_start = row['Timestamp']
            elif row['Event'] == end_event:
                if current_start is not None:
                    sessions.append({'Username': user, 'Start': current_start, 'End': row['Timestamp']})
                    current_start = None
        
        if current_start is not None:
            sessions.append({'Username': user, 'Start': current_start, 'End': input_events['Timestamp'].max()})
            
    return sessions

if __name__ == "__main__":
    debug_interval()
