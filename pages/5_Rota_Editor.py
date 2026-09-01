import streamlit as st
import json
import os

st.set_page_config(page_title="Rota Editor", layout="wide")
st.title("Rota Editor")
st.write("Manually adjust shift allocations before finalizing.")

def load_json(filepath):
    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
        return []
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def save_rotas(rotas_list):
    with open("data/rotas.json", "w") as f:
        json.dump(rotas_list, f, indent=4)

rotas_data = load_json("data/rotas.json")

if not rotas_data:
    st.info("No draft rotas found. Generate a rota first in the 'Generate Rota' module.")
    st.stop()

# Select which draft to edit
rota_options = {r['show_id']: f"{r['date']} - {r['show_name']} ({r['status']})" for r in rotas_data}
selected_rota_id = st.selectbox("Select Rota to Edit", options=list(rota_options.keys()), format_func=lambda x: rota_options[x])

selected_rota_index = next((index for (index, r) in enumerate(rotas_data) if r["show_id"] == selected_rota_id), None)
current_rota = rotas_data[selected_rota_index]

st.write("---")
st.subheader(f"Editing: {current_rota['show_name']}")

# Combine currently assigned staff and reserves into a single pool of options for the dropdowns
allocation = current_rota['allocation']
reserves = current_rota.get('reserves', [])

# Flatten all currently assigned staff to build the master options list
all_assigned = []
for role, staff_list in allocation.items():
    all_assigned.extend(staff_list)

available_options = ["--- Unassigned ---"] + sorted(all_assigned + reserves)

# Helper function to generate dropdowns
def role_editor(role_name, assigned_list):
    st.write(f"**{role_name}**")
    new_assigned = []
    
    # Show existing assignments
    for i in range(max(len(assigned_list), 1)):
        current_val = assigned_list[i] if i < len(assigned_list) else "--- Unassigned ---"
        selected = st.selectbox(
            f"{role_name} Slot {i+1}", 
            options=available_options, 
            index=available_options.index(current_val) if current_val in available_options else 0,
            key=f"{selected_rota_id}_{role_name}_{i}"
        )
        if selected != "--- Unassigned ---":
            new_assigned.append(selected)
            
    # Option to add an extra person to this role (e.g. adding an extra usher manually)
    extra = st.selectbox(f"+ Add extra {role_name}", options=available_options, key=f"{selected_rota_id}_{role_name}_extra")
    if extra != "--- Unassigned ---":
        new_assigned.append(extra)
        
    return new_assigned

with st.form("edit_rota_form"):
    col1, col2 = st.columns(2)
    
    updated_allocation = {}
    
    with col1:
        updated_allocation["Supervisor"] = role_editor("Supervisor", allocation.get("Supervisor", []))
        st.write("---")
        updated_allocation["Kiosk"] = role_editor("Kiosk", allocation.get("Kiosk", []))
        st.write("---")
        updated_allocation["Merch"] = role_editor("Merch", allocation.get("Merch", []))
        st.write("---")
        updated_allocation["Access Host"] = role_editor("Access Host", allocation.get("Access Host", []))
        
    with col2:
        updated_allocation["Ushers"] = role_editor("Ushers", allocation.get("Ushers", []))

    st.write("---")
    submitted = st.form_submit_button("💾 Save Changes", type="primary")

    if submitted:
        # Recalculate reserves (anyone in the original pool who isn't currently assigned)
        new_assigned_flat = []
        for role, staff_list in updated_allocation.items():
            new_assigned_flat.extend(staff_list)
            
        new_reserves = [staff for staff in (all_assigned + reserves) if staff not in new_assigned_flat]
        
        # Update the master data
        rotas_data[selected_rota_index]["allocation"] = updated_allocation
        rotas_data[selected_rota_index]["reserves"] = list(set(new_reserves)) # Remove duplicates
        
        save_rotas(rotas_data)
        st.success("Rota updated successfully!")
        st.rerun()

st.write("### Current Reserves")
if current_rota.get('reserves'):
    st.write(", ".join(current_rota['reserves']))
else:
    st.info("No reserve staff available for this shift.")
