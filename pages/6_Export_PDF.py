import streamlit as st
import json
import os
from io import BytesIO
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

st.set_page_config(page_title="Export PDF", layout="wide")
st.title("Export Weekly Rota PDF")
st.write("Generate professional, week-per-page matrix rotas matching your standard format.")

def load_json(filepath):
    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
        return []
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

rotas_data = load_json("data/rotas.json")
shows_data = load_json("data/shows.json")
staff_data = load_json("data/staff.json")

if not rotas_data:
    st.warning("No generated rotas found. Please create and save some batches first.")
    st.stop()

shows_dict = {s['id']: s for s in shows_data}
staff_names = sorted([s['name'] for s in staff_data])

# Group saved rotas by Monday of their respective week
def get_monday(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    monday = dt - timedelta(days=dt.weekday())
    return monday.strftime("%Y-%m-%d")

weeks_dict = {}
for rota in rotas_data:
    date_str = rota['date']
    monday_str = get_monday(date_str)
    if monday_str not in weeks_dict:
        weeks_dict[monday_str] = []
    weeks_dict[monday_str].append(rota)

st.subheader("Select Weeks to Export")
selected_weeks = []

for monday_str, rotas_in_week in sorted(weeks_dict.items()):
    m_dt = datetime.strptime(monday_str, "%Y-%m-%d")
    sun_dt = m_dt + timedelta(days=6)
    label = f"Week Commencing: {m_dt.strftime('%d %b %Y')} – {sun_dt.strftime('%d %b %Y')} ({len(rotas_in_week)} shifts scheduled)"
    
    # Use unique keys to prevent duplicate ID crashes
    if st.checkbox(label, value=True, key=f"week_chk_{monday_str}"):
        selected_weeks.append(monday_str)

if not selected_weeks:
    st.warning("Please select at least one week to export.")
    st.stop()

if st.button("📄 Generate Weekly PDF(s)", type="primary"):
    with st.spinner("Building professional weekly matrices..."):
        buffer = BytesIO()
        
        # Landscape A4 gives us maximum width for 7 days + staff names
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
        elements = []
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'WeekTitle',
            parent=styles['Heading1'],
            fontSize=16,
            leading=20,
            alignment=1, # Center
            textColor=colors.HexColor("#1f2937")
        )
        cell_style = ParagraphStyle(
            'GridCell',
            parent=styles['Normal'],
            fontSize=7,
            leading=9,
            alignment=1 # Center
        )
        name_style = ParagraphStyle(
            'StaffName',
            parent=styles['Normal'],
            fontSize=7.5,
            leading=9,
            fontName='Helvetica-Bold',
            alignment=0 # Left
        )
        header_style = ParagraphStyle(
            'HeaderCell',
            parent=styles['Normal'],
            fontSize=8,
            leading=10,
            fontName='Helvetica-Bold',
            alignment=1,
            textColor=colors.whitesmoke
        )

        for w_idx, monday_str in enumerate(selected_weeks):
            m_dt = datetime.strptime(monday_str, "%Y-%m-%d")
            week_rotas = weeks_dict[monday_str]
            
            # Map out the 7 days of the week (Monday to Sunday)
            days = [m_dt + timedelta(days=i) for i in range(7)]
            day_names = [d.strftime("%a %d %b") for d in days]
            
            # Organize shows by day
            shows_by_day = {i: [] for i in range(7)}
            for r in week_rotas:
                r_dt = datetime.strptime(r['date'], "%Y-%m-%d")
                day_idx = r_dt.weekday() # 0 = Mon, 6 = Sun
                if 0 <= day_idx <= 6:
                    shows_by_day[day_idx].append(r)
            
            # Build Matrix Headers
            venues_row = ["Staff Name"]
            shows_row = ["Venue / Show"]
            times_row = ["Perf Time"]
            
            for i in range(7):
                day_shows = shows_by_day[i]
                if day_shows:
                    # If multiple shows on one day, combine or take primary
                    v_str = ", ".join(set([shows_dict.get(s['show_id'], {}).get('venue', 'Alhambra') for s in day_shows]))
                    s_str = ", ".join([s['show_name'] for s in day_shows])
                    t_str = ", ".join([shows_dict.get(s['show_id'], {}).get('curtain_time', '')[:5] for s in day_shows])
                    
                    venues_row.append(v_str)
                    shows_row.append(s_str)
                    times_row.append(t_str)
                else:
                    venues_row.append("-")
                    shows_row.append("No Show")
                    times_row.append("-")
            
            table_data = [
                [Paragraph(f"<b>BRADFORD THEATRES - FOH ROTA (W/C {m_dt.strftime('%d %B %Y')})</b>", title_style), "", "", "", "", "", "", ""],
                [Paragraph(h, header_style) for h in ["Staff Name"] + day_names],
                [Paragraph(v, cell_style) for v in venues_row],
                [Paragraph(s, cell_style) for s in shows_row],
                [Paragraph(t, cell_style) for t in times_row]
            ]
            
            # Map staff allocations across the week
            # We want to check every rota in this week to see where each staff member is working
            for staff in staff_names:
                row = [Paragraph(staff, name_style)]
                for i in range(7):
                    day_shows = shows_by_day[i]
                    assigned_roles = []
                    
                    for s in day_shows:
                        alloc = s.get('allocation', {})
                        for role, members in alloc.items():
                            if staff in members:
                                # Find call time if available
                                show_info = shows_dict.get(s['show_id'], {})
                                call_t = show_info.get('call_time', '18:45:00')[:5]
                                role_short = role[:5] # e.g. Super, Usher, Kiosk
                                assigned_roles.append(f"{call_t} {role_short}")
                                
                    if assigned_roles:
                        row.append(Paragraph("<br/>".join(assigned_roles), cell_style))
                    else:
                        row.append(Paragraph("", cell_style))
                table_data.append(row)
            
            # Column widths: 90 for staff names, 100 for each of the 7 days (Total ~790 fits landscape A4)
            col_widths = [90, 100, 100, 100, 100, 100, 100, 100]
            
            t = Table(table_data, colWidths=col_widths, repeatRows=2)
            t.setStyle(TableStyle([
                ('SPAN', (0, 0), (-1, 0)), # Title span across all columns
                ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor("#1f2937")), # Day header dark background
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 1), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
                ('BACKGROUND', (0, 2), (-1, 4), colors.HexColor("#f3f4f6")), # Venue/Show/Time meta rows background
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            
            elements.append(t)
            
            # Add Page Break between weeks (ensuring strictly one week per page)
            if w_idx < len(selected_weeks) - 1:
                elements.append(PageBreak())
                
        doc.build(elements)
        
        st.success("Weekly Matrix PDF Generated Successfully!")
        st.download_button(
            label="⬇️ Download Weekly Rota PDF",
            data=buffer.getvalue(),
            file_name="Bradford_FoH_Weekly_Rotas.pdf",
            mime="application/pdf",
            type="primary"
        )
