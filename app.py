"""
app.py — Resource Usage Prediction Model — Main Frontend
──────────────────────────────────────────────────────────
Tabs:
  1. Run Prediction   — input date range, run model, view output
  2. Import Data      — upload CSV/Excel log file or concurrency report
  3. Employee Leaves  — submit / view / delete employee leave records
  4. Results Viewer   — browse saved prediction CSV files
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinterdnd2 import TkinterDnD, DND_FILES
import pandas as pd
from load_holidays import load_holidays
import os
import sys
import subprocess
import threading
from datetime import datetime, timedelta, date
import shutil
import configparser
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# ── colour palette ─────────────────────────────────────────────────────────────
BG        = '#0b0f19' # Deeper dark
BG2       = '#111827' # Section backgrounds
BG3       = '#1f2937' # Highlights / Borders
ACCENT    = '#8b5cf6' # Violet accent
ACCENT2   = '#7c3aed' # Darker violet
SUCCESS   = '#10b981' # Emerald green
WARNING   = '#f59e0b' # Amber
DANGER    = '#f43f5e' # Rose red
FG        = '#f9fafb' # Near white
FG2       = '#9ca3af' # Muted grey
FONT      = ('Inter', 10)
FONT_B    = ('Inter', 10, 'bold')
FONT_T    = ('Inter', 15, 'bold')
FONT_S    = ('Inter', 9)
CODE      = ('JetBrains Mono', 9)

LEAVE_FILE = 'employee_leaves.csv'
LEAVE_COLS = ['Employee Name','Start Date','End Date','Leave Type','Half Day','Description','Submitted On']
HR_COLS    = [
    'Employee Number','Employee Name','UserId','Job Title',
    'Business Unit','Department','Sub Department','Location',
    'Cost Center','Reporting Manager','Leave Types',
    'From Date','From Session','To Date','To Session',
    'Total Duration','Unit','Requested On','Requested By',
    'Note','Reason','Status','Last Action Taken by',
    'Last Action Taken on','Next Approver',
]


class ScrollableTab(tk.Frame):
    def __init__(self, parent, bg_color):
        super().__init__(parent, bg=bg_color)
        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0, bg=bg_color)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=bg_color)
        self.scrollable_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self.scrollable_window, width=e.width)
        )
        
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.scrollable_frame.bind("<Enter>", self._bind_mouse)
        self.scrollable_frame.bind("<Leave>", self._unbind_mouse)
        self.canvas.bind("<Enter>", self._bind_mouse)
        self.canvas.bind("<Leave>", self._unbind_mouse)
        
    def _bind_mouse(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
    def _unbind_mouse(self, event):
        self.canvas.unbind_all("<MouseWheel>")
        
    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

# ══════════════════════════════════════════════════════════════════════════════
class App(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title('Resource Usage Prediction Model')
        self.geometry('960x680')
        self.minsize(860, 580)
        self.configure(bg=BG)
        self._build_header()
        self._build_tabs()

    # ── Top header ─────────────────────────────────────────────────────────────
    def _build_header(self):
        hdr = tk.Frame(self, bg=BG, pady=15)
        hdr.pack(fill='x')
        
        # Glow effect / Title
        title_f = tk.Frame(hdr, bg=BG)
        title_f.pack(side='left', padx=30)
        
        tk.Label(title_f, text='🖥  Resource Usage Prediction',
                 font=FONT_T, bg=BG, fg=ACCENT).pack(side='top', anchor='w')
        tk.Label(title_f, text='AI-DRIVEN CAPACITY PLANNING ENGINE',
                 font=('Inter', 8, 'bold'), bg=BG, fg=FG2).pack(side='top', anchor='w', pady=(2,0))
        
        # Bottom divider for header
        tk.Frame(self, bg=BG3, height=1).pack(fill='x')

    # ── Tabs ───────────────────────────────────────────────────────────────────
    def _build_tabs(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('TNotebook',          background=BG,  borderwidth=0)
        style.configure('TNotebook.Tab',      background=BG3, foreground=FG2,
                        padding=[12, 6], font=('Inter', 10, 'bold'))
        style.map('TNotebook.Tab',
                  background=[('selected', BG2)],
                  foreground=[('selected', ACCENT)])

        style.configure('Treeview',           background=BG2, fieldbackground=BG2,
                        foreground=FG,        rowheight=30,   font=FONT_S, borderwidth=0)
        style.configure('Treeview.Heading',   background=BG, foreground=ACCENT,
                        font=FONT_B,          relief='flat')
        style.map('Treeview', 
                  background=[('selected', ACCENT)],
                  foreground=[('selected', 'white')])
        
        # Row alternating colors logic is usually done in the loading phase, 
        # but I'll set the base style here.
        style.configure('TCombobox', fieldbackground=BG3, background=BG3,
                        foreground=FG, selectbackground=ACCENT)

        self.main_nb = ttk.Notebook(self)
        self.main_nb.pack(fill='both', expand=True, padx=10, pady=(6,10))


        self.tab_predict  = ScrollableTab(self.main_nb, bg_color=BG2)
        self.tab_import   = ScrollableTab(self.main_nb, bg_color=BG2)
        self.tab_leave    = ScrollableTab(self.main_nb, bg_color=BG2)
        self.tab_holiday  = ScrollableTab(self.main_nb, bg_color=BG2)
        self.tab_backtest = ScrollableTab(self.main_nb, bg_color=BG2)
        self.tab_results  = ScrollableTab(self.main_nb, bg_color=BG2)
        self.tab_userpred = ScrollableTab(self.main_nb, bg_color=BG2)
        self.tab_usermaster = ScrollableTab(self.main_nb, bg_color=BG2)
        self.tab_graphs   = ttk.Frame(self.main_nb) # Changed to standard Frame to fix geometry

        self.main_nb.add(self.tab_predict,  text=' 🚀 PREDICTION ')
        self.main_nb.add(self.tab_import,   text=' 📥 IMPORT ')
        self.main_nb.add(self.tab_leave,    text=' 📝 LEAVES ')
        self.main_nb.add(self.tab_holiday,  text=' 🗓️ HOLIDAYS ')
        self.main_nb.add(self.tab_backtest, text=' 🎯 BACKTEST ')
        self.main_nb.add(self.tab_results,  text=' 📂 RESULTS ')
        self.main_nb.add(self.tab_userpred, text=' 👤 USERS ')
        self.main_nb.add(self.tab_usermaster, text=' 👥 USER MASTER ')
        self.main_nb.add(self.tab_graphs,   text=' 📊 GRAPHS ')

        self._build_predict_tab()
        self._build_import_tab()
        self._build_leave_tab()
        self._build_holiday_tab()
        self._build_backtest_tab()
        self._build_results_tab()
        self._build_user_prediction_tab()
        self._build_user_master_tab()
        self._build_graphs_tab()


    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — Run Prediction
    # ══════════════════════════════════════════════════════════════════════════
    def _build_predict_tab(self):
        p = self.tab_predict.scrollable_frame
        self._section(p, '⚙️  Prediction Settings').pack(fill='x', padx=15, pady=(12,4))

        # Form helpers
        def lbl(text, parent, row, col):
            tk.Label(parent, text=text, font=FONT, bg=parent['bg'], fg=FG2, anchor='w'
                     ).grid(row=row, column=col, sticky='w', padx=8, pady=5)
        def ent(parent, row, col, default='', width=18):
            # Using a slightly lighter background for better input contrast
            e = tk.Entry(parent, font=FONT, width=width, bg=BG3, fg=FG,
                         insertbackground=ACCENT, relief='flat', bd=0, highlightthickness=1,
                         highlightbackground=BG3, highlightcolor=ACCENT)
            e.grid(row=row, column=col, sticky='ew', padx=8, pady=5)
            e.insert(0, default)
            return e

        tomorrow = (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')
        next_week = (date.today() + timedelta(days=7)).strftime('%Y-%m-%d')
        ninety_ago = (date.today() - timedelta(days=90)).strftime('%Y-%m-%d')
        today      = date.today().strftime('%Y-%m-%d')

        self._section(p, '⚙️  Train Model (Optional)').pack(fill='x', padx=15, pady=(10,4))
        train_form = tk.Frame(p, bg=BG2)
        train_form.pack(fill='x', padx=15, pady=2)
        
        lbl('Train From Date:', train_form, 0, 0)
        self.train_start = ent(train_form, 0, 1, default=ninety_ago, width=14)
        lbl('Train To Date:', train_form, 0, 2)
        self.train_end = ent(train_form, 0, 3, default=today, width=14)
        self._btn(train_form, '⚙️ Train Models', ACCENT2, self._run_training).grid(row=0, column=4, padx=12, pady=4)


        self._section(p, '🔮  Run Prediction').pack(fill='x', padx=15, pady=(15,4))
        pred_form = tk.Frame(p, bg=BG2)
        pred_form.pack(fill='x', padx=15, pady=2)

        lbl('Start Date (YYYY-MM-DD)', pred_form, 0, 0);  self.pred_start = ent(pred_form, 0, 1, tomorrow)
        lbl('End Date   (YYYY-MM-DD)', pred_form, 0, 2);  self.pred_end   = ent(pred_form, 0, 3, next_week)
        
        lbl('Prediction Window', pred_form, 0, 4)
        self.pred_window = tk.StringVar(value='15m')
        cb = ttk.Combobox(pred_form, textvariable=self.pred_window, values=['15m', '30m', '60m', 'all'], 
                          state='readonly', width=10, font=FONT)
        cb.grid(row=0, column=5, padx=8, pady=5)

        # Buttons
        bf = tk.Frame(p, bg=BG2)
        bf.pack(pady=8)
        self._btn(bf, '▶  Run Prediction', ACCENT2,   self._run_prediction).pack(side='left', padx=6)
        self._btn(bf, '📁  Export to Excel', SUCCESS, self._export_prediction_excel).pack(side='left', padx=6)
        self._btn(bf, '📊 Batch Daily Graphs', ACCENT, self._run_batch_daily_graphs_predict).pack(side='left', padx=6)

        # Status
        self.pred_status = tk.StringVar(value='Ready.')
        tk.Label(p, textvariable=self.pred_status, font=FONT_S,
                 bg=BG2, fg=FG2).pack(pady=2)

        # Output log
        self._section(p, '📄  Output Log').pack(fill='x', padx=15, pady=(8,2))
        self.pred_log = tk.Text(p, height=10, font=CODE, bg=BG, fg='#10b981',
                                insertbackground='white', relief='flat', state='disabled',
                                padx=10, pady=10)
        self.pred_log.pack(fill='both', expand=True, padx=15, pady=(0,10))

    def _run_prediction(self):
        start = self.pred_start.get().strip()
        end   = self.pred_end.get().strip()
        if not start or not end:
            messagebox.showerror('Missing', 'Please enter Start and End dates.'); return

        self.pred_status.set('Running prediction…')
        self._log_clear()

        def worker():
            try:
                win = self.pred_window.get()
                cmd = [sys.executable, 'predict_future.py', start, end, '--window', win]
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, text=True,
                                        cwd=os.getcwd())
                for line in proc.stdout:
                    self._log(line.rstrip())
                proc.wait()
                self.pred_status.set('✅ Prediction complete.')
                
                # Auto-select the latest file in the Result Viewer
                self._refresh_results()
                # Find the index of the new file
                new_file = f"backtest_{win}_{start}_to_{end}.csv"
                try:
                    for i in range(self.results_lb.size()):
                        if self.results_lb.get(i) == new_file:
                            self.results_lb.select_set(i)
                            self.results_lb.see(i)
                            break
                except: pass
                
                self._refresh_graphs_list()
            except Exception as e:
                self._log(f'ERROR: {e}')
                self.pred_status.set('❌ Error during prediction.')

        threading.Thread(target=worker, daemon=True).start()

    def _run_training(self):
        start = self.train_start.get().strip()
        end   = self.train_end.get().strip()
        if not start or not end:
            messagebox.showerror('Missing', 'Please enter Train From and Train To dates.'); return

        self.pred_status.set('Training Models...')
        self._log_clear()

        def worker():
            self._btn_disable_all()
            try:
                cmd = [sys.executable, 'run_project.py', start, end]
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, text=True,
                                        cwd=os.getcwd())
                for line in proc.stdout:
                    self._log(line.rstrip())
                proc.wait()
                if proc.returncode == 0:
                    self.pred_status.set('✅ Training complete.')
                    self._refresh_graphs_list()
                else:
                    self.pred_status.set('❌ Error during training.')
            except Exception as e:
                self._log(f'ERROR: {e}')
                self.pred_status.set('❌ Exception running training.')
            finally:
                self._btn_enable_all()

        threading.Thread(target=worker, daemon=True).start()

    def _btn_disable_all(self):
        for w in self.tab_predict.winfo_children():
            if isinstance(w, tk.Frame):
                for child in w.winfo_children():
                    if isinstance(child, tk.Button):
                        child.configure(state='disabled')

    def _btn_enable_all(self):
        for w in self.tab_predict.winfo_children():
            if isinstance(w, tk.Frame):
                for child in w.winfo_children():
                    if isinstance(child, tk.Button):
                        child.configure(state='normal')

    def _export_prediction_excel(self):
        files = [f for f in os.listdir('.') if f.startswith('prediction_') and f.endswith('.csv')]
        if not files:
            messagebox.showinfo('No Files', 'Run a prediction first.'); return
        latest = sorted(files)[-1]
        df = pd.read_csv(latest)
        out = latest.replace('.csv', '.xlsx')
        df.to_excel(out, index=False, engine='openpyxl')
        messagebox.showinfo('Exported ✅', f'Saved to {out}')

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — Import Data
    # ══════════════════════════════════════════════════════════════════════════
    def _build_import_tab(self):
        p = self.tab_import.scrollable_frame

        # ── DB Connection Section ──────────────────────────────────────────────
        self._section(p, '🗄  Fetch from SQL Server Express').pack(fill='x', padx=15, pady=(12,2))

        db_outer = tk.Frame(p, bg=BG2, relief='flat', bd=0)
        db_outer.pack(fill='x', padx=15, pady=(0,6))

        db_form = tk.Frame(db_outer, bg=BG2, padx=10, pady=8)
        db_form.pack(fill='x')

        def dlbl(text, row, col, colspan=1):
            tk.Label(db_form, text=text, font=FONT, bg=BG2, fg=FG2, anchor='w'
                     ).grid(row=row, column=col, columnspan=colspan, sticky='w', padx=6, pady=3)

        def dent(row, col, default='', width=22, show=''):
            e = tk.Entry(db_form, font=FONT, width=width, bg=BG3, fg=FG,
                         insertbackground=ACCENT, relief='flat', bd=0, highlightthickness=1,
                         highlightbackground=BG3, highlightcolor=ACCENT, show=show)
            e.grid(row=row, column=col, sticky='ew', padx=6, pady=3)
            e.insert(0, default)
            return e

        # Row 0 — Server & Database
        dlbl('Server\\Instance',  0, 0)
        self.db_server = dent(0, 1, default=r'.\SQLEXPRESS', width=22)
        dlbl('Database Name', 0, 2)
        self.db_name   = dent(0, 3, default='', width=22)

        # Row 1 — Table & Auth type
        dlbl('Table Name', 1, 0)
        self.db_table  = dent(1, 1, default='Logs', width=22)
        dlbl('Authentication', 1, 2)
        self.db_auth = tk.StringVar(value='windows')
        auth_f = tk.Frame(db_form, bg=BG2)
        auth_f.grid(row=1, column=3, sticky='w', padx=6)
        tk.Radiobutton(auth_f, text='Windows Auth', variable=self.db_auth, value='windows',
                       bg=BG2, fg=FG, selectcolor=BG, activebackground=BG2,
                       font=FONT, command=self._db_toggle_auth, indicatoron=0, 
                       padx=10, pady=4, cursor='hand2').pack(side='left')
        tk.Radiobutton(auth_f, text='SQL Auth', variable=self.db_auth, value='sql',
                       bg=BG2, fg=FG, selectcolor=BG, activebackground=BG2,
                       font=FONT, command=self._db_toggle_auth, indicatoron=0,
                       padx=10, pady=4, cursor='hand2').pack(side='left', padx=8)

        # Row 2 — SQL Auth credentials (hidden by default)
        dlbl('Username', 2, 0)
        self.db_user = dent(2, 1, default='', width=22)
        dlbl('Password', 2, 2)
        self.db_pass = dent(2, 3, default='', width=22, show='*')
        self.db_cred_labels = []
        self.db_cred_entries = [self.db_user, self.db_pass]
        # store references to the grid labels too
        for w in db_form.grid_slaves(row=2):
            self.db_cred_labels.append(w)

        # Row 3 — Date range
        today      = date.today()
        ninety_ago = (today - timedelta(days=90)).strftime('%Y-%m-%d')
        dlbl('From Date (YYYY-MM-DD)', 3, 0)
        self.db_from = dent(3, 1, default=ninety_ago, width=18)
        dlbl('To Date   (YYYY-MM-DD)', 3, 2)
        self.db_to   = dent(3, 3, default=today.strftime('%Y-%m-%d'), width=18)

        # Row 4 — Buttons
        btn_f = tk.Frame(db_form, bg=BG2)
        btn_f.grid(row=4, column=0, columnspan=4, pady=(6,2), sticky='w', padx=4)
        self._btn(btn_f, '🔌 Test Connection', ACCENT2,  self._db_test).pack(side='left', padx=4)
        self._btn(btn_f, '⬇  Fetch Data',      SUCCESS,  self._db_fetch).pack(side='left', padx=4)
        self.db_status_lbl = tk.Label(btn_f, text='', font=FONT_S, bg=BG2, fg=FG2)
        self.db_status_lbl.pack(side='left', padx=10)

        # Row 5 — Mini log
        self.db_log = tk.Text(db_outer, height=4, font=CODE, bg=BG, fg=ACCENT,
                              relief='flat', state='disabled', padx=10, pady=8)
        self.db_log.pack(fill='x', padx=10, pady=(0,8))

        # Load saved settings
        self._db_load_config()
        # Apply initial auth visibility
        self._db_toggle_auth()

        # ── File Import Section ────────────────────────────────────────────────
        self._section(p, '📤  Import Input Files (CSV or Excel)').pack(fill='x', padx=15, pady=(8,4))
        tk.Label(p, text='💡 Tip: You can also drag & drop files from File Explorer directly onto each row below',
                 font=FONT_S, bg=BG2, fg=WARNING).pack(padx=15, anchor='w', pady=(0,4))

        imports = [
            ('📄 Raw Log File',          'log_data.csv',              'Import raw system log data', None),
            ('📈 Concurrency Report',    'concurrency_report.csv',    'Import pre-computed concurrency report', None),
            ('🏖️ Holidays File',         'holidays.csv',              'Import holiday list (Date/Start Date/End Date/Type)', 3),
            ('📅 Employee Leaves',       LEAVE_FILE,                  'Import employee leave records', 2),
        ]

        for label, fname, hint, t_idx in imports:
            row = tk.Frame(p, bg=BG2, pady=10, padx=12)
            row.pack(fill='x', padx=15, pady=4)
            tk.Label(row, text=label, font=FONT_B, bg=BG2, fg=FG,  width=22, anchor='w').pack(side='left')
            tk.Label(row, text=hint,  font=FONT_S, bg=BG2, fg=FG2, width=32, anchor='w').pack(side='left')
            # Drag & drop zone label
            dnd_lbl = tk.Label(row, text='⬇ Drop here', font=FONT_S, bg=BG3,
                               fg=ACCENT, width=12, relief='flat', pady=4, cursor='hand2')
            dnd_lbl.pack(side='left', padx=6)
            self._make_drop_target(dnd_lbl, row, fname)
            
            # Quick Edit Button
            if t_idx is not None:
                self._btn(row, '📝 Edit', BG3, lambda i=t_idx: self.main_nb.select(i)).pack(side='right', padx=4)
            self._btn(row, '📂 Browse', ACCENT2,
                      lambda f=fname: self._browse_import(f)).pack(side='right', padx=4)
            # Status indicator
            if fname == 'holidays.csv':
                exists_bool = os.path.exists('holidays.csv') or os.path.exists('holidays.xlsx')
            else:
                exists_bool = os.path.exists(fname)
            exists = '✅ Exists' if exists_bool else '❌ Missing'
            color  = SUCCESS if exists_bool else DANGER
            tk.Label(row, text=exists, font=FONT_S, bg=BG2, fg=color, width=10).pack(side='right', padx=4)

        # ── Special row: Employee Holidays (HR Excel) ──────────────────────────
        hr_row = tk.Frame(p, bg=BG2, pady=10, padx=12, highlightthickness=1, highlightbackground=SUCCESS)
        hr_row.pack(fill='x', padx=15, pady=6)
        tk.Label(hr_row, text='📁 Employee Holidays\n(HR Excel)',
                 font=FONT_B, bg=BG2, fg=SUCCESS, width=22, anchor='w').pack(side='left')
        tk.Label(hr_row, text='Planned & Unplanned leaves from HR system',
                 font=FONT_S, bg=BG2, fg=FG2, width=32, anchor='w').pack(side='left')
        hr_dnd = tk.Label(hr_row, text='⬇ Drop here', font=FONT_S, bg=BG3,
                          fg=ACCENT, width=12, relief='flat', pady=4, cursor='hand2')
        hr_dnd.pack(side='left', padx=6)
        self._make_hr_drop_target(hr_dnd)
        self._btn(hr_row, '📂 Browse', SUCCESS,
                  self._browse_hr_excel).pack(side='right', padx=4)
        self._btn(hr_row, '📝 Edit Records', BG3, lambda: self.main_nb.select(2)).pack(side='right', padx=4)
        count_lbl_text = f'📋 {len(self._load_leaves())} records' if os.path.exists(LEAVE_FILE) else '❌ No leaves yet'
        count_color    = SUCCESS if os.path.exists(LEAVE_FILE) else DANGER
        tk.Label(hr_row, text=count_lbl_text, font=FONT_S, bg=BG2,
                 fg=count_color, width=14).pack(side='right', padx=4)


        # --- NEW: Live SQL Sync UI Section ---
        sync_f = tk.Frame(p, bg=BG2, padx=10)
        sync_f.pack(fill='x', padx=15, pady=(15, 0))
        self._section(sync_f, '🔄  Real-Time Machine Learning Sync').pack(fill='x', anchor='w')
        
        sm_lbl = tk.Label(sync_f, text="Automatically pulls ONLY missing logs from the SQL Database\nand merges them into your AI Model without downloading the whole past history again.", font=FONT_S, bg=BG2, fg=FG2, justify='left')
        sm_lbl.pack(anchor='w', pady=(8,4))
        
        btn_strip = tk.Frame(sync_f, bg=BG2)
        btn_strip.pack(fill='x', pady=5)
        
        self.sync_btn = self._btn(btn_strip, '⚡ Sync Latest Logs', SUCCESS, self._trigger_live_sync)
        self.sync_btn.pack(side='left')
        
        self.sync_status_lbl = tk.Label(btn_strip, text="", font=FONT, bg=BG2, fg=WARNING)
        self.sync_status_lbl.pack(side='left', padx=10)


        # Preview section
        self._section(p, '👁  Preview Imported File').pack(fill='x', padx=15, pady=(14,2))

        pf = tk.Frame(p, bg=BG2)
        pf.pack(fill='x', padx=15)
        self.import_path_var = tk.StringVar(value='No file selected')
        tk.Label(pf, textvariable=self.import_path_var, font=FONT_S,
                 bg=BG2, fg=FG2).pack(side='left')
        self._btn(pf, '👁 Preview Any File', BG3, self._preview_any).pack(side='right')

        self.import_tree_frame = tk.Frame(p, bg=BG2)
        self.import_tree_frame.pack(fill='both', expand=True, padx=15, pady=(4,10))
        self.import_tree = None

    def _trigger_live_sync(self):
        auth = self.db_auth.get()
        user = self.db_user.get()
        pwd = self.db_pass.get()
        server = self.db_server.get() # Corrected from db_serv
        db = self.db_name.get()
        table = self.db_table.get() # Corrected from db_tbl
        
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
                            lines = res.stdout.strip().split('\n')
                        else:
                            res = subprocess.run(['tail', '-n', '50', log_file], capture_output=True, text=True)
                            lines = res.stdout.strip().split('\n')
                            
                        if lines and lines[-1].strip():
                            import pandas as pd
                            with open('_tmp_tail.csv', 'w', encoding='utf-8') as tf:
                                tf.write('\n'.join(lines))
                            
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
                    self.after(0, lambda: self.sync_status_lbl.config(text=f"Status: Active Model Sync Complete! Graphs auto-refreshed.", fg=SUCCESS))
                    # Auto-refresh the graphs dashboard immediately so real-time images pop up!
                    self.after(0, self._refresh_graphs_list)
                else:
                    self.after(0, lambda: self.sync_status_lbl.config(text=f"Status: Pipeline completed with warnings.", fg=WARNING))
                    self.after(0, self._refresh_graphs_list)
                    
            except Exception as e:
                 self.after(0, lambda: self.sync_status_lbl.config(text=f"Error: {e}", fg=DANGER))
            finally:
                 self.after(0, lambda: self.sync_btn.config(state='normal'))
                 
        import threading
        import sys
        import os
        threading.Thread(target=worker, daemon=True).start()


    def _make_drop_target(self, widget, row_frame, target_filename):
        """Register a widget as a drag-and-drop target for a specific file."""
        def on_drop(event):
            print(f"DEBUG: Drop detected! Data: {event.data}")
            # Clean up the path from tkinterdnd2 (it often adds {} around paths with spaces)
            path = event.data.strip()
            if path.startswith('{') and path.endswith('}'):
                path = path[1:-1]
            elif path.startswith('"') and path.endswith('"'):
                path = path[1:-1]
            
            if not os.path.exists(path):
                messagebox.showerror('Drop Error', f'File not found:\n{path}'); return
            try:
                # Handle holidays Excel files specially
                actual_target = target_filename
                if target_filename == 'holidays.csv' and path.lower().endswith(('.xlsx', '.xls')):
                    actual_target = 'holidays.xlsx'
                    if os.path.exists('holidays.csv'): os.remove('holidays.csv')
                elif target_filename == 'holidays.csv' and path.lower().endswith('.csv'):
                    if os.path.exists('holidays.xlsx'): os.remove('holidays.xlsx')
                
                shutil.copy2(path, os.path.join(os.getcwd(), actual_target))
                # Flash the drop zone green to confirm
                widget.configure(bg=SUCCESS, text='✅ Imported!')
                self.after(2000, lambda: widget.configure(bg=BG3, text='⬇ Drop here'))
                messagebox.showinfo('Imported ✅', f'File saved as  {actual_target}')
                self.import_path_var.set(actual_target)
                self._preview_file(actual_target)
            except Exception as e:
                messagebox.showerror('Drop Error', str(e))

        def on_enter(event): widget.configure(bg=ACCENT2)
        def on_leave(event): widget.configure(bg=BG3)

        widget.drop_target_register(DND_FILES)
        widget.dnd_bind('<<Drop>>',      on_drop)
        widget.dnd_bind('<<DragEnter>>', on_enter)
        widget.dnd_bind('<<DragLeave>>', on_leave)

    def _make_hr_drop_target(self, widget):
        """Drop target for the HR Excel holiday file — calls import_employee_holidays.py."""
        def on_drop(event):
            # Clean up the path from tkinterdnd2
            path = event.data.strip()
            if path.startswith('{') and path.endswith('}'):
                path = path[1:-1]
            elif path.startswith('"') and path.endswith('"'):
                path = path[1:-1]
                
            if not os.path.exists(path):
                messagebox.showerror('Drop Error', f'File not found:\n{path}'); return
            widget.configure(bg=SUCCESS, text='⏳ Importing...')
            self.after(100, lambda: self._run_hr_import(path, widget))

        def on_enter(event): widget.configure(bg=ACCENT2)
        def on_leave(event): widget.configure(bg=BG3)

        widget.drop_target_register(DND_FILES)
        widget.dnd_bind('<<Drop>>',      on_drop)
        widget.dnd_bind('<<DragEnter>>', on_enter)
        widget.dnd_bind('<<DragLeave>>', on_leave)

    def _browse_hr_excel(self):
        path = filedialog.askopenfilename(
            title='Select HR Employee Holiday Excel',
            filetypes=[('Excel/CSV', '*.xlsx *.xls *.csv'), ('All', '*.*')])
        if path:
            self._run_hr_import(path, widget=None)

    def _run_hr_import(self, path, widget=None):
        """Call import_employee_holidays.py in a thread and show result."""
        def worker():
            try:
                result = subprocess.run(
                    [sys.executable, 'import_employee_holidays.py', path],
                    capture_output=True, text=True, cwd=os.getcwd()
                )
                output  = result.stdout + result.stderr
                # Parse added/skipped from output
                added   = next((l for l in output.splitlines() if 'Added' in l), '')
                if widget:
                    self.after(0, lambda: widget.configure(bg=BG3, text='⬇ Drop here'))
                self.import_path_var.set(LEAVE_FILE)
                self._preview_file(LEAVE_FILE)
                messagebox.showinfo('HR Holidays Imported ✅',
                                    f'{added}\n\nAll records merged into {LEAVE_FILE}.')
                self._refresh_leaves()
            except Exception as e:
                if widget:
                    self.after(0, lambda: widget.configure(bg=BG3, text='⬇ Drop here'))
                messagebox.showerror('Import Error', str(e))

        threading.Thread(target=worker, daemon=True).start()

    def _browse_import(self, target_filename):
        path = filedialog.askopenfilename(
            title=f'Select file to import',
            filetypes=[('CSV/Excel', '*.csv *.xlsx *.xls'), ('All', '*.*')])
        if not path: return
        try:
            # Handle holidays Excel files specially
            actual_target = target_filename
            if target_filename == 'holidays.csv' and path.lower().endswith(('.xlsx', '.xls')):
                actual_target = 'holidays.xlsx'
                if os.path.exists('holidays.csv'): os.remove('holidays.csv')
            elif target_filename == 'holidays.csv' and path.lower().endswith('.csv'):
                if os.path.exists('holidays.xlsx'): os.remove('holidays.xlsx')

            shutil.copy2(path, os.path.join(os.getcwd(), actual_target))
            messagebox.showinfo('Imported ✅', f'File saved as {actual_target}')
            self.import_path_var.set(actual_target)
            self._preview_file(actual_target)
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def _preview_any(self):
        path = filedialog.askopenfilename(
            filetypes=[('CSV/Excel', '*.csv *.xlsx'), ('All', '*.*')])
        if path:
            self.import_path_var.set(os.path.basename(path))
            self._preview_file(path)

    def _preview_file(self, path):
        try:
            if path.endswith('.xlsx') or path.endswith('.xls'):
                df = pd.read_excel(path, engine='openpyxl', nrows=100)
            else:
                df = pd.read_csv(path, nrows=100)
        except Exception as e:
            messagebox.showerror('Preview Error', str(e)); return

        for w in self.import_tree_frame.winfo_children():
            w.destroy()

        cols = list(df.columns)
        tree = ttk.Treeview(self.import_tree_frame, columns=cols, show='headings', height=8)
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c,  width=max(80, min(180, len(c)*12)), anchor='center')
        for _, row in df.iterrows():
            tree.insert('', 'end', values=list(row))
        vsb = ttk.Scrollbar(self.import_tree_frame, orient='vertical',   command=tree.yview)
        hsb = ttk.Scrollbar(self.import_tree_frame, orient='horizontal',  command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        self.import_tree_frame.rowconfigure(0, weight=1)
        self.import_tree_frame.columnconfigure(0, weight=1)

    # ══════════════════════════════════════════════════════════════════════════
    # DB Helper Methods
    # ══════════════════════════════════════════════════════════════════════════
    DB_CONFIG_FILE = 'db_config.ini'

    def _db_toggle_auth(self):
        """Show/hide SQL Auth credential fields based on auth type selection."""
        show = self.db_auth.get() == 'sql'
        state = 'normal' if show else 'disabled'
        for w in self.db_cred_entries:
            w.configure(state=state, fg=FG if show else FG2)

    def _db_log_write(self, msg, color='#7dd3fc'):
        self.db_log.configure(state='normal')
        self.db_log.insert('end', msg + '\n')
        self.db_log.see('end')
        self.db_log.configure(state='disabled')

    def _db_log_clear(self):
        self.db_log.configure(state='normal')
        self.db_log.delete('1.0', 'end')
        self.db_log.configure(state='disabled')

    def _db_args(self):
        """Build the common CLI args list from form fields."""
        args = [
            sys.executable, 'fetch_from_db.py',
            '--server',   self.db_server.get().strip(),
            '--database', self.db_name.get().strip(),
            '--table',    self.db_table.get().strip(),
            '--auth',     self.db_auth.get(),
        ]
        if self.db_auth.get() == 'sql':
            args += ['--user', self.db_user.get().strip(),
                     '--password', self.db_pass.get()]
        return args

    def _db_test(self):
        """Test connection in background thread."""
        server = self.db_server.get().strip()
        dbname = self.db_name.get().strip()
        if not server or not dbname:
            messagebox.showerror('Missing Fields', 'Server and Database Name are required.'); return
        self._db_log_clear()
        self._db_log_write('Testing connection…')
        self.db_status_lbl.config(text='⏳ Connecting…', fg=WARNING)
        self._db_save_config()

        def worker():
            args = self._db_args() + ['--test']
            try:
                result = subprocess.run(args, capture_output=True, text=True, cwd=os.getcwd())
                output = (result.stdout + result.stderr).strip()
                for line in output.splitlines():
                    self.after(0, lambda l=line: self._db_log_write(l))
                if 'SUCCESS' in output:
                    self.after(0, lambda: self.db_status_lbl.config(text='✅ Connected', fg=SUCCESS))
                else:
                    self.after(0, lambda: self.db_status_lbl.config(text='❌ Failed', fg=DANGER))
            except Exception as e:
                self.after(0, lambda: self._db_log_write(f'ERROR: {e}'))
                self.after(0, lambda: self.db_status_lbl.config(text='❌ Error', fg=DANGER))

        threading.Thread(target=worker, daemon=True).start()

    def _db_fetch(self):
        """Fetch data from DB in background thread."""
        server  = self.db_server.get().strip()
        dbname  = self.db_name.get().strip()
        date_from = self.db_from.get().strip()
        date_to   = self.db_to.get().strip()
        if not server or not dbname:
            messagebox.showerror('Missing Fields', 'Server and Database Name are required.'); return
        if not date_from or not date_to:
            messagebox.showerror('Missing Fields', 'From Date and To Date are required.'); return
        # Validate dates
        try:
            datetime.strptime(date_from, '%Y-%m-%d')
            datetime.strptime(date_to,   '%Y-%m-%d')
        except ValueError:
            messagebox.showerror('Date Error', 'Dates must be in YYYY-MM-DD format.'); return

        self._db_log_clear()
        self._db_log_write(f'Fetching data from {date_from} to {date_to}…')
        self.db_status_lbl.config(text='⏳ Fetching…', fg=WARNING)
        self._db_save_config()

        def worker():
            args = self._db_args() + ['--from', date_from, '--to', date_to]
            try:
                proc = subprocess.Popen(args, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, text=True,
                                        cwd=os.getcwd())
                for line in proc.stdout:
                    self.after(0, lambda l=line.rstrip(): self._db_log_write(l))
                proc.wait()
                if proc.returncode == 0:
                    self.after(0, lambda: self.db_status_lbl.config(
                        text='✅ log_data.csv saved', fg=SUCCESS))
                    # Auto-preview the freshly saved log_data.csv
                    self.after(200, lambda: (
                        self.import_path_var.set('log_data.csv'),
                        self._preview_file('log_data.csv')
                    ))
                else:
                    self.after(0, lambda: self.db_status_lbl.config(text='❌ Fetch failed', fg=DANGER))
            except Exception as e:
                self.after(0, lambda: self._db_log_write(f'ERROR: {e}'))
                self.after(0, lambda: self.db_status_lbl.config(text='❌ Error', fg=DANGER))

        threading.Thread(target=worker, daemon=True).start()

    def _db_save_config(self):
        cfg = configparser.ConfigParser()
        cfg['sqlserver'] = {
            'server':   self.db_server.get().strip(),
            'database': self.db_name.get().strip(),
            'table':    self.db_table.get().strip(),
            'auth':     self.db_auth.get(),
            'user':     self.db_user.get().strip(),
        }
        with open(self.DB_CONFIG_FILE, 'w') as f:
            cfg.write(f)

    def _db_load_config(self):
        if not os.path.exists(self.DB_CONFIG_FILE):
            return
        cfg = configparser.ConfigParser()
        cfg.read(self.DB_CONFIG_FILE)
        s = cfg.get('sqlserver', 'server',   fallback='')
        d = cfg.get('sqlserver', 'database', fallback='')
        t = cfg.get('sqlserver', 'table',    fallback='Logs')
        a = cfg.get('sqlserver', 'auth',     fallback='windows')
        u = cfg.get('sqlserver', 'user',     fallback='')
        if s: self.db_server.delete(0, tk.END); self.db_server.insert(0, s)
        if d: self.db_name.delete(0, tk.END);   self.db_name.insert(0, d)
        if t: self.db_table.delete(0, tk.END);  self.db_table.insert(0, t)
        self.db_auth.set(a)
        if u: self.db_user.delete(0, tk.END);   self.db_user.insert(0, u)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 — Employee Leaves
    # ══════════════════════════════════════════════════════════════════════════
    def _build_leave_tab(self):
        p = self.tab_leave.scrollable_frame
        self._section(p, '📝  Submit New Leave').pack(fill='x', padx=15, pady=(12,4))

        form = tk.Frame(p, bg=BG2, padx=10)
        form.pack(fill='x', padx=15, pady=4)

        def lbl(t, r, c):
            tk.Label(form, text=t, font=FONT, bg=BG2, fg=FG2, anchor='w'
                     ).grid(row=r, column=c, sticky='w', padx=6, pady=4)
        def ent(r, c, default='', w=18):
            e = tk.Entry(form, font=FONT, width=w, bg=BG3, fg=FG,
                         insertbackground=ACCENT, relief='flat', bd=0, highlightthickness=1,
                         highlightbackground=BG3, highlightcolor=ACCENT)
            e.grid(row=r, column=c, sticky='ew', padx=6, pady=4)
            e.insert(0, default)
            return e

        today = str(date.today())
        lbl('Employee Name *',          0, 0); self.lv_name  = ent(0, 1, w=24)
        lbl('Start Date (YYYY-MM-DD) *',0, 2); self.lv_start = ent(0, 3, today)
        lbl('End Date   (YYYY-MM-DD) *',1, 0); self.lv_end   = ent(1, 1, today)

        lbl('Leave Type', 1, 2)
        self.lv_type = tk.StringVar(value='Annual Leave')
        ttk.Combobox(form, textvariable=self.lv_type, font=FONT, width=20, state='readonly',
                     values=['Annual Leave','Sick Leave','Personal Leave',
                             'Maternity / Paternity','Compensatory Off','Shutdown / Closure','Other']
                     ).grid(row=1, column=3, sticky='ew', padx=6, pady=4)

        lbl('Half Day', 2, 0)
        self.lv_half = tk.StringVar(value='No')
        ttk.Combobox(form, textvariable=self.lv_half, font=FONT, width=18, state='readonly',
                     values=['No','Morning Half','Afternoon Half']
                     ).grid(row=2, column=1, sticky='ew', padx=6, pady=4)

        lbl('Reason', 2, 2); self.lv_desc = ent(2, 3, w=28)

        bf = tk.Frame(p, bg=BG2)
        bf.pack(pady=8)
        self._btn(bf, '✔ Submit Leave',    ACCENT2, self._submit_leave).pack(side='left', padx=5)
        self._btn(bf, '📥 Import Leaves CSV/Excel', SUCCESS, self._import_leaves).pack(side='left', padx=5)
        self._btn(bf, '📤 Export Leaves',  BG3,     self._export_leaves).pack(side='left', padx=5)
        self._btn(bf, '🗑 Delete Selected', DANGER,  self._delete_leave).pack(side='left', padx=5)

        self._section(p, '📋  All Submitted Leaves').pack(fill='x', padx=15, pady=(8,2))

        lf = tk.Frame(p, bg=BG2)
        lf.pack(fill='both', expand=True, padx=15, pady=(0,10))
        cols = ('Employee Name','Start Date','End Date','Leave Type','Status','Approved By','Description')
        self.lv_tree = ttk.Treeview(lf, columns=cols, show='headings', height=8)
        col_widths = {'Employee Name': 180, 'Start Date': 100, 'End Date': 100,
                      'Leave Type': 200, 'Status': 90, 'Approved By': 140, 'Description': 180}
        for c in cols:
            self.lv_tree.heading(c, text=c)
            self.lv_tree.column(c, width=col_widths.get(c, 120), anchor='center')
        self.lv_tree.tag_configure('approved',  foreground=SUCCESS)
        self.lv_tree.tag_configure('pending',   foreground=WARNING)
        self.lv_tree.tag_configure('rejected',  foreground=DANGER)
        self.lv_tree.tag_configure('cancelled', foreground='#fca5a5')
        self.lv_tree.tag_configure('pending',   foreground='#fde68a')

        vsb = ttk.Scrollbar(lf, orient='vertical', command=self.lv_tree.yview)
        self.lv_tree.configure(yscrollcommand=vsb.set)
        self.lv_tree.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')
        self._refresh_leaves()

    def _submit_leave(self):
        name  = self.lv_name.get().strip()
        start = self.lv_start.get().strip()
        end   = self.lv_end.get().strip()
        ltype = self.lv_type.get()
        hday  = self.lv_half.get()
        desc  = self.lv_desc.get().strip()
        if not name:
            messagebox.showerror('Missing', 'Employee Name is required.'); return
        try:
            s = datetime.strptime(start, '%Y-%m-%d').date()
            e = datetime.strptime(end,   '%Y-%m-%d').date()
        except ValueError:
            messagebox.showerror('Date Error', 'Use YYYY-MM-DD format.'); return
        if e < s:
            messagebox.showerror('Date Error', 'End Date before Start Date.'); return
        if hday != 'No' and s != e:
            messagebox.showerror('Half Day', 'Half Day only valid for a single day.'); return

        df = self._load_leaves()
        new_row = pd.DataFrame([{
            'Employee Name': name, 'Start Date': str(s), 'End Date': str(e),
            'Leave Type': ltype,   'Half Day': hday,     'Description': desc,
            'Submitted On': str(date.today())
        }])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(LEAVE_FILE, index=False)
        days = (e - s).days + 1
        messagebox.showinfo('Submitted ✅', f'{name}: {days} day(s) from {s} to {e}')
        self._refresh_leaves()
        self.lv_name.delete(0, tk.END)
        self.lv_desc.delete(0, tk.END)

    def _import_leaves(self):
        """Open a custom dialog to collect multiple files, then import them all."""

        # ── Custom multi-file picker dialog ───────────────────────────────────
        dlg = tk.Toplevel(self)
        dlg.title('Import Leave Files')
        dlg.configure(bg=BG2)
        dlg.resizable(False, False)
        dlg.grab_set()

        tk.Label(dlg, text='Add one or more HR Leave Excel / CSV files:',
                 font=FONT, bg=BG2, fg=FG2).pack(padx=16, pady=(14,4), anchor='w')

        # File list box
        lf = tk.Frame(dlg, bg=BG2)
        lf.pack(fill='x', padx=16, pady=4)
        vsb = ttk.Scrollbar(lf, orient='vertical')
        vsb.pack(side='right', fill='y')
        file_lb = tk.Listbox(lf, font=CODE, bg=BG3, fg=FG, selectbackground=ACCENT2,
                              height=7, width=60, yscrollcommand=vsb.set, relief='flat')
        file_lb.pack(side='left', fill='x', expand=True)
        vsb.config(command=file_lb.yview)

        file_paths = []   # stores absolute paths parallel to listbox items

        def add_file():
            p = filedialog.askopenfilename(
                parent=dlg,
                title='Select a Leave Excel / CSV File',
                filetypes=[('Excel/CSV', '*.xlsx *.xls *.csv'), ('All', '*.*')])
            if p and p not in file_paths:
                file_paths.append(p)
                file_lb.insert('end', os.path.basename(p))

        def remove_file():
            sel = file_lb.curselection()
            for i in reversed(sel):
                file_lb.delete(i)
                file_paths.pop(i)

        # Buttons row
        br = tk.Frame(dlg, bg=BG2)
        br.pack(fill='x', padx=16, pady=6)
        self._btn(br, '+ Add File',       ACCENT2, add_file).pack(side='left',  padx=4)
        self._btn(br, '- Remove Selected', DANGER,  remove_file).pack(side='left', padx=4)

        status_lbl = tk.Label(dlg, text='', font=FONT_S, bg=BG2, fg=FG2)
        status_lbl.pack(padx=16, anchor='w')

        # ── Core import logic (same as before, now receives file list) ────────
        def do_import():
            if not file_paths:
                messagebox.showwarning('No Files', 'Please add at least one file.', parent=dlg)
                return

            # Load existing data
            existing_df = pd.DataFrame()
            if os.path.exists(LEAVE_FILE):
                try:
                    existing_df = self._load_hr_leaves()
                    if 'From Date' in existing_df.columns:
                        existing_df['From Date'] = pd.to_datetime(
                            existing_df['From Date'], errors='coerce').dt.strftime('%Y-%m-%d')
                except Exception:
                    existing_df = pd.DataFrame()

            combined = existing_df.copy()
            grand_total = grand_new = grand_approved = 0
            file_results = []
            errors = []

            for path in file_paths:
                fname = os.path.basename(path)
                status_lbl.config(text=f'Processing: {fname}...', fg=WARNING)
                dlg.update_idletasks()
                try:
                    if path.lower().endswith(('.xlsx', '.xls')):
                        raw = pd.read_excel(path, engine='openpyxl', header=None)
                    else:
                        raw = pd.read_csv(path, header=None, encoding='utf-8', on_bad_lines='skip')

                    header_row = None
                    for i, row in raw.iterrows():
                        if any('userid' in str(v).lower() for v in row.values):
                            header_row = i; break

                    if header_row is None:
                        errors.append(f'{fname}: No "UserId" header — skipped.')
                        continue

                    if path.lower().endswith(('.xlsx', '.xls')):
                        df = pd.read_excel(path, engine='openpyxl', header=header_row)
                    else:
                        df = pd.read_csv(path, header=header_row, encoding='utf-8', on_bad_lines='skip')
                    df.columns = df.columns.str.strip()

                    if 'UserId' in df.columns:
                        df = df[df['UserId'].astype(str).str.strip() != 'UserId']
                        df = df[df['UserId'].notna() & (df['UserId'].astype(str).str.strip() != 'nan')]

                    for dc in ['From Date','To Date']:
                        if dc in df.columns:
                            df[dc] = pd.to_datetime(df[dc], errors='coerce').dt.strftime('%Y-%m-%d')

                    n_file = len(df)
                    n_approved = (len(df[df['Status'].astype(str).str.strip().str.lower() == 'approved'])
                                  if 'Status' in df.columns else n_file)

                    if not combined.empty and 'UserId' in combined.columns and \
                       'From Date' in combined.columns and 'UserId' in df.columns:
                        exist_key = combined[['UserId','From Date']].astype(str).agg('_'.join, axis=1)
                        new_key   = df[['UserId','From Date']].astype(str).agg('_'.join, axis=1)
                        truly_new = df[~new_key.isin(exist_key)]
                    else:
                        truly_new = df

                    n_new = len(truly_new)
                    combined = pd.concat([combined, truly_new], ignore_index=True)
                    grand_total += n_file; grand_new += n_new; grand_approved += n_approved
                    file_results.append(f'  {fname}: {n_file} records, {n_approved} approved, {n_new} new')
                except Exception as e:
                    errors.append(f'{fname}: ERROR - {e}')

            if not combined.empty:
                # Strip Unnamed / empty columns before saving — keeps CSV clean
                combined = combined.loc[:, ~combined.columns.str.match(r'^Unnamed')]
                combined = combined.loc[:, combined.columns.str.strip() != '']
                combined.to_csv(LEAVE_FILE, index=False)

            dlg.destroy()
            summary  = f'Imported {len(file_paths)} file(s):\n\n' + '\n'.join(file_results)
            summary += f'\n\n{"="*38}\n'
            summary += f'  TOTAL records   : {grand_total}\n'
            summary += f'  TOTAL approved  : {grand_approved}\n'
            summary += f'  TOTAL new added : {grand_new}\n'
            summary += f'  Duplicates skip : {grand_total - grand_new}'
            if errors:
                summary += '\n\nWarnings:\n' + '\n'.join(errors)
            messagebox.showinfo('Import Complete', summary)
            self._refresh_leaves()

        # Import / Cancel buttons
        bb = tk.Frame(dlg, bg=BG2)
        bb.pack(fill='x', padx=16, pady=(4,14))
        self._btn(bb, 'Import All', SUCCESS, do_import).pack(side='left',  padx=4)
        self._btn(bb, 'Cancel',     BG3,     dlg.destroy).pack(side='left', padx=4)

        dlg.wait_window()




    def _export_leaves(self):
        df = self._load_leaves()
        if df.empty:
            messagebox.showinfo('Empty', 'No leave records to export.'); return
        path = filedialog.asksaveasfilename(
            defaultextension='.xlsx',
            filetypes=[('Excel', '*.xlsx'), ('CSV', '*.csv')])
        if not path: return
        if path.endswith('.xlsx'):
            df.to_excel(path, index=False, engine='openpyxl')
        else:
            df.to_csv(path, index=False)
        messagebox.showinfo('Exported ✅', f'Saved to {path}')

    def _delete_leave(self):
        selected = self.lv_tree.selection()
        if not selected:
            messagebox.showinfo('Select', 'Select a row first.'); return
        if not messagebox.askyesno('Delete', 'Delete selected leave(s)?'): return
        df = self._load_leaves()
        indices = [self.lv_tree.index(i) for i in selected]
        df = df.drop(index=indices).reset_index(drop=True)
        df.to_csv(LEAVE_FILE, index=False)
        self._refresh_leaves()

    def _load_leaves(self):
        if os.path.exists(LEAVE_FILE):
            df = pd.read_csv(LEAVE_FILE)
            for c in LEAVE_COLS:
                if c not in df.columns: df[c] = ''
            return df
        return pd.DataFrame(columns=LEAVE_COLS)

    def _load_hr_leaves(self):
        """Load HR-format leave CSV, auto-detecting the real header row and stripping junk cols."""
        if not os.path.exists(LEAVE_FILE):
            return pd.DataFrame()

        # Key columns that MUST ALL be present in the real header row
        HEADER_KEYS = {'userid', 'employee name', 'from date', 'status'}

        try:
            raw = pd.read_csv(LEAVE_FILE, header=None, encoding='utf-8', on_bad_lines='skip')

            # Find the row where ALL header keys appear as values
            header_row = None
            for i, row in raw.iterrows():
                vals = {str(v).strip().lower() for v in row.values}
                if HEADER_KEYS.issubset(vals):
                    header_row = i
                    break

            if header_row is None:
                return pd.DataFrame()

            # Re-read with correct header
            df = pd.read_csv(LEAVE_FILE, header=header_row, encoding='utf-8', on_bad_lines='skip')
            df.columns = df.columns.str.strip()

            # Keep ONLY the known HR columns (drops all junk/Unnamed cols)
            keep = [c for c in HR_COLS if c in df.columns]
            df = df[keep]

            # Drop repeat-header rows and empty UserId rows
            if 'UserId' in df.columns:
                df = df[df['UserId'].astype(str).str.strip().str.lower() != 'userid']
                df = df[df['UserId'].notna() & (df['UserId'].astype(str).str.strip() != 'nan')]

            return df.reset_index(drop=True)
        except Exception:
            return pd.DataFrame()

    def _run_single_day_detail(self):
        day = self.bt_test_start.get().strip()
        try:
            datetime.strptime(day, '%Y-%m-%d')
        except:
            messagebox.showerror('Error', 'Invalid date for detail report.'); return
            
        self.bt_status.config(text=f'Generating detailed report for {day}...', fg=WARNING)
        self.update()
        
        def job():
            try:
                # 1. Run prediction for that day
                cmd = [sys.executable, 'predict_future.py', day, day, '--window', 'all']
                subprocess.run(cmd, check=True, capture_output=True)
                
                # 2. Find the generated CSV
                csv_file = f'backtest_all_{day}_to_{day}.csv'
                if not os.path.exists(csv_file):
                    self.bt_status.config(text="CSV Error: File not found", fg=DANGER)
                    return
                
                # 3. Use matplotlib to generate the 3-panel plot
                df = pd.read_csv(csv_file)
                df['Time Interval'] = pd.to_datetime(df['Time Interval'])
                
                fig, axes = plt.subplots(3, 1, figsize=(15, 18), sharex=True)
                configs = [
                    (0, '15m Window', 'PREDICTED LOGIN COUNT', 'Login Count', '#3b82f6'),
                    (1, '30m Window', 'PREDICTED LOGIN 30M',   'Login 30m',   '#f43f5e'),
                    (2, '60m Window', 'PREDICTED LOGIN 60M',   'Login 60m',   '#10b981')
                ]
                for i, title, pred, actual, color in configs:
                    ax = axes[i]
                    ax.plot(df['Time Interval'], df[pred], label=f'Predicted {title}', color=color, linewidth=2.5)
                    if actual in df.columns:
                        ax.plot(df['Time Interval'], df[actual], label=f'Actual {title}', color='gray', alpha=0.3, linewidth=2)
                    ax.set_title(title, fontsize=14, fontweight='bold')
                    ax.legend(); ax.grid(True, alpha=0.5)

                plt.suptitle(f"Detailed Day Analysis: {day}", fontsize=18, fontweight='bold')
                import matplotlib.dates as mdates
                plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=1))
                plt.xticks(rotation=45)
                plt.tight_layout(rect=[0, 0.03, 1, 0.95])
                
                png_file = f"detail_report_{day}.png"
                plt.savefig(png_file)
                plt.close()
                
                self.after(0, lambda: self._on_detail_done(png_file))
            except Exception as e:
                self.after(0, lambda: self.bt_status.config(text=f"Error: {e}", fg=DANGER))

        threading.Thread(target=job, daemon=True).start()

    def _on_detail_done(self, png_file):
        self.bt_status.config(text=f"Success! Saved to {png_file}", fg=SUCCESS)
        self._refresh_graphs_list()
        messagebox.showinfo('Report Ready', f'Detailed report for the day has been saved as:\n{png_file}\n\nYou can view it in the GRAPHS tab.')

    def _refresh_leaves(self):
        for r in self.lv_tree.get_children(): self.lv_tree.delete(r)
        # Try HR-format first (imported via Import button)
        df = self._load_hr_leaves()
        if df.empty:
            df = self._load_leaves()   # fallback to simple format

        def col(row, *candidates):
            """Return the first non-empty value from the candidate column names."""
            for c in candidates:
                v = row.get(c, '')
                if v and str(v).strip() not in ('', 'nan', 'NaT', 'None'):
                    return str(v).strip()
            return ''

        for _, row in df.iterrows():
            leave_type = col(row, 'Leave Types', 'Leave Type')
            half_day   = col(row, 'From Session', 'Half Day')
            if half_day and half_day.lower() not in ('no', 'fullday', 'full day', ''):
                leave_type = f'{leave_type} ({half_day})'
            status     = col(row, 'Status')
            approved_by= col(row, 'Last Action Taken by')

            # Tag for colour
            tag = 'approved' if status.lower() == 'approved' else \
                  'cancelled' if status.lower() == 'cancelled' else 'pending'

            self.lv_tree.insert('', 'end', tags=(tag,), values=(
                col(row, 'Employee Name'),
                col(row, 'From Date',   'Start Date'),
                col(row, 'To Date',     'End Date'),
                leave_type,
                status,
                approved_by,
                col(row, 'Reason',      'Description'),
            ))


    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3.5 — Company Holidays
    # ══════════════════════════════════════════════════════════════════════════
    def _build_holiday_tab(self):
        p = self.tab_holiday.scrollable_frame
        self._section(p, '📝  Add Company Holiday').pack(fill='x', padx=15, pady=(12,4))

        form = tk.Frame(p, bg=BG2, padx=10)
        form.pack(fill='x', padx=15, pady=4)

        def lbl(t, r, c):
            tk.Label(form, text=t, font=FONT, bg=BG2, fg=FG2, anchor='w'
                     ).grid(row=r, column=c, sticky='w', padx=6, pady=4)
        def ent(r, c, default='', w=18):
            e = tk.Entry(form, font=FONT, width=w, bg=BG3, fg=FG,
                         insertbackground=ACCENT, relief='flat', bd=0, highlightthickness=1,
                         highlightbackground=BG3, highlightcolor=ACCENT)
            e.grid(row=r, column=c, sticky='ew', padx=6, pady=4)
            e.insert(0, default)
            return e

        today = str(date.today())
        lbl('Description *',            0, 0); self.hol_desc  = ent(0, 1, w=24)
        lbl('Start Date (YYYY-MM-DD) *',0, 2); self.hol_start = ent(0, 3, today)
        lbl('End Date   (YYYY-MM-DD) *',1, 0); self.hol_end   = ent(1, 1, today)

        lbl('Holiday Type', 1, 2)
        self.hol_type = tk.StringVar(value='Mandatory')
        ttk.Combobox(form, textvariable=self.hol_type, font=FONT, width=20, state='readonly',
                     values=['Mandatory', 'Optional']
                     ).grid(row=1, column=3, sticky='ew', padx=6, pady=4)

        bf = tk.Frame(p, bg=BG2)
        bf.pack(pady=8)
        self._btn(bf, '✔ Add Holiday',    ACCENT2, self._submit_holiday).pack(side='left', padx=5)
        self._btn(bf, '📥 Import CSV/Excel', SUCCESS, self._import_holidays).pack(side='left', padx=5)
        self._btn(bf, '🗑 Delete Selected', DANGER,  self._delete_holiday).pack(side='left', padx=5)

        self._section(p, '🏢  All Company Holidays').pack(fill='x', padx=15, pady=(8,2))

        lf = tk.Frame(p, bg=BG2)
        lf.pack(fill='both', expand=True, padx=15, pady=(0,10))
        cols = ('Start Date', 'End Date', 'Description', 'Type')
        self.hol_tree = ttk.Treeview(lf, columns=cols, show='headings', height=10)
        col_widths = {'Start Date': 120, 'End Date': 120, 'Description': 300, 'Type': 150}
        for c in cols:
            self.hol_tree.heading(c, text=c)
            self.hol_tree.column(c, width=col_widths.get(c, 150), anchor='center')
            
        self.hol_tree.tag_configure('mandatory', foreground=SUCCESS)
        self.hol_tree.tag_configure('optional',  foreground=WARNING)

        vsb = ttk.Scrollbar(lf, orient='vertical', command=self.hol_tree.yview)
        self.hol_tree.configure(yscrollcommand=vsb.set)
        self.hol_tree.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')
        self._refresh_holidays()

    def _submit_holiday(self):
        desc  = self.hol_desc.get().strip()
        start = self.hol_start.get().strip()
        end   = self.hol_end.get().strip()
        htype = self.hol_type.get()
        if not desc:
            messagebox.showerror('Missing', 'Holiday Description is required.'); return
        try:
            s = datetime.strptime(start, '%Y-%m-%d').date()
            e = datetime.strptime(end,   '%Y-%m-%d').date()
        except ValueError:
            messagebox.showerror('Date Error', 'Use YYYY-MM-DD format.'); return
        if e < s:
            messagebox.showerror('Date Error', 'End Date before Start Date.'); return

        df = self._load_holidays_df()
        new_row = pd.DataFrame([{
            'Start Date': str(s), 'End Date': str(e), 'Description': desc, 'Type': htype
        }])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv('holidays.csv', index=False)
        days = (e - s).days + 1
        messagebox.showinfo('Added ✅', f'{desc}: {days} day(s) added.')
        
        # Reset UI
        self.hol_desc.delete(0, tk.END)
        self.hol_start.delete(0, tk.END)
        self.hol_end.delete(0, tk.END)
        today = str(date.today())
        self.hol_start.insert(0, today)
        self.hol_end.insert(0, today)
        
        self._refresh_holidays()

    def _delete_holiday(self):
        selected = self.hol_tree.selection()
        if not selected:
            messagebox.showinfo('Select', 'Select a row first.'); return
        if not messagebox.askyesno('Delete', 'Delete selected holiday(s)?'): return
        
        df = self._load_holidays_df()
        
        # Extract the real CSV row indices we embedded in the visual Treeview
        csv_indices = [int(i) for i in selected]
        
        df = df.drop(index=csv_indices).reset_index(drop=True)
        df.to_csv('holidays.csv', index=False)
        self._refresh_holidays()

    def _load_login_logs(self):
        if not os.path.exists('login_logs.csv'):
            messagebox.showwarning('Missing', 'login_logs.csv not found.')
            return None
        try:
            return pd.read_csv('login_logs.csv')
        except Exception as e:
            messagebox.showerror('Error', f'Could not read login_logs.csv: {e}')
            return None

    def _load_holidays_df(self):
        if os.path.exists('holidays.csv'):
            df = pd.read_csv('holidays.csv')
            
            # Auto-upgrade purely 'Date' format to 'Start Date / End Date' format for internal UI consistency
            if 'Date' in df.columns and 'Start Date' not in df.columns:
                df['Start Date'] = df['Date']
                df['End Date']   = df['Date']
                if 'Type' not in df.columns: df['Type'] = 'Mandatory'
                if 'Description' not in df.columns: df['Description'] = 'Holiday'
                df = df[['Start Date', 'End Date', 'Description', 'Type']]
            return df
        return pd.DataFrame(columns=['Start Date', 'End Date', 'Description', 'Type'])

    def _refresh_holidays(self):
        for r in self.hol_tree.get_children(): self.hol_tree.delete(r)
        df = self._load_holidays_df()
        
        # We must keep track of the original true CSV index so deletion is accurate
        # even after the dataframe is visually sorted.
        df['Original_Index'] = df.index
        
        # Sort by start date
        if 'Start Date' in df.columns and not df.empty:
            df['SortDate'] = pd.to_datetime(df['Start Date'], errors='coerce')
            df = df.sort_values(by='SortDate').drop(columns=['SortDate'])

        for _, row in df.iterrows():
            tag = 'mandatory' if str(row.get('Type', '')).strip().lower() == 'mandatory' else 'optional'
            
            # Insert using the original DataFrame row index as the internal item ID (iid)
            # This allows safe deletion regardless of visual sort order.
            real_index = str(row['Original_Index'])
            self.hol_tree.insert('', 'end', iid=real_index, tags=(tag,), values=(
                row.get('Start Date', row.get('Date', '')),
                row.get('End Date',   row.get('Date', '')),
                row.get('Description', ''),
                row.get('Type', 'Mandatory')
            ))

    def _import_holidays(self):
        path = filedialog.askopenfilename(
            title='Select a Holiday Excel / CSV File',
            filetypes=[('Excel/CSV', '*.xlsx *.xls *.csv'), ('All', '*.*')])
        if not path: return
        
        try:
            if path.lower().endswith(('.xlsx', '.xls')):
                imported_df = pd.read_excel(path, engine='openpyxl')
            else:
                imported_df = pd.read_csv(path, encoding='utf-8')
                
            cols = [col.strip().lower() for col in imported_df.columns]
            imported_df.columns = cols
            
            new_holidays = []
            
            # Standardize based on format
            if 'start date' in cols and 'end date' in cols:
                for _, row in imported_df.iterrows():
                    new_holidays.append({
                        'Start Date': str(pd.to_datetime(row['start date']).date()),
                        'End Date':   str(pd.to_datetime(row['end date']).date()),
                        'Description': str(row.get('description', 'Imported Holiday')).strip(),
                        'Type': str(row.get('type', 'Mandatory')).strip().capitalize()
                    })
            elif 'date' in cols:
                for _, row in imported_df.iterrows():
                    new_holidays.append({
                        'Start Date': str(pd.to_datetime(row['date']).date()),
                        'End Date':   str(pd.to_datetime(row['date']).date()),
                        'Description': str(row.get('description', 'Imported Holiday')).strip(),
                        'Type': str(row.get('type', 'Mandatory')).strip().capitalize()
                    })
            else:
                messagebox.showerror('Format Error', 'File must contain either a "Date" column OR "Start Date" and "End Date" columns.')
                return
                
            if not new_holidays:
                messagebox.showwarning('Empty', 'No valid dates found in file.')
                return
                
            new_df = pd.DataFrame(new_holidays)
            current_df = self._load_holidays_df()
            final_df = pd.concat([current_df, new_df], ignore_index=True)
            
            # Deduplicate exact matches
            final_df = final_df.drop_duplicates(subset=['Start Date', 'End Date', 'Description'])
            final_df.to_csv('holidays.csv', index=False)
            
            added = len(final_df) - len(current_df)
            messagebox.showinfo('Imported ✅', f'Successfully imported {added} new holiday record(s).')
            self._refresh_holidays()
            
        except Exception as e:
            messagebox.showerror('Import Error', f'Failed to process file:\n{str(e)}')

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3.8 — Model Backtest
    # ══════════════════════════════════════════════════════════════════════════
    def _build_backtest_tab(self):
        p = self.tab_backtest.scrollable_frame
        self._section(p, '🧪  Blind Backtest Configuration').pack(fill='x', padx=15, pady=(12,4))

        form = tk.Frame(p, bg=BG2, padx=10)
        form.pack(fill='x', padx=15, pady=4)

        def lbl(t, r, c):
            tk.Label(form, text=t, font=FONT, bg=BG2, fg=FG2, anchor='w'
                     ).grid(row=r, column=c, sticky='w', padx=6, pady=4)
        def ent(r, c, default='', w=16):
            e = tk.Entry(form, font=FONT, width=w, bg=BG3, fg=FG,
                         insertbackground=ACCENT, relief='flat', bd=0, highlightthickness=1,
                         highlightbackground=BG3, highlightcolor=ACCENT)
            e.grid(row=r, column=c, sticky='e', padx=6, pady=4)
            e.insert(0, default)
            return e

        # Train Dates
        lbl('Train Model FROM (YYYY-MM-DD):', 0, 0); self.bt_train_start = ent(0, 1, '2025-12-01')
        lbl('Train Model TO   (YYYY-MM-DD):', 1, 0); self.bt_train_end   = ent(1, 1, '2026-02-11')

        # Test Dates
        lbl('Blind Test FROM  (YYYY-MM-DD):', 0, 2); self.bt_test_start  = ent(0, 3, '2026-02-12')
        lbl('Blind Test TO    (YYYY-MM-DD):', 1, 2); self.bt_test_end    = ent(1, 3, '2026-03-16')

        bf = tk.Frame(p, bg=BG2)
        bf.pack(pady=10)
        self.bt_run_btn = self._btn(bf, '🚀 Run Live Backtest Analysis', ACCENT2, self._run_backtest)
        self.bt_run_btn.pack(side='left', padx=10)
        
        self.bt_detail_btn = self._btn(bf, '📅 Single-Day Detail Graph', SUCCESS, self._run_single_day_detail)
        self.bt_detail_btn.pack(side='left', padx=10)
        self._btn(bf, '📊 Batch Daily Graphs', ACCENT, self._run_batch_daily_graphs_backtest).pack(side='left', padx=10)

        self.bt_status = tk.Label(bf, text='', font=FONT_S, bg=BG2, fg=WARNING)
        self.bt_status.pack(side='left', padx=10)

        # Results area
        res_frame = tk.Frame(p, bg=BG2)
        res_frame.pack(fill='both', expand=True, padx=15, pady=10)

        self.bt_metrics = tk.Label(res_frame, text='Run analysis to see errors...', font=FONT_B, bg=BG2, fg=SUCCESS, justify='left')
        self.bt_metrics.pack(fill='x', pady=5)

        self.bt_img_label = tk.Label(res_frame, bg=BG2)
        self.bt_img_label.pack(fill='both', expand=True, pady=10)
        self.bt_img_ref = None

    def _run_backtest(self):
        ts = self.bt_train_start.get().strip()
        te = self.bt_train_end.get().strip()
        vs = self.bt_test_start.get().strip()
        ve = self.bt_test_end.get().strip()

        if not (ts and te and vs and ve):
            messagebox.showerror("Error", "All date fields are required.")
            return

        self.bt_run_btn.config(state='disabled')
        self.bt_status.config(text="Status: Training Model... Please wait.", fg=WARNING)
        self.bt_metrics.config(text="")
        self.bt_img_label.config(image='')

        def worker():
            try:
                cmd = [sys.executable, 'test_model_accuracy.py', ts, te, vs, ve]
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                
                mae, rmse, peak_a, peak_p = 'N/A', 'N/A', 'N/A', 'N/A'
                
                for line in proc.stdout:
                    line = line.strip()
                    if line.startswith("GUI_METRIC:MAE:"): mae = line.split(":")[-1]
                    elif line.startswith("GUI_METRIC:RMSE:"): rmse = line.split(":")[-1]
                    elif line.startswith("GUI_METRIC:PEAK_ACTUAL:"): peak_a = line.split(":")[-1]
                    elif line.startswith("GUI_METRIC:PEAK_PREDICTED:"): peak_p = line.split(":")[-1]
                
                proc.wait()
                
                if proc.returncode != 0:
                    err = proc.stderr.read()
                    self.after(0, lambda: messagebox.showerror("Backtest Failed", f"Execution Error:\n{err}"))
                    self.after(0, lambda: self.bt_status.config(text="Status: Failed.", fg=DANGER))
                else:
                    metrics_str = f"✅ Analysis Complete!\n\n⭐ Mean Absolute Error: {mae} users | Root Mean Squared Error: {rmse} users\n⭐ Peak Actual: {peak_a} | Peak Predicted: {peak_p}"
                    self.after(0, lambda: self._show_backtest_results(metrics_str))
            
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Backtest Error", str(e)))
                self.after(0, lambda: self.bt_status.config(text="Status: Error.", fg=DANGER))
            finally:
                self.after(0, lambda: self.bt_run_btn.config(state='normal'))

        threading.Thread(target=worker, daemon=True).start()

    # ── Batch Daily Graphs Logic ──────────────────────────────────────────────
    def _run_batch_daily_graphs_backtest(self):
        start = self.bt_test_start.get().strip()
        end   = self.bt_test_end.get().strip()
        self._run_batch_daily_graphs(start, end, is_backtest=True)

    def _run_batch_daily_graphs_predict(self):
        start = self.pred_start.get().strip()
        end   = self.pred_end.get().strip()
        self._run_batch_daily_graphs(start, end, is_backtest=False)

    def _run_batch_daily_graphs(self, start_str, end_str, is_backtest=True):
        if not start_str or not end_str:
            messagebox.showerror('Error', 'Please enter both Start and End dates.'); return
        
        # 1. Load Data
        df_proc = None
        if os.path.exists('processed_data.csv'):
            try:
                df_proc = pd.read_csv('processed_data.csv')
                df_proc['Time Interval'] = pd.to_datetime(df_proc['Time Interval'])
            except: pass

        def worker():
            try:
                self.after(0, lambda: self.bt_status.config(text="Status: Generating Batch Graphs...", fg=WARNING))
                
                win = 'all'
                fname = f"backtest_{win}_{start_str}_to_{end_str}.csv"
                if not is_backtest:
                    fname = f"prediction_{start_str}_to_{end_str}.csv" # Fallback if standard naming

                # Try finding any file that matches the dates if standard fails
                if not os.path.exists(fname):
                    possible = [f for f in os.listdir('.') if start_str in f and end_str in f and f.endswith('.csv')]
                    if possible: fname = possible[0]

                if not os.path.exists(fname):
                    # Run prediction to generate the CSV if missing
                    # self.after(0, lambda: self._log(f"Generating missing result file: {fname}..."))
                    cmd = [sys.executable, 'predict_future.py', start_str, end_str, '--window', win]
                    subprocess.run(cmd, check=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                
                # Check again
                if not os.path.exists(fname):
                    self.after(0, lambda: messagebox.showerror("Error", f"Could not find or generate result file for {start_str} to {end_str}"))
                    return

                df_pred = pd.read_csv(fname)
                df_pred['Time Interval'] = pd.to_datetime(df_pred['Time Interval'])
                df_pred['Date'] = df_pred['Time Interval'].dt.date
                
                unique_dates = sorted(df_pred['Date'].unique())
                total_days = len(unique_dates)
                
                if total_days == 0:
                    self.after(0, lambda: messagebox.showinfo("No Data", "No prediction data found for this range."))
                    return

                for idx, d in enumerate(unique_dates):
                    self.after(0, lambda i=idx+1: self.bt_status.config(text=f"Status: Generating Day {i}/{total_days} ({d})..."))
                    
                    day_pred = df_pred[df_pred['Date'] == d].copy()
                    day_proc = None
                    if df_proc is not None:
                        day_proc = df_proc[df_proc['Time Interval'].dt.date == d].copy()

                    # Generate 3-panel plot
                    fig, axes = plt.subplots(3, 1, figsize=(12, 12))
                    
                    configs = [
                        (axes[0], '15m', 'PREDICTED LOGIN COUNT', 'Login Count', 'Login Count (15m)'),
                        (axes[1], '30m', 'PREDICTED LOGIN 30M', 'Login 30m', 'Login Count (30m)'),
                        (axes[2], '60m', 'PREDICTED LOGIN 60M', 'Login 60m', 'Login Count (60m)')
                    ]
                    
                    active_configs = [c for c in configs if c[2] in day_pred.columns]
                    num_plots = len(active_configs)
                    
                    if num_plots == 0:
                        continue # No data for this day

                    # Dynamic height based on number of panels (e.g., 5 inches per panel)
                    fig, axes = plt.subplots(num_plots, 1, figsize=(12, 5 * num_plots))
                    
                    # Convert to list if only one subplot to make it iterable
                    if num_plots == 1: axes = [axes]

                    for i, (ax, win_sz, pred_col, act_col, title) in enumerate(active_configs):
                        # Plot Predicted
                        ax.plot(day_pred['Time Interval'], day_pred[pred_col], label='Predicted', color='#8b5cf6', linewidth=2)
                        
                        # Plot Actual if available
                        if day_proc is not None and not day_proc.empty and act_col in day_proc.columns:
                            ax.plot(day_proc['Time Interval'], day_proc[act_col], label='Actual', color='gray', alpha=0.5, linestyle='--')
                        
                        ax.set_title(title, loc='left', fontsize=11, fontweight='bold', color=ACCENT)
                        ax.legend(loc='upper right', frameon=False, fontsize=9)
                        ax.grid(True, alpha=0.2)
                        
                        # Granular Time Axis
                        ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
                        ax.xaxis.set_major_formatter(mdates.DateFormatter('%I %p'))
                        plt.setp(ax.get_xticklabels(), rotation=0, fontsize=8)
                        
                    plt.suptitle(f"Detailed Daily Comparison: {d}", fontsize=16, fontweight='bold', color=BG2)
                    plt.tight_layout(rect=[0, 0.03, 1, 0.96 if num_plots > 1 else 0.92])
                    
                    out_name = f"comparison_report_{d}.png"
                    plt.savefig(out_name, dpi=100)
                    plt.close(fig)

                self.after(0, lambda: self.bt_status.config(text="Status: Batch Generation Complete!", fg=SUCCESS))
                self.after(0, self._refresh_graphs_list)
                self.after(0, lambda: messagebox.showinfo("Success", f"Generated {total_days} daily report(s) in the Graphs tab."))
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.after(0, lambda: messagebox.showerror("Batch Error", f"Failed to generate graphs: {e}"))
                self.after(0, lambda: self.bt_status.config(text="Status: Batch Generation Failed.", fg=DANGER))
        
        threading.Thread(target=worker, daemon=True).start()

    def _show_backtest_results(self, metrics_text):
        self.bt_status.config(text="Status: Complete! CSV and Graph rendered.", fg=SUCCESS)
        self.bt_metrics.config(text=metrics_text)
        
        # Try loading the generated graph
        try:
            if os.path.exists('app_backtest_chart.png'):
                import shutil
                shutil.copy2('app_backtest_chart.png', '_tmp_app_backtest_chart.png')
                img = Image.open('_tmp_app_backtest_chart.png')
                # Resize for UI
                view_w = 900
                ratio = view_w / float(img.size[0])
                view_h = int((float(img.size[1]) * float(ratio)))
                img = img.resize((view_w, view_h), Image.LANCZOS)
                
                self.bt_img_ref = ImageTk.PhotoImage(img)
                self.bt_img_label.config(image=self.bt_img_ref)
        except Exception as e:
            self.bt_status.config(text=f"Graph Error: {e}", fg=DANGER)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 4 — Results Viewer
    # ══════════════════════════════════════════════════════════════════════════
    def _build_results_tab(self):
        p = self.tab_results.scrollable_frame
        self._section(p, '📁  Saved Prediction Files').pack(fill='x', padx=15, pady=(12,4))

        top = tk.Frame(p, bg=BG2)
        top.pack(fill='x', padx=15, pady=4)
        
        # Replace Combobox with Listbox + Scrollbar for multi-select
        lb_frame = tk.Frame(top, bg=BG2)
        lb_frame.pack(side='left', fill='x', expand=True, padx=(0,8))
        
        self.results_lb = tk.Listbox(lb_frame, font=FONT, height=5, bg=BG3, fg=FG,
                                     selectmode='extended', relief='flat', bd=0, highlightthickness=0)
        self.results_lb.pack(side='left', fill='x', expand=True)
        
        rsb = ttk.Scrollbar(lb_frame, orient='vertical', command=self.results_lb.yview)
        rsb.pack(side='right', fill='y')
        self.results_lb.configure(yscrollcommand=rsb.set)

        btn_f = tk.Frame(top, bg=BG2)
        btn_f.pack(side='right')
        
        self._btn(btn_f, '🔄 Refresh', BG3,    self._refresh_results).pack(fill='x', pady=2)
        self._btn(btn_f, '👁 View',    ACCENT2, self._view_result).pack(fill='x', pady=2)
        self._btn(btn_f, '📤 Export Excel', SUCCESS, self._export_result_excel).pack(fill='x', pady=2)
        self._btn(btn_f, '🗑️ Delete', DANGER, self._delete_result).pack(fill='x', pady=2)
        self._btn(btn_f, '💣 Delete All', DANGER, self._delete_all_results).pack(fill='x', pady=2)

        self._section(p, '📊  Preview (first 2000 rows)').pack(fill='x', padx=15, pady=(10,2))

        rf = tk.Frame(p, bg=BG2)
        rf.pack(fill='both', expand=True, padx=15, pady=(0,10))

        cols = ('Time Interval', 'PREDICTED LOGIN COUNT', 'PREDICTED LOGIN 30M', 'PREDICTED LOGIN 60M', 'PREDICTED ACTIVE USERS', 'Employees on Leave')
        self.res_tree = ttk.Treeview(rf, columns=cols, show='headings', height=14)
        for c in cols:
            self.res_tree.heading(c, text=c)
            self.res_tree.column(c, width=155, anchor='center')
        vsb = ttk.Scrollbar(rf, orient='vertical',   command=self.res_tree.yview)
        hsb = ttk.Scrollbar(rf, orient='horizontal',  command=self.res_tree.xview)
        self.res_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.res_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        rf.rowconfigure(0, weight=1); rf.columnconfigure(0, weight=1)

        self._refresh_results()

    def _delete_result(self):
        selected_indices = self.results_lb.curselection()
        if not selected_indices:
            messagebox.showwarning('No Selection', 'Please select one or more files to delete.')
            return
            
        files_to_delete = [self.results_lb.get(i) for i in selected_indices]
        msg = f"Are you sure you want to delete {len(files_to_delete)} file(s)?\n" + "\n".join(files_to_delete[:10])
        if len(files_to_delete) > 10: msg += "\n...and more"
        
        if messagebox.askyesno('Delete Results', msg + "\n\nThis cannot be undone."):
            try:
                for f in files_to_delete:
                    if os.path.exists(f): os.remove(f)
                self._refresh_results()
                for i in self.res_tree.get_children(): self.res_tree.delete(i)
                messagebox.showinfo('Deleted', f'{len(files_to_delete)} file(s) have been deleted.')
            except Exception as e:
                messagebox.showerror('Error', f'Could not delete file(s): {e}')

    def _view_result(self):
        indices = self.results_lb.curselection()
        if not indices: return
        fname = self.results_lb.get(indices[0])
        if not os.path.exists(fname): return
        
        try:
            df = pd.read_csv(fname)
            for i in self.res_tree.get_children(): self.res_tree.delete(i)
            
            # Match columns with the Treeview's defined columns
            display_cols = [c for c in ('Time Interval', 'PREDICTED LOGIN COUNT', 'PREDICTED LOGIN 30M', 'PREDICTED LOGIN 60M', 'PREDICTED ACTIVE USERS', 'Employees on Leave')
                            if c in df.columns]
            
            self.res_tree['columns'] = display_cols
            for c in display_cols:
                self.res_tree.heading(c, text=c)
                self.res_tree.column(c, width=155, anchor='center')

            for _, row in df[display_cols].head(2000).iterrows():
                self.res_tree.insert('', 'end', values=list(row))
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def _export_result_excel(self):
        indices = self.results_lb.curselection()
        if not indices: return
        fname = self.results_lb.get(indices[0])
        if not os.path.exists(fname): return
        
        df  = pd.read_csv(fname)
        out = fname.replace('.csv', '.xlsx')
        df.to_excel(out, index=False, engine='openpyxl')
        messagebox.showinfo('Exported ✅', f'Saved as {out}')

    def _delete_all_results(self):
        files = [f for f in os.listdir('.') if (f.startswith('prediction_') or f.startswith('backtest_')) and f.endswith('.csv')]
        if not files:
            messagebox.showinfo('Info', 'No result files to delete.')
            return
        if messagebox.askyesno('Delete All', f'Are you sure you want to delete ALL {len(files)} result files?\nThis cannot be undone.'):
            try:
                for f in files: os.remove(f)
                self._refresh_results()
                for i in self.res_tree.get_children(): self.res_tree.delete(i)
                messagebox.showinfo('Deleted', 'All result files have been deleted.')
            except Exception as e:
                messagebox.showerror('Error', f'Could not delete all files: {e}')

    def _refresh_results(self):
        files = sorted([f for f in os.listdir('.')
                        if (f.startswith('prediction_') or f.startswith('backtest_')) and f.endswith('.csv')], reverse=True)
        self.results_lb.delete(0, 'end')
        for f in files:
            self.results_lb.insert('end', f)

    # ── Helpers ────────────────────────────────────────────────────────────────
    def _section(self, parent, text):
        bg_col = BG2 # Default for most tabs
        f = tk.Frame(parent, bg=bg_col)
        f.pack(fill='x', pady=(15, 8))
        lbl = tk.Label(f, text=text.upper(), font=('Inter', 9, 'bold'), bg=bg_col, fg=ACCENT)
        lbl.pack(side='left')
        tk.Frame(f, bg=BG3, height=1).pack(side='left', fill='x', expand=True, padx=(10, 0), pady=5)
        return f

    def _btn(self, parent, text, color, command, width=None):
        btn = tk.Button(parent, text=text, font=FONT_B, bg=color, fg='white',
                         activebackground=color, activeforeground=FG,
                         padx=20, pady=8, relief='flat', cursor='hand2',
                         command=command, bd=0, highlightthickness=0)
        if width: btn.config(width=width)
        
        def on_ent(e): btn.config(bg=ACCENT2 if color==ACCENT else BG3)
        def on_lev(e): btn.config(bg=color)
        
        btn.bind('<Enter>', on_ent)
        btn.bind('<Leave>', on_lev)
        return btn

    def _log(self, msg):
        self.pred_log.configure(state='normal')
        self.pred_log.insert('end', msg + '\n')
        self.pred_log.see('end')
        self.pred_log.configure(state='disabled')

    def _log_clear(self):
        self.pred_log.configure(state='normal')
        self.pred_log.delete('1.0', 'end')
        self.pred_log.configure(state='disabled')


    # ══════════════════════════════════════════════════════════════════════════
    # TAB 5 — User Prediction
    # ══════════════════════════════════════════════════════════════════════════
    def _build_user_prediction_tab(self):
        p = self.tab_userpred.scrollable_frame



        # ── User selector ──────────────────────────────────────────────────────
        self._section(p, '👤  Select User').pack(fill='x', padx=15, pady=(12,4))

        top = tk.Frame(p, bg=BG2)
        top.pack(fill='x', padx=15, pady=4)

        tk.Label(top, text='Username:', font=FONT, bg=BG2, fg=FG2).pack(side='left', padx=(0,6))
        self.up_user_var = tk.StringVar()
        self.up_user_cb  = ttk.Combobox(top, textvariable=self.up_user_var,
                                         font=FONT, width=30, state='normal')
        self.up_user_cb.pack(side='left', padx=4)
        # Autocomplete: filter dropdown as user types
        self._up_all_users = []
        self.up_user_cb.bind('<KeyRelease>', self._up_filter_users)

        self._btn(top, '🔄 Load Users', BG3,    self._up_load_users).pack(side='left', padx=6)
        self._btn(top, '📈 Analyze',   ACCENT2, self._up_analyze).pack(side='left', padx=4)

        self.up_status = tk.Label(p, text='Click "Load Users" to begin.',
                                   font=FONT_S, bg=BG2, fg=ACCENT)
        self.up_status.pack(pady=2)

        # ── Pattern section (fixed height so tree below gets expand room) ──────
        pat_outer = tk.Frame(p, bg=BG2, height=185)
        pat_outer.pack(fill='x', padx=15, pady=(6,0))
        pat_outer.pack_propagate(False)   # <- locks height at 185px

        # Day column
        day_col = tk.Frame(pat_outer, bg=BG2)
        day_col.pack(side='left', fill='both', expand=True, padx=(0,6))
        self._section(day_col, '📅  Login Days (past history)').pack(fill='x')
        day_scroll_f = tk.Frame(day_col, bg=BG2)
        day_scroll_f.pack(fill='both', expand=True)
        day_vsb = ttk.Scrollbar(day_scroll_f, orient='vertical')
        day_vsb.pack(side='right', fill='y')
        self.up_day_canvas = tk.Canvas(day_scroll_f, bg=BG2, highlightthickness=0,
                                        yscrollcommand=day_vsb.set)
        self.up_day_canvas.pack(side='left', fill='both', expand=True)
        day_vsb.config(command=self.up_day_canvas.yview)
        self.up_day_frame = tk.Frame(self.up_day_canvas, bg=BG2)
        self.up_day_canvas.create_window((0,0), window=self.up_day_frame, anchor='nw')
        self.up_day_frame.bind('<Configure>', lambda e: self.up_day_canvas.configure(
            scrollregion=self.up_day_canvas.bbox('all')))

        # Hour column
        hr_col = tk.Frame(pat_outer, bg=BG2)
        hr_col.pack(side='left', fill='both', expand=True)
        self._section(hr_col, '🕐  Login Hours (past history)').pack(fill='x')
        hr_scroll_f = tk.Frame(hr_col, bg=BG2)
        hr_scroll_f.pack(fill='both', expand=True)
        hr_vsb = ttk.Scrollbar(hr_scroll_f, orient='vertical')
        hr_vsb.pack(side='right', fill='y')
        self.up_hour_canvas = tk.Canvas(hr_scroll_f, bg=BG2, highlightthickness=0,
                                         yscrollcommand=hr_vsb.set)
        self.up_hour_canvas.pack(side='left', fill='both', expand=True)
        hr_vsb.config(command=self.up_hour_canvas.yview)
        self.up_hour_frame = tk.Frame(self.up_hour_canvas, bg=BG2)
        self.up_hour_canvas.create_window((0,0), window=self.up_hour_frame, anchor='nw')
        self.up_hour_frame.bind('<Configure>', lambda e: self.up_hour_canvas.configure(
            scrollregion=self.up_hour_canvas.bbox('all')))

        # ── Stats strip ────────────────────────────────────────────────────────
        self.up_stats_var = tk.StringVar(value='')
        tk.Label(p, textvariable=self.up_stats_var, font=FONT_S,
                 bg=BG2, fg=SUCCESS, anchor='w').pack(fill='x', padx=20, pady=(4,0))

        # ── First Login of the Day section ────────────────────────────────────
        self._section(p, '⏰  First Login of the Day').pack(fill='x', padx=15, pady=(10,2))

        fl_outer = tk.Frame(p, bg=BG2, height=230)
        fl_outer.pack(fill='x', padx=15, pady=(0,2))
        fl_outer.pack_propagate(False)

        # Bar chart canvas (vertical scroll)
        fl_left = tk.Frame(fl_outer, bg=BG2)
        fl_left.pack(side='left', fill='both', expand=True, padx=(0,6))
        fl_scroll_f = tk.Frame(fl_left, bg=BG2)
        fl_scroll_f.pack(fill='both', expand=True)
        fl_vsb = ttk.Scrollbar(fl_scroll_f, orient='vertical')
        fl_vsb.pack(side='right', fill='y')
        self.up_fl_canvas = tk.Canvas(fl_scroll_f, bg=BG2, highlightthickness=0,
                                       yscrollcommand=fl_vsb.set)
        self.up_fl_canvas.pack(side='left', fill='both', expand=True)
        fl_vsb.config(command=self.up_fl_canvas.yview)
        self.up_fl_frame = tk.Frame(self.up_fl_canvas, bg=BG2)
        self.up_fl_canvas.create_window((0, 0), window=self.up_fl_frame, anchor='nw')
        self.up_fl_frame.bind('<Configure>', lambda e: self.up_fl_canvas.configure(
            scrollregion=self.up_fl_canvas.bbox('all')))


        # Stats panel (right side)
        fl_right = tk.Frame(fl_outer, bg=BG3, width=200)
        fl_right.pack(side='left', fill='y', padx=(0,0))
        fl_right.pack_propagate(False)
        self._section(fl_right, 'Analysis').pack(fill='x', padx=6, pady=(6,2))
        stats_scroll_f = tk.Frame(fl_right, bg=BG3)
        stats_scroll_f.pack(fill='both', expand=True, padx=(4,0), pady=(0,4))
        
        stats_vsb = ttk.Scrollbar(stats_scroll_f, orient='vertical')
        stats_vsb.pack(side='right', fill='y')
        
        up_fl_stats_canvas = tk.Canvas(stats_scroll_f, bg=BG3, highlightthickness=0, yscrollcommand=stats_vsb.set)
        up_fl_stats_canvas.pack(side='left', fill='both', expand=True)
        stats_vsb.config(command=up_fl_stats_canvas.yview)
        
        up_fl_stats_frame = tk.Frame(up_fl_stats_canvas, bg=BG3)
        up_fl_stats_canvas.create_window((0,0), window=up_fl_stats_frame, anchor='nw', width=175)
        
        up_fl_stats_frame.bind('<Configure>', lambda e: up_fl_stats_canvas.configure(
            scrollregion=up_fl_stats_canvas.bbox('all')))

        self.up_fl_stats_var = tk.StringVar(value='Run Analyze to see stats.')
        tk.Label(up_fl_stats_frame, textvariable=self.up_fl_stats_var,
                 font=FONT_S, bg=BG3, fg=FG2, justify='left',
                 anchor='nw', wraplength=165).pack(fill='both', expand=True, padx=4, pady=2)


        self._section(p, '🔮  Future Login Prediction').pack(fill='x', padx=15, pady=(10,4))

        pred_bar = tk.Frame(p, bg=BG2)
        pred_bar.pack(fill='x', padx=15, pady=2)

        tk.Label(pred_bar, text='From:', font=FONT, bg=BG2, fg=FG2).pack(side='left')
        tomorrow  = (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')
        next_week = (date.today() + timedelta(days=7)).strftime('%Y-%m-%d')

        self.up_from = tk.Entry(pred_bar, font=FONT, width=14, bg=BG3, fg=FG,
                                 insertbackground='white', relief='flat', bd=4)
        self.up_from.pack(side='left', padx=4)
        self.up_from.insert(0, tomorrow)

        tk.Label(pred_bar, text='To:', font=FONT, bg=BG2, fg=FG2).pack(side='left', padx=(8,0))
        self.up_to = tk.Entry(pred_bar, font=FONT, width=14, bg=BG3, fg=FG,
                               insertbackground='white', relief='flat', bd=4)
        self.up_to.pack(side='left', padx=4)
        self.up_to.insert(0, next_week)

        self._btn(pred_bar, '🔮 Predict', SUCCESS, self._up_predict).pack(side='left', padx=10)

        # Results tree — fixed height inside scrollable canvas
        rf = tk.Frame(p, bg=BG2)
        rf.pack(fill='x', padx=15, pady=(4,10))

        cols = ('Date', 'Day', 'Likely Login?', 'Login Window',
                'Most Common Login', 'Avg Session (hrs)', 'On Leave?')
        self.up_tree = ttk.Treeview(rf, columns=cols, show='headings', height=12)
        widths = [110, 90, 100, 180, 140, 130, 90]
        for c, w in zip(cols, widths):
            self.up_tree.heading(c, text=c)
            self.up_tree.column(c, width=w, anchor='center')
        vsb = ttk.Scrollbar(rf, orient='vertical', command=self.up_tree.yview)
        hsb = ttk.Scrollbar(rf, orient='horizontal', command=self.up_tree.xview)
        self.up_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.up_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        rf.rowconfigure(0, weight=1); rf.columnconfigure(0, weight=1)


        # Tag colours
        self.up_tree.tag_configure('likely',   background='#1a3a1a', foreground='#86efac')
        self.up_tree.tag_configure('unlikely', background='#1a1a2e', foreground=FG2)
        self.up_tree.tag_configure('leave',    background='#3a1a1a', foreground='#fca5a5')

    # ── User Prediction Helpers ────────────────────────────────────────────────
    def _up_load_users(self):
        """Load unique usernames from login_logs.csv into the combobox."""
        if not os.path.exists('login_logs.csv'):
            messagebox.showwarning('Missing File',
                'login_logs.csv not found.\nRun Import Data first to generate it.')
            return
        try:
            df = pd.read_csv('login_logs.csv')
            col = next((c for c in df.columns if 'username' in c.lower()), None)
            if not col:
                messagebox.showerror('Error', 'No Username column found in login_logs.csv')
                return
            users = sorted(df[col].dropna().str.lower().str.strip().unique().tolist())
            self._up_all_users = users          # store full list for filtering
            self.up_user_cb['values'] = users
            self.up_status.config(text=f'{len(users)} users loaded. Type to filter or select one, then click Analyze.',
                                   fg=SUCCESS)
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def _up_filter_users(self, event=None):
        """Filter combobox dropdown in real time as the user types."""
        # Ignore navigation keys to avoid double-processing
        if event and event.keysym in ('Return', 'Tab', 'Down', 'Up', 'Escape', 'Left', 'Right'):
            return

        typed = self.up_user_var.get()
        typed_lower = typed.strip().lower()
        all_u = self._up_all_users if getattr(self, '_up_all_users', None) else []

        if not typed:
            self.up_user_cb['values'] = all_u
        else:
            filtered = [u for u in all_u if typed_lower in u.lower()]
            self.up_user_cb['values'] = filtered
            
            if filtered:
                # Save cursor position
                cursor_pos = self.up_user_cb.index(tk.INSERT)
                
                # Asynchronously open dropdown and clear selection so Tkinter 
                # doesn't overwrite it after this function returns
                def _open_and_fix():
                    self.up_user_cb.event_generate('<Down>')
                    self.up_user_cb.selection_clear()
                    self.up_user_cb.icursor(cursor_pos)
                
                self.up_user_cb.after(10, _open_and_fix)

    def _up_analyze(self):
        """Analyze selected user's login history and show patterns."""
        username = self.up_user_var.get().strip().lower()
        if not username:
            messagebox.showwarning('Select User', 'Please select or type a username first.')
            return
        if not os.path.exists('login_logs.csv'):
            messagebox.showwarning('Missing', 'login_logs.csv not found.')
            return
        try:
            df  = pd.read_csv('login_logs.csv')
            col = next((c for c in df.columns if 'username' in c.lower()), None)
            ts_col = next((c for c in df.columns if 'timestamp' in c.lower() or
                           'time' in c.lower()), None)
            if not col or not ts_col:
                messagebox.showerror('Error', 'Required columns not found.'); return

            udf = df[df[col].str.lower().str.strip() == username].copy()
            if udf.empty:
                self.up_status.config(text=f'No records found for user: {username}', fg=DANGER)
                return

            udf[ts_col] = pd.to_datetime(udf[ts_col], errors='coerce')
            udf = udf.dropna(subset=[ts_col])
            udf['DayName'] = udf[ts_col].dt.day_name()
            udf['Hour']    = udf[ts_col].dt.hour

            # Store for prediction later
            self._up_udf = udf
            self._up_ts_col = ts_col

            # ── Day of week bar chart (text-based) ────────────────────────────
            day_order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
            day_counts = udf['DayName'].value_counts().reindex(day_order, fill_value=0)
            max_d = max(day_counts.max(), 1)

            for w in self.up_day_frame.winfo_children(): w.destroy()
            for day, cnt in day_counts.items():
                bar_len = int((cnt / max_d) * 20)
                bar = '█' * bar_len
                color = SUCCESS if cnt == day_counts.max() else (
                        ACCENT if cnt > 0 else FG2)
                tk.Label(self.up_day_frame,
                         text=f'{day[:3]}  {bar}  {cnt}',
                         font=CODE, bg=BG2, fg=color, anchor='w'
                         ).pack(fill='x', padx=4, pady=1)

            # ── Hour of day bar chart ──────────────────────────────────────────
            hour_counts = udf['Hour'].value_counts().sort_index()
            max_h = max(hour_counts.max(), 1)

            for w in self.up_hour_frame.winfo_children(): w.destroy()
            for hr, cnt in hour_counts.items():
                bar_len = int((cnt / max_h) * 18)
                bar = '█' * bar_len
                ampm = 'AM' if hr < 12 else 'PM'
                hr12 = hr if hr <= 12 else hr - 12
                hr12 = 12 if hr12 == 0 else hr12
                color = WARNING if cnt == hour_counts.max() else FG
                tk.Label(self.up_hour_frame,
                         text=f'{hr12:2d}{ampm}  {bar}  {cnt}',
                         font=CODE, bg=BG2, fg=color, anchor='w'
                         ).pack(fill='x', padx=4, pady=1)

            # ── Stats ──────────────────────────────────────────────────────────
            most_day  = day_counts.idxmax()
            most_hour = hour_counts.idxmax()
            hr12 = most_hour if most_hour <= 12 else most_hour - 12
            hr12 = 12 if hr12 == 0 else hr12
            ampm = 'AM' if most_hour < 12 else 'PM'

            self.up_stats_var.set(
                f'  Total Logins: {len(udf)}   |   Most Active Day: {most_day}'
                f'   |   Peak Login Hour: {hr12}:00 {ampm}   |   Date Range: '
                f'{udf[ts_col].min().date()} to {udf[ts_col].max().date()}'
            )

            # ── First Login of the Day chart ──────────────────────────────────
            # Filter: consider the entire day (12 AM to next 12 AM) for 'First Login'
            full_udf = udf.copy()
            full_udf['Date'] = full_udf[ts_col].dt.date
            first_logins = full_udf.groupby('Date')[ts_col].min().reset_index()
            first_logins.columns = ['Date', 'FirstLogin']
            first_logins['FirstHour'] = first_logins['FirstLogin'].dt.hour
            first_logins['FirstMinute'] = first_logins['FirstLogin'].dt.minute

            fl_hour_counts = first_logins['FirstHour'].value_counts().sort_index()
            max_fl = max(fl_hour_counts.max(), 1) if not fl_hour_counts.empty else 1

            for w in self.up_fl_frame.winfo_children(): w.destroy()
            for hr, cnt in fl_hour_counts.items():
                bar_len = int((cnt / max_fl) * 22)
                bar  = '█' * bar_len
                ampm_fl = 'AM' if hr < 12 else 'PM'
                hr12_fl = hr if hr <= 12 else hr - 12
                hr12_fl = 12 if hr12_fl == 0 else hr12_fl
                color = ACCENT if cnt == fl_hour_counts.max() else FG
                tk.Label(self.up_fl_frame,
                         text=f'{hr12_fl:2d}:00 {ampm_fl}  {bar}  {cnt}d',
                         font=CODE, bg=BG2, fg=color, anchor='w'
                         ).pack(fill='x', padx=4, pady=1)

            # First login stats
            total_days  = len(first_logins)
            if total_days > 0:
                # Most common first-login time (HH:MM string mode)
                avg_fl = first_logins['FirstLogin'].dt.strftime('%H:%M').mode()
                avg_fl = avg_fl.iloc[0] if not avg_fl.empty else 'N/A'

                # Earliest & latest by TIME OF DAY only (minutes since midnight)
                first_logins['MinOfDay'] = (first_logins['FirstHour'] * 60
                                            + first_logins['FirstMinute'])
                min_idx = first_logins['MinOfDay'].idxmin()
                max_idx = first_logins['MinOfDay'].idxmax()
                early_fl = first_logins.loc[min_idx, 'FirstLogin'].strftime('%H:%M')
                late_fl  = first_logins.loc[max_idx, 'FirstLogin'].strftime('%H:%M')

                # Dynamic hourly percentages
                hour_counts = first_logins['FirstHour'].value_counts().sort_index()
                hour_stats_lines = []
                for hr, cnt in hour_counts.items():
                    ampm = 'AM' if hr < 12 else 'PM'
                    hr12 = hr if hr <= 12 else hr - 12
                    hr12 = 12 if hr12 == 0 else hr12
                    pct = int(round((cnt / total_days) * 100))
                    hour_stats_lines.append(f'{hr12:02d}:00 {ampm}: {cnt}d ({pct}%)')
                
                hour_stats_str = '\n'.join(hour_stats_lines)

            else:
                avg_fl = early_fl = 'N/A'
                hour_stats_str = 'No data available'

            self.up_fl_stats_var.set(
                f'Working days: {total_days}\n\n'
                f'Earliest login:\n  {early_fl}\n\n'
                f'Most common:\n  {avg_fl}\n\n'
                f'Hourly Breakdown:\n{hour_stats_str}'
            )

            self.up_status.config(
                text=f'Analysis complete for "{username}". Now click Predict.', fg=SUCCESS)

        except Exception as e:
            messagebox.showerror('Analysis Error', str(e))

    def _up_predict(self):
        """Predict future login windows for the selected user."""
        username = self.up_user_var.get().strip().lower()
        if not username:
            messagebox.showwarning('Select User', 'Select a user and click Analyze first.')
            return
        if not hasattr(self, '_up_udf') or self._up_udf is None or self._up_udf.empty:
            messagebox.showwarning('Analyze First', 'Click Analyze before Predict.')
            return

        from_str = self.up_from.get().strip()
        to_str   = self.up_to.get().strip()
        try:
            from_dt = datetime.strptime(from_str, '%Y-%m-%d').date()
            to_dt   = datetime.strptime(to_str,   '%Y-%m-%d').date()
        except ValueError:
            messagebox.showerror('Date Error', 'Use YYYY-MM-DD format.'); return
        if to_dt < from_dt:
            messagebox.showerror('Date Error', 'End date must be after Start date.'); return

        udf    = self._up_udf
        ts_col = self._up_ts_col

        # Build pattern
        day_order   = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
        day_counts  = udf['DayName'].value_counts().reindex(day_order, fill_value=0)
        total_days_seen = udf[ts_col].dt.date.nunique()
        days_with_login = set(udf['DayName'].unique())

        # First login window and Most Common Login time
        full_udf = udf.copy()
        full_udf['Date'] = full_udf[ts_col].dt.date
        first_logins = full_udf.groupby('Date')[ts_col].min().reset_index()

        if not first_logins.empty:
            total_days = len(first_logins)
            
            # If only 1 day of data, create a simple +/- 1 hour window around it
            if total_days == 1:
                single_hr = first_logins[ts_col].dt.hour.iloc[0]
                win_start = max(0, int(single_hr - 1))
                win_end   = min(23, int(single_hr + 1))
                most_common_login_str = first_logins[ts_col].dt.strftime('%H:%M').iloc[0]
            else:
                mean_hr = first_logins[ts_col].dt.hour.mean()
                std_hr  = first_logins[ts_col].dt.hour.std()
                if pd.isna(std_hr): std_hr = 1.0
                win_start = max(0, int(mean_hr - max(std_hr, 0.5)))
                win_end   = min(23, int(mean_hr + max(std_hr, 0.5)) + 1)
                
                # Most common first-login time — 3-level fallback:
                hhmm_series = first_logins[ts_col].dt.strftime('%H:%M')
                hhmm_mode   = hhmm_series.mode()
                hhmm_top_count = hhmm_series.value_counts().iloc[0] if not hhmm_series.empty else 1

                if not hhmm_mode.empty and hhmm_top_count > 1:
                    most_common_login_str = hhmm_mode.iloc[0]
                else:
                    hr_series = first_logins[ts_col].dt.hour
                    hr_mode   = hr_series.mode()
                    hr_top_count = hr_series.value_counts().iloc[0] if not hr_series.empty else 1

                    if not hr_mode.empty and hr_top_count > 1:
                        h = int(hr_mode.iloc[0])
                        ampm = 'AM' if h < 12 else 'PM'
                        h12  = h if h <= 12 else h - 12
                        h12  = 12 if h12 == 0 else h12
                        most_common_login_str = f'~{h12}:00 {ampm}'
                    else:
                        avg_min = int(first_logins[ts_col].dt.hour.mean() * 60
                                      + first_logins[ts_col].dt.minute.mean())
                        most_common_login_str = f'~{avg_min//60:02d}:{avg_min%60:02d} (avg)'

        else:
            win_start, win_end = 9, 10
            most_common_login_str = 'N/A'
            total_days = 0

        def fmt_hr(h):
            ampm = 'AM' if h < 12 else 'PM'
            h12  = h if h <= 12 else h - 12
            h12  = 12 if h12 == 0 else h12
            return f'{h12}:00 {ampm}'

        # Determine Login Window based on the most frequent hour for a tighter prediction
        if total_days > 1:
            hour_counts = first_logins[ts_col].dt.hour.value_counts().sort_values(ascending=False)
            
            if len(hour_counts) >= 1:
                # Take the single most frequent hour to create a strict 1-hour window
                top_hour = hour_counts.index[0]
                win_start = int(top_hour)
                win_end   = win_start + 1
        
        # Ensure the 'Most Common Login' falls inside the calculated window
        if most_common_login_str not in ('N/A', 'No data'):
            # Try to extract the hour from the most_common_login_str
            mc_hr = None
            if ':' in most_common_login_str and 'AM' in most_common_login_str.upper():
                try: mc_hr = int(most_common_login_str.split(':')[0].replace('~','')) % 12
                except: pass
            elif ':' in most_common_login_str and 'PM' in most_common_login_str.upper():
                try: mc_hr = (int(most_common_login_str.split(':')[0].replace('~','')) % 12) + 12
                except: pass
            elif ':' in most_common_login_str and 'avg' not in most_common_login_str:
                # 24 hour exact string (Level 1 mode)
                try: mc_hr = int(most_common_login_str.split(':')[0])
                except: pass
                
            if mc_hr is not None:
                if mc_hr < win_start:
                    win_start = mc_hr
                if mc_hr >= win_end:
                    win_end = mc_hr + 1
                    
        win_str = f'{fmt_hr(win_start)} - {fmt_hr(win_end)}'


        # Average session duration — from concurrency_report if available
        avg_session = 'N/A'

        # Load APPROVED leave records for this specific user only
        on_leave_dates = set()
        if os.path.exists(LEAVE_FILE):
            try:
                ldf = self._load_hr_leaves()
                # Only keep rows where UserId matches and Status is Approved
                if 'UserId' in ldf.columns and 'Status' in ldf.columns:
                    ldf = ldf[
                        (ldf['UserId'].astype(str).str.strip().str.lower() == username) &
                        (ldf['Status'].astype(str).str.strip().str.lower() == 'approved')
                    ]
                    for _, row in ldf.iterrows():
                        try:
                            s = pd.to_datetime(row.get('From Date', '')).date()
                            e = pd.to_datetime(row.get('To Date', '')).date()
                            cur = s
                            while cur <= e:
                                on_leave_dates.add(cur)
                                cur += timedelta(days=1)
                        except Exception:
                            pass
            except Exception:
                pass


        mandatory, optional = load_holidays()
        holidays = mandatory.union(optional)

        # Populate tree
        for r in self.up_tree.get_children(): self.up_tree.delete(r)

        cur_date = from_dt
        while cur_date <= to_dt:
            day_name  = cur_date.strftime('%A')
            on_leave  = cur_date in on_leave_dates
            is_holiday= cur_date in holidays
            day_cnt   = day_counts.get(day_name, 0)
            likely    = (day_name in days_with_login) and not on_leave and not is_holiday and day_cnt > 0

            if is_holiday:
                tag   = 'leave'
                pred  = 'Holiday'
                win   = '-'
                mcommon = '-'
            elif on_leave:
                tag   = 'leave'
                pred  = 'On Leave'
                win   = '-'
                mcommon = '-'
            elif likely:
                tag   = 'likely'
                pred  = 'Yes'
                win   = win_str
                mcommon = most_common_login_str
            else:
                tag   = 'unlikely'
                pred  = 'No'
                win   = '-'
                mcommon = '-'

            self.up_tree.insert('', 'end', tags=(tag,), values=(
                cur_date.strftime('%Y-%m-%d'),
                day_name,
                pred,
                win,
                mcommon,
                avg_session,
                'Yes' if on_leave else 'No',
            ))
            cur_date += timedelta(days=1)

        self.up_status.config(
            text=f'Prediction done for "{username}" from {from_str} to {to_str}.', fg=SUCCESS)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 6 — Graphs Dashboard
    # ══════════════════════════════════════════════════════════════════════════
    def _build_graphs_tab(self):
        p = self.tab_graphs # Now it's a direct frame
        tk.Frame(p, bg=BG).place(relwidth=1, relheight=1) # Background fill
        self._section(p, '📈  Generated Graphs & Visualizations').pack(fill='x', padx=15, pady=(12,4))
        
        main_f = tk.Frame(p, bg=BG)
        main_f.pack(fill='both', expand=True, padx=15, pady=5)
        
        # Left sidebar for list of graphs
        side_f = tk.Frame(main_f, bg=BG2, width=250)
        side_f.pack(side='left', fill='y', padx=(0, 10))
        side_f.pack_propagate(False)

        top_side = tk.Frame(side_f, bg=BG2)
        top_side.pack(fill='x', padx=10, pady=(10,5))
        tk.Label(top_side, text='CONTROLS:', font=FONT_B, bg=BG2, fg=ACCENT).pack(side='left')
        
        btn_col = tk.Frame(side_f, bg=BG2)
        btn_col.pack(fill='x', padx=10, pady=(0, 10))
        
        # Stacked buttons for clear visibility in narrow sidebar
        self._btn(btn_col, '🔄  Refresh List', ACCENT2, self._refresh_graphs_list).pack(fill='x', pady=2)
        self._btn(btn_col, '🗑️  Delete Selected', DANGER, self._delete_current_graph).pack(fill='x', pady=2)
        self._btn(btn_col, '💣  Delete All', DANGER, self._delete_all_graphs).pack(fill='x', pady=2)

        tk.Frame(side_f, bg=BG3, height=1).pack(fill='x', padx=10, pady=5) # Divider
        tk.Label(side_f, text='AVAILABLE GRAPHS:', font=FONT_B, bg=BG2, fg=FG2).pack(anchor='w', padx=10, pady=2)

        # Listbox for graphs
        self.graphs_listbox = tk.Listbox(side_f, font=FONT_S, bg=BG, fg=FG,
                                         selectmode='extended', 
                                         selectbackground=ACCENT, selectforeground='#ffffff',
                                         relief='flat', bd=0, highlightthickness=0)
        self.graphs_listbox.pack(fill='both', expand=True, padx=10, pady=(0,10))
        self.graphs_listbox.bind('<<ListboxSelect>>', self._on_graph_select)
        
        # Right viewport for image
        self.view_f = tk.Frame(main_f, bg=BG)
        self.view_f.pack(side='right', fill='both', expand=True)
        self.view_f.pack_propagate(False) # CRITICAL: Prevent image label from resizing the parent frame
        
        self.img_label = tk.Label(self.view_f, bg=BG)
        self.img_label.pack(fill='both', expand=True, padx=10, pady=(10, 0))
        
        # Bottom Description Bar
        desc_frame = tk.Frame(self.view_f, bg=BG)
        desc_frame.pack(fill='x', side='bottom', pady=5)
        
        # Initialize variables
        self.graph_desc_var = tk.StringVar(value="")
        self.current_img_tk = None
        self.current_pil_img = None
        self._last_loaded_graph = None

        self.graph_desc_lbl = tk.Label(desc_frame, textvariable=self.graph_desc_var, font=FONT, 
                                      bg=BG, fg=ACCENT, justify='center', wraplength=700)
        self.graph_desc_lbl.pack(fill='x', pady=(2, 5))
        
        # Bind resize event
        self.view_f.bind('<Configure>', self._on_view_resize)
        
        # Finally refresh list
        self._refresh_graphs_list()

    def _refresh_graphs_list(self):
        sel = self.graphs_listbox.curselection()
        current_idx = sel[0] if sel else 0

        self.graphs_listbox.delete(0, tk.END)
        self.available_graphs = [f for f in os.listdir('.') if f.endswith('.png') and not f.startswith('_tmp_')]
        for g in self.available_graphs:
            icon = "📊"
            if 'concurrency' in g.lower(): icon = "⚡"
            elif 'backtest' in g.lower():    icon = "🧪"
            elif 'simulation' in g.lower():  icon = "💡"
            elif 'user' in g.lower():        icon = "👤"
            elif 'comparison' in g.lower():  icon = "🔍"
            elif 'active_user' in g.lower(): icon = "🔑"
            
            self.graphs_listbox.insert(tk.END, f" {icon}  {g}")
        
        if not self.available_graphs:
            self.img_label.configure(image='', text='No graphs generated yet.\nRun Prediction/Training first.', fg=FG2, font=FONT_T)
            self.current_pil_img = None
            self.graph_desc_var.set("")
        else:
            if current_idx >= len(self.available_graphs): current_idx = 0
            self.graphs_listbox.select_set(current_idx)
            self._on_graph_select()

    def _delete_current_graph(self):
        selected_indices = self.graphs_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning('Warning', 'Please select one or more graphs to delete.')
            return
        
        files_to_delete = [self.available_graphs[i] for i in selected_indices]
        msg = f"Are you sure you want to delete {len(files_to_delete)} graph(s)?\n" + "\n".join(files_to_delete[:10])
        if len(files_to_delete) > 10: msg += "\n...and more"
        
        if messagebox.askyesno('Delete Graphs', msg + "\n\nThis cannot be undone."):
            try:
                for f in files_to_delete:
                    if os.path.exists(f): os.remove(f)
                self._refresh_graphs_list()
                self.img_label.configure(image='')
                messagebox.showinfo('Deleted', f'{len(files_to_delete)} graph(s) deleted.')
            except Exception as e:
                messagebox.showerror('Error', f'Could not delete graph(s): {e}')

    def _delete_all_graphs(self):
        files = [f for f in os.listdir('.') if f.endswith('.png') and not f.startswith('_tmp_')]
        if not files:
            messagebox.showinfo('Info', 'No graphs to delete.')
            return
        if messagebox.askyesno('Delete All', f'Are you sure you want to delete ALL {len(files)} graphs?\nThis cannot be undone.'):
            try:
                for f in files: os.remove(f)
                self._refresh_graphs_list()
                self.img_label.configure(image='')
                messagebox.showinfo('Deleted', 'All graphs have been deleted.')
            except Exception as e:
                messagebox.showerror('Error', f'Could not delete all graphs: {e}')

    def _on_graph_select(self, event=None):
        sel = self.graphs_listbox.curselection()
        if not sel: return
        # Extract filename (after the icon)
        display_text = self.graphs_listbox.get(sel[0])
        filename = self.available_graphs[sel[0]]

        # Dynamic Descriptions
        desc = ""
        
        if 'prediction' in filename:
            desc = "🎯 Login Intensity: Predicted login counts at 15m, 30m, and 60m intervals to visualize peak traffic times."
        elif 'active_user_logins' in filename:
            desc = "🔑 Historical Login Throughput: Total volume of successful login events recorded during this time interval."
        elif 'concurrency' in filename:
            desc = "⚡ Measured Login Frequency: Direct login counts calculated from raw SQL logs (non-ML)."
        elif 'backtest' in filename:
            desc = "🧪 Prediction Validation: Accuracy comparison between AI-predicted logins and historical ground truth."
        elif 'simulation' in filename:
            desc = "💡 Data Prep Analysis: Distribution and frequency analysis of login events across different days."
        else:
            desc = ""

        # Premium formatting for label
        if desc:
            self.graph_desc_var.set(f"FILENAME: {filename}\n—\n{desc}")
        else:
            self.graph_desc_var.set(f"FILENAME: {filename}")
  
        try:
            target_path = f"_tmp_{filename}"
            # Only reload if filename changed OR image not yet loaded
            if self._last_loaded_graph != filename or self.current_pil_img is None:
                shutil.copy2(filename, target_path)
                self.current_pil_img = Image.open(target_path)
                self.img_label.configure(text='')
                self._last_loaded_graph = filename
            self._resize_and_show_img()
        except Exception as e:
            self.img_label.configure(image='', text=f'Error loading graph:\n{e}', fg=DANGER, font=FONT_T)
            self.current_pil_img = None

    def _on_view_resize(self, event):
        if self.current_pil_img:
            self._resize_and_show_img()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 9 — User Master Report
    # ══════════════════════════════════════════════════════════════════════════
    def _build_user_master_tab(self):
        p = self.tab_usermaster.scrollable_frame
        self._section(p, '📋  All Users Prediction Report').pack(fill='x', padx=15, pady=(12,4))

        # Controls
        ctrl = tk.Frame(p, bg=BG2)
        ctrl.pack(fill='x', padx=15, pady=5)
        
        tk.Label(ctrl, text="Target Date:", font=FONT, bg=BG2, fg=FG2).pack(side='left', padx=5)
        self.um_date_ent = tk.Entry(ctrl, font=FONT, width=12, bg=BG3, fg=FG)
        self.um_date_ent.pack(side='left', padx=5)
        self.um_date_ent.insert(0, date.today().strftime('%Y-%m-%d'))

        self._btn(ctrl, '⚡ Generate Report', SUCCESS, self._run_user_master_report).pack(side='left', padx=10)
        
        tk.Label(ctrl, text="Search User:", font=FONT, bg=BG2, fg=FG2).pack(side='left', padx=(20, 5))
        self.um_search_var = tk.StringVar()
        self.um_search_var.trace_add('write', self._filter_user_master)
        tk.Entry(ctrl, textvariable=self.um_search_var, font=FONT, width=20, bg=BG3, fg=FG).pack(side='left', padx=5)

        self._section(p, '📑  Master List (Predicting for selected date)').pack(fill='x', padx=15, pady=(10,2))

        # Table
        rf = tk.Frame(p, bg=BG2)
        rf.pack(fill='both', expand=True, padx=15, pady=(0,10))

        cols = ('User Name', 'Prediction', 'Login Window (Pattern)', 'Status')
        self.um_tree = ttk.Treeview(rf, columns=cols, show='headings', height=25)
        for c in cols:
            self.um_tree.heading(c, text=c)
            self.um_tree.column(c, width=200 if 'Window' in c else 150, anchor='center')
        
        self.um_tree.tag_configure('likely',   foreground=SUCCESS)
        self.um_tree.tag_configure('unlikely', foreground=FG2)
        self.um_tree.tag_configure('leave',    foreground=DANGER)

        vsb = ttk.Scrollbar(rf, orient='vertical', command=self.um_tree.yview)
        self.um_tree.configure(yscrollcommand=vsb.set)
        self.um_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        rf.rowconfigure(0, weight=1); rf.columnconfigure(0, weight=1)

        self._um_full_data = [] # Store for filtering

    def _run_user_master_report(self):
        target_str = self.um_date_ent.get().strip()
        win_type   = '60m'
        try:
            target_date = datetime.strptime(target_str, '%Y-%m-%d').date()
        except:
            messagebox.showerror('Error', 'Invalid date format (YYYY-MM-DD)'); return

        # 1. Load Data
        df = self._load_login_logs()
        if df is None: return
        
        col    = next((c for c in df.columns if 'user' in c.lower()), None)
        ts_col = next((c for c in df.columns if 'timestamp' in c.lower() or 'time' in c.lower()), None)
        if not col or not ts_col:
            messagebox.showerror('Error', 'User or Timestamp columns not found in login_logs.csv')
            return

        df[ts_col] = pd.to_datetime(df[ts_col], errors='coerce')
        df = df.dropna(subset=[ts_col])
        df['DateOnly'] = df[ts_col].dt.date
        df['DayName']  = df[ts_col].dt.day_name()
        df['UserOnly'] = df[col].str.lower().str.strip()
        
        # Round timestamps based on window (using lowercase for modern pandas compatibility)
        if win_type == '15m':
            df['TargetTime'] = df[ts_col].dt.floor('15min').dt.strftime('%H:%M')
            delta = timedelta(minutes=15)
        elif win_type == '30m':
            df['TargetTime'] = df[ts_col].dt.floor('30min').dt.strftime('%H:%M')
            delta = timedelta(minutes=30)
        else: # 60m
            df['TargetTime'] = df[ts_col].dt.floor('1h').dt.strftime('%H:%M')
            delta = timedelta(hours=1)
        
        # 2. Get Holidays & Global Leaves
        mandatory, optional = load_holidays()
        holidays = mandatory.union(optional)
        
        all_leaves = {} # UserId -> set of dates
        if os.path.exists(LEAVE_FILE):
            try:
                ldf = self._load_hr_leaves()
                if 'UserId' in ldf.columns and 'Status' in ldf.columns:
                    approved = ldf[ldf['Status'].astype(str).str.strip().str.lower() == 'approved']
                    for _, row in approved.iterrows():
                        uid = str(row['UserId']).strip().lower()
                        s = pd.to_datetime(row.get('From Date')).date()
                        e = pd.to_datetime(row.get('To Date')).date()
                        all_leaves.setdefault(uid, set()).update(pd.date_range(s, e).date)
            except: pass

        # 3. Analyze per User — Optimized
        self.tab_usermaster.scrollable_frame.config(cursor="wait")
        self.update()
        
        day_name = target_date.strftime('%A')
        is_holiday = target_date in holidays
        
        # Pre-group first logins for speed (on Rounded TargetTime)
        first_logins_all = df.groupby(['UserOnly', 'DateOnly'])['TargetTime'].first().reset_index()
        user_patterns = df.groupby('UserOnly')['DayName'].unique()
        
        master_results = []
        unique_users = sorted(df['UserOnly'].unique())
        
        def fmt_time_str(t_str):
            try:
                dt = datetime.strptime(t_str, '%H:%M')
                val = dt.strftime('%I:%M %p').lstrip('0')
                end = (dt + delta).strftime('%I:%M %p').lstrip('0')
                return f"{val} - {end}"
            except: return t_str

        for user in unique_users:
            user_first = first_logins_all[first_logins_all['UserOnly'] == user]
            if user_first.empty: continue
            
            # Typical Window (Mode of TargetTime)
            modes = user_first['TargetTime'].mode()
            top_time = modes.iloc[0] if not modes.empty else "09:00"
            win_str = fmt_time_str(top_time)
            
            # Prediction
            on_leave = target_date in all_leaves.get(user, set())
            has_pattern = day_name in user_patterns.get(user, [])
            
            status = 'Normal Day'
            tag = 'likely'
            prediction = 'Likely'
            
            if is_holiday:
                status = 'Public Holiday'; tag = 'unlikely'; prediction = 'No'
            elif on_leave:
                status = 'On Leave'; tag = 'leave'; prediction = 'No'
            elif not has_pattern:
                status = 'Off Day'; tag = 'unlikely'; prediction = 'No'
            
            master_results.append((user, prediction, win_str, status, tag))

        self.tab_usermaster.scrollable_frame.config(cursor="")
        self._um_full_data = master_results
        self._filter_user_master()

    def _filter_user_master(self, *args):
        search = self.um_search_var.get().strip().lower()
        for r in self.um_tree.get_children(): self.um_tree.delete(r)
        
        for user, pred, win, status, tag in self._um_full_data:
            if not search or search in user:
                self.um_tree.insert('', 'end', values=(user, pred, win, status), tags=(tag,))

    def _resize_and_show_img(self):
        if not self.current_pil_img: return
        
        # Get current frame dimensions
        view_w = self.view_f.winfo_width() - 20 # padding
        view_h = self.view_f.winfo_height() - 20
        
        if view_w <= 10 or view_h <= 10: return
        
        # Calculate aspect maintaining size
        img_w, img_h = self.current_pil_img.size
        ratio = min(view_w/img_w, view_h/img_h)
        new_w = int(img_w * ratio)
        new_h = int(img_h * ratio)
        
        # Resize
        resized = self.current_pil_img.resize((new_w, new_h), Image.LANCZOS)
        self.current_img_tk = ImageTk.PhotoImage(resized)
        
        self.img_label.configure(image=self.current_img_tk)

# ── Launch ─────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    app = App()
    app.mainloop()
