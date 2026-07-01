import streamlit as st
import pandas as pd
import os
import requests
from datetime import datetime

# Configuration
EXCEL_FILE = "Price List.xlsx"
ORDERS_FILE = "Orders_Database.xlsx"
ADMIN_PASSWORD = "your_secret_password"  # Change this to your preferred admin password

# TELEGRAM BOT CONFIGURATION
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"
TELEGRAM_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID_HERE"

st.set_page_config(page_title="Store POS & Price Checker", page_icon="💰", layout="wide")

# DETECT URL INTERACTION QUERY (?view=staff)
query_params = st.query_params
is_staff_link = query_params.get("view") == "staff"

# 1. Load Core Inventory Data
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
    with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl") as writer:
        df_items.to_excel(writer, sheet_name="Sheet1", index=False)
        df_rules.to_excel(writer, sheet_name="WS_Rules", index=False)
    st.cache_data.clear()

df, df_rules = load_data()

def load_orders():
    if os.path.exists(ORDERS_FILE):
        return pd.read_excel(ORDERS_FILE)
    else:
        return pd.DataFrame(columns=["Timestamp", "Customer", "Fulfillment", "Payment", "Ref No", "Items Ordered", "Total Bill", "Status"])

def save_order_record(new_order_dict):
    orders_df = load_orders()
    new_row = pd.DataFrame([new_order_dict])
    orders_df = pd.concat([orders_df, new_row], ignore_index=True)
    orders_df.to_excel(ORDERS_FILE, index=False)

def update_order_status(timestamp, new_status):
    orders_df = load_orders()
    orders_df.loc[orders_df["Timestamp"] == timestamp, "Status"] = new_status
    orders_df.to_excel(ORDERS_FILE, index=False)

def send_telegram_alert(message_text):
    if TELEGRAM_BOT_TOKEN != "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message_text, "parse_mode": "Markdown"}
        try: requests.post(url, json=payload)
        except Exception: pass

def get_wholesale_threshold(product_name):
    rule = df_rules[(df_rules["Product name"] == product_name) & (df_rules["Active"] == True)]
    if not rule.empty: return int(rule.iloc[0]["Target Qty"])
    return None

# Session State Initialization
if "cart" not in st.session_state: st.session_state.cart = {}
if "qty_multiplier" not in st.session_state: st.session_state.qty_multiplier = 1
if "staff_mode" not in st.session_state: st.session_state.staff_mode = "Live Orders Counter Board"

