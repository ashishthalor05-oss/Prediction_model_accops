import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.base import BaseEstimator, RegressorMixin
import matplotlib.pyplot as plt

class BaselineModel(BaseEstimator, RegressorMixin):
    def __init__(self):
        self.lookup_table = None
        self.global_mean = 0

    def fit(self, X, y):
        # Calculate mean active users for each (DayOfWeek, Hour, IsHoliday)
        # Using a copy to avoid SettingWithCopyWarning on the input X
        data = X.copy()
        data['target'] = y
        self.lookup_table = data.groupby(['DayOfWeek', 'Hour', 'IsHoliday'])['target'].mean().to_dict()
        self.global_mean = y.mean()
        return self

    def predict(self, X):
        predictions = []
        for _, row in X.iterrows():
            key = (row['DayOfWeek'], row['Hour'], row['IsHoliday'])
            pred = self.lookup_table.get(key, self.global_mean) # Fallback to global mean
            predictions.append(pred)
        return np.array(predictions)

def train_and_evaluate():
    input_file = 'processed_data.csv'
    print(f"Loading data from {input_file}...")
    try:
        df = pd.read_csv(input_file)
    except FileNotFoundError:
        print(f"Error: {input_file} not found.")
        return

    # Prepare specific time-based split
    # Sort just in case
    df = df.sort_values(by='Time Interval')
    

    # Define features and target
    # Define features and target
    features = ['Hour', 'DayOfWeek', 'IsWeekend', 'IsHoliday', 'IsOptionalHoliday', 'Month', 'Day']
    targets = []
    
    if 'Active Users' in df.columns:
        targets.append('Active Users')
    if 'Single Session Users' in df.columns:
        targets.append('Single Session Users')
    if 'Multi Session Users' in df.columns:
        targets.append('Multi Session Users')
    if 'Single Session Logins' in df.columns:
        targets.append('Single Session Logins')
    if 'Multi Session Logins' in df.columns:
        targets.append('Multi Session Logins')

    for target in targets:
        print(f"\n=== Training Model for {target} ===")
        # Use Random Split to handle non-stationary data (drift in user load)
        # in a real scenario, this implies frequent retraining.
        X = df[features]
        y = df[target]
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, shuffle=True)
        
        print(f"Training Data Size: {len(X_train)}")
        print(f"Testing Data Size: {len(X_test)}")

        # 1. Baseline Model
        print(f"\n--- Training Baseline Model ({target}) ---")
        baseline = BaselineModel()
        baseline.fit(X_train, y_train)
        baseline_preds = baseline.predict(X_test)
        
        baseline_mae = mean_absolute_error(y_test, baseline_preds)
        baseline_rmse = np.sqrt(mean_squared_error(y_test, baseline_preds))
        print(f"Baseline MAE: {baseline_mae:.4f}")
        print(f"Baseline RMSE: {baseline_rmse:.4f}")
        
        # 2. Random Forest Model
        print(f"\n--- Training Random Forest Model ({target}) ---")
        rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
        rf_model.fit(X_train, y_train)
        rf_preds = rf_model.predict(X_test)
        
        rf_mae = mean_absolute_error(y_test, rf_preds)
        rf_rmse = np.sqrt(mean_squared_error(y_test, rf_preds))
        print(f"Random Forest MAE: {rf_mae:.4f}")
        print(f"Random Forest RMSE: {rf_rmse:.4f}")
        
        # Comparison
        print("\n--- Model Comparison ---")
        improvement = ((baseline_mae - rf_mae) / baseline_mae) * 100
        print(f"Improvement over Baseline (MAE): {improvement:.2f}%")

        # Feature Importance
        print(f"\n--- Feature Importance ({target}) ---")
        importances = rf_model.feature_importances_
        feature_imp_df = pd.DataFrame({'Feature': features, 'Importance': importances})
        print(feature_imp_df.sort_values(by='Importance', ascending=False))

        # Save Model
        import joblib
        safe_target_name = target.replace(' ', '_').lower()
        model_filename = f'rf_model_{safe_target_name}.joblib'
        joblib.dump(rf_model, model_filename)
        print(f"Model saved to {model_filename}")

        # Visualization of Predictions
        plt.figure(figsize=(15, 6))
        
        # Plot a subset of test data for clarity (e.g., first 3 days of test set)
        sorted_indices = y_test.index.sort_values() # Sort via index to show time progression if random split was used but index preserved time order
        # Actually random split shuffles index too. 
        # But we can try to plot a small sample.
        subset_len = min(100, len(y_test))
        
        plt.plot(range(subset_len), y_test.iloc[:subset_len].values, label='Actual', color='black', alpha=0.7)
        plt.plot(range(subset_len), rf_preds[:subset_len], label='Random Forest', color='green', alpha=0.7)
        
        plt.title(f'Prediction Comparison ({target}) - First {subset_len} test samples')
        plt.xlabel('Sample')
        plt.ylabel(target)
        plt.legend()
        plt.savefig(f'prediction_comparison_{safe_target_name}.png')
        print(f"Saved prediction_comparison_{safe_target_name}.png")
    
    # Save metrics
    with open('model_metrics.txt', 'w') as f:
        f.write(f"Baseline MAE: {baseline_mae:.4f}\n")
        f.write(f"Baseline RMSE: {baseline_rmse:.4f}\n")
        f.write(f"RF MAE: {rf_mae:.4f}\n")
        f.write(f"RF RMSE: {rf_rmse:.4f}\n")
        f.write(f"Improvement: {improvement:.2f}%\n")

if __name__ == "__main__":
    train_and_evaluate()
