import streamlit as st
import pandas as pd
import json
import os
import re
from datetime import datetime

st.set_page_config(page_title="Import Shows from Excel", layout="wide")
st.title("Import Programme from Availability Sheet")
st.write("Extract performance dates, venues, and names directly from the Microsoft Forms headers.")

SHOWS_FILE = "data/shows.json"

def load_json(filepath):
    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
        return []
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def save_shows(shows):
    if not os.path.exists("data"):
        os.makedirs("data")
    with open(SHOWS_FILE, "w") as f:
        json.dump(shows, f, indent=4)

uploaded_file = st.file_uploader("Upload Availability Spreadsheet (.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        
        if 'Name1' not in df.columns:
            st.error("Invalid format. Could not find the 'Name1' column from Microsoft Forms.")
        else:
            st.success("File analyzed successfully! Extracting performances...")
            
            comments_col = [col for col in df.columns if 'Comments' in col][0]
            start_idx = df.columns.get_loc(comments_col) + 1
            performance_columns = df.columns[start_idx:]
            
            existing_shows = load_json(SHOWS_FILE)
            existing_ids = {s['id'] for s in existing_shows}
            new_shows_added = 0
            
            parsed_shows_preview = []
            
            for col in performance_columns:
                col_str = str(col)
                
                # --- Intelligent Text Parsing of the Header ---
                # Example header: "Tuesday 31 March 19:30\u2002\u2002Barnum\u2002\u2002\u2002\u2002\u2002Alhambra..."
                
                # 1. Extract Venue
                venue = "Alhambra"
                if "St George's Hall" in col_str or "St George’s Hall" in col_str:
                    venue = "St George's Hall"
                elif "Studio" in col_str or "The Studio" in col_str:
                    venue = "The Studio"
                
                # 2. Extract Time (Look for HH:MM pattern)
                time_match = re.search(r'\b(0?[1-9]|1[0-2]):([0-5][0-9])\b', col_str)
                curtain_time = time_match.group(0) if time_match else "19:30"
                # Normalize time format to HH:MM:SS for storage consistency
                if len(curtain_time) == 5: curtain_time += ":00"
                
                # 3. Extract Date (Look for Day Month pattern, e.g., "31 March")
                date_match = re.search(r'([0-3]?[0-9])\s+(January|February|March|April|May|June|July|August|September|October|November|December)', col_str, re.IGNORECASE)
                
                show_date_str = "2026-04-01" # fallback
                if date_match:
                    day = date_match.group(1).zfill(2)
                    month_name = date_match.group(2)
                    # Assuming 2026 based on your files
                    try:
                        temp_dt = datetime.strptime(f"{day} {month_name} 2026", "%d %B %Y")
                        show_date_str = temp_dt.strftime("%Y-%m-%d")
                    except:
                        pass
                
                # 4. Extract Show Name (Strip out dates, times, venues, and call times)
                # Clean up whitespace separators
                cleaned_name = col_str.split('\n')[0] # Usually first line has date/show/venue
                # Remove venue names
                cleaned_name = cleaned_name.replace("Alhambra", "").replace("St George's Hall", "").replace("The Studio", "")
                # Remove date components like "Tuesday 31 March 19:30" or "19:30"
                cleaned_name = re.sub(r'^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+[0-3]?[0-9]\s+\w+\s+(\d{1,2}:\d{2}\s*(&\s*\d{1,2}:\d{2})?)?', '', cleaned_name).strip()
                cleaned_name = re.sub(r'\b\d{1,2}:\d{2}\b', '', cleaned_name).strip()
                cleaned_name = cleaned_name.replace("–", "-").strip(' \t\n\r&')
                
                if not cleaned_name:
                    cleaned_name = "Unknown Show"

                show_id = f"{show_date_str}_{cleaned_name.replace(' ', '')}_{curtain_time}"
                
                # Default rules setup
                audience = 1150 if venue == "Alhambra" else 800
                req_sup = 1
                req_ush = 6 if venue == "Alhambra" else 4
                
                show_record = {
                    "id": show_id,
                    "show_name": cleaned_name,
                    "venue": venue,
                    "date": show_date_str,
                    "curtain_time": curtain_time,
                    "audience": audience,
                    "stalls_open": True,
                    "dc_open": True,
                    "uc_open": True,
                    "merch_req": True,
                    "kiosk_req": True,
                    "access_host": False,
                    "notes": "Auto-imported from Excel Header",
                    "priority_group": "None",
                    "requirements": {
                        "Supervisor": req_sup,
                        "Ushers": req_ush,
                        "Merch": 1,
                        "Kiosk": 2,
                        "Access Host": 0,
                        "Total": req_sup + req_ush + 3
                    }
                }
                
                parsed_shows_preview.append(show_record)
                
                if show_id not in existing_ids:
                    existing_shows.append(show_record)
                    existing_ids.add(show_id)
                    new_shows_added += 1
            
            save_shows(existing_shows)
            
            st.success(f"Successfully processed headers! Added **{new_shows_added}** new performances to your programme.")
            
            st.subheader("Extracted Programme Preview")
            df_preview = pd.DataFrame(parsed_shows_preview)
            st.dataframe(df_preview[["date", "curtain_time", "show_name", "venue"]], use_container_width=True, hide_index=True)
            
            st.info("Head over to the **Show Setup** module anytime to adjust audience sizes, open levels, or staffing requirements for these shows.")
            
    except Exception as e:
        st.error(f"An error occurred while parsing headers: {e}")
else:
    existing_shows = load_json(SHOWS_FILE)
    if existing_shows:
        st.write("### Currently Loaded Programme")
        st.write(f"**{len(existing_shows)}** shows currently in the system.")
