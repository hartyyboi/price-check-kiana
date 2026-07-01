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
@st.cache_data(ttl=5) # Low TTL so rule changes/inventory updates pop up immediately
def load_data():
    # Load main price sheet
    if os.path.exists(EXCEL_FILE):
        df_items = pd.read_excel(EXCEL_FILE, sheet_name="Sheet1")
    else:
        df_items = pd.DataFrame(columns=["Product name", "Unit Price", "Wholesale"])
        
    # Load or create wholesale rules sheet
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
    st.subheader("🔍 Product Lookup & Add to Cart")
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
                if p_name in st.session_state.cart:
                    st.session_state.cart[p_name] += 1
                else:
                    st.session_state.cart[p_name] = 1
                st.toast(f"Added {p_name}")
                st.rerun()

with cart_col:
    st.subheader("🛒 Current Order")
    
    if not st.session_state.cart:
        st.info("Cart is empty.")
        total_bill = 0.0
    else:
        total_bill = 0.0
        items_to_remove = []
        
        for name, current_qty in list(st.session_state.cart.items()):
            # Grab matching item details
            item_data = df[df["Product name"] == name].iloc[0]
            r_price = float(item_data["Unit Price"]) if pd.notna(item_data["Unit Price"]) else 0.0
            w_price = float(item_data["Wholesale"]) if pd.notna(item_data["Wholesale"]) else r_price
            
            # Wholesale Logic evaluation
            ws_target = get_wholesale_threshold(name)
            is_wholesale = ws_target is not None and current_qty >= ws_target
            active_price = w_price if is_wholesale else r_price
            
            subtotal = active_price * current_qty
            total_bill += subtotal
            
            # Build item card row
            st.markdown(f"🔹 **{name}**")
            if is_wholesale:
                st.caption(f"✨ Wholesale Rate Applied! (₱{w_price:,.2f}/pc)")
            else:
                st.caption(f"Standard Retail (₱{r_price:,.2f}/pc)")

            # Custom Qty Input + Removal Button
            c_input, c_del = st.columns([3, 1])
            with c_input:
                new_qty = st.number_input(f"Qty for {name}:", min_value=1, value=int(current_qty), step=1, key=f"qty_num_{name}")
                st.session_state.cart[name] = new_qty
            with c_del:
                if st.button("❌", key=f"del_{name}"):
                    items_to_remove.append(name)
            
            # Big Shortcut Buttons (x6, x10, x12) placed horizontally directly underneath
            s1, s2, s3 = st.columns(3)
            with s1:
                if st.button("x6", key=f"s6_{name}", use_container_width=True):
                    st.session_state.cart[name] = 6
                    st.rerun()
            with s2:
                if st.button("x10", key=f"s10_{name}", use_container_width=True):
                    st.session_state.cart[name] = 10
                    st.rerun()
            with s3:
                if st.button("x12", key=f"s12_{name}", use_container_width=True):
                    st.session_state.cart[name] = 12
                    st.rerun()
                    
            st.markdown(f"<div style='text-align: right; font-weight: bold;'>Subtotal: ₱{subtotal:,.2f}</div>", unsafe_allow_html=True)
            st.markdown("---")
                    
        for name in items_to_remove:
            del st.session_state.cart[name]
            st.rerun()
            
        st.markdown(f"### 🧾 Total: ₱{total_bill:,.2f}")
        
        cash_received = st.number_input("💵 Cash Received:", min_value=0.0, step=20.0, value=0.0)
        if cash_received > 0:
            change = cash_received - total_bill
            if change >= 0:
                st.success(f"### 🪙 Change: ₱{change:,.2f}")
            else:
                st.error(f"⚠️ Kulang ng: ₱{abs(change):,.2f}")
                
        if st.button("✅ Clear / New Transaction", type="primary", use_container_width=True):
            st.session_state.cart = {}
            st.rerun()

# 3. Admin Access Adjustments Panel
if admin_mode:
    st.markdown("---")
    st.subheader("🛠️ Admin Management Panel")
    action = st.radio("Choose Action:", ["Update Existing Price", "Wholesale Rules Configuration", "Add New Product", "Delete Product"], horizontal=True)
    
    # NEW MANAGEMENT TAB FOR BULK/WHOLESALE DISCOUNTS
    if action == "Wholesale Rules Configuration":
        st.markdown("#### 📦 Set Custom Wholesale Target Limits")
        rule_search = st.text_input("Search product for rule adjustment:", key="rule_search")
        all_products = df["Product name"].unique().tolist()
        filtered_rules = [p for p in all_products if rule_search.lower() in str(p).lower()] if rule_search else all_products
        
        if filtered_rules:
            selected_rule_product = st.selectbox("Select Target Product:", filtered_rules)
            
            # Check current setup status
            existing_rule = df_rules[df_rules["Product name"] == selected_rule_product]
            current_active = bool(existing_rule.iloc[0]["Active"]) if not existing_rule.empty else False
            current_target = int(existing_rule.iloc[0]["Target Qty"]) if not existing_rule.empty else 6
            
            is_active = st.checkbox("Enable Wholesale Target Quantity Rule?", value=current_active)
            target_amount = st.number_input("Trigger wholesale pricing at what quantity?", min_value=1, value=current_target, step=1)
            
            if st.button("Save Rule Profile", type="primary"):
                if not existing_rule.empty:
                    df_rules.loc[df_rules["Product name"] == selected_rule_product, ["Active", "Target Qty"]] = [is_active, target_amount]
                else:
                    new_rule_row = pd.DataFrame([{"Product name": selected_rule_product, "Active": is_active, "Target Qty": target_amount}])
                    df_rules = pd.concat([df_rules, new_rule_row], ignore_index=True)
                
                save_data(df, df_rules)
                st.success(f"Configured wholesale discount logic profile for '{selected_rule_product}'!")
                st.rerun()

    elif action == "Update Existing Price":
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
                save_data(df, df_rules)
                st.success("Updated successfully!")
                st.rerun()
                
    elif action == "Add New Product":
        new_name = st.text_input("Product Name:")
        col1, col2 = st.columns(2)
        with col1:
            new_unit_price = st.number_input("Unit Price:", min_value=0.0, value=0.0)
        with col2:
            new_wholesale = st.number_input("Wholesale Price:", min_value=0.0, value=0.0)
            
        if st.button("Add to Inventory", type="primary"):
            if new_name.strip() == "":
                st.error("Product Name cannot be empty!")
            elif new_name in df["Product name"].values:
                st.error("This product already exists!")
            else:
                new_row = pd.DataFrame([{"Product name": new_name, "Unit Price": new_unit_price, "Wholesale": new_wholesale}])
                df = pd.concat([df, new_row], ignore_index=True)
                save_data(df, df_rules)
                st.success(f"Added '{new_name}' successfully!")
                st.rerun()
                
    elif action == "Delete Product":
        del_search = st.text_input("⌨️ Search item to delete:", key="admin_del_search")
        all_products = df["Product name"].unique().tolist()
        filtered_del_options = [p for p in all_products if del_search.lower() in str(p).lower()] if del_search else all_products
        
        if filtered_del_options:
            product_to_delete = st.selectbox("Select Product to Remove:", filtered_del_options)
            st.warning(f"Are you sure you want to completely remove '{product_to_delete}'?")
            if st.button("Permanently Delete", type="primary"):
                df = df[df["Product name"] != product_to_delete]
                df_rules = df_rules[df_rules["Product name"] != product_to_delete]
                save_data(df, df_rules)
                st.success(f"Deleted '{product_to_delete}' from inventory.")
                st.rerun()
