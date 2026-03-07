import subprocess
import os
import sys
import time

def run_script(script_name):
    print(f"\n[{time.strftime('%H:%M:%S')}] Running {script_name}...")
    try:
        # Run the script and wait for it to finish
        result = subprocess.run([sys.executable, script_name], check=True)
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
    print("   User Login Prediction Model - Full Pipeline    ")
    print("==================================================")
    print(f"Python Executable: {sys.executable}")
    print(f"Working Directory: {os.getcwd()}")
    
    # 1. Filter Logs
    # Optional step: Only run if log_data.csv exists, or if the user wants to regenerate logs
    # We'll try to run it, but if it fails (e.g. missing input), we check if we can proceed.
    if os.path.exists('log_data.csv'):
        if not run_script('filter_logs.py'):
            print("⚠️ filter_logs.py failed. Checking if we can proceed with existing intermediate files...")
            if not (os.path.exists('login_logs.csv') and os.path.exists('disconnect_logs.csv')):
                print("❌ Critical: login_logs.csv or disconnect_logs.csv missing. Cannot proceed.")
                return
    else:
        print("ℹ️ log_data.csv not found. Skipping filter_logs.py and assuming intermediate logs exist.")

    # 2. Calculate Concurrency
    if not run_script('calculate_concurrency.py'):
         print("❌ Pipeline stopped at calculate_concurrency.py")
         return

    # 3. Data Analysis & Feature Engineering
    if not run_script('data_analysis_and_prep.py'):
         print("❌ Pipeline stopped at data_analysis_and_prep.py")
         return

    # 4. Prediction Model
    if not run_script('prediction_model.py'):
         print("❌ Pipeline stopped at prediction_model.py")
         return

    # 5. Simulation
    if not run_script('simulation.py'):
         print("❌ Pipeline stopped at simulation.py")
         return

    print("\n==================================================")
    print("   Pipeline Execution Finished Successfully       ")
    print("==================================================")
    print("Outputs generated:")
    print(" 1. concurrency_report.csv")
    print(" 2. processed_data.csv")
    print(" 3. prediction_comparison.png")
    print(" 4. provisioning_simulation.png")
    print(" 5. active_users_over_time.png")
    print(" 6. model_metrics.txt")
    print(" 7. cost_optimization_report.txt")

if __name__ == "__main__":
    main()
