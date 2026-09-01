import streamlit as st
import pandas as pd
import json
import os
import sys

# Ensure the app can find the services module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from services.storage import load_staff, save_staff

st.set_page_config(page_title="Import Availability", layout="wide")
st.title("Import Staff Availability")
st.write("Upload the Microsoft Forms Excel export to process availability and automatically import new staff.")

AVAILABILITY_FILE = "data/availability.json"

def save_availability(data):
    if not os.path.exists("data"):
        os.makedirs("data")
    with open(AVAILABILITY_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_availability():
    if not os.path.exists(AVAILABILITY_FILE) or os.path.getsize(AVAILABILITY_FILE) == 0:
        return []
    try:
        with open(AVAILABILITY_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

uploaded_file = st.file_uploader("Upload Availability Spreadsheet (.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        
        if 'Name1' not in df.columns:
            st.error("Invalid format. Could not find the 'Name1' column from Microsoft Forms.")
        else:
            st.success("File uploaded successfully! Processing data...")
            
            comments_col = [col for col in df.columns if 'Comments' in col][0]
            start_idx = df.columns.get_loc(comments_col) + 1
            performance_columns = df.columns[start_idx:]
            
            processed_data = []
            
            # Load existing staff to check against
            staff_list = load_staff()
            existing_staff_names = [staff['name'].lower() for staff in staff_list]
            new_staff_added = 0
            
            for index, row in df.iterrows():
                name = str(row['Name1']).strip()
                comments = str(row[comments_col]).strip() if pd.notna(row[comments_col]) else ""
                
                available_shifts = []
                for col in performance_columns:
                    shift_id = " ".join(str(col).split())
                    if pd.notna(row[col]) and str(row[col]).strip().lower() == 'yes':
                        available_shifts.append(shift_id)
                
                if name and name != "nan":
                    processed_data.append({
                        "employee": name,
                        "comments": comments,
                        "available_shifts": available_shifts,
                        "total_available": len(available_shifts)
                    })
                    
                    # Auto-import new staff
                    if name.lower() not in existing_staff_names:
                        new_profile = {
                            "name": name,
                            "active": True,
                            "roles": ["Usher"], # Default baseline role
                            "preferred_shifts": 3,
                            "max_shifts": 5,
                            "double_allowed": True,
                            "venue_restrictions": ["ALH", "SGH", "Studio"],
                            "notes": "Auto-imported from Availability Sheet"
                        }
                        staff_list.append(new_profile)
                        existing_staff_names.append(name.lower())
                        new_staff_added += 1
            
            save_availability(processed_data)
            
            if new_staff_added > 0:
                save_staff(staff_list)
                st.toast(f"Auto-imported {new_staff_added} new staff members!", icon="✅")
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Staff Submissions", len(processed_data))
            col2.metric("New Profiles Created", new_staff_added)
            
            total_shifts_offered = sum(len(p['available_shifts']) for p in processed_data)
            col3.metric("Total Shifts Logged", total_shifts_offered)
            
            st.subheader("Data Preview")
            display_df = pd.DataFrame(processed_data)
            display_df['comments'] = display_df['comments'].apply(lambda x: x[:50] + '...' if len(x) > 50 else x)
            
            st.dataframe(
                display_df[["employee", "total_available", "comments"]],
                use_container_width=True,
                hide_index=True
            )
            
            with st.expander("🔍 View Detailed Shift Allocations"):
                for person in processed_data:
                    st.write(f"**{person['employee']}** ({person['total_available']} shifts)")
                    st.write(person['available_shifts'])
                    st.divider()
            
            st.info("Data saved. You can now edit specific roles and restrictions for the newly imported staff in the Staff Database.")
            
    except Exception as e:
        st.error(f"An error occurred while processing the file: {e}")
else:
    existing_data = load_availability()
    if existing_data:
        st.write("### Currently Loaded Availability")
        st.write(f"**{len(existing_data)}** staff submissions currently in the system.")
