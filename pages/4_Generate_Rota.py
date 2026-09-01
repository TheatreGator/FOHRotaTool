import streamlit as st
import pandas as pd
import json
import os
import re
from datetime import datetime, timedelta

st.set_page_config(page_title="Generate Weekly Rota", layout="wide")
st.title("Weekly Rota Generator")
st.write("Batch allocate staff for performances based on availability and venue rules.")

def load_json(filepath):
    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
        return []
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def save_rotas(new_rotas):
    rotas_file = "data/rotas.json"
    existing_rotas = load_json(rotas_file)
    
    new_show_ids = [r['show_id'] for r in new_rotas]
    filtered_rotas = [r for r in existing_rotas if r['show_id'] not in new_show_ids]
    
    filtered_rotas.extend(new_rotas)
    
    with open(rotas_file, "w") as f:
        json.dump(filtered_rotas, f, indent=4)

staff_data = load_json("data/staff.json")
availability_data = load_json("data/availability.json")
shows_data = load_json("data/shows.json")
rotas_data = load_json("data/rotas.json")
commitments_data = load_json("data/commitments.json")

if not shows_data:
    st.warning("No shows found. Please import your master spreadsheet first.")
    st.stop()
if not staff_data or not availability_data:
    st.warning("Please ensure Staff and Availability data are loaded.")
    st.stop()

staff_dict = {s['name']: s for s in staff_data}

def clean_string(text):
    text = re.sub(r'[^\w\s]', '', str(text).lower())
    return " ".join(text.split())

# Sort all shows chronologically by default
shows_data.sort(key=lambda x: (x['date'], x['curtain_time']))

st.write("### 1. Select Scheduling Scope")
selection_mode = st.radio("Choose selection method:", ["By Date Range", "Select All Loaded Shows (" + str(len(shows_data)) + " total)"])

shows_in_batch = []

if selection_mode == "By Date Range":
    col1, col2 = st.columns(2)
    min_date = datetime.strptime(shows_data[0]['date'], "%Y-%m-%d").date()
    max_date = datetime.strptime(shows_data[-1]['date'], "%Y-%m-%d").date()
    
    with col1:
        start_date = st.date_input("Start Date", value=min_date, min_value=min_date, max_value=max_date)
    with col2:
        end_date = st.date_input("End Date", value=max_date, min_value=min_date, max_value=max_date)
        
    shows_in_batch = [
        s for s in shows_data 
        if start_date <= datetime.strptime(s['date'], "%Y-%m-%d").date() <= end_date
    ]
else:
    shows_in_batch = shows_data

if not shows_in_batch:
    st.info("No shows found in the selected range.")
    st.stop()

st.write("---")
st.write(f"### 2. Shows Included in this Batch ({len(shows_in_batch)})")

with st.expander("🔍 View Selected Shows List"):
    for s in shows_in_batch:
        st.write(f"- {s['date']} {s['curtain_time'][:5]} | **{s['show_name']}** ({s['venue']})")

