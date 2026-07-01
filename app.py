# --- MODE 2: STAFF PRICE CHECKER (WITH INLINE EDITING) ---
    elif st.session_state.staff_mode == "Price Checker":
        st.title("🔍 Quick Counter Price Lookup")
        search_query = st.text_input("Search Item Name...", placeholder="Type here to instantly find items...")
        filtered_df = df[df["Product name"].astype(str).str.contains(search_query, case=False, na=False)] if search_query else df.head(15)

        for idx, row in filtered_df.iterrows():
            p_name = row["Product name"]
            p_price = float(row["Unit Price"]) if pd.notna(row["Unit Price"]) else 0.0
            p_ws = float(row["Wholesale"]) if pd.notna(row["Wholesale"]) else 0.0
            ws_target = get_wholesale_threshold(p_name)
            
            sc1, sc2, sc3, sc4 = st.columns([2.5, 1.2, 1.2, 1.1], vertical_alignment="center")
            with sc1:
                st.markdown(f'<span style="font-size: 1.5em; font-weight: bold;">{p_name}</span>', unsafe_allow_html=True)
                if ws_target: 
                    st.caption(f"Wholesale triggers at {ws_target} items")
            with sc2: 
                st.markdown(f"**Retail:** ₱{p_price:,.2f}")
            with sc3: 
                st.markdown(f"**Wholesale:** ₱{p_ws:,.2f}")
            with sc4:
                # Expandable drop-down panel right next to the item row
                with st.popover("✏️ Edit", use_container_width=True):
                    st.markdown(f"### Modify: {p_name}")
                    new_name = st.text_input("Edit Name:", value=p_name, key=f"edit_name_{idx}")
                    new_retail = st.number_input("Edit Retail Price (₱):", value=p_price, min_value=0.0, step=0.5, key=f"edit_ret_{idx}")
                    new_wholesale = st.number_input("Edit Wholesale Price (₱):", value=p_ws, min_value=0.0, step=0.5, key=f"edit_ws_{idx}")
                    
                    if st.button("💾 Save Changes", key=f"save_btn_{idx}", type="primary", use_container_width=True):
                        # Locate the exact row in the master dataframe using index and update values
                        df.at[idx, "Product name"] = new_name
                        df.at[idx, "Unit Price"] = new_retail
                        df.at[idx, "Wholesale"] = new_wholesale
                        
                        # Save changes back to the actual Excel file on your server/repository
                        save_data(df, df_rules)
                        st.toast(f"✅ Updated {new_name} successfully!")
                        st.rerun()
                        
            st.markdown("<hr style='margin: 8px 0px; border-top: 1px solid #f1f1f1;'>", unsafe_allow_html=True)
