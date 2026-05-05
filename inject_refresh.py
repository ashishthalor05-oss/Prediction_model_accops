import re

with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

# We need to find the specific injection we made earlier which triggers the run_project subprocess logic inside _trigger_live_sync's worker definition.
old_completion_code = """                res_pl = subprocess.run([sys.executable, 'run_project.py'], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                
                if res_pl.returncode == 0:
                    self.after(0, lambda: self.sync_status_lbl.config(text=f"Status: AI Model Sync Complete! Ready to predict.", fg=SUCCESS))
                else:
                    self.after(0, lambda: self.sync_status_lbl.config(text=f"Status: Pipeline ran into warnings.", fg=WARNING))"""
                    
new_completion_code = """                res_pl = subprocess.run([sys.executable, 'run_project.py'], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                
                if res_pl.returncode == 0:
                    self.after(0, lambda: self.sync_status_lbl.config(text=f"Status: Active Model Sync Complete! Graphs auto-refreshed.", fg=SUCCESS))
                    # Auto-refresh the graphs dashboard immediately so real-time images pop up!
                    self.after(0, self._refresh_graphs_list)
                else:
                    self.after(0, lambda: self.sync_status_lbl.config(text=f"Status: Pipeline completed with warnings.", fg=WARNING))
                    self.after(0, self._refresh_graphs_list)"""

if old_completion_code in text:
    text = text.replace(old_completion_code, new_completion_code)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Graph auto-refresh injected.")
else:
    print("Could not find the target code string.")
