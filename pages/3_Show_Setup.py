import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

st.set_page_config(page_title="Show Setup", layout="wide")
st.title("Show Setup & Staffing Calculator")
st.write("Define your programme and automatically calculate required staffing levels.")

SHOWS_FILE = "data/shows.json"

def load_shows():
    if not os.path.exists(SHOWS_FILE) or os.path.getsize(SHOWS_FILE) == 0:
        return []
    try:
        with open(SHOWS_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def save_shows(shows):
    if not os.path.exists("data"):
        os.makedirs("data")
    with open(SHOWS_FILE, "w") as f:
        json.dump(shows, f, indent=4)

shows_list = load_shows()

col1, col2, col3 = st.columns(3)

with col1:
    with st.expander("➕ Add Show", expanded=False):
        with st.form("add_show_form"):
            show_name = st.text_input("Show Name", placeholder="e.g. Blood Brothers")
            venue = st.selectbox("Venue", ["Alhambra", "St George's Hall", "The Studio"])
            show_date = st.date_input("Date")
            curtain_time = st.time_input("Curtain Time")
            
            audience = st.number_input("Expected Audience", min_value=0, max_value=2000, step=50, value=1150)
            stalls_open = st.checkbox("Stalls Open", value=True)
            dc_open = st.checkbox("Dress Circle Open", value=True)
            uc_open = st.checkbox("Upper Circle Open", value=True)
            
            merch_req = st.checkbox("Merch Staff Required", value=True)
            kiosk_req = st.checkbox("Kiosk Staff Required", value=True)
            access_host = st.checkbox("Access Host Required", value=False)
            notes = st.text_input("Special Requirements")
            priority_group = st.selectbox("Priority Staff Group", ["None", "Disney Merch", "VIP Hosts", "First Aiders"])

            submitted = st.form_submit_button("Save Show")

            if submitted and show_name:
                req_supervisor = 1
                req_ushers = 0
                
                if venue == "Alhambra":
                    if stalls_open: req_ushers += 4
                    if dc_open: req_ushers += 2
                    if uc_open: req_ushers += 2
                elif venue == "St George's Hall":
                    if stalls_open: req_ushers += 4
                    if dc_open: req_ushers += 2
                else: 
                    req_ushers += 2
                    
                if audience > 500:
                    req_ushers += int((audience - 500) // 250)
                    
                total_staff = req_supervisor + req_ushers + (1 if merch_req else 0) + (2 if kiosk_req else 0) + (1 if access_host else 0)

                new_show = {
                    "id": f"{show_date}_{show_name.replace(' ', '')}_{curtain_time}",
                    "show_name": show_name,
                    "venue": venue,
                    "date": str(show_date),
                    "curtain_time": str(curtain_time),
                    "audience": audience,
                    "stalls_open": stalls_open,
                    "dc_open": dc_open,
                    "uc_open": uc_open,
                    "merch_req": merch_req,
                    "kiosk_req": kiosk_req,
                    "access_host": access_host,
                    "notes": notes,
                    "priority_group": priority_group,
                    "requirements": {
                        "Supervisor": req_supervisor,
                        "Ushers": req_ushers,
                        "Merch": 1 if merch_req else 0,
                        "Kiosk": 2 if kiosk_req else 0,
                        "Access Host": 1 if access_host else 0,
                        "Total": total_staff
                    }
                }
                
                shows_list.append(new_show)
                save_shows(shows_list)
                st.success(f"{show_name} saved successfully!")
                st.rerun()

with col2:
    if shows_list:
        with st.expander("✏️ Edit Show", expanded=False):
            show_options = {s['id']: f"{s['date']} {s['curtain_time'][:5]} - {s['show_name']} ({s['venue']})" for s in shows_list}
            edit_target_id = st.selectbox("Select show to edit", options=list(show_options.keys()), format_func=lambda x: show_options[x])
            edit_target = next((s for s in shows_list if s["id"] == edit_target_id), None)
            
            if edit_target:
                with st.form("edit_show_form"):
                    e_name = st.text_input("Show Name", value=edit_target.get("show_name", ""))
                    
                    venue_options = ["Alhambra", "St George's Hall", "The Studio"]
                    current_venue_idx = venue_options.index(edit_target.get("venue", "Alhambra")) if edit_target.get("venue") in venue_options else 0
                    e_venue = st.selectbox("Venue", venue_options, index=current_venue_idx)
                    
                    current_date = datetime.strptime(edit_target["date"], "%Y-%m-%d").date() if "date" in edit_target else datetime.today().date()
                    current_time = datetime.strptime(edit_target["curtain_time"], "%H:%M:%S").time() if "curtain_time" in edit_target else datetime.now().time()
                    
                    e_date = st.date_input("Date", value=current_date)
                    e_time = st.time_input("Curtain Time", value=current_time)
                    
                    e_audience = st.number_input("Expected Audience", min_value=0, max_value=2000, step=50, value=edit_target.get("audience", 1150))
                    
                    e_stalls = st.checkbox("Stalls Open", value=edit_target.get("stalls_open", True))
                    e_dc = st.checkbox("Dress Circle Open", value=edit_target.get("dc_open", True))
                    e_uc = st.checkbox("Upper Circle Open", value=edit_target.get("uc_open", True))
                    e_merch = st.checkbox("Merch Staff Required", value=edit_target.get("merch_req", True))
                    e_kiosk = st.checkbox("Kiosk Staff Required", value=edit_target.get("kiosk_req", True))
                    e_access = st.checkbox("Access Host Required", value=edit_target.get("access_host", False))
                    e_notes = st.text_input("Special Requirements", value=edit_target.get("notes", ""))
                    
                    p_options = ["None", "Disney Merch", "VIP Hosts", "First Aiders"]
                    current_p_idx = p_options.index(edit_target.get("priority_group", "None")) if edit_target.get("priority_group") in p_options else 0
                    e_priority = st.selectbox("Priority Staff Group", p_options, index=current_p_idx)
                    
                    update_show_submitted = st.form_submit_button("Recalculate & Update Show")
                    
                    if update_show_submitted:
                        req_sup = 1
                        req_ush = 0
                        
                        if e_venue == "Alhambra":
                            if e_stalls: req_ush += 4
                            if e_dc: req_ush += 2
                            if e_uc: req_ush += 2
                        elif e_venue == "St George's Hall":
                            if e_stalls: req_ush += 4
                            if e_dc: req_ush += 2
                        else: 
                            req_ush += 2
                            
                        if e_audience > 500:
                            req_ush += int((e_audience - 500) // 250)
                            
                        t_staff = req_sup + req_ush + (1 if e_merch else 0) + (2 if e_kiosk else 0) + (1 if e_access else 0)
                        
                        edit_target.update({
                            "show_name": e_name,
                            "venue": e_venue,
                            "date": str(e_date),
                            "curtain_time": str(e_time),
                            "audience": e_audience,
                            "stalls_open": e_stalls,
                            "dc_open": e_dc,
                            "uc_open": e_uc,
                            "merch_req": e_merch,
                            "kiosk_req": e_kiosk,
                            "access_host": e_access,
                            "notes": e_notes,
                            "priority_group": e_priority,
                            "requirements": {
                                "Supervisor": req_sup,
                                "Ushers": req_ush,
                                "Merch": 1 if e_merch else 0,
                                "Kiosk": 2 if e_kiosk else 0,
                                "Access Host": 1 if e_access else 0,
                                "Total": t_staff
                            }
                        })
                        
                        save_shows(shows_list)
                        st.success(f"{e_name} updated successfully!")
                        st.rerun()

with col3:
    if shows_list:
        with st.expander("🗑️ Delete Show", expanded=False):
            to_delete_id = st.selectbox("Select show to remove", options=list(show_options.keys()), format_func=lambda x: show_options[x])
            
            if st.button("Delete Performance", type="primary"):
                shows_list = [s for s in shows_list if s["id"] != to_delete_id]
                save_shows(shows_list)
                st.success("Performance removed successfully!")
                st.rerun()

if shows_list:
    st.write("---")
    st.subheader("Upcoming Programme & Requirements")
    
    display_data = []
    for s in shows_list:
        flat_record = {
            "Date": s["date"],
            "Time": s["curtain_time"][:5], 
            "Show": s["show_name"],
            "Venue": s["venue"],
            "Priority Group": s.get("priority_group", "None"),
            "Supervisor": s["requirements"]["Supervisor"],
            "Ushers": s["requirements"]["Ushers"],
            "Kiosk": s["requirements"]["Kiosk"],
            "Merch": s["requirements"]["Merch"],
            "Total Required": s["requirements"]["Total"]
        }
        display_data.append(flat_record)
        
    df = pd.DataFrame(display_data)
    df = df.sort_values(by=["Date", "Time"])
    
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("No shows found. Add a performance above to generate staffing requirements.")
