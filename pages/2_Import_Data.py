import streamlit as st
import pandas as pd
import json
import os
import re
from datetime import datetime

st.set_page_config(page_title="Import & Data Management", layout="wide")
st.title("Data Management & Master Importer")
st.write("Upload your Microsoft Forms export to process data, back up your current workspace, or reset the system.")

AVAILABILITY_FILE = "data/availability.json"
STAFF_FILE = "data/staff.json"
SHOWS_FILE = "data/shows.json"
ROTAS_FILE = "data/rotas.json"
COMMITMENTS_FILE = "data/commitments.json"

def load_json(filepath):
    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
        return []
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def save_json(filepath, data):
    directory = os.path.dirname(filepath)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=4)

# --- SECTION 1: SYSTEM STATE BACKUP & WIPE ---
st.subheader("💾 System State & Backup")
col_b1, col_b2 = st.columns(2)

with col_b1:
    snapshot = {
        "staff": load_json(STAFF_FILE),
        "availability": load_json(AVAILABILITY_FILE),
        "shows": load_json(SHOWS_FILE),
        "rotas": load_json(ROTAS_FILE),
        "commitments": load_json(COMMITMENTS_FILE)
    }
    snapshot_bytes = json.dumps(snapshot, indent=4).encode('utf-8')
    
    st.download_button(
        label="📥 Save / Export Current State (JSON Backup)",
        data=snapshot_bytes,
        file_name=f"bradford_foh_backup_{datetime.today().strftime('%Y-%m-%d')}.json",
        mime="application/json",
        type="primary"
    )

with col_b2:
    with st.expander("⚠️ Danger Zone: Wipe All Data"):
        confirm_wipe = st.checkbox("I understand this will delete all staff records, shows, availability, rotas, and commitments.")
        if confirm_wipe:
            if st.button("🗑️ Wipe All System Data", type="primary"):
                for f_path in [STAFF_FILE, AVAILABILITY_FILE, SHOWS_FILE, ROTAS_FILE, COMMITMENTS_FILE]:
                    if os.path.exists(f_path):
                        os.remove(f_path)
                st.success("All system data has been wiped clean.")
                st.rerun()

st.write("---")

