import streamlit as st
import pandas as pd
import json
import os

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

col1, col2 = st.columns(2)

with col1:
    # Form to add a new show
    with st.expander("➕ Add New Performance", expanded=False):
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
            notes = st.text_input("Special Requirements", placeholder="e.g. Audio Described, Relaxed")

            submitted = st.form_submit_button("Calculate Staff & Save Show")

            if submitted and show_name:
                # Core Staffing Rules Engine
                req_supervisor = 1
                req_ushers = 0
                
                # Venue specific base rules
                if venue == "Alhambra":
                    if stalls_open: req_ushers += 4
                    if dc_open: req_ushers += 2
                    if uc_open: req_ushers += 2
                elif venue == "St George's Hall":
                    if stalls_open: req_ushers += 4
                    if dc_open: req_ushers += 2
                else: # Studio
                    req_ushers += 2
                    
                # Extra ushers driven by audience size (1 extra per 250 attendees over 500)
                if audience > 500:
                    extra_ushers = (audience - 500) // 250
                    req_ushers += int(extra_ushers)
                    
                # Specialized roles
                req_merch = 1 if merch_req else 0
                req_kiosk = 2 if kiosk_req else 0
                req_access = 1 if access_host else 0
                
                total_staff = req_supervisor + req_ushers + req_merch + req_kiosk + req_access

                # Create the show record
                new_show = {
                    "id": f"{show_date}_{show_name.replace(' ', '')}_{curtain_time}",
                    "show_name": show_name,
                    "venue": venue,
                    "date": str(show_date),
                    "curtain_time": str(curtain_time),
                    "audience": audience,
                    "requirements": {
                        "Supervisor": req_supervisor,
                        "Ushers": req_ushers,
                        "Merch": req_merch,
                        "Kiosk": req_kiosk,
                        "Access Host": req_access,
                        "Total": total_staff
                    },
                    "notes": notes
                }
                
                shows_list.append(new_show)
                save_shows(shows_list)
                st.success(f"{show_name} saved successfully!")
                st.rerun()

with col2:
    # Form to delete a show
    if shows_list:
        with st.expander("🗑️ Delete Performance", expanded=False):
            show_options = {s['id']: f"{s['date']} {s['curtain_time'][:5]} - {s['show_name']} ({s['venue']})" for s in shows_list}
            to_delete_id = st.selectbox("Select performance to remove", options=list(show_options.keys()), format_func=lambda x: show_options[x])
            
            if st.button("Delete Performance", type="primary"):
                shows_list = [s for s in shows_list if s["id"] != to_delete_id]
                save_shows(shows_list)
                st.success("Performance removed successfully!")
                st.rerun()

# Display current shows
if shows_list:
    st.write("---")
    st.subheader("Upcoming Programme & Requirements")
    
    # Flatten the dictionary structure for a clean pandas dataframe display
    display_data = []
    for s in shows_list:
        flat_record = {
            "Date": s["date"],
            "Time": s["curtain_time"][:5], # truncate seconds
            "Show": s["show_name"],
            "Venue": s["venue"],
            "Audience": s["audience"],
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
    
