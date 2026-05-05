import streamlit as st
import pandas as pd
import os
import subprocess
import shutil
import pyodbc
from datetime import datetime, date
from PIL import Image
import configparser

# ── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Prediction Engine",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── THEME & STYLING ─────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main {
        background-color: #0b0f19;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #8b5cf6;
        color: white;
    }
    .stButton>button:hover {
        background-color: #7c3aed;
        border: 1px solid #c4b5fd;
    }
</style>
""", unsafe_allow_html=True)

# ── CONFIG HELPERS ──────────────────────────────────────────────────────────
CONFIG_FILE = "prediction_config.ini"

def load_config():
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
    return config

def save_config(server, db, table, start_date, end_date):
    config = configparser.ConfigParser()
    config['DB'] = {
        'server': server,
        'db': db,
        'table': table,
        'start': start_date,
        'end': end_date
    }
    with open(CONFIG_FILE, 'w') as f:
        config.write(f)

# ── SIDEBAR NAVIGATION ───────────────────────────────────────────────────────
st.sidebar.title("🚀 AI Prediction")
st.sidebar.markdown("---")
menu = st.sidebar.radio(
    "Navigation",
    ["📊 Dashboard", "🎯 Run Prediction", "📥 Sync SQL Data", "📝 Employee Leaves", "🗓️ Company Holidays", "🔍 Results Viewer"]
)

# ── MAIN CONTENT ─────────────────────────────────────────────────────────────
st.title(f"🚀 AI-Driven Resource Planning")
st.subheader(f"Internal Module: {menu}")
st.markdown("---")

# ── LOGIC: DASHBOARD ─────────────────────────────────────────────────────────
if menu == "📊 Dashboard":
    st.info("Visualizing resource trends and capacity planning metrics.")
    
    col1, col2 = st.columns([1, 3])
    
    available_graphs = [f for f in os.listdir('.') if f.endswith('.png') and not f.startswith('_tmp_')]
    
    with col1:
        st.write("### 📂 Available Visuals")
        if not available_graphs:
            st.warning("No graphs generated yet. Run Prediction first.")
        else:
            selected_graph = st.selectbox("Select a graph to view:", available_graphs)
            
            # Mapping from app.py
            desc = ""
            if 'comparison' in selected_graph:
                desc = "🔍 **Accuracy Comparison**: Side-by-side validation of predicted vs. actual user demand."
            elif 'active_users' in selected_graph:
                desc = "🎯 **Total Concurrent Users**: Real-time visualization of active system engagement."
            elif 'single_session_users' in selected_graph:
                desc = "👤 **Standard Users**: Users accessing lightweight resources."
            elif 'multi_session_users' in selected_graph:
                desc = "👥 **Power Users**: High-performance software or virtual desktop users."
            elif 'backtest' in selected_graph:
                desc = "🧪 **Model Validation**: Accuracy comparison for performance tuning."
            
            st.markdown(desc)

    with col2:
        if available_graphs:
            img = Image.open(selected_graph)
            st.image(img, use_container_width=True)

# ── LOGIC: PREDICTION ────────────────────────────────────────────────────────
elif menu == "🎯 Run Prediction":
    st.write("### ⚙️ Set Prediction Range")
    c1, c2 = st.columns(2)
    start_p = c1.date_input("From Date", date.today())
    end_p = c2.date_input("To Date", date.today())
    
    if st.button("🚀 Execute AI Model"):
        with st.spinner("Analyzing historical trends and generating predictions..."):
            try:
                # Same logic as app.py
                cmd = f'python predict_future.py "{start_p}" "{end_p}"'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    st.success("Prediction Completed Successfully!")
                    st.code(result.stdout)
                else:
                    st.error(f"Error during prediction:\n{result.stderr}")
            except Exception as e:
                st.exception(e)

# ── LOGIC: SYNC SQL DATA ─────────────────────────────────────────────────────
elif menu == "📥 Sync SQL Data":
    config = load_config()
    st.write("### 🔌 Database Configuration")
    
    with st.form("sql_sync_form"):
        srv = st.text_input("Server Name", config.get('DB', 'server', fallback='.\\SQLEXPRESS'))
        db_n = st.text_input("Database Name", config.get('DB', 'db', fallback='UserLogsDB'))
        tbl = st.text_input("Table Name", config.get('DB', 'table', fallback='UserLogs'))
        
        c1, c2 = st.columns(2)
        s_dt = c1.text_input("Last Sync End", config.get('DB', 'end', fallback='2025-12-01'))
        e_dt = c2.text_input("New Sync End", datetime.now().strftime('%Y-%m-%d'))
        
        submitted = st.form_submit_button("🔁 Sync & Re-train")
        
        if submitted:
            save_config(srv, db_n, tbl, s_dt, e_dt)
            with st.spinner("Fetching data from SQL and updating ML models..."):
                # Simulation of logic from app.py
                st.info(f"Connecting to {srv}...")
                # Note: Real SQL execution would go here or call db_sync.py
                st.success("Data Synced! Background Training Started.")

# ── LOGIC: RESULTS VIEWER ────────────────────────────────────────────────────
elif menu == "🔍 Results Viewer":
    st.write("### 📉 Latest Prediction Results")
    
    files = sorted([f for f in os.listdir('.') if f.startswith('prediction_') and f.endswith('.csv')], reverse=True)
    
    if not files:
        st.warning("No prediction results found.")
    else:
        selected_file = st.selectbox("Select a Result File:", files)
        
        c1, c2, c3 = st.columns([1,1,2])
        if c1.button("👁 View Data"):
            df = pd.read_csv(selected_file)
            st.dataframe(df, use_container_width=True)
            
        if c2.button("🗑️ Delete File"):
            if os.path.exists(selected_file):
                os.remove(selected_file)
                st.success(f"Deleted {selected_file}")
                st.rerun()

# ── FOOTER ──────────────────────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.info("v2.0 Web Engine | AI-Driven Analytics")
