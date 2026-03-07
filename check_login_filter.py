import pandas as pd

col_names = ['ID','Timestamp','Level','Component','Message','Unused1','Unused2','SessionID','Username','Host']
df = pd.read_csv('log_data.csv', names=col_names, header=None, nrows=500000)

login_mask = df['Message'].str.contains('LOGGED IN', na=False)
client_mask = df['Message'].str.contains("'Client Logged in'", na=False)

print('Rows matching LOGGED IN (current login_logs filter):', login_mask.sum())
print('Rows matching Client Logged in (resource user_start filter):', client_mask.sum())
print()
print('Sample LOGGED IN messages:')
print(df[login_mask]['Message'].head(3).to_string())
print()
print('Sample Client Logged in messages:')
print(df[client_mask]['Message'].head(3).to_string())

# Check if ayaz.dhala is in each
user = 'ayaz.dhala'
in_login = df[login_mask & df['Message'].str.contains(user, na=False, case=False)]
in_client = df[client_mask & df['Message'].str.contains(user, na=False, case=False)]
print(f"\n'{user}' in LOGGED IN events: {len(in_login)}")
print(f"'{user}' in Client Logged in events: {len(in_client)}")
