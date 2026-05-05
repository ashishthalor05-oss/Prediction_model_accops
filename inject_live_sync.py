import re

with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

sync_ui_code = """
        # --- NEW: Live SQL Sync UI Section ---
        sync_f = tk.Frame(p, bg=BG2, padx=10)
        sync_f.pack(fill='x', padx=15, pady=(15, 0))
        self._section(sync_f, '🔄  Real-Time Machine Learning Sync').pack(fill='x', anchor='w')
        
        sm_lbl = tk.Label(sync_f, text="Automatically pulls ONLY missing logs from the SQL Database\\nand merges them into your AI Model without downloading the whole past history again.", font=FONT_S, bg=BG2, fg=FG2, justify='left')
        sm_lbl.pack(anchor='w', pady=(8,4))
        
        btn_strip = tk.Frame(sync_f, bg=BG2)
        btn_strip.pack(fill='x', pady=5)
        
        self.sync_btn = self._btn(btn_strip, '⚡ Sync Latest Logs', SUCCESS, self._trigger_live_sync)
        self.sync_btn.pack(side='left')
        
        self.sync_status_lbl = tk.Label(btn_strip, text="", font=FONT, bg=BG2, fg=WARNING)
        self.sync_status_lbl.pack(side='left', padx=10)

    def _trigger_live_sync(self):
        auth = self.db_auth.get()
        user = self.db_user.get()
        pwd = self.db_pass.get()
        server = self.db_serv.get()
        db = self.db_name.get()
        table = self.db_tbl.get()
        
        if not all([server, db, table]):
            messagebox.showerror('Error', 'Please fill Server, Database, and Table fields in the section above first.')
            return
            
        self.sync_btn.config(state='disabled')
        self.sync_status_lbl.config(text="Status: Finding last log date...", fg=WARNING)
        
        def worker():
            try:
                # 1. Determine the last logged date
                last_date = None
                log_file = 'log_data.csv'
                if os.path.exists(log_file):
                    # We only need the last row's date to know where to resume
                    try:
                        import subprocess
                        # Read the last 50 lines to be safe and find the latest date
                        if os.name == 'nt':
                            res = subprocess.run(['powershell', '-Command', f"Get-Content {log_file} -Tail 50"], capture_output=True, text=True)
                            lines = res.stdout.strip().split('\\n')
                        else:
                            res = subprocess.run(['tail', '-n', '50', log_file], capture_output=True, text=True)
                            lines = res.stdout.strip().split('\\n')
                            
                        if lines and lines[-1].strip():
                            import pandas as pd
                            with open('_tmp_tail.csv', 'w', encoding='utf-8') as tf:
                                tf.write('\\n'.join(lines))
                            
                            df_tail = pd.read_csv('_tmp_tail.csv', header=None, on_bad_lines='skip')
                            # Look for any column that looks like a datetime
                            for col in df_tail.columns:
                                try:
                                    tail_dates = pd.to_datetime(df_tail[col], errors='coerce').dropna()
                                    if len(tail_dates) > 0:
                                        last_date = tail_dates.max().strftime('%Y-%m-%d')
                                        break
                                except:
                                    pass
                            
                            if os.path.exists('_tmp_tail.csv'): os.remove('_tmp_tail.csv')
                    except Exception as e:
                        print(f"Tail extraction failed: {e}")
                
                if not last_date:
                    self.after(0, lambda: self.sync_status_lbl.config(text="Status: No history found. Please run a full fetch first.", fg=DANGER))
                    return

                # Assuming today is the target
                from datetime import date
                today = date.today().strftime('%Y-%m-%d')
                
                if last_date >= today:
                    self.after(0, lambda: self.sync_status_lbl.config(text=f"Status: SQL Data is already Synced up to {last_date}!", fg=SUCCESS))
                    return
                
                self.after(0, lambda: self.sync_status_lbl.config(text=f"Status: Fetching missing SQL logs ({last_date} to {today})...", fg=WARNING))
                
                # 2. Append fetching
                cmd = [sys.executable, 'fetch_from_db.py', 
                       '--server', server, '--database', db, '--table', table,
                       '--from', last_date, '--to', today, '--output', '_tmp_new_logs.csv']
                       
                if auth == 'sql':
                    cmd.extend(['--auth', 'sql', '--user', user, '--password', pwd])
                else:
                    cmd.extend(['--auth', 'windows'])
                    
                import subprocess
                res = subprocess.run(cmd, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                
                if res.returncode != 0:
                    self.after(0, lambda: messagebox.showerror("Fetch Error", res.stderr))
                    self.after(0, lambda: self.sync_status_lbl.config(text="Status: SQL Filter Failed.", fg=DANGER))
                    return
                
                # If 0 rows fetched
                if 'SUCCESS: 0 rows fetched' in res.stdout or not os.path.exists('_tmp_new_logs.csv'):
                    self.after(0, lambda: self.sync_status_lbl.config(text=f"Status: SQL Database is identical. No new logins found.", fg=SUCCESS))
                    return
                
                # Append to existing log_data.csv
                self.after(0, lambda: self.sync_status_lbl.config(text=f"Status: Updating CSVs and Retraining ML Models...", fg=WARNING))
                
                with open('_tmp_new_logs.csv', 'r', encoding='utf-8') as f_new, open('log_data.csv', 'a', encoding='utf-8') as f_old:
                    f_old.write(f_new.read())
                    
                if os.path.exists('_tmp_new_logs.csv'): os.remove('_tmp_new_logs.csv')
                
                # Run the whole run_project.py pipeline smoothly in background
                res_pl = subprocess.run([sys.executable, 'run_project.py'], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                
                if res_pl.returncode == 0:
                    self.after(0, lambda: self.sync_status_lbl.config(text=f"Status: AI Model Sync Complete! Ready to predict.", fg=SUCCESS))
                else:
                    self.after(0, lambda: self.sync_status_lbl.config(text=f"Status: Pipeline ran into warnings.", fg=WARNING))
                    
            except Exception as e:
                 self.after(0, lambda: self.sync_status_lbl.config(text=f"Error: {e}", fg=DANGER))
            finally:
                 self.after(0, lambda: self.sync_btn.config(state='normal'))
                 
        import threading
        import sys
        import os
        threading.Thread(target=worker, daemon=True).start()

"""

# Finding the preview section marker
end_of_import_tab_marker = "        # Preview section\n        self._section(p, '👁  Preview Imported File').pack(fill='x', padx=15, pady=(14,2))"

parts = text.split(end_of_import_tab_marker)
if len(parts) == 2:
    text = parts[0] + sync_ui_code + end_of_import_tab_marker + parts[1]
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Injection complete.")
else:
    print("Could not find exact import tab marker.")
