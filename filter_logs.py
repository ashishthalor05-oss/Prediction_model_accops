import pandas as pd

# Define column names based on inspection of the data
# The file appears to lack a header row, so we provide names manually.
column_names = ['ID', 'Timestamp', 'Level', 'Component', 'Message', 'Unused1', 'Unused2', 'SessionID', 'Username', 'Host']

try:
    df = pd.read_csv('log_data.csv', names=column_names, header=None)
    
    # Standardize Username to lowercase to avoid mismatch
    df['Username'] = df['Username'].str.lower().str.strip()
except Exception as e:
    print(f"Error reading CSV: {e}")
    exit()

# Filter for Login logs
# Targeting '[USER LOGGED IN]'
login_logs = df[df['Message'].str.contains('LOGGED IN', na=False)]

# Filter for Logout logs
# Targeting only ['UserLogOut'] UserName: ... (explicit graceful logout)
# DO NOT include 'Disconnect' events (abrupt disconnects are not treated as logouts)
logout_logs = df[df['Message'].str.contains("UserLogOut", na=False) & df['Message'].str.contains("UserName:", na=False)]

# --- Resource Usage Extraction ---

# Single Session
# Start: [SOURCE : CONTROLLER. DESKTOP CONNECTED]
single_start = df[df['Message'].str.contains(r'\[SOURCE : CONTROLLER\. DESKTOP CONNECTED\]', regex=True, na=False)].copy()
single_start['ResourceType'] = 'Single'
single_start['Event'] = 'Start'
# Extract Username: User 'username'
single_start['Username'] = single_start['Message'].str.extract(r"User '([^']+)'")

# End: [SOURCE : HYDESK]. Endpoint ... session dismissal
single_end = df[df['Message'].str.contains(r'\[SOURCE : HYDESK\].*session dismissal', regex=True, na=False)].copy()
single_end['ResourceType'] = 'Single'
single_end['Event'] = 'End'
single_end['Username'] = single_end['Message'].str.extract(r"User '([^']+)'")

# Multi Session
# Start: [SOURCE : SESSION HOST] ... Status changed to 'Connected'
multi_start = df[df['Message'].str.contains(r'\[SOURCE : SESSION HOST\].*Status changed to \'Connected\'', regex=True, na=False)].copy()
multi_start['ResourceType'] = 'Multi'
multi_start['Event'] = 'Start'
multi_start['Username'] = multi_start['Message'].str.extract(r"User '([^']+)'")

# End: [SOURCE : SESSION HOST] ... Status changed to 'LogOut'
# User requested to IGNORE 'Disconnect' for count, only 'LogOut' (or maybe both? instructions said "do not teke the dissconnect message for count")
# "Stop Multi - Session ... Status changed to 'LogOut'. OR ... Status changed to Disconnect."
# Then "do not teke the dissconnect message for count". So I will only take 'LogOut'.
multi_end = df[df['Message'].str.contains(r'\[SOURCE : SESSION HOST\].*Status changed to \'LogOut\'', regex=True, na=False)].copy()
multi_end['ResourceType'] = 'Multi'
multi_end['Event'] = 'End'
multi_end['Username'] = multi_end['Message'].str.extract(r"User '([^']+)'")

# --- User Session Extraction (Active Users) ---
# Start: ['Client Logged in'] UserName: ...
user_start = df[df['Message'].str.contains(r"\['Client Logged in'\] UserName:", regex=True, na=False)].copy()
user_start['ResourceType'] = 'UserSession'
user_start['Event'] = 'Start'
user_start['Username'] = user_start['Message'].str.extract(r"UserName: ([^,]+)")

# End: ['UserLogOut'] UserName: ...
user_end = df[df['Message'].str.contains(r"\['UserLogOut'\] UserName:", regex=True, na=False)].copy()
user_end['ResourceType'] = 'UserSession'
user_end['Event'] = 'End'
user_end['Username'] = user_end['Message'].str.extract(r"UserName: ([^,]+)")

# Combine all resource logs
resource_logs = pd.concat([single_start, single_end, multi_start, multi_end, user_start, user_end])

# Select relevant columns
resource_logs = resource_logs[['Timestamp', 'Username', 'ResourceType', 'Event', 'Message']].sort_values(by='Timestamp')

print(f"Total Logins Found: {len(login_logs)}")
print(f"Total Disconnects Found: {len(logout_logs)}")
print(f"Total Resource Usage Events Found: {len(resource_logs)}")

# Save to CSV
login_logs.to_csv('login_logs.csv', index=False, header=True)
logout_logs.to_csv('disconnect_logs.csv', index=False, header=True)
resource_logs.to_csv('resource_logs.csv', index=False)
print(f"Saved resource_logs.csv with {len(resource_logs)} events.")
print("Saved login_logs.csv, disconnect_logs.csv, and resource_logs.csv")

print("\n--- Top 5 Login Logs ---")
print(login_logs[['Timestamp', 'Username', 'Message']].head())

print("\n--- Top 5 Disconnect Logs ---")
print(logout_logs[['Timestamp', 'Username', 'Message']].head())
