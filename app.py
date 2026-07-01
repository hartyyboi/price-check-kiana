import streamlit as st
import pandas as pd
import os

# Configuration
EXCEL_FILE = "Price List.xlsx"
ADMIN_PASSWORD = "your_secret_password"  # Change this to your preferred admin password

st.set_page_config(page_title="Store POS & Price Checker", page_icon="💰", layout="wide")
st.title("🏪 Store POS & Price Checker")

# Initialize Cart in memory if it doesn't exist
if "cart" not in st.session_state:
    st.session_state.cart = {}

# 1. Load Data
@st.cache_data(ttl=10) # Low TTL so inventory changes reflect quickly
def load_data():
    if os.path.exists(EXCEL_FILE):
        return pd.read_excel(EXCEL_FILE, sheet_name="Sheet1")
    else:
        return pd.DataFrame(columns=["Product name", "Unit Price", "Wholesale"])

def save_data(df):
    if os.path.exists(EXCEL_FILE):
        with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
            df.to_excel(writer, sheet_name="Sheet1", index=False)
    else:
        df.to_excel(EXCEL_FILE, sheet_name="Sheet1", index=False)
    st.cache_data.clear()

df = load_data()

# 2. Sidebar - Admin Access & Cart System Split
st.sidebar.header("🔐 Access Control")
admin_mode = False
pwd_input = st.sidebar.text_input("Admin Password", type="password")
if pwd_input == ADMIN_PASSWORD:
    st.sidebar.success("Admin Mode Activated! 🎉")
    admin_mode = True
elif pwd_input != "":
    st.sidebar.error("Incorrect password")

# Layout Split: Main Area for Shopping/Search, Sidebar for active Cart Calculator
main_col, cart_col = st.columns([2, 1])

with main_col:
    st.subheader("🔍 Product Lookup & Add to Cart")
    search_query = st.text_input("Search by Product Name...", placeholder="Type item name here...", key="staff_search")

    if search_query:
        filtered_df = df[df["Product name"].astype(str).str.contains(search_query, case=False, na=False)]
    else:
        filtered_df = df.head(10) # Show first 10 items by default if empty

    # Display items with an "Add to Cart" mechanism
    for idx, row in filtered_df.iterrows():
        p_name = row["Product name"]
        p_price = float(row["Unit Price"]) if pd.notna(row["Unit Price"]) else 0.0
        p_ws = float(row["Wholesale"]) if pd.notna(row["Wholesale"]) else 0.0
        
        # Grid layout for each item row
        item_col1, item_col2, item_col3, item_col4 = st.columns([3, 1, 1, 1])
        with item_col1:
            st.markdown(f"**{p_name}**")
        with item_col2:
            st.markdown(f"Retail: ₱{p_price:,.2f}")
        with item_col3:
            st.markdown(f"WS: ₱{p_ws:,.2f}")
        with item_col4:
            if st.button("➕ Add", key=f"add_{idx}"):
                if p_name in st.session_state.cart:
                    st.session_state.cart[p_name]["qty"] += 1
                else:
                    st.session_state.cart[p_name] = {"price": p_price, "qty": 1}
                st.toast(f"Added {p_name} to cart!")
                st.rerun()

with cart_col:
    st.subheader("🛒 Current Order")
    
    if not st.session_state.cart:
        st.info("Cart is empty. Tap 'Add' on items next door!")
        total_bill = 0.0
    else:
        total_bill = 0.0
        items_to_remove = []
        
        for name, details in list(st.session_state.cart.items()):
            subtotal = details["price"] * details["qty"]
            total_bill += subtotal
            
            # Display item details in cart with controls
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                st.write(f"{name} (x{details['qty']})")
            with c2:
                st.write(f"₱{subtotal:,.2f}")
            with c3:
                if st.button("❌", key=f"rem_{name}"):
                    items_to_remove.append(name)
                    
        for name in items_to_remove:
            del st.session_state.cart[name]
            st.rerun()
            
        st.markdown("---")
        st.markdown(f"### 🧾 Total: ₱{total_bill:,.2f}")
        
        # Calculator on Steroids Section
        cash_received = st.number_input("💵 Cash Received:", min_value=0.0, step=20.0, value=0.0)
        if cash_received > 0:
            change = cash_received - total_bill
            if change >= 0:
                st.success(f"### 🪙 Change: ₱{change:,.2f}")
            else:
                st.error(f"⚠️ Kulang ng: ₱{abs(change):,.2f}")
                
        if st.button("✅ Clear / New Transaction", type="primary", use_container_width=True):
            st.session_state.cart = {}
            st.success("Transaction Cleared!")
            st.rerun()

# 3. Admin Panel (Kept intact at the bottom for back-end management)
if admin_mode:
    st.markdown("---")
    st.subheader("🛠️ Admin Management Panel")
    action = st.radio("Choose Action:", ["Update Existing Price", "Add New Product", "Delete Product"], horizontal=True)
    
    if action == "Update Existing Price":
        admin_search = st.text_input("⌨️ Search item to edit:", key="admin_edit_search")
        all_products = df["Product name"].unique().tolist()
        filtered_options = [p for p in all_products if admin_search.lower() in str(p).lower()] if admin_search else all_products
        
        if filtered_options:
            product_to_update = st.selectbox("🎯 Select Product:", filtered_options)
            current_row = df[df["Product name"] == product_to_update].iloc[0]
            
            rename_checkbox = st.checkbox("✏️ Rename this product?")
            new_name = st.text_input("New Name:", value=str(product_to_update)) if rename_checkbox else str(product_to_update)
            
            col1, col2 = st.columns(2)
            with col1:
                new_unit_price = st.number_input("New Unit Price:", value=float(current_row["Unit Price"]) if pd.notna(current_row["Unit Price"]) else 0.0)
            with col2:
                new_wholesale = st.number_input("New Wholesale Price:", value=float(current_row["Wholesale"]) if pd.notna(current_row["Wholesale"]) else 0.0)
                
            if st.button("Apply Changes"):
                df.loc[df["Product name"] == product_to_update, ["Product name", "Unit Price", "Wholesale"]] = [new_name, new_unit_price, new_wholesale]
                save_data(df)
                st.success("Updated successfully!")
                st.rerun()
