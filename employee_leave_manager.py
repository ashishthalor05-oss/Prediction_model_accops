"""
employee_leave_manager.py
──────────────────────────
GUI application for employees to submit their leave/holiday.
Supports: Full Day, Half Day (Morning), Half Day (Afternoon)
Data saved to: employee_leaves.csv
"""

import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import os
from datetime import datetime, date, timedelta

LEAVE_FILE = 'employee_leaves.csv'
COLUMNS = ['Employee Name', 'Start Date', 'End Date', 'Leave Type', 'Half Day', 'Description', 'Submitted On']

# ── Load or create leave file ──────────────────────────────────────────────────
def load_leaves():
    if os.path.exists(LEAVE_FILE):
        df = pd.read_csv(LEAVE_FILE)
        for col in COLUMNS:
            if col not in df.columns:
                df[col] = ''
        return df
    return pd.DataFrame(columns=COLUMNS)

def save_leave(record):
    df = load_leaves()
    new_row = pd.DataFrame([record])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(LEAVE_FILE, index=False)


# ══════════════════════════════════════════════════════════════════════════════
class LeaveManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Employee Leave Manager")
        self.root.geometry("780x620")
        self.root.resizable(True, True)
        self.root.configure(bg='#1e293b')

        # Fonts
        self.font_title  = ('Segoe UI', 16, 'bold')
        self.font_label  = ('Segoe UI', 10)
        self.font_entry  = ('Segoe UI', 10)
        self.font_button = ('Segoe UI', 10, 'bold')
        self.font_small  = ('Segoe UI', 9)

        self._build_header()
        self._build_form()
        self._build_table()
        self._refresh_table()

    # ── Header ─────────────────────────────────────────────────────────────────
    def _build_header(self):
        header = tk.Frame(self.root, bg='#0f172a', pady=14)
        header.pack(fill='x')
        tk.Label(header, text='📅  Employee Leave Manager',
                 font=self.font_title, bg='#0f172a', fg='#38bdf8').pack()
        tk.Label(header, text='Submit your leave — Full Day or Half Day',
                 font=self.font_small, bg='#0f172a', fg='#94a3b8').pack()

    # ── Form ───────────────────────────────────────────────────────────────────
    def _build_form(self):
        form_frame = tk.Frame(self.root, bg='#1e293b', padx=20, pady=10)
        form_frame.pack(fill='x')

        def lbl(parent, text, row, col, colspan=1):
            tk.Label(parent, text=text, font=self.font_label,
                     bg='#1e293b', fg='#cbd5e1', anchor='w').grid(
                row=row, column=col, columnspan=colspan,
                sticky='w', padx=8, pady=4)

        def entry(parent, row, col, width=22, colspan=1):
            e = tk.Entry(parent, font=self.font_entry, width=width,
                         bg='#334155', fg='#f1f5f9', insertbackground='white',
                         relief='flat', bd=4)
            e.grid(row=row, column=col, columnspan=colspan,
                   sticky='ew', padx=8, pady=4)
            return e

        # ── Row 0: Employee Name ───────────────────────────────────────────────
        lbl(form_frame, 'Employee Name *', 0, 0)
        self.emp_name = entry(form_frame, 0, 1, width=30)

        # ── Row 1: Start Date / End Date ───────────────────────────────────────
        lbl(form_frame, 'Start Date * (YYYY-MM-DD)', 1, 0)
        self.start_date = entry(form_frame, 1, 1)
        self.start_date.insert(0, str(date.today()))

        lbl(form_frame, 'End Date * (YYYY-MM-DD)', 1, 2)
        self.end_date = entry(form_frame, 1, 3)
        self.end_date.insert(0, str(date.today()))

        # ── Row 2: Leave Type ──────────────────────────────────────────────────
        lbl(form_frame, 'Leave Type *', 2, 0)
        self.leave_type_var = tk.StringVar(value='Annual Leave')
        leave_types = ['Annual Leave', 'Sick Leave', 'Personal Leave',
                       'Maternity / Paternity', 'Compensatory Off', 'Shutdown / Closure', 'Other']
        cb = ttk.Combobox(form_frame, textvariable=self.leave_type_var,
                          values=leave_types, state='readonly',
                          font=self.font_entry, width=20)
        cb.grid(row=2, column=1, sticky='ew', padx=8, pady=4)

        # ── Row 2: Half Day ────────────────────────────────────────────────────
        lbl(form_frame, 'Half Day?', 2, 2)
        self.half_day_var = tk.StringVar(value='No')
        half_opts = ['No', 'Morning Half', 'Afternoon Half']
        hd = ttk.Combobox(form_frame, textvariable=self.half_day_var,
                          values=half_opts, state='readonly',
                          font=self.font_entry, width=20)
        hd.grid(row=2, column=3, sticky='ew', padx=8, pady=4)
        hd.bind('<<ComboboxSelected>>', self._on_half_day_change)

        # ── Row 3: Description ─────────────────────────────────────────────────
        lbl(form_frame, 'Reason / Description', 3, 0)
        self.description = entry(form_frame, 3, 1, width=60, colspan=3)

        # ── Row 4: Buttons ─────────────────────────────────────────────────────
        btn_frame = tk.Frame(form_frame, bg='#1e293b')
        btn_frame.grid(row=4, column=0, columnspan=4, pady=12)

        tk.Button(btn_frame, text='✔  Submit Leave',
                  font=self.font_button, bg='#0ea5e9', fg='white',
                  activebackground='#0284c7', activeforeground='white',
                  padx=20, pady=6, relief='flat', cursor='hand2',
                  command=self._submit).pack(side='left', padx=8)

        tk.Button(btn_frame, text='✖  Clear Form',
                  font=self.font_button, bg='#475569', fg='white',
                  activebackground='#334155', activeforeground='white',
                  padx=20, pady=6, relief='flat', cursor='hand2',
                  command=self._clear).pack(side='left', padx=8)

        tk.Button(btn_frame, text='🗑  Delete Selected',
                  font=self.font_button, bg='#ef4444', fg='white',
                  activebackground='#dc2626', activeforeground='white',
                  padx=20, pady=6, relief='flat', cursor='hand2',
                  command=self._delete_selected).pack(side='left', padx=8)

        # Style comboboxes
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TCombobox', fieldbackground='#334155',
                        background='#334155', foreground='#f1f5f9',
                        selectbackground='#0ea5e9')

        form_frame.columnconfigure(1, weight=1)
        form_frame.columnconfigure(3, weight=1)

    def _on_half_day_change(self, event=None):
        """If Half Day selected, force End Date = Start Date."""
        if self.half_day_var.get() != 'No':
            self.end_date.delete(0, tk.END)
            self.end_date.insert(0, self.start_date.get())

    # ── Table ──────────────────────────────────────────────────────────────────
    def _build_table(self):
        sep = tk.Frame(self.root, bg='#334155', height=1)
        sep.pack(fill='x', padx=20)

        tbl_label = tk.Frame(self.root, bg='#1e293b', pady=4)
        tbl_label.pack(fill='x')
        tk.Label(tbl_label, text='📋  Submitted Leaves',
                 font=('Segoe UI', 11, 'bold'), bg='#1e293b', fg='#38bdf8').pack(side='left', padx=20)

        tbl_frame = tk.Frame(self.root, bg='#1e293b', padx=15, pady=6)
        tbl_frame.pack(fill='both', expand=True)

        cols = ('Employee Name', 'Start Date', 'End Date', 'Leave Type', 'Half Day', 'Description')
        self.tree = ttk.Treeview(tbl_frame, columns=cols, show='headings', height=10)

        style = ttk.Style()
        style.configure('Treeview',
                        background='#1e293b', foreground='#f1f5f9',
                        fieldbackground='#1e293b', rowheight=26,
                        font=('Segoe UI', 9))
        style.configure('Treeview.Heading',
                        background='#0f172a', foreground='#38bdf8',
                        font=('Segoe UI', 9, 'bold'), relief='flat')
        style.map('Treeview', background=[('selected', '#0ea5e9')])

        widths = [160, 100, 100, 140, 110, 200]
        for col, w in zip(cols, widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor='center')

        vsb = ttk.Scrollbar(tbl_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')

    def _refresh_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        df = load_leaves()
        for _, row in df.iterrows():
            self.tree.insert('', 'end', values=(
                row.get('Employee Name', ''),
                row.get('Start Date', ''),
                row.get('End Date', ''),
                row.get('Leave Type', ''),
                row.get('Half Day', ''),
                row.get('Description', ''),
            ))

    # ── Submit ─────────────────────────────────────────────────────────────────
    def _submit(self):
        name  = self.emp_name.get().strip()
        start = self.start_date.get().strip()
        end   = self.end_date.get().strip()
        ltype = self.leave_type_var.get()
        hday  = self.half_day_var.get()
        desc  = self.description.get().strip()

        # Validation
        if not name:
            messagebox.showerror('Missing', 'Employee Name is required.'); return
        try:
            s = datetime.strptime(start, '%Y-%m-%d').date()
            e = datetime.strptime(end,   '%Y-%m-%d').date()
        except ValueError:
            messagebox.showerror('Invalid Date', 'Use format YYYY-MM-DD for dates.'); return
        if e < s:
            messagebox.showerror('Invalid Range', 'End Date cannot be before Start Date.'); return
        if hday != 'No' and s != e:
            messagebox.showerror('Half Day', 'Half Day is only allowed for a single day (Start = End).'); return

        days = (e - s).days + 1
        label = f'{days} day(s)' if hday == 'No' else f'Half day ({hday})'

        record = {
            'Employee Name': name,
            'Start Date':    str(s),
            'End Date':      str(e),
            'Leave Type':    ltype,
            'Half Day':      hday,
            'Description':   desc,
            'Submitted On':  str(date.today()),
        }
        save_leave(record)
        messagebox.showinfo('Submitted ✅',
            f'Leave submitted for {name}\n{s} → {e} ({label})\nType: {ltype}')
        self._refresh_table()
        self._clear()

    def _clear(self):
        self.emp_name.delete(0, tk.END)
        self.start_date.delete(0, tk.END); self.start_date.insert(0, str(date.today()))
        self.end_date.delete(0, tk.END);   self.end_date.insert(0, str(date.today()))
        self.leave_type_var.set('Annual Leave')
        self.half_day_var.set('No')
        self.description.delete(0, tk.END)

    def _delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo('Delete', 'Please select a row to delete.'); return
        if not messagebox.askyesno('Delete', 'Delete selected leave record(s)?'): return

        df = load_leaves()
        indices = [self.tree.index(item) for item in selected]
        df = df.drop(index=indices).reset_index(drop=True)
        df.to_csv(LEAVE_FILE, index=False)
        self._refresh_table()


# ── Run ────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    root = tk.Tk()
    app = LeaveManagerApp(root)
    root.mainloop()
