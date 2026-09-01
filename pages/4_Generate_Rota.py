import streamlit as st
import pandas as pd
import json
import os
import re
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

def save_rota(show_id, show_name, date, allocation, reserves):
    rotas_file = "data/rotas.json"
    rotas = load_json(rotas_file)
    
    # Remove older drafts of this same show to avoid duplicates
    rotas = [r for r in rotas if r['show_id'] != show_id]
    
    new_rota = {
        "show_id": show_id,
        "show_name": show_name,
        "date": date,
        "allocation": allocation,
        "reserves": reserves,
        "status": "Draft"
    }
    rotas.append(new_rota)
    
    with open(rotas_file, "w") as f:
        json.dump(rotas, f, indent=4)

staff_data = load_json("data/staff.json")
availability_data = load_json("data/availability.json")
shows_data = load_json("data/shows.json")

if not shows_data:
    st.warning("No shows found. Please add a performance in the Show Setup module first.")
    st.stop()
if not staff_data or not availability_data:
    st.warning("Please ensure Staff and Availability data are loaded before generating rotas.")
    st.stop()

staff_dict = {s['name']: s for s in staff_data}

show_options = {s['id']: f"{s['date']} {s['curtain_time'][:5]} - {s['show_name']} ({s['venue']})" for s in shows_data}
selected_show_id = st.selectbox("Select Performance to Schedule", options=list(show_options.keys()), format_func=lambda x: show_options[x])
selected_show = next((s for s in shows_data if s['id'] == selected_show_id), None)

def clean_string(text):
    text = re.sub(r'[^\w\s]', '', str(text).lower())
    return " ".join(text.split())

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
            
            show_date_obj = datetime.strptime(selected_show['date'], "%Y-%m-%d")
            exact_date_str = show_date_obj.strftime("%d %B").lower() 
            clean_target_name = clean_string(selected_show['show_name'])
            
            available_candidates = []
            debug_log = []
            
            for person in availability_data:
                for shift_str in person['available_shifts']:
                    clean_shift = clean_string(shift_str)
                    
                    if exact_date_str in clean_shift and clean_target_name in clean_shift:
                        if person['employee'] in staff_dict: 
                            available_candidates.append(person['employee'])
                        else:
                            debug_log.append(f"⚠️ Found {person['employee']} in availability, but they are MISSING from the Staff Database!")
                        break 
            
            if len(available_candidates) == 0:
                st.error("Found 0 available staff members for this shift.")
                st.info(f"**Troubleshooting:** The system searched your availability spreadsheet for any shifts containing: \n\n`{exact_date_str}` AND `{clean_target_name}`")
                if debug_log:
                    for log in debug_log:
                        st.warning(log)
                st.stop()
            else:
                st.info(f"**Found {len(available_candidates)} available staff members for this shift.**")
                if debug_log:
                    with st.expander("Database Warnings"):
                        for log in debug_log:
                            st.write(log)
            
            # Allocation Engine
            allocation = {"Supervisor": [], "Merch": [], "Kiosk": [], "Access Host": [], "Ushers": []}
            remaining_candidates = available_candidates.copy()
            
            def allocate_role(role_name, required_count, staff_pool):
                assigned = []
                for _ in range(required_count):
                    best_candidate = None
                    best_score = -9999
                    
                    for candidate in staff_pool:
                        profile = staff_dict[candidate]
                        score = 1000 
                        
                        if role_name in profile.get('roles', []):
                            score += 500
                        else:
                            score -= 2000 
                            
                        venue_short = "ALH" if selected_show['venue'] == "Alhambra" else "SGH" if selected_show['venue'] == "St George's Hall" else "Studio"
                        if venue_short not in profile.get('venue_restrictions', []):
                            score -= 3000 
                            
                        if score > best_score:
                            best_score = score
                            best_candidate = candidate
                            
                    if best_candidate and best_score > 0:
                        assigned.append(best_candidate)
                        staff_pool.remove(best_candidate)
                        
                return assigned

            allocation["Supervisor"] = allocate_role("Supervisor", reqs['Supervisor'], remaining_candidates)
            allocation["Merch"] = allocate_role("Merch", reqs['Merch'], remaining_candidates)
            allocation["Kiosk"] = allocate_role("Kiosk", reqs['Kiosk'], remaining_candidates)
            if reqs.get("Access Host", 0) > 0:
                allocation["Access Host"] = allocate_role("Access Host", reqs['Access Host'], remaining_candidates)
            
            allocation["Ushers"] = allocate_role("Usher", reqs['Ushers'], remaining_candidates)
            
            # Save the draft
            save_rota(selected_show['id'], selected_show['show_name'], selected_show['date'], allocation, remaining_candidates)
            
            st.success("Draft Generated and Saved! Head to the Rota Editor to make manual tweaks.")
            
            col_left, col_right = st.columns(2)
            
            with col_left:
                for role in ["Supervisor", "Merch", "Kiosk", "Access Host"]:
                    if reqs.get(role, 0) > 0:
                        st.write(f"**{role} ({len(allocation.get(role, []))}/{reqs[role]})**")
                        if allocation.get(role):
                            for name in allocation[role]:
                                st.write(f"- {name}")
                        
                        # Check if we are short on staff for this role
                        shortfall = reqs[role] - len(allocation.get(role, []))
                        if shortfall > 0:
                            st.error(f"Missing {shortfall} {role}(s) - Check reserves or staff training")
                        st.write("")
                        
            with col_right:
                st.write(f"**Ushers ({len(allocation.get('Ushers', []))}/{reqs['Ushers']})**")
                if allocation.get('Ushers'):
                    for name in allocation['Ushers']:
                        st.write(f"- {name}")
                
                # Check if we are short on ushers
                usher_shortfall = reqs['Ushers'] - len(allocation.get('Ushers', []))
                if usher_shortfall > 0:
                    st.error(f"Missing {usher_shortfall} Usher(s) - Not enough available staff")
                    
            st.write("---")
            if remaining_candidates:
                with st.expander(f"Available Reserves ({len(remaining_candidates)})"):
                    for name in remaining_candidates:
                        st.write(f"- {name}")
