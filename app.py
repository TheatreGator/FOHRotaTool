import streamlit as st
from services.storage import load_staff

st.set_page_config(page_title="Bradford Theatres FOH Rota", layout="wide")

st.title("Bradford Theatres FOH Workforce Optimization")
st.write("Welcome to the assisted scheduling engine.")

staff_data = load_staff()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Staff Records", len(staff_data))
col2.metric("Upcoming Shows", "0 (Draft)")
col3.metric("Draft Rotas", "0")
col4.metric("Published Rotas", "0")

st.info("Navigate to the Staff Database using the sidebar to begin building your team profiles.")

