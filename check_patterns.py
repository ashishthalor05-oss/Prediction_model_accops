import pandas as pd

col_names = ['ID','Timestamp','Level','Component','Message','Unused1','Unused2','SessionID','Username','Host']
print("Loading log_data.csv...")
df = pd.read_csv('log_data.csv', names=col_names, header=None)
print(f"Total rows loaded: {len(df)}\n")

checks = {
    "1. Login        ['Client Logged in'] UserName:":
        df['Message'].str.contains("'Client Logged in'", na=False),

    "2. UserLogOut   ['UserLogOut'] UserName:":
        df['Message'].str.contains("UserLogOut", na=False) & df['Message'].str.contains("UserName:", na=False),

    "3. Single START [SOURCE : CONTROLLER. DESKTOP CONNECTED]":
        df['Message'].str.contains(r'\[SOURCE : CONTROLLER\. DESKTOP CONNECTED\]', regex=True, na=False),

    "4. Single END   [SOURCE : HYDESK]...session dismissal":
        df['Message'].str.contains(r'\[SOURCE : HYDESK\].*session dismissal', regex=True, na=False),

    "5. Multi START  [SOURCE : SESSION HOST]...Status changed to 'Connected'":
        df['Message'].str.contains(r"\[SOURCE : SESSION HOST\].*Status changed to 'Connected'", regex=True, na=False),

    "6. Multi END    [SOURCE : SESSION HOST]...Status changed to 'LogOut'":
        df['Message'].str.contains(r"\[SOURCE : SESSION HOST\].*Status changed to 'LogOut'", regex=True, na=False),

    "7. Multi DISC   [SOURCE : SESSION HOST]...Status changed to Disconnect (EXCLUDED)":
        df['Message'].str.contains(r"\[SOURCE : SESSION HOST\].*Status changed to.{0,3}Disconnect", regex=True, na=False),
}

print(f"{'Pattern':<60} {'Count':>7}")
print("-" * 70)
for label, mask in checks.items():
    count = mask.sum()
    print(f"{label:<60} {count:>7}")
