import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add tab definition
tab_def_old = '''        self.tab_holiday  = ScrollableTab(nb, bg_color=BG2)
        self.tab_results  = ScrollableTab(nb, bg_color=BG2)'''
tab_def_new = '''        self.tab_holiday  = ScrollableTab(nb, bg_color=BG2)
        self.tab_backtest = ScrollableTab(nb, bg_color=BG2)
        self.tab_results  = ScrollableTab(nb, bg_color=BG2)'''
content = content.replace(tab_def_old, tab_def_new)

tab_add_old = '''        nb.add(self.tab_holiday,  text=' 🏖️  Company Holidays ')
        nb.add(self.tab_results,  text=' 📋  Results Viewer ')'''
tab_add_new = '''        nb.add(self.tab_holiday,  text=' 🏖️  Company Holidays ')
        nb.add(self.tab_backtest, text=' 🎯  Model Backtest ')
        nb.add(self.tab_results,  text=' 📋  Results Viewer ')'''
content = content.replace(tab_add_old, tab_add_new)

build_calls_old = '''        self._build_holiday_tab()
        self._build_results_tab()'''
build_calls_new = '''        self._build_holiday_tab()
        self._build_backtest_tab()
        self._build_results_tab()'''
content = content.replace(build_calls_old, build_calls_new)

# 2. Add the implementation of _build_backtest_tab just before TAB 4 (Results Viewer)
backtest_impl = '''
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
                         insertbackground='white', relief='flat', bd=4)
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
                    self.after(0, lambda: messagebox.showerror("Backtest Failed", f"Execution Error:\\n{err}"))
                    self.after(0, lambda: self.bt_status.config(text="Status: Failed.", fg=DANGER))
                else:
                    metrics_str = f"✅ Analysis Complete!\\n\\n⭐ Mean Absolute Error: {mae} users | Root Mean Squared Error: {rmse} users\\n⭐ Peak Actual: {peak_a} | Peak Predicted: {peak_p}"
                    self.after(0, lambda: self._show_backtest_results(metrics_str))
            
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Backtest Error", str(e)))
                self.after(0, lambda: self.bt_status.config(text="Status: Error.", fg=DANGER))
            finally:
                self.after(0, lambda: self.bt_run_btn.config(state='normal'))

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

'''

tab4_marker = '''    # ══════════════════════════════════════════════════════════════════════════
    # TAB 4 — Results Viewer'''
    
if tab4_marker in content:
    content = content.replace(tab4_marker, backtest_impl + tab4_marker)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Insertion complete.")
