import streamlit as st
import pandas as pd
import os

# Configuration
EXCEL_FILE = "Price List.xlsx"

st.set_page_config(page_title="Suan Soy Price Lookup", page_icon="🔍", layout="wide")

# 1. Load Core Data from Excel
@st.cache_data(ttl=2)  # Low TTL so edits refresh almost instantly
def load_data():
    if os.path.exists(EXCEL_FILE):
        # Reads your primary inventory sheet
        return pd.read_excel(EXCEL_FILE, sheet_name="Sheet1")
    else:
        # Fallback if file doesn't exist yet
        return pd.DataFrame(columns=["Product name", "Unit Price", "Wholesale"])

def save_data(df_items):
    with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl") as writer:
        df_items.to_excel(writer, sheet_name="Sheet1", index=False)
    st.cache_data.clear()

# Initialize data
df = load_data()

# --- MAIN APP INTERFACE ---
st.title("🔍 Quick Counter Price Lookup")
st.caption("Search item rates or use the edit button to update pricing records instantly.")

# Search Bar Filter
search_query = st.text_input("Search Item Name...", placeholder="Type here to instantly find items...")

if not df.empty:
    # Filter database based on search input
    filtered_df = df[df["Product name"].astype(str).str.contains(search_query, case=False, na=False)] if search_query else df.head(20)

    # Loop through rows and display items
    for idx, row in filtered_df.iterrows():
        p_name = row["Product name"]
        p_price = float(row["Unit Price"]) if pd.notna(row["Unit Price"]) else 0.0
        p_ws = float(row["Wholesale"]) if pd.notna(row["Wholesale"]) else 0.0
        
        # Grid layout for clean alignment
        sc1, sc2, sc3, sc4 = st.columns([3.0, 1.2, 1.2, 1.0], vertical_alignment="center")
        
        with sc1:
            # Displays product name at 1.5x standard text size
            st.markdown(f'<span style="font-size: 1.5em; font-weight: bold;">{p_name}</span>', unsafe_allow_html=True)
            
        with sc2: 
            st.markdown(f"**Retail:** ₱{p_price:,.2f}")
            
        with sc3: 
            st.markdown(f"**Wholesale:** ₱{p_ws:,.2f}")
            
        with sc4:
            # Inline edit popover drawer
            with st.popover("✏️ Edit", use_container_width=True):
                st.markdown(f"### Update Item Details")
                new_name = st.text_input("Edit Name:", value=p_name, key=f"name_{idx}")
                new_retail = st.number_input("Edit Retail (₱):", value=p_price, min_value=0.0, step=0.5, key=f"ret_{idx}")
                new_wholesale = st.number_input("Edit Wholesale (₱):", value=p_ws, min_value=0.0, step=0.5, key=f"ws_{idx}")
                
                if st.button("💾 Save", key=f"save_{idx}", type="primary", use_container_width=True):
                    # Write values directly to the master dataframe reference row
                    df.at[idx, "Product name"] = new_name
                    df.at[idx, "Unit Price"] = new_retail
                    df.at[idx, "Wholesale"] = new_wholesale
                    
                    # Commit adjustments straight to the Excel file
                    save_data(df)
                    st.toast(f"✅ Updated {new_name} successfully!")
                    st.rerun()
                    
        st.markdown("<hr style='margin: 8px 0px; border-top: 1px solid #f1f1f1;'>", unsafe_allow_html=True)
else:
    st.warning("⚠️ No database file found. Please check that 'Price List.xlsx' is in your directory.")
