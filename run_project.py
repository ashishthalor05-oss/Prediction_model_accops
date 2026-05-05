import subprocess
import os
import sys
import time

def run_script(script_name, args=None):
    if args is None: args = []
    print(f"\n[{time.strftime('%H:%M:%S')}] Running {script_name}...")
    try:
        cmd = [sys.executable, script_name] + args
        result = subprocess.run(cmd, check=True)
        print(f"[OK] {script_name} completed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] running {script_name}. Exit code: {e.returncode}")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error running {script_name}: {e}")
        return False

def main():
    print("==================================================")
    print("   User Login Prediction Model - Login Only       ")
    print("==================================================")
    
    start_date = sys.argv[1] if len(sys.argv) > 1 else None
    end_date   = sys.argv[2] if len(sys.argv) > 2 else None
    
    # 1. Filter Logs
    if os.path.exists('log_data.csv'):
        run_script('filter_logs.py')
    
    # 2. Aggregate Logins (formerly calculate_concurrency)
    # This now produces processed_data.csv with 15m login counts
    if not run_script('calculate_concurrency.py'):
         print("Error: Pipeline stopped at aggregation step.")
         return

    # 3. Prediction Model (Training)
    model_args = []
    if start_date and end_date:
        model_args = [start_date, end_date]
    if not run_script('prediction_model.py', args=model_args):
         print("Error: Pipeline stopped at prediction_model.py")
         return

    print("\n==================================================")
    print("   Training Pipeline Finished Successfully        ")
    print("==================================================")
    print("Outputs generated:")
    print(" 1. processed_data.csv (Login intervals)")
    print(" 2. rf_model_login_count.joblib")
    print(" 3. model_metrics.txt")

if __name__ == "__main__":
    main()