# ==========================================================
# 🛑 VIEW 1: STAFF REGISTER & ORDERS SCREEN (?view=staff)
# ==========================================================
if is_staff_link:
    st.sidebar.title("👑 Staff Navigation")
    
    # Mode selector buttons inside the sidebar
    if st.sidebar.button("📥 Live Orders Board", use_container_width=True, type="primary" if st.session_state.staff_mode == "Live Orders Counter Board" else "secondary"):
        st.session_state.staff_mode = "Live Orders Counter Board"
        st.rerun()
        
    if st.sidebar.button("🔍 Price Checker", use_container_width=True, type="primary" if st.session_state.staff_mode == "Price Checker" else "secondary"):
        st.session_state.staff_mode = "Price Checker"
        st.rerun()
        
    if st.sidebar.button("💪 Calculator on Steroids", use_container_width=True, type="primary" if st.session_state.staff_mode == "Calculator on Steroids" else "secondary"):
        st.session_state.staff_mode = "Calculator on Steroids"
        st.rerun()

    st.sidebar.markdown("---")
    pwd_input = st.sidebar.text_input("Admin Password (To Edit Inventory)", type="password")
    admin_authenticated = (pwd_input == ADMIN_PASSWORD)

    # --- MODE 1: LIVE ORDERS COUNTER BOARD ---
    if st.session_state.staff_mode == "Live Orders Counter Board":
        st.title("📥 Live Orders Counter Board")
        orders_df = load_orders()
        
        # Calculate dynamic waiting metrics for notifications
        pending_orders = orders_df[orders_df["Status"] == "Pending ⏳"]
        num_pending = len(pending_orders)
        
        if num_pending > 0:
            # Parse the oldest order timestamp
            oldest_time_str = pending_orders.iloc[0]["Timestamp"]
            try:
                oldest_time = datetime.strptime(oldest_time_str, "%Y-%m-%d %H:%M:%S")
                time_delta = datetime.now() - oldest_time
                minutes_waiting = int(time_delta.total_seconds() / 60)
                
                if minutes_waiting == 0:
                    time_status = "Just now"
                else:
                    time_status = f"{minutes_waiting} mins ago"
            except Exception:
                time_status = oldest_time_str
                
            st.error(f"🚨 **Notification:** There are **{num_pending} pending order(s)** waiting! Oldest unhandled order arrived **{time_status}**.")
        else:
            st.success("✅ **Notification:** All caught up! 0 pending orders left in queue.")

        st.markdown("---")
        
        if orders_df.empty:
            st.info("No incoming orders currently recorded in history.")
        else:
            for idx, row in orders_df.iloc[::-1].iterrows():
                status = row["Status"]
                if status == "Pending ⏳": card_color = "#FFF4E5"; border = "#FFA500"
                elif status == "Paid & Completed ✅": card_color = "#E8F5E9"; border = "#4CAF50"
                else: card_color = "#FFEBEE"; border = "#F44336"
                
                st.markdown(
                    f'<div style="background-color: {card_color}; border-left: 6px solid {border}; '
                    f'padding: 12px; border-radius: 5px; margin-bottom: 10px;">'
                    f'<h4>👤 {row["Customer"]} ({row["Fulfillment"]})</h4>'
                    f'<p style="margin:2px 0;">⏰ Received: {row["Timestamp"]} | 💳 Mode: {row["Payment"]} (Ref: {row["Ref No"]})</p>'
                    f'</div>', unsafe_allow_html=True
                )
                o_col1, o_col2, o_col3 = st.columns([2.5, 1, 1])
                with o_col1:
                    st.text(row["Items Ordered"])
                    st.markdown(f"**Total Amount Due: ₱{float(row['Total Bill']):,.2f}**")
                with o_col2:
                    if status == "Pending ⏳" and st.button("✅ Complete Paid", key=f"pay_{row['Timestamp']}"):
                        update_order_status(row["Timestamp"], "Paid & Completed ✅"); st.rerun()
                with o_col3:
                    if status != "Cancelled ❌" and st.button("❌ Cancel", key=f"can_{row['Timestamp']}"):
                        update_order_status(row["Timestamp"], "Cancelled ❌"); st.rerun()
                st.markdown("---")

    # --- MODE 2: STAFF PRICE CHECKER ---
    elif st.session_state.staff_mode == "Price Checker":
        st.title("🔍 Quick Counter Price Lookup")
        search_query = st.text_input("Search Item Name...", placeholder="Type here to instantly find items...")
        filtered_df = df[df["Product name"].astype(str).str.contains(search_query, case=False, na=False)] if search_query else df.head(15)

        for idx, row in filtered_df.iterrows():
            p_name = row["Product name"]
            p_price = float(row["Unit Price"]) if pd.notna(row["Unit Price"]) else 0.0
            p_ws = float(row["Wholesale"]) if pd.notna(row["Wholesale"]) else 0.0
            ws_target = get_wholesale_threshold(p_name)
            
            sc1, sc2, sc3 = st.columns([3, 1.5, 1.5])
            with sc1:
                st.markdown(f"### {p_name}")
                if ws_target: st.caption(f"Wholesale triggers at {ws_target} items")
            with sc2: st.markdown(f"**Retail:** ₱{p_price:,.2f}")
            with sc3: st.markdown(f"**Wholesale:** ₱{p_ws:,.2f}")
            st.markdown("<hr style='margin: 4px 0px; border-top: 1px solid #f1f1f1;'>", unsafe_allow_html=True)

    # --- MODE 3: CALCULATOR ON STEROIDS ---
    elif st.session_state.staff_mode == "Calculator on Steroids":
        st.title("💪 Calculator on Steroids (Walk-In Register)")
        main_col, cart_col = st.columns([1.8, 1.2])
        
        with main_col:
            # Multiplier configuration bar
            s_col1, s_col2, s_col3, s_col4, s_col5 = st.columns([1, 1, 1, 1, 2])
            with s_col1:
                if st.button("x1", use_container_width=True, type="secondary" if st.session_state.qty_multiplier != 1 else "primary"): st.session_state.qty_multiplier = 1; st.rerun()
            with s_col2:
                if st.button("x6", use_container_width=True, type="secondary" if st.session_state.qty_multiplier != 6 else "primary"): st.session_state.qty_multiplier = 6; st.rerun()
            with s_col3:
                if st.button("x10", use_container_width=True, type="secondary" if st.session_state.qty_multiplier != 10 else "primary"): st.session_state.qty_multiplier = 10; st.rerun()
            with s_col4:
                if st.button("x12", use_container_width=True, type="secondary" if st.session_state.qty_multiplier != 12 else "primary"): st.session_state.qty_multiplier = 12; st.rerun()
            with s_col5:
                custom_mult = st.number_input("Custom Qty:", min_value=1, value=int(st.session_state.qty_multiplier), step=1)
                if custom_mult != st.session_state.qty_multiplier: st.session_state.qty_multiplier = custom_mult; st.rerun()

            st.info(f"🚀 **Active Multiplier:** Tapping Add inserts **{st.session_state.qty_multiplier}** pc(s).")
            
            search_query = st.text_input("Quick Counter Scan/Search...", placeholder="Filter list...")
            filtered_df = df[df["Product name"].astype(str).str.contains(search_query, case=False, na=False)] if search_query else df.head(10)

            for idx, row in filtered_df.iterrows():
                p_name = row["Product name"]
                p_price = float(row["Unit Price"]) if pd.notna(row["Unit Price"]) else 0.0
                p_ws = float(row["Wholesale"]) if pd.notna(row["Wholesale"]) else 0.0
                
                item_col1, item_col2, item_col3, item_col4 = st.columns([2.5, 1, 1, 0.8], vertical_alignment="center")
                with item_col1: st.markdown(f"**{p_name}**")
                with item_col2: st.markdown(f"₱{p_price:,.2f}")
                with item_col3: st.markdown(f"₱{p_ws:,.2f}")
                with item_col4:
                    if st.button("➕ Add", key=f"register_add_{idx}"):
                        st.session_state.cart[p_name] = st.session_state.cart.get(p_name, 0) + st.session_state.qty_multiplier
                        st.session_state.qty_multiplier = 1
                        st.rerun()

        with cart_col:
            st.subheader("🧾 Active Counter Transaction")
            if not st.session_state.cart:
                st.info("No items scanned yet.")
                total_bill = 0.0
            else:
                total_bill = 0.0
                items_to_remove = []
                for name, qty in list(st.session_state.cart.items()):
                    item_data = df[df["Product name"] == name].iloc[0]
                    r_price = float(item_data["Unit Price"]) if pd.notna(item_data["Unit Price"]) else 0.0
                    w_price = float(item_data["Wholesale"]) if pd.notna(item_data["Wholesale"]) else r_price
                    ws_target = get_wholesale_threshold(name)
                    is_ws = ws_target is not None and qty >= ws_target
                    price = w_price if is_ws else r_price
                    subtotal = price * qty
                    total_bill += subtotal
                    
                    rc1, rc2, rc3 = st.columns([2.2, 0.8, 0.5])
                    with rc1: st.markdown(f"**{name}** x{qty}{' (WS)' if is_ws else ''}")
                    with rc2: st.markdown(f"₱{subtotal:,.2f}")
                    with rc3:
                        if st.button("❌", key=f"reg_del_{name}"): items_to_remove.append(name)
                
                for name in items_to_remove:
                    del st.session_state.cart[name]; st.rerun()
                    
                st.markdown(f"## Total: ₱{total_bill:,.2f}")
                cash_rec = st.number_input("Cash Tendered:", min_value=0.0, step=20.0)
                if cash_rec > 0:
                    change = cash_rec - total_bill
                    if change >= 0: st.success(f"Change: ₱{change:,.2f}")
                    else: st.error(f"Kulang: ₱{abs(change):,.2f}")
                    
                if st.button("✅ Log & Clear Transaction", type="primary", use_container_width=True):
                    st.session_state.cart = {}
                    st.success("Transaction Complete!")
                    st.rerun()

