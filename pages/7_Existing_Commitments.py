import streamlit as st
import pandas as pd
import json
import os

st.set_page_config(page_title="Existing Commitments", layout="wide")
st.title("Existing Commitments Tracker")
st.write("Log staff who are booked for other duties (DM, Stage Door, Tech) so they are excluded from the FOH rota.")

COMMITMENTS_FILE = "data/commitments.json"

def load_commitments():
    if not os.path.exists(COMMITMENTS_FILE) or os.path.getsize(COMMITMENTS_FILE) == 0:
        return []
    try:
        with open(COMMITMENTS_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def save_commitments(data):
    with open(COMMITMENTS_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_staff():
    if not os.path.exists("data/staff.json"): return []
    with open("data/staff.json", "r") as f: return json.load(f)

commitments_data = load_commitments()
staff_data = load_staff()
staff_names = [s["name"] for s in staff_data]

col1, col2 = st.columns(2)

with col1:
    with st.expander("➕ Add Commitment", expanded=True):
        with st.form("add_commitment"):
            staff_member = st.selectbox("Staff Member", staff_names if staff_names else ["No staff found"])
            date = st.date_input("Date of Commitment")
            role = st.selectbox("Role / Duty", ["Duty Manager (DM)", "Stage Door", "Tech", "Box Office", "Marketing", "Other"])
            notes = st.text_input("Notes")
            
            if st.form_submit_button("Save Commitment") and staff_data:
                new_commitment = {
                    "id": f"{staff_member}_{date}_{role}",
                    "name": staff_member,
                    "date": str(date),
                    "role": role,
                    "notes": notes
                }
                # Prevent duplicates
                commitments_data = [c for c in commitments_data if c['id'] != new_commitment['id']]
                commitments_data.append(new_commitment)
                save_commitments(commitments_data)
                st.success(f"Commitment saved for {staff_member}")
                st.rerun()

with col2:
    if commitments_data:
        with st.expander("🗑️ Delete Commitment", expanded=False):
            options = {c['id']: f"{c['date']} - {c['name']} ({c['role']})" for c in commitments_data}
            to_delete = st.selectbox("Select commitment to remove", options=list(options.keys()), format_func=lambda x: options[x])
            if st.button("Delete Commitment", type="primary"):
                commitments_data = [c for c in commitments_data if c['id'] != to_delete]
                save_commitments(commitments_data)
                st.success("Commitment removed.")
                st.rerun()

if commitments_data:
    st.write("---")
    st.subheader("Upcoming Commitments")
    df = pd.DataFrame(commitments_data)
    df = df.sort_values(by=["date", "name"])
    st.dataframe(df[["date", "name", "role", "notes"]], use_container_width=True, hide_index=True)
else:
    st.info("No existing commitments logged.")
