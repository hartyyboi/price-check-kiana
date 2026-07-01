import streamlit as st
import pandas as pd
import os

# Configuration
EXCEL_FILE = "Price List.xlsx"
ADMIN_PASSWORD = "your_secret_password"  # Change this to your preferred admin password

st.set_page_config(page_title="Store POS & Price Checker", page_icon="💰", layout="wide")
st.title("🏪 Store POS & Price Checker")

# Initialize Session States
if "cart" not in st.session_state:
    st.session_state.cart = {}
if "qty_multiplier" not in st.session_state:
    st.session_state.qty_multiplier = 1
if "app_mode" not in st.session_state:
    st.session_state.app_mode = "Price Checker"

# 1. Load Data
@st.cache_data(ttl=5)
def load_data():
    if os.path.exists(EXCEL_FILE):
        df_items = pd.read_excel(EXCEL_FILE, sheet_name="Sheet1")
    else:
        df_items = pd.DataFrame(columns=["Product name", "Unit Price", "Wholesale"])
        
    if os.path.exists(EXCEL_FILE):
        try:
            df_rules = pd.read_excel(EXCEL_FILE, sheet_name="WS_Rules")
        except Exception:
            df_rules = pd.DataFrame(columns=["Product name", "Active", "Target Qty"])
    else:
        df_rules = pd.DataFrame(columns=["Product name", "Active", "Target Qty"])
        
    return df_items, df_rules

def save_data(df_items, df_rules):
    if os.path.exists(EXCEL_FILE):
        with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
            df_items.to_excel(writer, sheet_name="Sheet1", index=False)
            df_rules.to_excel(writer, sheet_name="WS_Rules", index=False)
    else:
        with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl") as writer:
            df_items.to_excel(writer, sheet_name="Sheet1", index=False)
            df_rules.to_excel(writer, sheet_name="WS_Rules", index=False)
    st.cache_data.clear()

df, df_rules = load_data()

# Helper to look up active wholesale rules
def get_wholesale_threshold(product_name):
    rule = df_rules[(df_rules["Product name"] == product_name) & (df_rules["Active"] == True)]
    if not rule.empty:
        return int(rule.iloc[0]["Target Qty"])
    return None

# MODE SELECTOR TABS AT THE TOP
m_col1, m_col2, _ = st.columns([1.5, 2, 5])
with m_col1:
    if st.button("🔍 Price Checker", use_container_width=True, type="primary" if st.session_state.app_mode == "Price Checker" else "secondary"):
        st.session_state.app_mode = "Price Checker"
        st.rerun()
with m_col2:
    if st.button("💪 Calculator Steroids (POS)", use_container_width=True, type="primary" if st.session_state.app_mode == "Calculator Steroids" else "secondary"):
        st.session_state.app_mode = "Calculator Steroids"
        st.rerun()

st.markdown("---")

# 2. Sidebar - Admin Access Setup
st.sidebar.header("🔐 Access Control")
admin_mode = False
pwd_input = st.sidebar.text_input("Admin Password", type="password")
if pwd_input == ADMIN_PASSWORD:
    st.sidebar.success("Admin Mode Activated! 🎉")
    admin_mode = True
elif pwd_input != "":
    st.sidebar.error("Incorrect password")

# Adjust Layout depending on Selected Mode
if st.session_state.app_mode == "Calculator Steroids":
    main_col, cart_col = st.columns([1.8, 1.2])
else:
    main_col = st.container()

with main_col:
    # ONLY SHOW MULTIPLIERS IF ON CALCULATOR STEROIDS MODE
    if st.session_state.app_mode == "Calculator Steroids":
        s_col1, s_col2, s_col3, s_col4, s_col5 = st.columns([1, 1, 1, 1, 2])
        with s_col1:
            if st.button("x1", use_container_width=True, type="secondary" if st.session_state.qty_multiplier != 1 else "primary"):
                st.session_state.qty_multiplier = 1
                st.rerun()
        with s_col2:
            if st.button("x6", use_container_width=True, type="secondary" if st.session_state.qty_multiplier != 6 else "primary"):
                st.session_state.qty_multiplier = 6
                st.rerun()
        with s_col3:
            if st.button("x10", use_container_width=True, type="secondary" if st.session_state.qty_multiplier != 10 else "primary"):
                st.session_state.qty_multiplier = 10
                st.rerun()
        with s_col4:
            if st.button("x12", use_container_width=True, type="secondary" if st.session_state.qty_multiplier != 12 else "primary"):
                st.session_state.qty_multiplier = 12
                st.rerun()
        with s_col5:
            custom_mult = st.number_input(
                "Custom Qty:", 
                min_value=1, 
                value=int(st.session_state.qty_multiplier), 
                step=1, 
                key=f"custom_multiplier_input_{st.session_state.qty_multiplier}"
            )
            if custom_mult != st.session_state.qty_multiplier:
                st.session_state.qty_multiplier = custom_mult
                st.rerun()

        st.info(f"🚀 **Active Multiplier Mode:** Tapping '➕ Add' below will add **{st.session_state.qty_multiplier} pc(s)** of that product.")
        st.markdown("---")
    
    search_query = st.text_input("Search by Product Name...", placeholder="Type item name here...", key="staff_search")

    if search_query:
        filtered_df = df[df["Product name"].astype(str).str.contains(search_query, case=False, na=False)]
    else:
        filtered_df = df.head(10)

    # Display
    
