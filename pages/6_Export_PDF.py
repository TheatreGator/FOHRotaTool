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
st.write("Generate professional, week-per-page matrix rotas matching your standard format with venue color coding.")

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
    label = f"Week Commencing: {m_dt.strftime('%d %b %Y')} – {sun_dt.strftime('%d %b %Y')} ({len(rotas_in_week)} performances scheduled)"
    
    if st.checkbox(label, value=True, key=f"week_chk_{monday_str}"):
        selected_weeks.append(monday_str)

if not selected_weeks:
    st.warning("Please select at least one week to export.")
    st.stop()

if st.button("📄 Generate Weekly PDF(s)", type="primary"):
    with st.spinner("Building professional venue-colorized matrices..."):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=15, leftMargin=15, topMargin=15, bottomMargin=15)
        elements = []
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('WeekTitle', parent=styles['Heading1'], fontSize=14, leading=18, alignment=1, textColor=colors.HexColor("#1f2937"))
        cell_style = ParagraphStyle('GridCell', parent=styles['Normal'], fontSize=6.5, leading=8, alignment=1)
        name_style = ParagraphStyle('StaffName', parent=styles['Normal'], fontSize=7, leading=8.5, fontName='Helvetica-Bold', alignment=0)
        header_style = ParagraphStyle('HeaderCell', parent=styles['Normal'], fontSize=7.5, leading=9, fontName='Helvetica-Bold', alignment=1, textColor=colors.whitesmoke)

        for w_idx, monday_str in enumerate(selected_weeks):
            m_dt = datetime.strptime(monday_str, "%Y-%m-%d")
            week_rotas = weeks_dict[monday_str]
            week_rotas.sort(key=lambda x: (x['date'], x['curtain_time']))
            
            dates_row = ["Staff Name"]
            venues_row = ["Venue"]
            shows_row = ["Show"]
            times_row = ["Perf Time"]
            
            for r in week_rotas:
                r_dt = datetime.strptime(r['date'], "%Y-%m-%d")
                show_info = shows_dict.get(r['show_id'], {})
                venue = show_info.get('venue', 'Alhambra')
                time = show_info.get('curtain_time', '')[:5]
                
                dates_row.append(r_dt.strftime("%a %d %b"))
                venues_row.append(venue)
                shows_row.append(r['show_name'])
                times_row.append(time)
            
            num_cols = len(week_rotas)
            
            table_data = [
                [Paragraph(f"<b>BRADFORD THEATRES - FOH ROTA (W/C {m_dt.strftime('%d %B %Y')})</b>", title_style)] + [""] * num_cols,
                [Paragraph(h, header_style) for h in dates_row],
                [Paragraph(v, header_style) for v in venues_row],
                [Paragraph(s, header_style) for s in shows_row],
                [Paragraph(t, header_style) for t in times_row]
            ]
            
            for staff in staff_names:
                row = [Paragraph(staff, name_style)]
                for r in week_rotas:
                    alloc = r.get('allocation', {})
                    assigned_roles = []
                    for role, members in alloc.items():
                        if staff in members:
                            show_info = shows_dict.get(r['show_id'], {})
                            call_t = show_info.get('call_time', '18:45:00')[:5]
                            role_short = role[:5]
                            assigned_roles.append(f"{call_t} {role_short}")
                            
                    if assigned_roles:
                        row.append(Paragraph("<br/>".join(assigned_roles), cell_style))
                    else:
                        row.append(Paragraph("", cell_style))
                table_data.append(row)
            
            usable_width = 812
            name_col_width = 85
            remaining_width = usable_width - name_col_width
            perf_col_width = max(40, remaining_width / num_cols) if num_cols > 0 else 50
            col_widths = [name_col_width] + [perf_col_width] * num_cols
            
            # Base table styling commands
            style_commands = [
                ('SPAN', (0, 0), (-1, 0)),
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#f3f4f6")), # Staff name column background
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 1), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
                ('TOPPADDING', (0, 0), (-1, -1), 2.5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
            ]
            
            # Dynamic Venue Color Coding per column (Rows 1 to 4 for headers)
            for col_idx, r in enumerate(week_rotas, start=1):
                show_info = shows_dict.get(r['show_id'], {})
                venue = show_info.get('venue', 'Alhambra')
                
                if venue == "Alhambra":
                    venue_color = colors.HexColor("#ea580c") # Vibrant Orange
                elif venue == "St George's Hall":
                    venue_color = colors.HexColor("#2563eb") # Royal Blue
                else: # Studio / The Studio
                    venue_color = colors.HexColor("#16a34a") # Forest Green
                    
                style_commands.append(('BACKGROUND', (col_idx, 1), (col_idx, 4), venue_color))

            t = Table(table_data, colWidths=col_widths, repeatRows=5)
            t.setStyle(TableStyle(style_commands))
            
            elements.append(t)
            if w_idx < len(selected_weeks) - 1:
                elements.append(PageBreak())
                
        doc.build(elements)
        st.success("Venue-Colorized Weekly Matrix PDF Generated Successfully!")
        st.download_button(
            label="⬇️ Download Weekly Rota PDF",
            data=buffer.getvalue(),
            file_name="Bradford_FoH_Weekly_Rotas.pdf",
            mime="application/pdf",
            type="primary"
        )
