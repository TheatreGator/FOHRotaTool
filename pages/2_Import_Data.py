import streamlit as st
import pandas as pd
import json
import os
import re
from datetime import datetime

st.set_page_config(page_title="Import & Data Management", layout="wide")
st.title("Data Management & Master Importer")
st.write("Upload your Microsoft Forms availability export and optional Staff Mastersheet to fine-tune profiles, roles, and shift constraints.")

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

# --- SECTION 2: MASTER AVAILABILITY & SHOWS UPLOAD ---
st.subheader("📊 Step 1: Upload Microsoft Forms Availability Spreadsheet")
uploaded_file = st.file_uploader("Upload Microsoft Forms Spreadsheet (.xlsx)", type=["xlsx"], key="avail_uploader")

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        
        if 'Name1' not in df.columns:
            st.error("Invalid format. Could not find the 'Name1' column from Microsoft Forms.")
        else:
            st.success("File uploaded successfully! Running master extraction...")
            
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
                        "notes": "Auto-imported from Availability Sheet"
                    }
                    staff_list.append(new_profile)
                    existing_staff_names.append(name.lower())
                    new_staff_added += 1
            
            save_json(AVAILABILITY_FILE, processed_availability)
            if new_staff_added > 0:
                save_json(STAFF_FILE, staff_list)
            
            # Process Shows
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
                
                call_time = "18:45:00"
                call_match = re.search(r'Call\s*Time[^\d]*(\d{1,2}:\d{2})', col_str, re.IGNORECASE)
                if call_match:
                    ct_str = call_match.group(1)
                    if len(ct_str) == 5: ct_str += ":00"
                    call_time = ct_str
                
                all_times = re.findall(r'(\d{1,2}:\d{2})', col_str)
                performance_times = []
                for t in all_times:
                    t_full = f"{t}:00" if len(t) == 5 else f"0{t}:00"
                    if t_full != call_time and "approx" not in col_str[col_str.find(t):]:
                        if t_full not in performance_times:
                            performance_times.append(t_full)
                
                if not performance_times:
                    performance_times = ["19:30:00"]
                
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

                audience = 1150 if venue == "Alhambra" else 800
                req_sup = 1
                req_ush = 6 if venue == "Alhambra" else 4
                
                for p_idx, curtain_time in enumerate(performance_times):
                    show_id = f"col_{idx}_p{p_idx}_{show_date_str}_{cleaned_name.replace(' ', '')}_{curtain_time}"
                    
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
            st.success(f"Processed {len(processed_availability)} availability submissions and extracted {len(parsed_shows_preview)} performances.")
            
    except Exception as e:
        st.error(f"An error occurred while processing the file: {e}")

st.write("---")

# --- SECTION 3: STAFF MASTERETHEET FINE-TUNING UPLOAD ---
st.subheader("⚙️ Step 2: Fine-Tune Staff Database with Mastersheet")
st.write("Upload your **Staff Mastersheet.xlsx** to update trained roles (Supervisor, Merch, Kiosk, Access Host), shift limits, double permissions, and reasonable adjustments.")

staff_master_file = st.file_uploader("Upload Staff Mastersheet (.xlsx)", type=["xlsx"], key="staff_master_uploader")

if staff_master_file is not None:
    try:
        master_df = pd.read_excel(staff_master_file)
        staff_list = load_json(STAFF_FILE)
        
        updated_count = 0
        for idx, row in master_df.iterrows():
            name_raw = row.get('Name')
            if pd.isna(name_raw):
                continue
            name = str(name_raw).strip()
            
            profile = next((s for s in staff_list if str(s.get('name', '')).strip().lower() == name.lower()), None)
            
            if not profile:
                profile = {
                    "name": name,
                    "active": True,
                    "roles": ["Usher"],
                    "groups": [],
                    "preferred_shifts": 3,
                    "max_shifts": 5,
                    "double_allowed": True,
                    "venue_restrictions": ["ALH", "SGH", "Studio"],
                    "notes": ""
                }
                staff_list.append(profile)
            
            # Extract Roles
            roles = ["Usher"]
            sup = str(row.get('Supervisor', '')).strip()
            merch = str(row.get('Merch', '')).strip()
            kiosk = str(row.get('Kiosk', '')).strip()
            access = str(row.get('Access Host', '')).strip()
            
            if "super" in sup.lower(): roles.append("Supervisor")
            if merch and merch.lower() not in ['no', 'no doesn\'t like', 'nan']: roles.append("Merch")
            if kiosk and kiosk.lower() not in ['no', 'no doesn\'t like', 'nan']: roles.append("Kiosk")
            if access and access.lower() not in ['no', 'no doesn\'t like', 'nan']: roles.append("Access Host")
            
            profile["roles"] = list(set(roles))
            
            # Extract Doubles Preference
            doubles = str(row.get('Rota Preference\nDoubles', '')).strip()
            profile["double_allowed"] = False if "no doubles" in doubles.lower() else True
            
            # Extract Shift Limits & Handle AMAP ("As Many As Possible")
            max_amt = str(row.get('Rota Preference\nMax amount', '')).strip().upper()
            if "AMAP" in max_amt:
                profile["max_shifts"] = 7
                profile["preferred_shifts"] = 5
            else:
                match = re.search(r'max\s*(\d+)', max_amt, re.IGNORECASE)
                if match:
                    val = int(match.group(1))
                    profile["max_shifts"] = val
                    profile["preferred_shifts"] = min(val, 3)
                elif "limited" in max_amt.lower() or "2" in max_amt:
                    profile["max_shifts"] = 2
                    profile["preferred_shifts"] = 2
                elif "3" in max_amt:
                    profile["max_shifts"] = 3
                    profile["preferred_shifts"] = 3
                elif "4" in max_amt:
                    profile["max_shifts"] = 4
                    profile["preferred_shifts"] = 3
                
            # Extract Adjustments & Notes
            notes_parts = []
            for col in ['No Lifting', 'No Selling', 'Levels / Other Notes', 'Rota Preference\nOther']:
                val = row.get(col)
                if pd.notna(val) and str(val).strip() and str(val).strip().lower() != 'nan':
                    notes_parts.append(str(val).strip())
            
            if notes_parts:
                profile["notes"] = " | ".join(notes_parts)
                
            updated_count += 1
            
        save_json(STAFF_FILE, staff_list)
        st.success(f"Successfully fine-tuned and updated **{updated_count}** staff profiles from the Mastersheet (AMAP processed as maximum capacity)!")
        
    except Exception as e:
        st.error(f"An error occurred while processing the Staff Mastersheet: {e}")

st.write("---")

# --- SECTION 4: CURRENT STATUS SUMMARY ---
st.subheader("📋 System Database Status")
staff_count = len(load_json(STAFF_FILE))
show_count = len(load_json(SHOWS_FILE))
avail_count = len(load_json(AVAILABILITY_FILE))
rota_count = len(load_json(ROTAS_FILE))

col1, col2, col3, col4 = st.columns(4)
col1.metric("Staff Database", staff_count)
col2.metric("Scheduled Shows", show_count)
col3.metric("Availability Entries", avail_count)
col4.metric("Generated Rotas", rota_count)
