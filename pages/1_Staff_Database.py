import streamlit as st
import pandas as pd
from services.storage import load_staff, save_staff

st.set_page_config(page_title="Staff Database", layout="wide")
st.title("Staff Database")

# Load existing data
staff_list = load_staff()

col1, col2, col3 = st.columns(3)

with col1:
    # Form to add new staff
    with st.expander("➕ Add Staff", expanded=False):
        with st.form("add_staff_form"):
            name = st.text_input("Full Name")
            active = st.checkbox("Active Employee", value=True)
            roles = st.multiselect("Trained Roles", 
                                   ["Usher", "Supervisor", "Kiosk", "Merch", "Access Host", "Laidler"])
            venues = st.multiselect("Venue Restrictions", 
                                    ["ALH", "SGH", "Studio"], default=["ALH", "SGH", "Studio"])
            
            pref_shifts = st.number_input("Preferred Weekly Shifts", min_value=0, max_value=7, value=3)
            max_shifts = st.number_input("Maximum Weekly Shifts", min_value=0, max_value=7, value=5)
            allow_doubles = st.checkbox("Can work doubles?", value=True)
            notes = st.text_area("Notes", placeholder="e.g., Stalls only, no stairs...")
                
            submitted = st.form_submit_button("Save Profile")
            
            if submitted and name:
                new_staff = {
                    "name": name,
                    "active": active,
                    "roles": roles,
                    "preferred_shifts": pref_shifts,
                    "max_shifts": max_shifts,
                    "double_allowed": allow_doubles,
                    "venue_restrictions": venues,
                    "notes": notes
                }
                staff_list.append(new_staff)
                save_staff(staff_list)
                st.success(f"{name} added successfully!")
                st.rerun()

with col2:
    # Form to edit staff
    if staff_list:
        with st.expander("✏️ Edit Staff", expanded=False):
            staff_names = [s["name"] for s in staff_list]
            edit_target_name = st.selectbox("Select staff to edit", staff_names)
            edit_target = next((s for s in staff_list if s["name"] == edit_target_name), None)
            
            if edit_target:
                with st.form("edit_staff_form"):
                    e_name = st.text_input("Full Name", value=edit_target.get("name", ""))
                    e_active = st.checkbox("Active Employee", value=edit_target.get("active", True))
                    e_roles = st.multiselect("Trained Roles", 
                                           ["Usher", "Supervisor", "Kiosk", "Merch", "Access Host", "Laidler"],
                                           default=edit_target.get("roles", []))
                    e_venues = st.multiselect("Venue Restrictions", 
                                            ["ALH", "SGH", "Studio"], 
                                            default=edit_target.get("venue_restrictions", []))
                    
                    e_pref = st.number_input("Preferred Weekly Shifts", min_value=0, max_value=7, value=edit_target.get("preferred_shifts", 3))
                    e_max = st.number_input("Maximum Weekly Shifts", min_value=0, max_value=7, value=edit_target.get("max_shifts", 5))
                    e_doubles = st.checkbox("Can work doubles?", value=edit_target.get("double_allowed", True))
                    e_notes = st.text_area("Notes", value=edit_target.get("notes", ""))
                    
                    update_submitted = st.form_submit_button("Update Profile")
                    
                    if update_submitted:
                        edit_target.update({
                            "name": e_name,
                            "active": e_active,
                            "roles": e_roles,
                            "preferred_shifts": e_pref,
                            "max_shifts": e_max,
                            "double_allowed": e_doubles,
                            "venue_restrictions": e_venues,
                            "notes": e_notes
                        })
                        save_staff(staff_list)
                        st.success(f"{e_name} updated successfully!")
                        st.rerun()

with col3:
    # Form to delete staff
    if staff_list:
        with st.expander("🗑️ Delete Staff", expanded=False):
            to_delete = st.selectbox("Select staff to remove", staff_names)
            
            if st.button("Delete Profile", type="primary"):
                staff_list = [s for s in staff_list if s["name"] != to_delete]
                save_staff(staff_list)
                st.success(f"{to_delete} has been removed.")
                st.rerun()

# Display current staff
if staff_list:
    st.write("---")
    st.subheader("Current Roster")
    df = pd.DataFrame(staff_list)
    df['roles'] = df['roles'].apply(lambda x: ", ".join(x) if isinstance(x, list) else x)
    df['venue_restrictions'] = df['venue_restrictions'].apply(lambda x: ", ".join(x) if isinstance(x, list) else x)
    
    st.dataframe(
        df[["name", "active", "roles", "preferred_shifts", "max_shifts", "venue_restrictions", "notes"]],
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("No staff records found. Add a staff member or import availability to get started.")
