import pandas as pd

dc = pd.read_csv('disconnect_logs.csv')
bad = dc[~dc['Message'].str.contains('UserLogOut', na=False)]
print('=== disconnect_logs.csv ===')
print(f'Total rows:        {len(dc)}')
print(f'Non-UserLogOut:    {len(bad)}  (should be 0)')

cr = pd.read_csv('concurrency_report.csv')
print()
print('=== concurrency_report.csv ===')
print(f'Total intervals:   {len(cr)}')
print(f'Peak Active Users: {cr["Active Users"].max()}')
print(f'Peak Single:       {cr["Single Session Users"].max()}')
print(f'Peak Multi:        {cr["Multi Session Users"].max()}')
