import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

st.set_page_config(page_title="Generate Rota", layout="wide")
st.title("Draft Rota Generator")
st.write("Allocate staff to performances based on availability, training, and venue rules.")

def load_json(filepath):
    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
        return []
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

staff_data = load_json("data/staff.json")
availability_data = load_json("data/availability.json")
shows_data = load_json("data/shows.json")

if not shows_data:
    st.warning("No shows found. Please add a performance in the Show Setup module first.")
    st.stop()
if not staff_data or not availability_data:
    st.warning("Please ensure Staff and Availability data are loaded before generating rotas.")
    st.stop()

# Create a fast-lookup dictionary for staff profiles
staff_dict = {s['name']: s for s in staff_data}

# Select a show
show_options = {s['id']: f"{s['date']} {s['curtain_time'][:5]} - {s['show_name']} ({s['venue']})" for s in shows_data}
selected_show_id = st.selectbox("Select Performance to Schedule", options=list(show_options.keys()), format_func=lambda x: show_options[x])
selected_show = next((s for s in shows_data if s['id'] == selected_show_id), None)

if selected_show:
    st.write("---")
    st.write(f"### Required Staffing: {selected_show['show_name']}")
    reqs = selected_show['requirements']
    
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Supervisor", reqs['Supervisor'])
    col2.metric("Ushers", reqs['Ushers'])
    col3.metric("Kiosk", reqs['Kiosk'])
    col4.metric("Merch", reqs['Merch'])
    col5.metric("Access Host", reqs.get('Access Host', 0))

    if st.button("🪄 Generate Draft Allocation", type="primary"):
        with st.spinner("Scoring candidates..."):
            
            # 1. Match messy MS Forms availability strings to this specific show date/name
            show_date_obj = datetime.strptime(selected_show['date'], "%Y-%m-%d")
            day_str = show_date_obj.strftime("%d").lstrip("0") # e.g. "28" or "1"
            month_str = show_date_obj.strftime("%B").lower() # e.g. "april"
            show_name_lower = selected_show['show_name'].lower()
            
            available_candidates = []
            for person in availability_data:
                for shift_str in person['available_shifts']:
                    shift_lower = shift_str.lower()
                    # Basic matching: check if day, month, and show name exist in the availability string
                    if day_str in shift_lower and month_str in shift_lower and show_name_lower in shift_lower:
                        if person['employee'] in staff_dict: # Ensure they exist in the database
                            available_candidates.append(person['employee'])
                        break 
            
            st.info(f"**Found {len(available_candidates)} available staff members for this shift.**")
            
            # 2. Allocation Engine (Scoring System)
            allocation = {"Supervisor": [], "Merch": [], "Kiosk": [], "Access Host": [], "Ushers": []}
            remaining_candidates = available_candidates.copy()
            
            def allocate_role(role_name, required_count, staff_pool):
                assigned = []
                for _ in range(required_count):
                    best_candidate = None
                    best_score = -9999
                    
                    for candidate in staff_pool:
                        profile = staff_dict[candidate]
                        score = 1000 # Base score: They are available
                        
                        # Bonus: Trained in the role
                        if role_name in profile.get('roles', []):
                            score += 500
                        else:
                            score -= 2000 # Penalty: Untrained
                            
                        # Penalty: Venue Restriction
                        venue_short = "ALH" if selected_show['venue'] == "Alhambra" else "SGH" if selected_show['venue'] == "St George's Hall" else "Studio"
                        if venue_short not in profile.get('venue_restrictions', []):
                            score -= 3000 # Penalty: Cannot work this venue
                            
                        if score > best_score:
                            best_score = score
                            best_candidate = candidate
                            
                    # Only assign if they meet the absolute minimum requirements (score > 0)
                    if best_candidate and best_score > 0:
                        assigned.append(best_candidate)
                        staff_pool.remove(best_candidate)
                        
                return assigned

            # Allocate specialized roles first, ushers last
            allocation["Supervisor"] = allocate_role("Supervisor", reqs['Supervisor'], remaining_candidates)
            allocation["Merch"] = allocate_role("Merch", reqs['Merch'], remaining_candidates)
            allocation["Kiosk"] = allocate_role("Kiosk", reqs['Kiosk'], remaining_candidates)
            if reqs.get("Access Host", 0) > 0:
                allocation["Access Host"] = allocate_role("Access Host", reqs['Access Host'], remaining_candidates)
            
            allocation["Ushers"] = allocate_role("Usher", reqs['Ushers'], remaining_candidates)
            
            # 3. Output Results
            st.success("Draft Generated!")
            
            col_left, col_right = st.columns(2)
            
            with col_left:
                for role in ["Supervisor", "Merch", "Kiosk", "Access Host"]:
                    if reqs.get(role, 0) > 0:
                        st.write(f"**{role} ({len(allocation[role])}/{reqs[role]})**")
                        if allocation[role]:
                            for name in allocation[role]:
                                st.write(f"- {name}")
                        else:
                            st.error(f"Missing {role}")
                        st.write("")
                        
            with col_right:
                st.write(f"**Ushers ({len(allocation['Ushers'])}/{reqs['Ushers']})**")
                if allocation['Ushers']:
                    for name in allocation['Ushers']:
                        st.write(f"- {name}")
                else:
                    st.error("Missing Ushers")
            
            st.write("---")
            if remaining_candidates:
                with st.expander(f"Available Reserves ({len(remaining_candidates)})"):
                    for name in remaining_candidates:
                        st.write(f"- {name}")
