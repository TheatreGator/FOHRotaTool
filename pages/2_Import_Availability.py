import streamlit as st
import pandas as pd
import json
import os

st.set_page_config(page_title="Import Availability", layout="wide")
st.title("Import Staff Availability")
st.write("Upload the Microsoft Forms Excel export to process availability for the upcoming period.")

# Setup storage path for the processed availability
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

# File uploader
uploaded_file = st.file_uploader("Upload Availability Spreadsheet (.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    try:
        # Read the Excel file
        df = pd.read_excel(uploaded_file)
        
        # Verify it's the correct format by checking for the 'Name1' column
        if 'Name1' not in df.columns:
            st.error("Invalid format. Could not find the 'Name1' column from Microsoft Forms.")
        else:
            st.success("File uploaded successfully! Processing data...")
            
            # Find the index where the actual performance columns start
            # Usually, it's after ID, Start time, Completion time, Name1, and Comments
            comments_col = [col for col in df.columns if 'Comments' in col][0]
            start_idx = df.columns.get_loc(comments_col) + 1
            
            performance_columns = df.columns[start_idx:]
            
            processed_data = []
            
            # Loop through each row (staff member)
            for index, row in df.iterrows():
                name = str(row['Name1']).strip()
                comments = str(row[comments_col]).strip() if pd.notna(row[comments_col]) else ""
                
                # Find all shifts where they answered "Yes" (or ticked the box)
                available_shifts = []
                for col in performance_columns:
                    # Clean up the column name to use as a shift ID (removes line breaks)
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
            
            # Save the processed data
            save_availability(processed_data)
            
            # Display summary metrics
            col1, col2, col3 = st.columns(3)
            col1.metric("Staff Submissions", len(processed_data))
            col2.metric("Total Performances Detected", len(performance_columns))
            
            total_shifts_offered = sum(len(p['available_shifts']) for p in processed_data)
            col3.metric("Total Available Shifts Logged", total_shifts_offered)
            
            # Display a preview of the processed data
            st.subheader("Data Preview")
            
            # Create a clean dataframe for display
            display_df = pd.DataFrame(processed_data)
            # Truncate long comments for the table view
            display_df['comments'] = display_df['comments'].apply(lambda x: x[:50] + '...' if len(x) > 50 else x)
            
            st.dataframe(
                display_df[["employee", "total_available", "comments"]],
                use_container_width=True,
                hide_index=True
            )
            
            st.info("Availability data has been saved and is ready for the allocation engine.")
            
    except Exception as e:
        st.error(f"An error occurred while processing the file: {e}")
else:
    # Show currently loaded availability if it exists
    existing_data = load_availability()
    if existing_data:
        st.write("### Currently Loaded Availability")
        st.write(f"**{len(existing_data)}** staff submissions currently in the system.")
