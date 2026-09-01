import streamlit as st
import pandas as pd
import json
import os

st.set_page_config(page_title="Fairness Dashboard", layout="wide")
st.title("Fairness & Analytics Dashboard")
st.write("Track staff shift allocations against their availability requests.")

def load_json(filepath):
    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
        return []
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except:
        return []

staff_data = load_json("data/staff.json")
availability_data = load_json("data/availability.json")
rotas_data = load_json("data/rotas.json")

if not staff_data:
    st.warning("No staff data found.")
    st.stop()

# Calculate stats
stats = []
for profile in staff_data:
    name = profile['name']
    
    # 1. How many shifts did they say they were available for?
    avail_record = next((a for a in availability_data if a['employee'] == name), None)
    total_available = avail_record['total_available'] if avail_record else 0
    
    # 2. How many shifts have they actually been assigned?
    assigned_shifts = 0
    roles_breakdown = {"Supervisor": 0, "Ushers": 0, "Merch": 0, "Kiosk": 0, "Access Host": 0}
    
    for r in rotas_data:
        alloc = r.get('allocation', {})
        for role, people in alloc.items():
            if name in people:
                assigned_shifts += 1
                if role in roles_breakdown:
                    roles_breakdown[role] += 1
                    
    # Calculate success ratio
    ratio = f"{int((assigned_shifts / total_available) * 100)}%" if total_available > 0 else "N/A"
    
    stats.append({
        "Name": name,
        "Target Weekly Shifts": profile.get('preferred_shifts', 0),
        "Total Available (Requested)": total_available,
        "Total Assigned": assigned_shifts,
        "Fulfillment Ratio": ratio,
        "Supervisor Shifts": roles_breakdown["Supervisor"],
        "Usher Shifts": roles_breakdown["Ushers"],
        "Merch Shifts": roles_breakdown["Merch"],
        "Kiosk Shifts": roles_breakdown["Kiosk"]
    })

df = pd.DataFrame(stats)

# Top level metrics
total_assigned = df["Total Assigned"].sum()
st.metric("Total Shifts Assigned Across Team", total_assigned)

st.write("---")
st.subheader("Individual Staff Analytics")
st.dataframe(df, use_container_width=True, hide_index=True)
