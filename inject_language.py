import re

with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Inject Radiobuttons & Language var underneath the Graph Image Layout
ui_setup_old = """        # Bottom Description Bar
        self.graph_desc_var = tk.StringVar(value="")
        self.graph_desc_lbl = tk.Label(self.view_f, textvariable=self.graph_desc_var, font=FONT, bg='#020617', fg='#93c5fd', justify='center', wraplength=700)
        self.graph_desc_lbl.pack(fill='x', side='bottom', pady=5)
        
        self.current_img_tk = None"""

ui_setup_new = """        # Bottom Description Bar
        desc_frame = tk.Frame(self.view_f, bg='#020617')
        desc_frame.pack(fill='x', side='bottom', pady=5)
        
        # Language Toggle
        lang_frame = tk.Frame(desc_frame, bg='#020617')
        lang_frame.pack(pady=2)
        
        self.desc_lang_var = tk.StringVar(value="en")
        tk.Radiobutton(lang_frame, text="English", variable=self.desc_lang_var, value="en", 
                       font=FONT_S, bg='#020617', fg=FG, selectcolor=BG3, cursor="hand2", 
                       indicatoron=1, activebackground='#020617', activeforeground=ACCENT,
                       command=lambda: self._on_graph_select(None)).pack(side='left', padx=10)
                       
        tk.Radiobutton(lang_frame, text="हिंदी (Hindi)", variable=self.desc_lang_var, value="hi", 
                       font=FONT_S, bg='#020617', fg=FG, selectcolor=BG3, cursor="hand2", 
                       indicatoron=1, activebackground='#020617', activeforeground=ACCENT,
                       command=lambda: self._on_graph_select(None)).pack(side='left', padx=10)

        self.graph_desc_var = tk.StringVar(value="")
        self.graph_desc_lbl = tk.Label(desc_frame, textvariable=self.graph_desc_var, font=FONT, bg='#020617', fg='#93c5fd', justify='center', wraplength=700)
        self.graph_desc_lbl.pack(fill='x', pady=(2, 5))
        
        self.current_img_tk = None"""

if ui_setup_old in text:
    text = text.replace(ui_setup_old, ui_setup_new)
else:
    print("UI setup block not found.")


# 2. Update the dynamic descriptions dictionary engine
select_old = """        # Dynamic Descriptions
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

select_new = """        # Dynamic Descriptions - Multilingual
        lang = getattr(self, 'desc_lang_var', tk.StringVar(value='en')).get()
        desc = ""
        
        if 'active_users' in filename:
            if lang == "hi": desc = "🎯 कुल सक्रिय उपयोगकर्ता: यह ग्राफ दिखाता है कि एक ही समय में सिस्टम पर कितने लोग एक्टिव (ऑनलाइन) हैं।"
            else: desc = "🎯 Total Active System Users: Shows the total number of people concurrently active on the platform."
        elif 'single_session_users' in filename:
            if lang == "hi": desc = "👤 सिंगल सेशन यूज़र्स: वो लोग जो सिर्फ वेब ऐप्स या हलके डैशबोर्ड इस्तेमाल करने के लिए लॉग-इन करते हैं।"
            else: desc = "👤 Single Session Users: People logging in to use simple, non-intensive resources like Web Apps or Dashboards."
        elif 'multi_session_users' in filename:
            if lang == "hi": desc = "👥 मल्टी सेशन यूज़र्स: वो भारी यूज़र्स जो वर्चुअल डेस्कटॉप या हैवी सॉफ्टवेयर का इस्तेमाल करते हैं।"
            else: desc = "👥 Multi Session Users: People accessing heavy, virtualized desktops or computational shared resources."
        elif 'active_user_logins' in filename:
            if lang == "hi": desc = "🔑 लॉगिन गतिविधि: यह ग्राफ कच्चे आंकड़े दिखाता है कि सिस्टम में कुल कितनी बार लॉगिन किया गया।"
            else: desc = "🔑 Login Activity: Raw count of how many times users triggered successful login events during these periods."
        elif 'provisioning_simulation' in filename:
            if lang == "hi": desc = "🖥️ सर्वर लॉजिक: यह दिखाता है कि एआई ने यूज़र्स की भीड़ को सँभालने के लिए कितने असली सर्वर ऑन किए।"
            else: desc = "🖥️ Server Logic: Shows how many physical servers the system would have allocated versus total active users."
        elif 'concurrency_report' in filename:
            if lang == "hi": desc = "⚡ कच्चा डेटा (Concurrency): बिना किसी एआई के सीधे SQL डेटाबेस से निकाले गए लॉगिन पीक्स।"
            else: desc = "⚡ Raw Concurrency: The direct mathematical peaks measured internally from pure SQL Logs without ML."
        elif 'backtest_accuracy_chart' in filename or 'app_backtest' in filename:
            if lang == "hi": desc = "🧪 एआई टेस्ट (Backtest): यह ग्राफ तुलना करता है कि एआई की भविष्यवाणी असलियत के कितनी करीब (सटीक) थी।"
            else: desc = "🧪 Blind Evaluation Backtest: How accurate the AI was at predicting the Future secretly compared to reality."
        elif 'simulation' in filename:
            if lang == "hi": desc = "💡 सिस्टम सिमुलेशन: यह बताता है कि एआई ने सर्वर मैनेजमेंट में कितने पैसे और बिजली बचाई।"
            else: desc = "💡 System Simulation: Mathematical representation of cost metrics and algorithmic load balancing decisions."
        else:
            if lang == "hi": desc = "इस ग्राफ के लिए कोई जानकारी उपलब्ध नहीं है।"
            else: desc = "No description available for this graph."

        self.graph_desc_var.set(f"📊 {filename}\\n{desc}")
  """

if select_old in text:
    text = text.replace(select_old, select_new)
else:
    print("Text logic block not found.")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(text)
    
print("Language toggles configured.")
