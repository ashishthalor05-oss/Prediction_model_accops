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
import os
import sys
import subprocess
import threading
from datetime import datetime, timedelta, date
import shutil
import configparser

# ── colour palette ─────────────────────────────────────────────────────────────
BG        = '#0f172a'
BG2       = '#1e293b'
BG3       = '#334155'
ACCENT    = '#38bdf8'
ACCENT2   = '#0ea5e9'
SUCCESS   = '#22c55e'
WARNING   = '#f59e0b'
DANGER    = '#ef4444'
FG        = '#f1f5f9'
FG2       = '#94a3b8'
FONT      = ('Segoe UI', 10)
FONT_B    = ('Segoe UI', 10, 'bold')
FONT_T    = ('Segoe UI', 14, 'bold')
FONT_S    = ('Segoe UI', 9)
CODE      = ('Consolas', 9)

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
        hdr = tk.Frame(self, bg='#020617', pady=10)
        hdr.pack(fill='x')
        tk.Label(hdr, text='🖥  Resource Usage Prediction Model',
                 font=FONT_T, bg='#020617', fg=ACCENT).pack(side='left', padx=20)
        tk.Label(hdr, text='AI-powered server capacity planning',
                 font=FONT_S, bg='#020617', fg=FG2).pack(side='left')

    # ── Tabs ───────────────────────────────────────────────────────────────────
    def _build_tabs(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('TNotebook',          background=BG,  borderwidth=0)
        style.configure('TNotebook.Tab',      background=BG3, foreground=FG2,
                        padding=[16,6], font=FONT)
        style.map('TNotebook.Tab',
                  background=[('selected', BG2)],
                  foreground=[('selected', ACCENT)])
        style.configure('Treeview',           background=BG2, fieldbackground=BG2,
                        foreground=FG,        rowheight=24,   font=FONT_S)
        style.configure('Treeview.Heading',   background='#020617', foreground=ACCENT,
                        font=FONT_B,          relief='flat')
        style.map('Treeview', background=[('selected', ACCENT2)])
        style.configure('TCombobox', fieldbackground=BG3, background=BG3,
                        foreground=FG, selectbackground=ACCENT2)

        nb = ttk.Notebook(self)
        nb.pack(fill='both', expand=True, padx=10, pady=(6,10))


        self.tab_predict  = tk.Frame(nb, bg=BG2)
        self.tab_import   = tk.Frame(nb, bg=BG2)
        self.tab_leave    = tk.Frame(nb, bg=BG2)
        self.tab_results  = tk.Frame(nb, bg=BG2)
        self.tab_userpred = tk.Frame(nb, bg=BG2)

        nb.add(self.tab_predict,  text=' 📊  Run Prediction ')
        nb.add(self.tab_import,   text=' 📂  Import Data ')
        nb.add(self.tab_leave,    text=' 📅  Employee Leaves ')
        nb.add(self.tab_results,  text=' 📋  Results Viewer ')
        nb.add(self.tab_userpred, text=' 👤  User Prediction ')

        self._build_predict_tab()
        self._build_import_tab()
        self._build_leave_tab()
        self._build_results_tab()
        self._build_user_prediction_tab()


    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — Run Prediction
    # ══════════════════════════════════════════════════════════════════════════
    def _build_predict_tab(self):
        p = self.tab_predict
        self._section(p, '⚙️  Prediction Settings').pack(fill='x', padx=15, pady=(12,4))

        form = tk.Frame(p, bg=BG2)
        form.pack(fill='x', padx=15, pady=4)

        def lbl(text, row, col):
            tk.Label(form, text=text, font=FONT, bg=BG2, fg=FG2, anchor='w'
                     ).grid(row=row, column=col, sticky='w', padx=8, pady=5)
        def ent(row, col, default='', width=18):
            e = tk.Entry(form, font=FONT, width=width, bg=BG3, fg=FG,
                         insertbackground='white', relief='flat', bd=4)
            e.grid(row=row, column=col, sticky='ew', padx=8, pady=5)
            e.insert(0, default)
            return e

        tomorrow = (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')
        next_week = (date.today() + timedelta(days=7)).strftime('%Y-%m-%d')

        lbl('Start Date (YYYY-MM-DD)', 0, 0);  self.pred_start = ent(0, 1, tomorrow)
        lbl('End Date   (YYYY-MM-DD)', 0, 2);  self.pred_end   = ent(0, 3, next_week)

        # Buttons
        bf = tk.Frame(p, bg=BG2)
        bf.pack(pady=8)
        self._btn(bf, '▶  Run Prediction', ACCENT2,   self._run_prediction).pack(side='left', padx=6)
        self._btn(bf, '📁  Export to Excel', SUCCESS, self._export_prediction_excel).pack(side='left', padx=6)

        # Status
        self.pred_status = tk.StringVar(value='Ready.')
        tk.Label(p, textvariable=self.pred_status, font=FONT_S,
                 bg=BG2, fg=FG2).pack(pady=2)

        # Output log
        self._section(p, '📄  Output Log').pack(fill='x', padx=15, pady=(8,2))
        self.pred_log = tk.Text(p, height=10, font=CODE, bg='#020617', fg='#86efac',
                                insertbackground='white', relief='flat', state='disabled')
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
                cmd = [sys.executable, 'predict_future.py', start, end]
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, text=True,
                                        cwd=os.getcwd())
                for line in proc.stdout:
                    self._log(line.rstrip())
                proc.wait()
                self.pred_status.set('✅ Prediction complete.')
                self._refresh_results()
            except Exception as e:
                self._log(f'ERROR: {e}')
                self.pred_status.set('❌ Error during prediction.')

        threading.Thread(target=worker, daemon=True).start()

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
        p = self.tab_import

        # ── DB Connection Section ──────────────────────────────────────────────
        self._section(p, '🗄  Fetch from SQL Server Express').pack(fill='x', padx=15, pady=(12,2))

        db_outer = tk.Frame(p, bg='#0f2336', relief='flat', bd=0)
        db_outer.pack(fill='x', padx=15, pady=(0,6))

        db_form = tk.Frame(db_outer, bg='#0f2336', padx=10, pady=8)
        db_form.pack(fill='x')

        def dlbl(text, row, col, colspan=1):
            tk.Label(db_form, text=text, font=FONT, bg='#0f2336', fg=FG2, anchor='w'
                     ).grid(row=row, column=col, columnspan=colspan, sticky='w', padx=6, pady=3)

        def dent(row, col, default='', width=22, show=''):
            e = tk.Entry(db_form, font=FONT, width=width, bg=BG3, fg=FG,
                         insertbackground='white', relief='flat', bd=4, show=show)
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
        auth_f = tk.Frame(db_form, bg='#0f2336')
        auth_f.grid(row=1, column=3, sticky='w', padx=6)
        tk.Radiobutton(auth_f, text='Windows Auth', variable=self.db_auth, value='windows',
                       bg='#0f2336', fg=FG, selectcolor=BG3, activebackground='#0f2336',
                       font=FONT, command=self._db_toggle_auth).pack(side='left')
        tk.Radiobutton(auth_f, text='SQL Auth', variable=self.db_auth, value='sql',
                       bg='#0f2336', fg=FG, selectcolor=BG3, activebackground='#0f2336',
                       font=FONT, command=self._db_toggle_auth).pack(side='left', padx=8)

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
        btn_f = tk.Frame(db_form, bg='#0f2336')
        btn_f.grid(row=4, column=0, columnspan=4, pady=(6,2), sticky='w', padx=4)
        self._btn(btn_f, '🔌 Test Connection', ACCENT2,  self._db_test).pack(side='left', padx=4)
        self._btn(btn_f, '⬇  Fetch Data',      SUCCESS,  self._db_fetch).pack(side='left', padx=4)
        self.db_status_lbl = tk.Label(btn_f, text='', font=FONT_S, bg='#0f2336', fg=FG2)
        self.db_status_lbl.pack(side='left', padx=10)

        # Row 5 — Mini log
        self.db_log = tk.Text(db_outer, height=4, font=CODE, bg='#020617', fg='#7dd3fc',
                              relief='flat', state='disabled', padx=6, pady=4)
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
            ('Raw Log File',          'log_data.csv',              'Import raw system log data'),
            ('Concurrency Report',    'concurrency_report.csv',    'Import pre-computed concurrency report'),
            ('Holidays File',         'holidays.csv',              'Import holiday list (Date/Start Date/End Date/Type)'),
            ('Employee Leaves',       LEAVE_FILE,                  'Import employee leave records'),
        ]

        for label, fname, hint in imports:
            row = tk.Frame(p, bg=BG3, pady=8, padx=12)
            row.pack(fill='x', padx=15, pady=4)
            tk.Label(row, text=label, font=FONT_B, bg=BG3, fg=FG,  width=22, anchor='w').pack(side='left')
            tk.Label(row, text=hint,  font=FONT_S, bg=BG3, fg=FG2, width=28, anchor='w').pack(side='left')
            # Drag & drop zone label
            dnd_lbl = tk.Label(row, text='⬇ Drop here', font=FONT_S, bg='#1e3a4a',
                               fg=ACCENT, width=12, relief='flat', pady=4, cursor='hand2')
            dnd_lbl.pack(side='left', padx=6)
            self._make_drop_target(dnd_lbl, row, fname)
            self._btn(row, '📂 Browse', ACCENT2,
                      lambda f=fname: self._browse_import(f)).pack(side='right', padx=4)
            # Status indicator
            exists = '✅ Exists' if os.path.exists(fname) else '❌ Missing'
            color  = SUCCESS if os.path.exists(fname) else DANGER
            tk.Label(row, text=exists, font=FONT_S, bg=BG3, fg=color, width=10).pack(side='right', padx=4)

        # ── Special row: Employee Holidays (HR Excel) ──────────────────────────
        hr_row = tk.Frame(p, bg='#1e2d1e', pady=8, padx=12)  # slightly different bg to stand out
        hr_row.pack(fill='x', padx=15, pady=4)
        tk.Label(hr_row, text='Employee Holidays\n(HR Excel)',
                 font=FONT_B, bg='#1e2d1e', fg='#86efac', width=22, anchor='w').pack(side='left')
        tk.Label(hr_row, text='Planned & Unplanned leaves from HR system',
                 font=FONT_S, bg='#1e2d1e', fg=FG2, width=28, anchor='w').pack(side='left')
        hr_dnd = tk.Label(hr_row, text='⬇ Drop here', font=FONT_S, bg='#1e3a4a',
                          fg=ACCENT, width=12, relief='flat', pady=4, cursor='hand2')
        hr_dnd.pack(side='left', padx=6)
        self._make_hr_drop_target(hr_dnd)
        self._btn(hr_row, '📂 Browse', SUCCESS,
                  self._browse_hr_excel).pack(side='right', padx=4)
        count_lbl_text = f'📋 {len(self._load_leaves())} records' if os.path.exists(LEAVE_FILE) else '❌ No leaves yet'
        count_color    = SUCCESS if os.path.exists(LEAVE_FILE) else DANGER
        tk.Label(hr_row, text=count_lbl_text, font=FONT_S, bg='#1e2d1e',
                 fg=count_color, width=14).pack(side='right', padx=4)

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

    def _make_drop_target(self, widget, row_frame, target_filename):
        """Register a widget as a drag-and-drop target for a specific file."""
        def on_drop(event):
            # tkinterdnd2 returns path(s) — strip braces for paths with spaces
            raw = event.data.strip()
            if raw.startswith('{') and raw.endswith('}'):
                raw = raw[1:-1]
            path = raw
            if not os.path.exists(path):
                messagebox.showerror('Drop Error', f'File not found: {path}'); return
            try:
                shutil.copy2(path, os.path.join(os.getcwd(), target_filename))
                # Flash the drop zone green to confirm
                widget.configure(bg=SUCCESS, text='✅ Imported!')
                self.after(2000, lambda: widget.configure(bg='#1e3a4a', text='⬇ Drop here'))
                messagebox.showinfo('Imported ✅', f'File saved as  {target_filename}')
                self.import_path_var.set(target_filename)
                self._preview_file(target_filename)
            except Exception as e:
                messagebox.showerror('Drop Error', str(e))

        def on_enter(event): widget.configure(bg=ACCENT2)
        def on_leave(event): widget.configure(bg='#1e3a4a')

        widget.drop_target_register(DND_FILES)
        widget.dnd_bind('<<Drop>>',      on_drop)
        widget.dnd_bind('<<DragEnter>>', on_enter)
        widget.dnd_bind('<<DragLeave>>', on_leave)

    def _make_hr_drop_target(self, widget):
        """Drop target for the HR Excel holiday file — calls import_employee_holidays.py."""
        def on_drop(event):
            raw = event.data.strip()
            if raw.startswith('{') and raw.endswith('}'):
                raw = raw[1:-1]
            path = raw
            if not os.path.exists(path):
                messagebox.showerror('Drop Error', f'File not found: {path}'); return
            widget.configure(bg=SUCCESS, text='⏳ Importing...')
            self.after(100, lambda: self._run_hr_import(path, widget))

        def on_enter(event): widget.configure(bg=ACCENT2)
        def on_leave(event): widget.configure(bg='#1e3a4a')

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
                    self.after(0, lambda: widget.configure(bg='#1e3a4a', text='⬇ Drop here'))
                self.import_path_var.set(LEAVE_FILE)
                self._preview_file(LEAVE_FILE)
                messagebox.showinfo('HR Holidays Imported ✅',
                                    f'{added}\n\nAll records merged into {LEAVE_FILE}.')
                self._refresh_leaves()
            except Exception as e:
                if widget:
                    self.after(0, lambda: widget.configure(bg='#1e3a4a', text='⬇ Drop here'))
                messagebox.showerror('Import Error', str(e))

        threading.Thread(target=worker, daemon=True).start()

    def _browse_import(self, target_filename):
        path = filedialog.askopenfilename(
            title=f'Select file to import as {target_filename}',
            filetypes=[('CSV/Excel', '*.csv *.xlsx *.xls'), ('All', '*.*')])
        if not path: return
        try:
            shutil.copy2(path, os.path.join(os.getcwd(), target_filename))
            messagebox.showinfo('Imported ✅', f'File saved as {target_filename}')
            self.import_path_var.set(target_filename)
            self._preview_file(target_filename)
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
        p = self.tab_leave
        self._section(p, '📝  Submit New Leave').pack(fill='x', padx=15, pady=(12,4))

        form = tk.Frame(p, bg=BG2, padx=10)
        form.pack(fill='x', padx=15, pady=4)

        def lbl(t, r, c):
            tk.Label(form, text=t, font=FONT, bg=BG2, fg=FG2, anchor='w'
                     ).grid(row=r, column=c, sticky='w', padx=6, pady=4)
        def ent(r, c, default='', w=18):
            e = tk.Entry(form, font=FONT, width=w, bg=BG3, fg=FG,
                         insertbackground='white', relief='flat', bd=4)
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
        self.lv_tree.tag_configure('approved',  foreground='#86efac')
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
    # TAB 4 — Results Viewer
    # ══════════════════════════════════════════════════════════════════════════
    def _build_results_tab(self):
        p = self.tab_results
        self._section(p, '📁  Saved Prediction Files').pack(fill='x', padx=15, pady=(12,4))

        top = tk.Frame(p, bg=BG2)
        top.pack(fill='x', padx=15, pady=4)
        self.results_var = tk.StringVar()
        self.results_cb  = ttk.Combobox(top, textvariable=self.results_var,
                                        font=FONT, width=50, state='readonly')
        self.results_cb.pack(side='left', padx=(0,8))
        self._btn(top, '🔄 Refresh', BG3,    self._refresh_results).pack(side='left', padx=4)
        self._btn(top, '👁 View',    ACCENT2, self._view_result).pack(side='left', padx=4)
        self._btn(top, '📤 Export Excel', SUCCESS, self._export_result_excel).pack(side='left', padx=4)

        self._section(p, '📊  Preview (first 200 rows)').pack(fill='x', padx=15, pady=(10,2))

        rf = tk.Frame(p, bg=BG2)
        rf.pack(fill='both', expand=True, padx=15, pady=(0,10))

        cols = ('Time Interval','Predicted Active Users','Leave Reduction',
                'Adjusted Active Users','Servers Needed')
        self.res_tree = ttk.Treeview(rf, columns=cols, show='headings', height=14)
        for c in cols:
            self.res_tree.heading(c, text=c)
            self.res_tree.column(c, width=150, anchor='center')
        vsb = ttk.Scrollbar(rf, orient='vertical',   command=self.res_tree.yview)
        hsb = ttk.Scrollbar(rf, orient='horizontal',  command=self.res_tree.xview)
        self.res_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.res_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        rf.rowconfigure(0, weight=1); rf.columnconfigure(0, weight=1)

        self._refresh_results()

    def _refresh_results(self):
        files = sorted([f for f in os.listdir('.')
                        if f.startswith('prediction_') and f.endswith('.csv')], reverse=True)
        self.results_cb['values'] = files
        if files and not self.results_var.get():
            self.results_var.set(files[0])

    def _view_result(self):
        fname = self.results_var.get()
        if not fname or not os.path.exists(fname):
            messagebox.showinfo('Select', 'Select a file first.'); return
        try:
            df = pd.read_csv(fname, nrows=200)
        except Exception as e:
            messagebox.showerror('Error', str(e)); return

        for r in self.res_tree.get_children(): self.res_tree.delete(r)

        display_cols = [c for c in ('Time Interval','Predicted Active Users',
                                    'Leave Reduction','Adjusted Active Users','Servers Needed')
                        if c in df.columns]
        self.res_tree['columns'] = display_cols
        for c in display_cols:
            self.res_tree.heading(c, text=c)
            self.res_tree.column(c, width=155, anchor='center')

        for _, row in df[display_cols].iterrows():
            self.res_tree.insert('', 'end', values=list(row))

    def _export_result_excel(self):
        fname = self.results_var.get()
        if not fname or not os.path.exists(fname):
            messagebox.showinfo('Select', 'Select a file first.'); return
        df  = pd.read_csv(fname)
        out = fname.replace('.csv', '.xlsx')
        df.to_excel(out, index=False, engine='openpyxl')
        messagebox.showinfo('Exported ✅', f'Saved as {out}')

    # ── Helpers ────────────────────────────────────────────────────────────────
    def _section(self, parent, text):
        f = tk.Frame(parent, bg=BG2)
        tk.Label(f, text=text, font=FONT_B, bg=BG2, fg=ACCENT).pack(side='left', padx=4)
        tk.Frame(f, bg=BG3, height=1).pack(side='left', fill='x', expand=True, padx=6)
        return f

    def _btn(self, parent, text, color, command):
        return tk.Button(parent, text=text, font=FONT_B, bg=color, fg='white',
                         activebackground=BG3, activeforeground=FG,
                         padx=12, pady=5, relief='flat', cursor='hand2',
                         command=command)

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
        tab = self.tab_userpred

        # ── Scrollable wrapper for the whole tab ───────────────────────────────
        _vsb = ttk.Scrollbar(tab, orient='vertical')
        _vsb.pack(side='right', fill='y')
        _canvas = tk.Canvas(tab, bg=BG2, highlightthickness=0,
                             yscrollcommand=_vsb.set)
        _canvas.pack(side='left', fill='both', expand=True)
        _vsb.config(command=_canvas.yview)

        p = tk.Frame(_canvas, bg=BG2)
        window_id = _canvas.create_window((0, 0), window=p, anchor='nw')

        def _on_frame_configure(e):
            _canvas.configure(scrollregion=_canvas.bbox('all'))
        p.bind('<Configure>', _on_frame_configure)

        def _on_canvas_configure(e):
            _canvas.itemconfig(window_id, width=e.width)
        _canvas.bind('<Configure>', _on_canvas_configure)

        def _on_mousewheel(e):
            _canvas.yview_scroll(int(-1 * (e.delta / 120)), 'units')
        _canvas.bind_all('<MouseWheel>', _on_mousewheel)

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
                                   font=FONT_S, bg=BG2, fg=FG2)
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

        # Determine Login Window based on Top 2 most frequent hours
        if total_days > 1:
            hour_counts = first_logins[ts_col].dt.hour.value_counts().sort_values(ascending=False)
            
            if len(hour_counts) >= 2:
                # Take the top 2 most frequent hours
                top_2_hrs = hour_counts.index[:2]
                win_start = int(min(top_2_hrs))
                win_end   = int(max(top_2_hrs)) + 1
            elif len(hour_counts) == 1:
                # Only 1 hour seen across multiple days
                top_hour = hour_counts.index[0]
                win_start = top_hour
                win_end   = top_hour + 1
        
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


        # Populate tree
        for r in self.up_tree.get_children(): self.up_tree.delete(r)

        cur_date = from_dt
        while cur_date <= to_dt:
            day_name  = cur_date.strftime('%A')
            on_leave  = cur_date in on_leave_dates
            day_cnt   = day_counts.get(day_name, 0)
            likely    = (day_name in days_with_login) and not on_leave and day_cnt > 0

            if on_leave:
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

# ── Launch ─────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    app = App()
    app.mainloop()
