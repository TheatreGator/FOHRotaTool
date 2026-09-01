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
rotas_data = load_json("data/rotas.json")

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
        with st.spinner("Analyzing conflicts and scoring candidates..."):
            
            show_date_obj = datetime.strptime(selected_show['date'], "%Y-%m-%d")
            exact_date_str = show_date_obj.strftime("%d %B").lower() 
            clean_target_name = clean_string(selected_show['show_name'])
            
            # 1. Analyze existing rotas for Fairness & Conflicts
            shift_counts = {s['name']: 0 for s in staff_data}
            conflicting_staff = []
            
            for r in rotas_data:
                alloc = r.get('allocation', {})
                for role, people in alloc.items():
                    for person in people:
                        if person != "--- Unassigned ---" and person in shift_counts:
                            shift_counts[person] += 1
                
                if r['date'] == selected_show['date'] and r['show_id'] != selected_show['id']:
                    if r.get('curtain_time', '')[:5] == selected_show['curtain_time'][:5]:
                        for role, people in alloc.items():
                            conflicting_staff.extend([p for p in people if p != "--- Unassigned ---"])

            # 2. Build Available Candidates & Calculate First-Come Rank
            available_candidates = []
            
            # Sort the entire availability data by completion time to rank them chronologically
            def parse_time(dt_str):
                try:
                    return pd.to_datetime(dt_str)
                except:
                    return pd.Timestamp.max
            
            availability_sorted = sorted(availability_data, key=lambda x: parse_time(x.get('completion_time', '')))
            
            # Create a dictionary of submission ranks (1 = fastest, 2 = second fastest, etc.)
            submission_ranks = {person['employee']: rank for rank, person in enumerate(availability_sorted)}
            
            for person in availability_data:
                emp_name = person['employee']
                if emp_name in conflicting_staff:
                    continue
                    
                for shift_str in person['available_shifts']:
                    clean_shift = clean_string(shift_str)
                    if exact_date_str in clean_shift and clean_target_name in clean_shift:
                        if emp_name in staff_dict: 
                            available_candidates.append(emp_name)
                        break 
            
            if len(available_candidates) == 0:
                st.error("Found 0 available staff members for this shift.")
                st.stop()
            
            # 3. Allocation Engine
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
                        
                        # PREVIOUS FAIRNESS: Subtract 100 points for every shift they already have
                        score -= (shift_counts.get(candidate, 0) * 100)
                        
                        # NEW FIRST-COME FAIRNESS: Add up to 100 bonus points based on how early they submitted their form
                        rank = submission_ranks.get(candidate, 100)
                        score += (100 - rank) 
                        
                        # TRAINING
                        if role_name in profile.get('roles', []):
                            score += 500
                        else:
                            score -= 2000 
                            
                        # VENUE
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
            
            save_rota(selected_show['id'], selected_show['show_name'], selected_show['date'], allocation, remaining_candidates)
            
            st.success("Draft Generated! Staff were prioritized based on their Form submission time.")
            
            col_left, col_right = st.columns(2)
            
            with col_left:
                for role in ["Supervisor", "Merch", "Kiosk", "Access Host"]:
                    if reqs.get(role, 0) > 0:
                        st.write(f"**{role} ({len(allocation.get(role, []))}/{reqs[role]})**")
                        if allocation.get(role):
                            for name in allocation[role]:
                                rank_display = submission_ranks.get(name, 'N/A') + 1
                                st.write(f"- {name} *(Submission #{rank_display})*")
                        
                        shortfall = reqs[role] - len(allocation.get(role, []))
                        if shortfall > 0:
                            st.error(f"Missing {shortfall} {role}(s)")
                        st.write("")
                        
            with col_right:
                st.write(f"**Ushers ({len(allocation.get('Ushers', []))}/{reqs['Ushers']})**")
                if allocation.get('Ushers'):
                    for name in allocation['Ushers']:
                        rank_display = submission_ranks.get(name, 'N/A') + 1
                        st.write(f"- {name} *(Submission #{rank_display})*")
                
                usher_shortfall = reqs['Ushers'] - len(allocation.get('Ushers', []))
                if usher_shortfall > 0:
                    st.error(f"Missing {usher_shortfall} Usher(s)")
                    
            st.write("---")
            if conflicting_staff:
                with st.expander(f"Blocked by Conflicts ({len(conflicting_staff)})"):
                    st.write("These staff members were available but are already assigned to another show at this exact time:")
                    for name in set(conflicting_staff):
                        st.write(f"- {name}")
                        
            if remaining_candidates:
                with st.expander(f"Available Reserves ({len(remaining_candidates)})"):
                    for name in remaining_candidates:
                        rank_display = submission_ranks.get(name, 'N/A') + 1
                        st.write(f"- {name} *(Submission #{rank_display})*")
