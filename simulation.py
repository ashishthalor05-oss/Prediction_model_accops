import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor

def run_simulation():
    input_file = 'processed_data.csv'
    print(f"Loading data from {input_file}...")
    try:
        df = pd.read_csv(input_file)
    except FileNotFoundError:
        print(f"Error: {input_file} not found.")
        return

    # Sort and Split
    df = df.sort_values(by='Time Interval')
    from sklearn.model_selection import train_test_split

    features = ['Hour', 'DayOfWeek', 'IsWeekend', 'IsHoliday', 'IsOptionalHoliday', 'Month', 'Day']
    target = 'Active Users' # Changed to Active Users as default per new report structure
    if target not in df.columns:
         print(f"Warning: {target} not found. Checking for Resource Users.")
         if 'Resource Users' in df.columns:
             target = 'Resource Users'
         else:
             print("Critical: No valid target column found.")
             return
    
    # Use Random Split to match prediction model logic
    X = df[features]
    y = df[target]
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, shuffle=True)
    
    # Re-index to keep time sorted for simulation visualization (optional but good for graph)
    # Actually, for simulation of "random days", sorting by time might be confusing if they are discontinuous.
    # But let's sort X_test by the original index to make the graph look like a time series of the test points.
    # We need the original index or timestamp.
    # Let's grab the indices from y_test and sort all by index.
    test_indices = y_test.index.sort_values()
    X_test = df.loc[test_indices, features]
    y_test = df.loc[test_indices, target]

    # Train Model
    print("Training Random Forest for Simulation...")
    rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
    rf_model.fit(X_train, y_train)
    predictions = rf_model.predict(X_test)
    
    # Simulation Parameters
    # Static Strategy: Max valid peak from historical data + 10% buffer
    # We use training data to determine the static capacity
    max_hist_concurrency = y_train.max()
    static_capacity = int(max_hist_concurrency * 1.1) 
    
    # Dynamic Strategy: Predicted + Buffer
    # Buffer could be percentage or fixed number. Let's use 10% + 5 users min buffer
    dynamic_buffer_pct = 0.10
    dynamic_buffer_fixed = 5
    
    # Run Simulation on Test Data
    results = []
    
    total_static_cost = 0
    total_dynamic_cost = 0
    
    under_provisioned_events = 0
    total_events = len(y_test)
    
    for actual, pred in zip(y_test, predictions):
        # Static Cost
        # Cost is proportional to capacity provisioned
        # Assuming 1 unit cost per user-slot per interval
        total_static_cost += static_capacity
        
        # Dynamic Cost
        # Calculate dynamic capacity
        dyn_cap = int(pred * (1 + dynamic_buffer_pct)) + dynamic_buffer_fixed
        
        # Ensure we don't go below 0 (though pred should be positive)
        dyn_cap = max(0, dyn_cap)
        
        total_dynamic_cost += dyn_cap
        
        # Check for under-provisioning
        if dyn_cap < actual:
            under_provisioned_events += 1
            
        results.append({
            'Actual': actual,
            'Predicted': pred,
            'Static_Capacity': static_capacity,
            'Dynamic_Capacity': dyn_cap
        })
        
    results_df = pd.DataFrame(results)
    
    # Analysis
    savings_pct = ((total_static_cost - total_dynamic_cost) / total_static_cost) * 100
    under_provision_pct = (under_provisioned_events / total_events) * 100
    
    print("\n--- Simulation Results ---")
    print(f"Total Intervals Evaluated: {total_events}")
    print(f"Static Provisioning Capacity: {static_capacity} users")
    print(f"Total Static Resource Units: {total_static_cost}")
    print(f"Total Dynamic Resource Units: {total_dynamic_cost}")
    print(f"Resource Savings: {savings_pct:.2f}%")
    print(f"Under-provisioned Intervals: {under_provisioned_events} ({under_provision_pct:.2f}%)")
    
    # Save Report
    with open('cost_optimization_report.txt', 'w') as f:
        f.write("--- Cost Optimization Analysis Report ---\n")
        f.write(f"Test Period Intervals: {total_events}\n")
        f.write(f"Static Capacity Set at: {static_capacity} (Max Historical + 10%)\n")
        f.write(f"Static Resource Consumption: {total_static_cost} units\n")
        f.write(f"Dynamic Resource Consumption: {total_dynamic_cost} units\n")
        f.write(f"Total Savings: {savings_pct:.2f}%\n")
        f.write(f"Risk: Under-provisioned events: {under_provisioned_events} ({under_provision_pct:.2f}%)\n")
        f.write("\nNote: 'Unit' represents one resource-slot for 15 minutes.\n")

    # Plot
    plt.figure(figsize=(15, 6))
    subset = 200 # First 200 intervals
    plt.plot(range(subset), results_df['Actual'].iloc[:subset], label='Actual Demand', color='black', alpha=0.6)
    plt.plot(range(subset), results_df['Static_Capacity'].iloc[:subset], label='Static Capacity', color='red', linestyle='--')
    plt.plot(range(subset), results_df['Dynamic_Capacity'].iloc[:subset], label='Dynamic Capacity', color='green', alpha=0.8)
    plt.fill_between(range(subset), results_df['Actual'].iloc[:subset], results_df['Dynamic_Capacity'].iloc[:subset], color='green', alpha=0.1, label='Saved Capacity')
    
    plt.title('Provisioning Simulation: Static vs Dynamic')
    plt.xlabel('Time Interval')
    plt.ylabel('User Capacity')
    plt.legend()
    plt.savefig('provisioning_simulation.png')
    print("Saved provisioning_simulation.png")

if __name__ == "__main__":
    run_simulation()
