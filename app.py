import streamlit as st
import pandas as pd
import os

# Configuration
EXCEL_FILE = "Price List.xlsx"
ADMIN_PASSWORD = "your_secret_password"  # Change this to your preferred admin password

st.set_page_config(page_title="Product Price Checker", page_icon="💰", layout="wide")
st.title("📦 Product Price Checker")

# 1. Load Data
@st.cache_data(ttl=60) # Caches data for 1 minute to stay snappy, but reloads updates
def load_data():
    if os.path.exists(EXCEL_FILE):
        return pd.read_excel(EXCEL_FILE, sheet_name="Sheet1")
    else:
        # Fallback if file isn't found
        return pd.DataFrame(columns=["Product name", "Unit Price", "Wholesale"])

def save_data(df):
    # Saves updates back to Sheet1 while preserving Sheet2 if it exists
    if os.path.exists(EXCEL_FILE):
        with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
            df.to_excel(writer, sheet_name="Sheet1", index=False)
    else:
        df.to_excel(EXCEL_FILE, sheet_name="Sheet1", index=False)
    st.cache_data.clear() # Clear cache so changes reflect instantly

df = load_data()

# 2. Sidebar - Access Control / Admin Mode
st.sidebar.header("🔐 Access Control")
admin_mode = False

pwd_input = st.sidebar.text_input("Admin Password", type="password", help="Enter password to unlock editing rights")
if pwd_input == ADMIN_PASSWORD:
    st.sidebar.success("Admin Mode Activated! 🎉")
    admin_mode = True
elif pwd_input != "":
    st.sidebar.error("Incorrect password")

# 3. Main Interface - Staff / Lookup View (Always Available)
st.subheader("🔍 Staff Lookup")
search_query = st.text_input("Search by Product Name...", placeholder="Type item name here...", key="staff_search")

# Filter data based on search
if search_query:
    filtered_df = df[df["Product name"].astype(str).str.contains(search_query, case=False, na=False)]
else:
    filtered_df = df

# Display data beautifully
st.dataframe(
    filtered_df, 
    column_config={
        "Product name": "Product Name",
        "Unit Price": st.column_config.NumberColumn("Unit Price", format="₱%.2f"),
        "Wholesale": st.column_config.NumberColumn("Wholesale Price", format="₱%.2f")
    },
    use_container_width=True,
    hide_index=True
)

# 4. Admin Management Panel (Only visible if password is correct)
if admin_mode:
    st.markdown("---")
    st.subheader("🛠️ Admin Management Panel")
    
    action = st.radio("Choose Action:", ["Update Existing Price", "Add New Product", "Delete Product"], horizontal=True)
    
    if action == "Update Existing Price":
        # NEW FEATURE: Search field to narrow down product dropdown list
        admin_search = st.text_input("⌨️ Type here to search for product to edit:", placeholder="Type name to filter list...", key="admin_edit_search")
        
        all_products = df["Product name"].unique().tolist()
        if admin_search:
            # Filter dropdown options based on what you typed
            filtered_options = [p for p in all_products if admin_search.lower() in str(p).lower()]
        else:
            filtered_options = all_products
            
        if not filtered_options:
            st.warning("No products match your search.")
            product_to_update = None
        else:
            product_to_update = st.selectbox("🎯 Select Product to Update:", filtered_options)
        
        if product_to_update:
            # Get current values
            current_row = df[df["Product name"] == product_to_update].iloc[0]
            
            # NEW FEATURE: Rename functionality checkbox
            rename_checkbox = st.checkbox("✏️ Rename this product?")
            if rename_checkbox:
                new_name = st.text_input("Enter New Product Name:", value=str(product_to_update))
            else:
                new_name = str(product_to_update)
            
            col1, col2 = st.columns(2)
            with col1:
                new_unit_price = st.number_input("New Unit Price:", value=float(current_row["Unit Price"]) if pd.notna(current_row["Unit Price"]) else 0.0)
            with col2:
                new_wholesale = st.number_input("New Wholesale Price:", value=float(current_row["Wholesale"]) if pd.notna(current_row["Wholesale"]) else 0.0)
                
            if st.button("Apply Changes", type="primary"):
                if rename_checkbox and new_name.strip() == "":
                    st.error("Product Name cannot be empty!")
                elif rename_checkbox and new_name != product_to_update and new_name in df["Product name"].values:
                    st.error("A product with that new name already exists!")
                else:
                    # Update row values
                    df.loc[df["Product name"] == product_to_update, ["Product name", "Unit Price", "Wholesale"]] = [new_name, new_unit_price, new_wholesale]
                    save_data(df)
                    st.success(f"Updated '{product_to_update}' successfully!")
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
                st.error("This product already exists! Use 'Update Existing Price' instead.")
            else:
                new_row = pd.DataFrame([{"Product name": new_name, "Unit Price": new_unit_price, "Wholesale": new_wholesale}])
                df = pd.concat([df, new_row], ignore_index=True)
                save_data(df)
                st.success(f"Added '{new_name}' successfully!")
                st.rerun()
                
    elif action == "Delete Product":
        # Search feature added to Delete tab as well for convenience
        del_search = st.text_input("⌨️ Type here to search for product to delete:", placeholder="Type name to filter list...", key="admin_del_search")
        all_products = df["Product name"].unique().tolist()
        
        if del_search:
            filtered_del_options = [p for p in all_products if del_search.lower() in str(p).lower()]
        else:
            filtered_del_options = all_products
            
        if not filtered_del_options:
            st.warning("No products match your search.")
            product_to_delete = None
        else:
            product_to_delete = st.selectbox("Select Product to Remove:", filtered_del_options)
            
        if product_to_delete:
            st.warning(f"Are you sure you want to completely remove '{product_to_delete}'?")
            if st.button("Permanently Delete", type="primary"):
                df = df[df["Product name"] != product_to_delete]
                save_data(df)
                st.success(f"Deleted '{product_to_delete}' from inventory.")
                st.rerun()
