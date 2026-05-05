import re

with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Add the text variable and label safely beneath the Graph Frame
ui_setup_old = """        self.view_f = tk.Frame(main_f, bg='#020617')
        self.view_f.pack(side='right', fill='both', expand=True)
        
        self.img_label = tk.Label(self.view_f, bg='#020617')
        self.img_label.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.current_img_tk = None"""

ui_setup_new = """        self.view_f = tk.Frame(main_f, bg='#020617')
        self.view_f.pack(side='right', fill='both', expand=True)
        
        self.img_label = tk.Label(self.view_f, bg='#020617')
        self.img_label.pack(fill='both', expand=True, padx=10, pady=(10, 0))
        
        # Bottom Description Bar
        self.graph_desc_var = tk.StringVar(value="")
        self.graph_desc_lbl = tk.Label(self.view_f, textvariable=self.graph_desc_var, font=FONT, bg='#020617', fg='#93c5fd', justify='center', wraplength=700)
        self.graph_desc_lbl.pack(fill='x', side='bottom', pady=5)
        
        self.current_img_tk = None"""

if ui_setup_old in text:
    text = text.replace(ui_setup_old, ui_setup_new)
else:
    print("Warning: Could not find UI setup marker.")

# 2. Add the dynamic description parser inside _on_graph_select
select_old = """    def _on_graph_select(self, event):
        sel = self.graphs_listbox.curselection()
        if not sel: return
        filename = self.graphs_listbox.get(sel[0])"""

select_new = """    def _on_graph_select(self, event):
        sel = self.graphs_listbox.curselection()
        if not sel: return
        filename = self.graphs_listbox.get(sel[0])

        # Dynamic Descriptions
        desc = "No description available for this graph."
        if 'active_users' in filename:
            desc = "🎯 Total Active System Users: Shows the total number of people concurrently active on the platform."
        elif 'single_session_users' in filename:
            desc = "👤 Single Session Users: People logging in to use simple, non-intensive resources like Web Apps or Dashboards."
        elif 'multi_session_users' in filename:
            desc = "👥 Multi Session Users: People accessing heavy, virtualized desktops or computational shared resources."
        elif 'active_user_logins' in filename:
            desc = "🔑 Login Activity: Raw count of how many times users triggered successful login events during these periods."
        elif 'provisioning_simulation' in filename:
            desc = "🖥️ Server Logic: Shows how many physical servers the system would have allocated versus total active users."
        elif 'concurrency_report' in filename:
            desc = "⚡ Raw Concurrency: The direct mathematical peaks measured internally from your pure SQL Logs without ML."
        elif 'backtest_accuracy_chart' in filename or 'app_backtest' in filename:
            desc = "🧪 Blind Evaluation Backtest: How accurate the AI was at predicting the Future secretly compared to reality."
        elif 'simulation' in filename:
            desc = "💡 System Simulation: Mathematical representation of cost metrics and algorithmic load balancing decisions."

        self.graph_desc_var.set(f"📊 {filename}\\n{desc}")
  """

if select_old in text:
    text = text.replace(select_old, select_new)
else:
    print("Warning: Could not find graph_select marker.")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(text)
    
print("Descriptions injected into Dashboard.")
