import streamlit as st
import json
import os
from io import BytesIO
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

st.set_page_config(page_title="Export PDF", layout="wide")
st.title("Export Final Rota")
st.write("Generate a colour-coded PDF of your finalized schedules.")

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

if not rotas_data:
    st.warning("No generated rotas found. Please create and save some drafts first.")
    st.stop()

# Create a fast lookup for venue and time data
shows_dict = {s['id']: s for s in shows_data}

# Sort rotas chronologically by date
rotas_data.sort(key=lambda x: x['date'])

st.subheader("Select Rotas to Include")

# Create a checklist for each saved rota
selected_rotas = []
for rota in rotas_data:
    show_info = shows_dict.get(rota['show_id'], {})
    venue = show_info.get('venue', 'Unknown Venue')
    time = show_info.get('curtain_time', '')[:5]
    
    label = f"{rota['date']} {time} - {rota['show_name']} ({venue})"
    if st.checkbox(label, value=True):
        selected_rotas.append((rota, show_info))

if not selected_rotas:
    st.warning("Please select at least one rota to export.")
    st.stop()

if st.button("📄 Generate PDF", type="primary"):
    with st.spinner("Building PDF document..."):
        buffer = BytesIO()
        
        # Set up a Landscape A4 document
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        elements = []
        styles = getSampleStyleSheet()
        
        title = Paragraph("Front of House Rota", styles['Title'])
        elements.append(title)
        elements.append(Spacer(1, 20))
        
        for rota, show in selected_rotas:
            venue = show.get('venue', 'Alhambra')
            time = show.get('curtain_time', '')[:5]
            
            # Apply colour coding based on venue rules
            if venue == "Alhambra":
                header_bg = colors.Color(0.85, 0.45, 0.15) # Orange
            elif venue == "St George's Hall":
                header_bg = colors.Color(0.2, 0.4, 0.7) # Blue
            else: 
                header_bg = colors.Color(0.2, 0.6, 0.3) # Green for Studio
                
            # Table headers
            data = [
                [f"{rota['date']} | {time} | {rota['show_name']} ({venue})", "", "", "", ""],
                ["Supervisor", "Merch", "Kiosk", "Access Host", "Ushers"]
            ]
            
            alloc = rota.get('allocation', {})
            
            # Determine how many rows the table needs based on the largest role list
            max_len = max(
                len(alloc.get('Supervisor', [])),
                len(alloc.get('Merch', [])),
                len(alloc.get('Kiosk', [])),
                len(alloc.get('Access Host', [])),
                len(alloc.get('Ushers', []))
            )
            
            if max_len == 0:
                data.append(["", "", "", "", ""])
            else:
                for i in range(max_len):
                    row = []
                    for role in ["Supervisor", "Merch", "Kiosk", "Access Host", "Ushers"]:
                        staff_list = alloc.get(role, [])
                        
                        val = staff_list[i] if i < len(staff_list) else ""
                        # Blank out "Unassigned" slots for a cleaner printout
                        if val == "--- Unassigned ---":
                            val = ""
                        row.append(val)
                    data.append(row)
                    
            # Build the ReportLab Table
            t = Table(data, colWidths=[140, 140, 140, 140, 160])
            t.setStyle(TableStyle([
                # Header row styling (Venue Colors)
                ('BACKGROUND', (0, 0), (-1, 0), header_bg),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('SPAN', (0, 0), (-1, 0)), # Merge the top row cells
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0,0), (-1,0), 8),
                ('TOPPADDING', (0,0), (-1,0), 8),
                
                # Sub-header row styling (Role Names)
                ('BACKGROUND', (0, 1), (-1, 1), colors.lightgrey),
                ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
                
                # General grid styling
                ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            elements.append(t)
            elements.append(Spacer(1, 20))
            
        doc.build(elements)
        
        st.success("PDF Generated Successfully!")
        st.download_button(
            label="⬇️ Download Rota PDF",
            data=buffer.getvalue(),
            file_name="FoH_Rota.pdf",
            mime="application/pdf",
            type="primary"
        )