# --- SECTION 2: MASTER SPREADSHEET UPLOAD ---
st.subheader("📊 Master Spreadsheet Importer")
uploaded_file = st.file_uploader("Upload Microsoft Forms Spreadsheet (.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        
        if 'Name1' not in df.columns:
            st.error("Invalid format. Could not find the 'Name1' column from Microsoft Forms.")
        else:
            st.success("File uploaded successfully! Running master extraction...")
            
            # 1. PROCESS AVAILABILITY & STAFF
            comments_col = [col for col in df.columns if 'Comments' in col][0]
            start_idx = df.columns.get_loc(comments_col) + 1
            performance_columns = df.columns[start_idx:]
            
            processed_availability = []
            staff_list = load_json(STAFF_FILE)
            existing_staff_names = [str(staff['name']).strip().lower() for staff in staff_list]
            new_staff_added = 0
            
            for index, row in df.iterrows():
                name = str(row['Name1']).strip()
                if not name or name == "nan":
                    continue
                    
                comments = str(row[comments_col]).strip() if pd.notna(row[comments_col]) else ""
                completion_time = str(row.get('Completion time', ''))
                
                available_shifts = []
                for col in performance_columns:
                    shift_id = " ".join(str(col).split())
                    if pd.notna(row[col]) and str(row[col]).strip().lower() == 'yes':
                        available_shifts.append(shift_id)
                
                processed_availability.append({
                    "employee": name,
                    "completion_time": completion_time,
                    "comments": comments,
                    "available_shifts": available_shifts,
                    "total_available": len(available_shifts)
                })
                
                if name.lower() not in existing_staff_names:
                    new_profile = {
                        "name": name,
                        "active": True,
                        "roles": ["Usher"],
                        "groups": [],
                        "preferred_shifts": 3,
                        "max_shifts": 5,
                        "double_allowed": True,
                        "venue_restrictions": ["ALH", "SGH", "Studio"],
                        "notes": "Auto-imported from Master Spreadsheet"
                    }
                    staff_list.append(new_profile)
                    existing_staff_names.append(name.lower())
                    new_staff_added += 1
            
            save_json(AVAILABILITY_FILE, processed_availability)
            if new_staff_added > 0:
                save_json(STAFF_FILE, staff_list)
            
            # 2. PROCESS SHOWS & ISOLATE CALL TIMES (WITH UNIQUE INDEXING)
            existing_shows = load_json(SHOWS_FILE)
            existing_show_ids = {s['id'] for s in existing_shows}
            new_shows_added = 0
            parsed_shows_preview = []
            
            for idx, col in enumerate(performance_columns):
                col_str = str(col)
                
                venue = "Alhambra"
                if "St George's Hall" in col_str or "St George’s Hall" in col_str:
                    venue = "St George's Hall"
                elif "Studio" in col_str or "The Studio" in col_str:
                    venue = "The Studio"
                
                all_times = re.findall(r'\b(0?[1-9]|1[0-2]|2[0-3]):([0-5][0-9])\b', col_str)
                
                curtain_time = "19:30:00"
                call_time = "18:45:00"
                
                call_match = re.search(r'Call\s*Time[^\d]*(\d{1,2}:\d{2})', col_str, re.IGNORECASE)
                if call_match:
                    call_time_extracted = call_match.group(1)
                    if len(call_time_extracted) == 5: call_time_extracted += ":00"
                    call_time = call_time_extracted
                
                valid_curtain_times = []
                for match in all_times:
                    t_str = f"{match[0].zfill(2)}:{match[1]}:00"
                    if t_str != call_time:
                        valid_curtain_times.append(t_str)
                
                if valid_curtain_times:
                    curtain_time = valid_curtain_times[0]
                
                date_match = re.search(r'([0-3]?[0-9])\s+(January|February|March|April|May|June|July|August|September|October|November|December)', col_str, re.IGNORECASE)
                show_date_str = "2026-04-01"
                if date_match:
                    day = date_match.group(1).zfill(2)
                    month_name = date_match.group(2)
                    try:
                        temp_dt = datetime.strptime(f"{day} {month_name} 2026", "%d %B %Y")
                        show_date_str = temp_dt.strftime("%Y-%m-%d")
                    except:
                        pass
                
                cleaned_name = col_str.split('\n')[0]
                cleaned_name = cleaned_name.replace("Alhambra", "").replace("St George's Hall", "").replace("The Studio", "")
                cleaned_name = re.sub(r'^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+[0-3]?[0-9]\s+\w+\s+(\d{1,2}:\d{2}\s*(&\s*\d{1,2}:\d{2})?)?', '', cleaned_name).strip()
                cleaned_name = re.sub(r'\b\d{1,2}:\d{2}\b', '', cleaned_name).strip()
                cleaned_name = cleaned_name.replace("–", "-").strip(' \t\n\r&')
                if not cleaned_name: cleaned_name = "Unknown Show"

                # Incorporate index `idx` to guarantee zero collisions for back-to-back shows
                show_id = f"col_{idx}_{show_date_str}_{cleaned_name.replace(' ', '')}_{curtain_time}"
                
                audience = 1150 if venue == "Alhambra" else 800
                req_sup = 1
                req_ush = 6 if venue == "Alhambra" else 4
                
                show_record = {
                    "id": show_id,
                    "show_name": cleaned_name,
                    "venue": venue,
                    "date": show_date_str,
                    "curtain_time": curtain_time,
                    "call_time": call_time,
                    "audience": audience,
                    "stalls_open": True,
                    "dc_open": True,
                    "uc_open": True,
                    "merch_req": True,
                    "kiosk_req": True,
                    "access_host": False,
                    "notes": f"Call Time: {call_time[:5]}",
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
                
                if show_id not in existing_show_ids:
                    existing_shows.append(show_record)
                    existing_show_ids.add(show_id)
                    new_shows_added += 1
            
            save_json(SHOWS_FILE, existing_shows)
            
            st.success("Master Import Complete!")
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Submissions Processed", len(processed_availability))
            c2.metric("New Staff Added", new_staff_added)
            c3.metric("Shows Extracted", len(parsed_shows_preview))
            c4.metric("New Shows Added", new_shows_added)
            
            st.subheader("Extracted Programme Preview")
            df_preview = pd.DataFrame(parsed_shows_preview)
            st.dataframe(df_preview[["date", "curtain_time", "call_time", "show_name", "venue"]], use_container_width=True, hide_index=True)
            
    except Exception as e:
        st.error(f"An error occurred while processing the master file: {e}")
else:
    st.write("### Currently Loaded Status")
    staff_count = len(load_json(STAFF_FILE))
    show_count = len(load_json(SHOWS_FILE))
    avail_count = len(load_json(AVAILABILITY_FILE))
    rota_count = len(load_json(ROTAS_FILE))
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Staff Database", staff_count)
    col2.metric("Scheduled Shows", show_count)
    col3.metric("Availability Entries", avail_count)
    col4.metric("Generated Rotas", rota_count)