if st.button("🪄 Generate Batch Allocation", type="primary"):
    with st.spinner("Processing batch allocation..."):
        
        def parse_time(dt_str):
            try: return pd.to_datetime(dt_str)
            except: return pd.Timestamp.max
        
        availability_sorted = sorted(availability_data, key=lambda x: parse_time(x.get('completion_time', '')))
        submission_ranks = {person['employee']: rank for rank, person in enumerate(availability_sorted)}
        
        weekly_shift_counts = {s['name']: 0 for s in staff_data}
        
        for r in rotas_data:
            if r['show_id'] not in [s['id'] for s in shows_in_batch]:
                for role, people in r.get('allocation', {}).items():
                    for person in people:
                        if person != "--- Unassigned ---" and person in weekly_shift_counts:
                            weekly_shift_counts[person] += 1
                            
        generated_rotas = []
        
        for show in shows_in_batch:
            show_date_obj = datetime.strptime(show['date'], "%Y-%m-%d")
            exact_date_str = show_date_obj.strftime("%d %B").lower() 
            clean_target_name = clean_string(show['show_name'])
            reqs = show['requirements']
            
            conflicting_staff = []
            
            for existing_draft in generated_rotas:
                if existing_draft['date'] == show['date'] and existing_draft['curtain_time'][:5] == show['curtain_time'][:5]:
                    for role, people in existing_draft['allocation'].items():
                        conflicting_staff.extend([p for p in people if p != "--- Unassigned ---"])
                        
            for c in commitments_data:
                if c['date'] == show['date']:
                    conflicting_staff.append(c['name'])
            
            available_candidates = []
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
                        
                        score -= (weekly_shift_counts.get(candidate, 0) * 100)
                        
                        rank = submission_ranks.get(candidate, 100)
                        score += (100 - rank) 
                        
                        if role_name in profile.get('roles', []): score += 500
                        else: score -= 2000 
                            
                        venue_short = "ALH" if show['venue'] == "Alhambra" else "SGH" if show['venue'] == "St George's Hall" else "Studio"
                        if venue_short not in profile.get('venue_restrictions', []):
                            score -= 3000 
                            
                        priority = show.get('priority_group', 'None')
                        if priority != "None" and priority in profile.get('groups', []):
                            score += 1500
                            
                        if score > best_score:
                            best_score = score
                            best_candidate = candidate
                            
                    if best_candidate and best_score > 0:
                        assigned.append(best_candidate)
                        staff_pool.remove(best_candidate)
                        weekly_shift_counts[best_candidate] += 1 
                        
                return assigned

            allocation["Supervisor"] = allocate_role("Supervisor", reqs['Supervisor'], remaining_candidates)
            allocation["Merch"] = allocate_role("Merch", reqs['Merch'], remaining_candidates)
            allocation["Kiosk"] = allocate_role("Kiosk", reqs['Kiosk'], remaining_candidates)
            if reqs.get("Access Host", 0) > 0:
                allocation["Access Host"] = allocate_role("Access Host", reqs['Access Host'], remaining_candidates)
            allocation["Ushers"] = allocate_role("Usher", reqs['Ushers'], remaining_candidates)
            
            generated_rotas.append({
                "show_id": show['id'],
                "show_name": show['show_name'],
                "venue": show['venue'],
                "date": show['date'],
                "curtain_time": show['curtain_time'],
                "allocation": allocation,
                "reserves": remaining_candidates,
                "status": "Draft"
            })

        save_rotas(generated_rotas)
        st.success(f"Successfully generated rotas for {len(generated_rotas)} shows!")
        
        st.write("### 3. Allocation Results")
        for draft in generated_rotas:
            with st.expander(f"{draft['date']} {draft['curtain_time'][:5]} - {draft['show_name']} ({draft['venue']})", expanded=False):
                alloc = draft['allocation']
                reqs = next(s['requirements'] for s in shows_in_batch if s['id'] == draft['show_id'])
                
                c1, c2 = st.columns(2)
                with c1:
                    for role in ["Supervisor", "Merch", "Kiosk", "Access Host"]:
                        if reqs.get(role, 0) > 0:
                            st.write(f"**{role} ({len(alloc.get(role, []))}/{reqs[role]})**")
                            for name in alloc.get(role, []):
                                st.write(f"- {name}")
                            shortfall = reqs[role] - len(alloc.get(role, []))
                            if shortfall > 0: st.error(f"Missing {shortfall} {role}(s)")
                            st.write("")
                with c2:
                    st.write(f"**Ushers ({len(alloc.get('Ushers', []))}/{reqs['Ushers']})**")
                    for name in alloc.get('Ushers', []):
                        st.write(f"- {name}")
                    usher_shortfall = reqs['Ushers'] - len(alloc.get('Ushers', []))
                    if usher_shortfall > 0: st.error(f"Missing {usher_shortfall} Usher(s)")
