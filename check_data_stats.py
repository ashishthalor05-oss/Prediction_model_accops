import pandas as pd

def check_stats():
    print("Loading logs...")
    try:
        login_df = pd.read_csv('login_logs.csv')
        resource_df = pd.read_csv('resource_logs.csv')
        disconnect_df = pd.read_csv('disconnect_logs.csv')
    except Exception as e:
        print(e)
        return

    print(f"Login Events: {len(login_df)}")
    print(f"Resource Events: {len(resource_df)}")
    print(f"Disconnect Events: {len(disconnect_df)}")

    login_users = set(login_df['Username'].unique())
    resource_users = set(resource_df['Username'].unique())

    print(f"Unique Login Users: {len(login_users)}")
    print(f"Unique Resource Users: {len(resource_users)}")

    only_resource = resource_users - login_users
    print(f"Users in Resource but NOT in Login: {len(only_resource)}")
    if len(only_resource) > 0:
        print("Sample users only in Resource:", list(only_resource)[:5])

    # Check for 'LogOut' events coverage
    print("\n--- Disconnect Types ---")
    print(disconnect_df['Message'].apply(lambda x: 'LogOut' if 'LogOut' in str(x) else 'Disconnect').value_counts())

if __name__ == "__main__":
    check_stats()