# ==========================================================
# 📱 VIEW 2: CLEAN ONLINE CUSTOMER SHOPPING SCREEN (Default)
# ==========================================================
else:
    st.title("🛒 Suan Soy Online Order & Prices")
    st.caption("Browse pricing or add items to your basket to submit an order right to our counter!")
    
    main_col, cart_col = st.columns([1.8, 1.2])
    
    with main_col:
        search_query = st.text_input("Search for items...", placeholder="Type name here to check prices...")
        filtered_df = df[df["Product name"].astype(str).str.contains(search_query, case=False, na=False)] if search_query else df.head(12)

        for idx, row in filtered_df.iterrows():
            p_name = row["Product name"]
            p_price = float(row["Unit Price"]) if pd.notna(row["Unit Price"]) else 0.0
            p_ws = float(row["Wholesale"]) if pd.notna(row["Wholesale"]) else 0.0
            ws_target = get_wholesale_threshold(p_name)
            rule_tag = f" (Wholesale price active at {ws_target}+ items)" if ws_target else ""

            item_col1, item_col2, item_col3 = st.columns([3.5, 1.5, 1.0], vertical_alignment="center")
            with item_col1:
                st.markdown(f"### {p_name}")
                if rule_tag: st.caption(rule_tag)
            with item_col2:
                st.markdown(f"**Retail:** ₱{p_price:,.2f}")
                st.markdown(f"**Wholesale:** ₱{p_ws:,.2f}")
            with item_col3:
                item_qty = st.number_input("Qty:", min_value=1, value=1, step=1, key=f"cust_qty_{idx}")
                if st.button("🛍️ Add", key=f"add_cust_{idx}", use_container_width=True):
                    st.session_state.cart[p_name] = st.session_state.cart.get(p_name, 0) + item_qty
                    st.toast(f"Added {item_qty}x {p_name} to cart!")
                    st.rerun()
            st.markdown("<hr style='margin: 8px 0px; border-top: 1px solid #eee;'>", unsafe_allow_html=True)

    with cart_col:
        st.subheader("📋 Your Shopping Basket")
        if not st.session_state.cart:
            st.info("Your basket is empty. Click 🛍️ Add next to items to build your order!")
        else:
            items_total = 0.0
            items_to_remove = []
            receipt_plain_text = ""
            
            for name, current_qty in list(st.session_state.cart.items()):
                item_data = df[df["Product name"] == name].iloc[0]
                r_price = float(item_data["Unit Price"]) if pd.notna(item_data["Unit Price"]) else 0.0
                w_price = float(item_data["Wholesale"]) if pd.notna(item_data["Wholesale"]) else r_price
                ws_target = get_wholesale_threshold(name)
                is_wholesale = ws_target is not None and current_qty >= ws_target
                active_price = w_price if is_wholesale else r_price
                subtotal = active_price * current_qty
                items_total += subtotal
                
                receipt_plain_text += f"• {current_qty}x {name} = ₱{subtotal:,.2f}\n"
                
                rc1, rc2, rc3 = st.columns([2.0, 1.0, 0.5])
                with rc1: st.markdown(f"**{name}**\n x{current_qty}")
                with rc2: st.markdown(f"**₱{subtotal:,.2f}**")
                with rc3:
                    if st.button("❌", key=f"del_cust_{name}"): items_to_remove.append(name)
                st.markdown("<hr style='margin: 4px 0px; border-top: 1px dashed #bbb;'>", unsafe_allow_html=True)
            
            for name in items_to_remove:
                del st.session_state.cart[name]; st.rerun()
                
            st.markdown("#### 📋 Checkout Details")
            cust_name = st.text_input("Your Name / Contact Info:")
            service_mode = st.radio("Order Option:", ["Pickup / Dine-In", "Delivery"])
            delivery_fee = 40.0 if service_mode == "Delivery" else 0.0
            
            total_bill = items_total + delivery_fee
            if delivery_fee > 0: st.caption(f"Includes standard delivery fee of ₱{delivery_fee:.2f}")
            st.markdown(f"### Total Amount: ₱{total_bill:,.2f}")
            
            pay_method = st.selectbox("Choose Payment Mode:", ["Cash on Pickup / COD", "GCash Online Transfer"])
            gcash_ref = ""
            if pay_method == "GCash Online Transfer":
                st.info("Please send GCash payment to: **0912-345-6789**")
                gcash_ref = st.text_input("Enter 13-digit GCash Reference Number:")

            submit_ready = bool(cust_name)
            if pay_method == "GCash Online Transfer" and not gcash_ref: submit_ready = False
            
            if st.button("🚀 SUBMIT ORDER TO SHOP COUNTER", type="primary", use_container_width=True, disabled=not submit_ready):
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                order_data = {
                    "Timestamp": now_str, "Customer": cust_name, "Fulfillment": service_mode,
                    "Payment": pay_method, "Ref No": gcash_ref if gcash_ref else "N/A",
                    "Items Ordered": receipt_plain_text, "Total Bill": total_bill, "Status": "Pending ⏳"
                }
                save_order_record(order_data)
                
                tg_alert = (
                    f"🚨 *NEW ONLINE CUSTOMER ORDER RECEIVED!*\n\n"
                    f"👤 *Customer:* {cust_name}\n"
                    f"📦 *Type:* {service_mode}\n"
                    f"💰 *Payment:* {pay_method}\n"
                    f"🔢 *Ref:* `{order_data['Ref No']}`\n\n"
                    f"🛒 *Items Ordered:*\n{receipt_plain_text}\n"
                    f"💵 *Total Bill:* **₱{total_bill:,.2f}**"
                )
                send_telegram_alert(tg_alert)
                
                st.session_state.cart = {}
                st.success("🎉 Order submitted successfully! We are processing your items. Thank you!")
                st.balloons()
                st.rerun()
