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

# 2. Sidebar - Admin Access Setup
st.sidebar.header("🔐 Access Control")
admin_mode = False
pwd_input = st.sidebar.text_input("Admin Password", type="password")
if pwd_input == ADMIN_PASSWORD:
    st.sidebar.success("Admin Mode Activated! 🎉")
    admin_mode = True
elif pwd_input != "":
    st.sidebar.error("Incorrect password")

# Layout Split: Left for Product List, Right for Cart Panel
main_col, cart_col = st.columns([1.8, 1.2])

with main_col:
    st.subheader("⚡ 1. Select Quantity First")
    
    # Horizontal shortcut buttons for the pre-selector multiplier
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
        # Custom option input field
        custom_mult = st.number_input("Custom Qty:", min_value=1, value=int(st.session_state.qty_multiplier), step=1, key="custom_multiplier_input")
        if custom_mult != st.session_state.qty_multiplier:
            st.session_state.qty_multiplier = custom_mult
            st.rerun()

    # REAL-TIME QUANTITY INDICATOR
    st.info(f"🚀 **Active Multiplier Mode:** Tapping '➕ Add' below will add **{st.session_state.qty_multiplier} pc(s)** of that product.")
    
    st.markdown("---")
    st.subheader("🔍 2. Search & Tap Product")
    search_query = st.text_input("Search by Product Name...", placeholder="Type item name here...", key="staff_search")

    if search_query:
        filtered_df = df[df["Product name"].astype(str).str.contains(search_query, case=False, na=False)]
    else:
        filtered_df = df.head(10)

    # Display loop
    for idx, row in filtered_df.iterrows():
        p_name = row["Product name"]
        p_price = float(row["Unit Price"]) if pd.notna(row["Unit Price"]) else 0.0
        p_ws = float(row["Wholesale"]) if pd.notna(row["Wholesale"]) else 0.0
        
        ws_target = get_wholesale_threshold(p_name)
        rule_tag = f" (Wholesale @ {ws_target}+ pcs)" if ws_target else ""

        item_col1, item_col2, item_col3, item_col4 = st.columns([2.5, 1, 1, 0.8])
        with item_col1:
            st.markdown(f"**{p_name}** *{rule_tag}*")
        with item_col2:
            st.markdown(f"Retail: ₱{p_price:,.2f}")
        with item_col3:
            st.markdown(f"WS: ₱{p_ws:,.2f}")
        with item_col4:
            if st.button("➕ Add", key=f"add_{idx}"):
                # Add using the current active preset multiplier
                add_amount = st.session_state.qty_multiplier
                if p_name in st.session_state.cart:
                    st.session_state.cart[p_name] += add_amount
                else:
                    st.session_state.cart[p_name] = add_amount
                
                st.toast(f"Added {add_amount}x {p_name}!")
                # Reset multiplier back to 1 for the next item choice
                st.session_state.qty_multiplier = 1
                st.rerun()

with cart_col:
    st.subheader("🛒 Current Order Receipt")
    
    if not st.session_state.cart:
        st.info("Cart is empty.")
        total_bill = 0.0
    else:
        total_bill = 0.0
        items_to_remove = []
        
        # Super clean, consolidated receipt-style formatting layout
        for name, current_qty in list(st.session_state.cart.items()):
            item_data = df[df["Product name"] == name].iloc[0]
            r_price = float(item_data["Unit Price"]) if pd.notna(item_data["Unit Price"]) else 0.0
            w_price = float(item_data["Wholesale"]) if pd.notna(item_data["Wholesale"]) else r_price
            
            ws_target = get_wholesale_threshold(name)
            is_wholesale = ws_target is not None and current_qty >= ws_target
            active_price = w_price if is_wholesale else r_price
            
            subtotal = active_price * current_qty
            total_bill += subtotal
            
            # 1-Row clean summary layout for the order panel
            rc1, rc2, rc3 = st.columns([2.2, 0.8, 0.5])
            with rc1:
                badge = " (✨ WS)" if is_wholesale else ""
                st.markdown(f"**{name}** x{current_qty}{badge}")
                st.caption(f"₱{active_price:,.2f} per pc")
            with rc2:
                st.markdown(f"**₱{subtotal:,.2f}**")
            with rc3:
                if st.button("❌", key=f"del_{name}"):
                    items_to_remove.append(name)
            st.markdown("<hr style='margin: 4px 0px; border-top: 1px dashed #bbb;'>", unsafe_allow_html=True)
                    
        for name in items_to_remove:
            del st.session_state.cart[name]
            st.rerun()
            
        st.markdown(f"### 🧾 Total Bill: ₱{total_bill:,.2f}")
        
        cash_received = st.number_input("💵 Cash Received:", min_value=0.0, step=20.0, value=0.0)
        if cash_received > 0:
            change = cash_received - total_bill
            if change >= 0:
                st.success(f"### 🪙 Change: ₱{change:,.2f}")
            else:
                st.error(f"⚠️ Kulang ng: ₱{abs(change):,.2f}")
                
        if st.button("✅ Clear / New Transaction", type="primary", use_container_width=True):
            st.session_state.cart = {}
            st.session_state.qty_multiplier = 1
            st.rerun()

# 3. Admin Access Adjustments Panel
if admin_mode:
    st.markdown("---")
    st.subheader("🛠️ Admin Management Panel")
    action = st.radio("Choose Action:", ["Update Existing Price", "Wholesale Rules Configuration", "Add New Product", "Delete Product"], horizontal=True)
    
    if action == "Wholesale Rules Configuration":
        st.markdown("#### 📦 Set Custom Wholesale Target Limits")
        rule_search = st.text_input("Search product for rule adjustment:", key="rule_search")
        all_products = df["Product name"].unique().tolist()
        filtered_rules =
