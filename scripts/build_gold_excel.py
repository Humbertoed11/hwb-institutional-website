import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.pagebreak import Break
import shutil

wb_path = "HWB-COMPANY/HWB-QUOTES/BOSANNA-COLLIN-COLLEGE/COLLIN-COLLEGE-FRISCO-BID-MODEL.xlsx"
wb = openpyxl.load_workbook(wb_path)

# Colors & Visual Hierarchy
navy_dark = "0F172A"
navy_blue = "1E3A8A"
soft_blue = "DBEAFE"
light_blue = "EFF6FF"
gold_amber = "D97706"
light_amber = "FEF3C7"
bg_gray = "F8FAFC"
border_gray = "CBD5E1"
border_amber = "F59E0B"
card_border_blue = "3B82F6"

# Typographic Standards
font_title = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
font_subtitle = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
font_sec_hdr = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
font_tbl_hdr = Font(name="Calibri", size=10, bold=True, color="1E3A8A")
font_kpi_label = Font(name="Calibri", size=9, bold=True, color="1E3A8A")
font_kpi_val = Font(name="Calibri", size=13, bold=True, color="0F172A")
font_kpi_sub = Font(name="Calibri", size=8.5, italic=True, color="475569")
font_bold = Font(name="Calibri", size=9.5, bold=True, color="0F172A")
font_regular = Font(name="Calibri", size=9.5, color="1E293B")
font_italic = Font(name="Calibri", size=9.5, italic=True, color="334155")
font_alert_text = Font(name="Calibri", size=9.5, bold=True, color="92400E")

fill_navy_title = PatternFill(start_color=navy_dark, end_color=navy_dark, fill_type="solid")
fill_navy_sub = PatternFill(start_color="334155", end_color="334155", fill_type="solid")
fill_sec_hdr = PatternFill(start_color=navy_blue, end_color=navy_blue, fill_type="solid")
fill_tbl_hdr = PatternFill(start_color=soft_blue, end_color=soft_blue, fill_type="solid")
fill_kpi_card = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
fill_kpi_highlight = PatternFill(start_color="E0E7FF", end_color="E0E7FF", fill_type="solid")
fill_amber_sub = PatternFill(start_color=light_amber, end_color=light_amber, fill_type="solid")

thin_border = Border(
    left=Side(style="thin", color=border_gray),
    right=Side(style="thin", color=border_gray),
    top=Side(style="thin", color=border_gray),
    bottom=Side(style="thin", color=border_gray)
)

card_border = Border(
    left=Side(style="medium", color=card_border_blue),
    right=Side(style="medium", color=card_border_blue),
    top=Side(style="medium", color=card_border_blue),
    bottom=Side(style="medium", color=card_border_blue)
)

double_bottom_border = Border(
    left=Side(style="thin", color=border_gray),
    right=Side(style="thin", color=border_gray),
    top=Side(style="thin", color=border_gray),
    bottom=Side(style="double", color=navy_blue)
)

# -------------------------------------------------------------
# 1. REBUILD COMMERCIAL PROPOSAL SHEET
# -------------------------------------------------------------
idx_prop = wb.sheetnames.index("Commercial_Proposal")
wb.remove(wb["Commercial_Proposal"])
ws = wb.create_sheet("Commercial_Proposal", idx_prop)

ws.views.sheetView[0].showGridLines = True

# Title Block
ws.cell(row=1, column=1, value="HWB CLEANING SERVICES LLC — COMMERCIAL CLEANING SUBCONTRACT QUOTE")
ws.merge_cells("A1:I1")
ws.cell(row=1, column=1).font = font_title
ws.cell(row=1, column=1).fill = fill_navy_title
ws.cell(row=1, column=1).alignment = Alignment(horizontal="center", vertical="center")
ws.row_dimensions[1].height = 28.0

ws.cell(row=2, column=1, value="COLLIN COLLEGE — FRISCO CAMPUS (10 BUILDINGS / 478,418 CLEANABLE SQ. FT. / 1,120.0 HOURS PER WEEK)")
ws.merge_cells("A2:I2")
ws.cell(row=2, column=1).font = font_subtitle
ws.cell(row=2, column=1).fill = fill_navy_sub
ws.cell(row=2, column=1).alignment = Alignment(horizontal="center", vertical="center")
ws.row_dimensions[2].height = 22.0

# Spacer Row 3
ws.row_dimensions[3].height = 10.0
ws.merge_cells("A3:I3")
ws.cell(row=3, column=1, value="")

# Project Meta
meta = [
    ("Prime Contractor / Client:", "Bosanna LLC (Attn: Angelica Hudgins)", "School / Project Name:", "Collin College Frisco Campus Custodial Replacement"),
    ("Approved Purchasing Program:", "Texas TIPS Purchasing Cooperative (#260103 / #260102)", "Contract Length:", "3-Year Base Contract + 2 One-Year Extensions"),
    ("Campus Size to Clean:", "478,418 Cleanable Sq. Ft. (10 Buildings + Parking Elevator Lobbies)", "Cleaning Quality Standard:", "Top-Tier School Clean (Spotless APPA Level 2 Clean Every Morning)"),
    ("Weekly Campus Work Hours:", "1,120.0 Hours Every Week (28 Full-Time Equivalent Workers)", "Proof of Hours Worked:", "Fingerprint Time Clock Records + Police Desk Sign-In Sheet")
]

for idx, (k1, v1, k2, v2) in enumerate(meta, start=4):
    ws.cell(row=idx, column=1, value=k1).font = font_bold
    ws.cell(row=idx, column=2, value=v1).font = font_regular
    ws.merge_cells(start_row=idx, start_column=2, end_row=idx, end_column=5)
    ws.cell(row=idx, column=6, value=k2).font = font_bold
    ws.cell(row=idx, column=7, value=v2).font = font_regular
    ws.merge_cells(start_row=idx, start_column=7, end_row=idx, end_column=9)
    ws.row_dimensions[idx].height = 18.0

# Spacer Row 8: Breathing Room between Header Block and Section 1.0
ws.row_dimensions[8].height = 18.0
ws.merge_cells("A8:I8")
ws.cell(row=8, column=1, value="")

# Section 1.0 Header
ws.cell(row=9, column=1, value="1.0 COMMERCIAL PRICING SCHEDULE (BILLED TO BOSANNA LLC)")
ws.merge_cells("A9:I9")
ws.cell(row=9, column=1).font = font_sec_hdr
ws.cell(row=9, column=1).fill = fill_sec_hdr
ws.cell(row=9, column=1).alignment = Alignment(horizontal="left", vertical="center", indent=1)
ws.row_dimensions[9].height = 26.0

# -------------------------------------------------------------
# EXECUTIVE KPI SUMMARY CARDS: FINAL NUMBERS AT A GLANCE
# -------------------------------------------------------------
# Row 10: Card Labels
kpis = [
    (1, 2, "MONTHLY SUBCONTRACT BASE", "$141,316.70", "Scheduled Labor + Restroom Supplies", fill_kpi_highlight),
    (3, 4, "ANNUAL SUBCONTRACT TOTAL", "$1,695,800.40", "12 Months Fixed Base (Lines 41 + 42)", fill_kpi_card),
    (5, 6, "SQUARE FOOT RATE", "$3.54 / SF / Year", "$0.295 / Sq. Ft. / Month", fill_kpi_card),
    (7, 9, "WEEKLY LABOR HOURS", "1,120.0 Hours / Wk", "28.0 Cleaners | Zero Overtime Scheduled", fill_kpi_card)
]

ws.row_dimensions[10].height = 18.0
ws.row_dimensions[11].height = 28.0
ws.row_dimensions[12].height = 18.0

for c_start, c_end, label, val, subtext, fill_type in kpis:
    # Label Row
    ws.cell(row=10, column=c_start, value=label).font = font_kpi_label
    ws.merge_cells(start_row=10, start_column=c_start, end_row=10, end_column=c_end)
    ws.cell(row=10, column=c_start).alignment = Alignment(horizontal="center", vertical="center")
    
    # Value Row (Big Font)
    ws.cell(row=11, column=c_start, value=val).font = font_kpi_val
    ws.merge_cells(start_row=11, start_column=c_start, end_row=11, end_column=c_end)
    ws.cell(row=11, column=c_start).alignment = Alignment(horizontal="center", vertical="center")
    
    # Subtext Row
    ws.cell(row=12, column=c_start, value=subtext).font = font_kpi_sub
    ws.merge_cells(start_row=12, start_column=c_start, end_row=12, end_column=c_end)
    ws.cell(row=12, column=c_start).alignment = Alignment(horizontal="center", vertical="center")
    
    # Card borders & fills
    for r in range(10, 13):
        for c in range(c_start, c_end + 1):
            cl = ws.cell(row=r, column=c)
            cl.fill = fill_type
            # Card boundary borders
            top_border = Side(style="medium", color=card_border_blue) if r == 10 else Side(style="thin", color=border_gray)
            bot_border = Side(style="medium", color=card_border_blue) if r == 12 else Side(style="thin", color=border_gray)
            left_border = Side(style="medium", color=card_border_blue) if c == c_start else Side(style="thin", color=border_gray)
            right_border = Side(style="medium", color=card_border_blue) if c == c_end else Side(style="thin", color=border_gray)
            cl.border = Border(top=top_border, bottom=bot_border, left=left_border, right=right_border)

# Spacer Row 13
ws.row_dimensions[13].height = 10.0
ws.merge_cells("A13:I13")
ws.cell(row=13, column=1, value="")

# Factual Operational Scope Statement (Plain Everyday English)
scope_statement = (
    "Cleaning Services & Direct Pricing: HWB Cleaning Services LLC provides full cleaning management, staff, floor machines, and restroom paper "
    "supplies for Collin College Frisco Campus (10 buildings / 478,418 cleanable sq. ft.). All 1,120.0 weekly hours are worked by 29 to 32 badged employees "
    "kept to regular daytime and evening hours, with zero overtime costs to Bosanna LLC ($0.00 overtime charge)."
)
ws.cell(row=14, column=1, value=scope_statement)
ws.merge_cells("A14:I14")
ws.cell(row=14, column=1).font = font_italic
ws.cell(row=14, column=1).alignment = Alignment(vertical="center", wrap_text=True)
ws.row_dimensions[14].height = 36.0

# Spacer Row 15
ws.row_dimensions[15].height = 10.0
ws.merge_cells("A15:I15")
ws.cell(row=15, column=1, value="")

# Table 1: RFP Pricing Schedule (HWB to Bosanna - Formatted with Wrap Text)
tbl1_headers = [
    (1, "RFP Line #"),
    (2, "Contract Section"),  # Dedicated Col B
    (3, "Service Description & Scope"),  # Dedicated Col C
    (4, "Unit"),
    (5, "Billing Schedule"),
    (6, "HWB Price ($)"),
    (7, "Monthly Total ($)"),
    (8, "Yearly Total ($)"),
    (9, "What is Included & Contract Scope")
]
for col_idx, h in tbl1_headers:
    c = ws.cell(row=16, column=col_idx, value=h)
    c.font = font_tbl_hdr
    c.fill = fill_tbl_hdr
    c.border = thin_border
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
ws.row_dimensions[16].height = 28.0

tbl1_data = [
    ("Line 41", "SOW § Schedule of Work", "Scheduled Campus Cleaning (Night & Day Teams)", "Month", "Fixed Monthly Price", 132984.20, 132984.20, 1595810.40, "1,120 hours of daily cleaning across all 10 campus buildings (29–32 trained workers | Zero Overtime)"),
    ("Line 42", "T&C § Restroom Supplies", "Restroom Supplies & Paper Products Refills", "Month", "Fixed Monthly Price", 8332.50, 8332.50, 99990.00, "Complete campus paper supplies: enMotion roll towels, 2-ply bath tissue, foaming soap & heavy-duty can liners"),
    ("Line 43", "SOW § Unscheduled Work", "Extra Cleaning Helper: Weekdays (Monday to Friday)", "Hour", "As Requested / Billed Hourly", 31.50, None, None, "Extra worker sent within 24 hours if the college requests one for weekday events"),
    ("Line 44", "SOW § Unscheduled Work", "Extra Cleaning Helper: Saturday", "Hour", "As Requested / Billed Hourly", 35.00, None, None, "Weekend helper sent for special campus events; worker speaks fluent English"),
    ("Line 45", "SOW § Unscheduled Work", "Extra Cleaning Helper: Sunday & Holidays", "Hour", "As Requested / Billed Hourly", 42.00, None, None, "Special holiday or Sunday event helper sent upon request"),
    ("Line 46", "SOW § Floor Care", "Tile Floor Deep Strip & 4-Coat Wax Refinishing", "Sq. Ft.", "Per Job Order Request", 0.270, None, None, "Strip off old wax, deep scrub bare floor, and put down 4 shiny, durable coats of floor wax"),
    ("Line 47", "SOW § Floor Care", "Carpet Deep Hot-Water Steam Cleaning", "Sq. Ft.", "Per Job Order Request", 0.300, None, None, "Heavy-duty steam machine pulls deep dirt, spills, and food stains from carpets"),
    ("Line 48", "SOW § 7.17 / T&C", "Square Foot Price Adjustment (Add or Close Space)", "Sq. Ft./Yr", "Yearly / Monthly Adjustment", 3.545, 0.295, 3.545, "Fair price per square foot if the college adds new rooms or temporarily closes a building")
]

for r_offset, row_vals in enumerate(tbl1_data, start=17):
    ws.row_dimensions[r_offset].height = 38.0
    # Col 1 (A): Line #
    c1 = ws.cell(row=r_offset, column=1, value=row_vals[0])
    c1.border = thin_border
    c1.font = font_bold
    c1.alignment = Alignment(horizontal="center", vertical="center")
    
    # Col 2 (B): Contract Section (NEW DEDICATED COLUMN)
    c2 = ws.cell(row=r_offset, column=2, value=row_vals[1])
    c2.border = thin_border
    c2.font = font_bold
    c2.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    
    # Col 3 (C): Service Description & Scope
    c3 = ws.cell(row=r_offset, column=3, value=row_vals[2])
    c3.border = thin_border
    c3.font = font_regular
    c3.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    
    # Col 4 (D): Unit
    c4 = ws.cell(row=r_offset, column=4, value=row_vals[3])
    c4.border = thin_border
    c4.font = font_regular
    c4.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    
    # Col 5 (E): Billing Schedule
    c5 = ws.cell(row=r_offset, column=5, value=row_vals[4])
    c5.border = thin_border
    c5.font = font_regular
    c5.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    
    # Col 6 (F): HWB Price ($)
    c6 = ws.cell(row=r_offset, column=6, value=row_vals[5])
    c6.border = thin_border
    c6.font = font_regular
    c6.alignment = Alignment(horizontal="right", vertical="center")
    if row_vals[5] is not None:
        c6.number_format = "$#,##0.00" if row_vals[5] >= 1 else "$#,##0.000"
        
    # Col 7 (G): Monthly Total ($)
    c7 = ws.cell(row=r_offset, column=7, value=row_vals[6])
    c7.border = thin_border
    c7.font = font_regular
    c7.alignment = Alignment(horizontal="right", vertical="center")
    if row_vals[6] is not None:
        c7.number_format = "$#,##0.00" if row_vals[6] >= 1 else "$#,##0.000"
        
    # Col 8 (H): Yearly Total ($)
    c8 = ws.cell(row=r_offset, column=8, value=row_vals[7])
    c8.border = thin_border
    c8.font = font_regular
    c8.alignment = Alignment(horizontal="right", vertical="center")
    if row_vals[7] is not None:
        c8.number_format = "$#,##0.00" if row_vals[7] >= 1 else "$#,##0.000"
        
    # Col 9 (I): What is Included & Contract Scope
    c9 = ws.cell(row=r_offset, column=9, value=row_vals[8])
    c9.border = thin_border
    c9.font = font_regular
    c9.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    c9.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

# Summary rows for Table 1
ws.cell(row=25, column=1, value="SCHEDULED BASE ANNUAL TOTAL (LINES 41 + 42)").font = font_bold
ws.merge_cells("A25:E25")
ws.cell(row=25, column=6, value="12 Months").alignment = Alignment(horizontal="center", vertical="center")
ws.cell(row=25, column=7, value="=G17+G18").number_format = "$#,##0.00"
ws.cell(row=25, column=8, value="=H17+H18").number_format = "$#,##0.00"
ws.cell(row=25, column=9, value="Complete cleaning service, heavy floor machines, and full team to keep campus clean and spotless.").alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
for c_idx in range(1, 10):
    cl = ws.cell(row=25, column=c_idx)
    cl.fill = fill_tbl_hdr
    cl.font = font_bold
    cl.border = thin_border
ws.row_dimensions[25].height = 28.0

ws.cell(row=26, column=1, value="SCHEDULED BASE MONTHLY BILLING (LINES 41 + 42)").font = font_bold
ws.merge_cells("A26:E26")
ws.cell(row=26, column=6, value="Per Month").alignment = Alignment(horizontal="center", vertical="center")
ws.cell(row=26, column=7, value="=G17+G18").number_format = "$#,##0.00"
ws.cell(row=26, column=8, value="=(G17+G18)*12").number_format = "$#,##0.00"
ws.cell(row=26, column=9, value="100% Backed by fingerprint clock records and police desk sign-in logbook").alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
for c_idx in range(1, 10):
    cl = ws.cell(row=26, column=c_idx)
    cl.fill = PatternFill(start_color="BFDBFE", end_color="BFDBFE", fill_type="solid")
    cl.font = font_bold
    cl.border = double_bottom_border
ws.row_dimensions[26].height = 30.0

# -------------------------------------------------------------
# 2. SECTION 2.0: WORK SCHEDULE & HOURLY PAY
# -------------------------------------------------------------
sec2_start = 27
ws.cell(row=sec2_start, column=1, value="2.0 WORK SCHEDULE & HOURLY PAY (BY SHIFT AND JOB TITLE)")
ws.merge_cells(start_row=sec2_start, start_column=1, end_row=sec2_start, end_column=9)
ws.cell(row=sec2_start, column=1).font = font_sec_hdr
ws.cell(row=sec2_start, column=1).fill = fill_sec_hdr
ws.cell(row=sec2_start, column=1).alignment = Alignment(horizontal="left", vertical="center", indent=1)
ws.row_dimensions[sec2_start].height = 26.0

sec2_narrative_factual = (
    "Wages & Floor Care Plan:\n"
    "• Competitive Hourly Wages: HWB pays $17.50 for Cleaners, $19.50 for Floor Techs, and $23.00 for Supervisors to eliminate turnover and keep experienced, "
    "background-checked staff on campus every day.\n"
    "• 4 Dedicated Floor Technicians: 4 certified technicians cover all 7 nights (2 full-time weekday technicians at 40 hours each + 2 weekend technicians at "
    "16 hours each), ensuring exactly 2 technicians operate heavy floor scrubbers every single night of the week with zero overtime."
)
ws.cell(row=sec2_start+1, column=1, value=sec2_narrative_factual)
ws.merge_cells(start_row=sec2_start+1, start_column=1, end_row=sec2_start+1, end_column=9)
ws.cell(row=sec2_start+1, column=1).font = font_italic
ws.cell(row=sec2_start+1, column=1).alignment = Alignment(vertical="center", wrap_text=True)
ws.row_dimensions[sec2_start+1].height = 52.0

# Spacer Row 29: Breathing Room between Narrative and Table 2 Headers
ws.row_dimensions[sec2_start+2].height = 10.0
ws.merge_cells(f"A{sec2_start+2}:I{sec2_start+2}")
ws.cell(row=sec2_start+2, column=1, value="")

tbl2_headers = [
    "Shift & Work Days", "Job Title", "Campus Building Duties", "Working Hours", 
    "Workers on Duty", "Weekly Hours", "Base Hourly Pay", 
    "With Taxes & Ins. (+20%)", "Weekly Base Pay ($)"
]
for col_idx, h in enumerate(tbl2_headers, start=1):
    c = ws.cell(row=sec2_start+3, column=col_idx, value=h)
    c.font = font_tbl_hdr
    c.fill = fill_tbl_hdr
    c.border = thin_border
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
ws.row_dimensions[sec2_start+3].height = 28.0

positions_data = [
    # 1. Weekday Daytime (Mon–Fri) - 5 Rows (200 hrs)
    ("Weekday Daytime (Mon–Fri)", "Day Shift Boss (Bilingual)", "Signs Police Desk Book / Campus Inspection & Rover", "7:30 AM – 4:00 PM (M–F)", "1 Supervisor", 40.0, 23.00, 27.60, 920.00),
    ("Weekday Daytime (Mon–Fri)", "Day Porter 1", "Founders Hall (Main Classrooms & Restrooms)", "8:00 AM – 4:30 PM (M–F)", "1 Day Porter", 40.0, 17.50, 21.00, 700.00),
    ("Weekday Daytime (Mon–Fri)", "Day Porter 2", "University Hall & Main Walkway Corridor", "8:00 AM – 4:30 PM (M–F)", "1 Day Porter", 40.0, 17.50, 21.00, 700.00),
    ("Weekday Daytime (Mon–Fri)", "Day Porter 3", "Heritage Hall & Student Center Cafeteria", "8:00 AM – 4:30 PM (M–F)", "1 Day Porter", 40.0, 17.50, 21.00, 700.00),
    ("Weekday Daytime (Mon–Fri)", "Day Porter 4", "IT Center (3 Floors), Lawler Hall & Parking Lobbies", "8:00 AM – 4:30 PM (M–F)", "1 Day Porter", 40.0, 17.50, 21.00, 700.00),
    
    # 2. Weekday Night Production (Mon–Fri Nights | 5 Nights/Wk) - 4 Rows (640 hrs)
    ("Weekday Night (Mon–Fri)", "Weekday Night Boss (Bilingual)", "Night Leader & Shift Commander (All 10 Buildings)", "10:00 PM – 6:30 AM (M–F)", "1 Supervisor / Night", 40.0, 23.00, 27.60, 920.00),
    ("Weekday Night (Mon–Fri)", "Weekday Floor Tech 1", "Riding Floor Scrubber Lead (Main Hallways & Corridors)", "10:00 PM – 6:30 AM (M–F)", "1 Floor Tech / Night", 40.0, 19.50, 23.40, 780.00),
    ("Weekday Night (Mon–Fri)", "Weekday Floor Tech 2", "Walk-Behind Scrubber & High-Speed Polisher", "10:00 PM – 6:30 AM (M–F)", "1 Floor Tech / Night", 40.0, 19.50, 23.40, 780.00),
    ("Weekday Night (Mon–Fri)", "Weekday Night Cleaners (13 Cleaners)", "Classrooms, Restrooms, Offices, Desks & Trash Reset", "10:00 PM – 6:30 AM (M–F)", "13 Cleaners / Night", 520.0, 17.50, 21.00, 9100.00),

    # 3. Saturday Daytime (Saturday) - 3 Rows (24 hrs)
    ("Saturday Daytime (Saturday)", "Saturday Day Boss (Lead Supervisor)", "English-Speaking Lead Supervisor (Campus Events)", "8:00 AM – 4:30 PM (Sat)", "1 Supervisor", 8.0, 23.00, 27.60, 184.00),
    ("Saturday Daytime (Saturday)", "Saturday Day Porter 1", "Classrooms, Science Labs & Library", "8:00 AM – 4:30 PM (Sat)", "1 Day Porter", 8.0, 17.50, 21.00, 140.00),
    ("Saturday Daytime (Saturday)", "Saturday Day Porter 2", "Cafeteria, Gymnasium & Student Center", "8:00 AM – 4:30 PM (Sat)", "1 Day Porter", 8.0, 17.50, 21.00, 140.00),
    
    # 4. Weekend Night Production (Sat & Sun Nights | 2 Nights/Wk) - 4 Rows (256 hrs)
    ("Weekend Night (Sat–Sun)", "Weekend Night Boss (Bilingual)", "Weekend Night Leader & Shift Commander", "10:00 PM – 6:30 AM (Sat–Sun)", "1 Supervisor / Night", 16.0, 23.00, 27.60, 368.00),
    ("Weekend Night (Sat–Sun)", "Weekend Floor Tech 1", "Riding Floor Scrubber Lead (Main Spine Reset)", "10:00 PM – 6:30 AM (Sat–Sun)", "1 Floor Tech / Night", 16.0, 19.50, 23.40, 312.00),
    ("Weekend Night (Sat–Sun)", "Weekend Floor Tech 2", "Deep Carpet Wash & Stone Floor Polish", "10:00 PM – 6:30 AM (Sat–Sun)", "1 Floor Tech / Night", 16.0, 19.50, 23.40, 312.00),
    ("Weekend Night (Sat–Sun)", "Weekend Night Cleaners (13 Cleaners)", "Deep Restroom Disinfection & Full Campus Reset", "10:00 PM – 6:30 AM (Sat–Sun)", "13 Cleaners / Night", 208.0, 17.50, 21.00, 3640.00)
]

r_pos = sec2_start + 4
for p_data in positions_data:
    ws.row_dimensions[r_pos].height = 34.0
    for c_idx, p_val in enumerate(p_data, start=1):
        cell = ws.cell(row=r_pos, column=c_idx, value=p_val)
        cell.border = thin_border
        cell.font = font_regular
        if c_idx in [1, 4, 5]:
            cell.alignment = Alignment(horizontal="center", vertical="center")
        elif c_idx in [2, 3]:
            cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
            if c_idx == 2:
                cell.font = font_bold
        elif c_idx in [6, 7, 8, 9]:
            cell.alignment = Alignment(horizontal="right", vertical="center")
            if c_idx == 6:
                cell.number_format = "#,##0.0 \"hrs\""
            else:
                cell.number_format = "$#,##0.00"
    r_pos += 1

# Shift Grouping Brackets in Column A (Clean Executive Alignment)
shift_group_ranges = [
    (sec2_start + 4, sec2_start + 8, "Weekday Daytime\n(Mon–Fri)\n[SOW Day 6-Day]"),
    (sec2_start + 9, sec2_start + 12, "Weekday Night\n(Mon–Fri)\n[SOW Night 7-Day]"),
    (sec2_start + 13, sec2_start + 15, "Saturday Daytime\n(Saturday)\n[SOW Day 6-Day]"),
    (sec2_start + 16, sec2_start + 19, "Weekend Night\n(Sat–Sun)\n[SOW Night 7-Day]")
]
for start_row, end_row, shift_label in shift_group_ranges:
    ws.merge_cells(start_row=start_row, start_column=1, end_row=end_row, end_column=1)
    grp_cell = ws.cell(row=start_row, column=1, value=shift_label)
    grp_cell.font = font_bold
    grp_cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for r in range(start_row, end_row + 1):
        ws.cell(row=r, column=1).border = thin_border

# Section 2.0 Totals Row (Matching Section 1.0 Executive Blue & Double Underline)
ws.cell(row=r_pos, column=1, value="TOTAL CAMPUS WORKFORCE (28 Full-Time Equivalent Workers | 4 Floor Techs)").font = font_bold
ws.merge_cells(start_row=r_pos, start_column=1, end_row=r_pos, end_column=4)
ws.cell(row=r_pos, column=5, value="140 Weekly Work Shifts").alignment = Alignment(horizontal="center", vertical="center")
ws.cell(row=r_pos, column=6, value=f"=SUM(F{sec2_start+4}:F{r_pos-1})").number_format = "#,##0.0 \"hrs\""
ws.cell(row=r_pos, column=7, value="Average Pay: $18.21").alignment = Alignment(horizontal="right", vertical="center")
ws.cell(row=r_pos, column=8, value="With Taxes: $21.85").alignment = Alignment(horizontal="right", vertical="center")
ws.cell(row=r_pos, column=9, value=f"=SUM(I{sec2_start+4}:I{r_pos-1})").number_format = "$#,##0.00"
for c_idx in range(1, 10):
    cl = ws.cell(row=r_pos, column=c_idx)
    cl.fill = PatternFill(start_color="BFDBFE", end_color="BFDBFE", fill_type="solid")
    cl.font = font_bold
    cl.border = double_bottom_border
ws.row_dimensions[r_pos].height = 30.0

# Spacer Row between Table 2 and Zero-Overtime Banner
r_spacer2 = r_pos + 1
ws.row_dimensions[r_spacer2].height = 10.0
ws.merge_cells(f"A{r_spacer2}:I{r_spacer2}")
ws.cell(row=r_spacer2, column=1, value="")

# Zero Overtime Banner
# Zero Overtime Banner
r_ot = r_spacer2 + 1
ws.cell(row=r_ot, column=1, value=(
    "⚡ ZERO-OVERTIME COMMITMENT: Our schedule spreads 140 weekly shifts across 29 to 32 trained workers capped at "
    "32 to 40 regular hours per week (including 4 floor specialists). Bosanna is never billed overtime charges "
    "($0.00 overtime), workers stay fresh, and backup cleaners step in when anyone is sick."
))
ws.merge_cells(start_row=r_ot, start_column=1, end_row=r_ot, end_column=9)
ws.cell(row=r_ot, column=1).font = font_alert_text
ws.cell(row=r_ot, column=1).fill = fill_amber_sub
ws.cell(row=r_ot, column=1).alignment = Alignment(vertical="center", wrap_text=True)
for c_idx in range(1, 10):
    ws.cell(row=r_ot, column=c_idx).border = Border(
        top=Side(style="thin", color=border_amber),
        bottom=Side(style="thin", color=border_amber),
        left=Side(style="thin", color=border_amber),
        right=Side(style="thin", color=border_amber)
    )
ws.row_dimensions[r_ot].height = 40.0

# -------------------------------------------------------------
# 3. SECTION 3.0: RESTROOM SUPPLIES & PAPER PRODUCTS (RFP LINE 42)
# -------------------------------------------------------------
sec3_start = r_ot + 1
ws.cell(row=sec3_start, column=1, value="3.0 RESTROOM SUPPLIES & PAPER PRODUCTS BREAKDOWN (RFP LINE 42)")
ws.merge_cells(start_row=sec3_start, start_column=1, end_row=sec3_start, end_column=9)
ws.cell(row=sec3_start, column=1).font = font_sec_hdr
ws.cell(row=sec3_start, column=1).fill = fill_sec_hdr
ws.cell(row=sec3_start, column=1).alignment = Alignment(horizontal="left", vertical="center", indent=1)
ws.row_dimensions[sec3_start].height = 26.0

sec3_narrative_factual = (
    "Restroom Supplies & Daily Refill Plan:\n"
    "• Complete Campus Supplies: We provide all paper towels, toilet paper, hand soap, trash bags, and batteries for all 10 campus buildings at one flat price ($8,332.50/mo | $99,990.00/yr).\n"
    "• Perfect Fit & Daily Refills: All paper towels, toilet paper, and soap fit the college's existing dispensers. Our team inspects and restocks every restroom daily so supplies never run out."
)
ws.cell(row=sec3_start+1, column=1, value=sec3_narrative_factual)
ws.merge_cells(start_row=sec3_start+1, start_column=1, end_row=sec3_start+1, end_column=9)
ws.cell(row=sec3_start+1, column=1).font = font_italic
ws.cell(row=sec3_start+1, column=1).alignment = Alignment(vertical="center", wrap_text=True)
ws.row_dimensions[sec3_start+1].height = 56.0

# Spacer Row: Breathing Room between Narrative and Table 3 Headers
ws.row_dimensions[sec3_start+2].height = 10.0
ws.merge_cells(f"A{sec3_start+2}:I{sec3_start+2}")
ws.cell(row=sec3_start+2, column=1, value="")

tbl3_headers = [
    "Supply Category", "Item Name & Type", "Where It Is Used on Campus", "Case Size / Box Count",
    "Cases Per Year", "Cases Per Month", "Price Per Case ($)",
    "Monthly Total ($)", "Yearly Total ($)"
]
for col_idx, h in enumerate(tbl3_headers, start=1):
    c = ws.cell(row=sec3_start+3, column=col_idx, value=h)
    c.font = font_tbl_hdr
    c.fill = fill_tbl_hdr
    c.border = thin_border
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
ws.row_dimensions[sec3_start+3].height = 28.0

supplies_data = [
    # 1. Paper Towels & Cleaning Wipes (3 items)
    ("Paper Towels & Cleaning Wipes", "Jumbo Roll Paper Towels 10\"x800'", "Automatic Towel Dispensers (All Restrooms)", "6 Rolls/Case (4,800 ft)", 780, 65.0, 28.05, 1823.25, 21879.00),
    ("Paper Towels & Cleaning Wipes", "Folded Paper Hand Towels", "Kitchens, Breakrooms & Staff Lounges", "16 Packs/Case (4,000 Towels)", 240, 20.0, 23.65, 473.00, 5676.00),
    ("Paper Towels & Cleaning Wipes", "Heavy-Duty Cleaning Wipes", "Science Labs, Art Studios & Health Clinics", "16 Packs/Case (4,000 Wipes)", 360, 30.0, 25.85, 775.50, 9306.00),

    # 2. Toilet Paper & Seat Covers (3 items)
    ("Toilet Paper & Seat Covers", "Jumbo Toilet Paper Rolls 9\" (2-Ply)", "Main Student Restroom Stalls (9\" Dispensers)", "12 Rolls/Case (2,400 m)", 540, 45.0, 26.95, 1212.75, 14553.00),
    ("Toilet Paper & Seat Covers", "Standard Toilet Paper Rolls (2-Ply)", "Faculty, Staff & Single Restrooms", "80 Rolls/Case (40,000 Sheets)", 540, 45.0, 29.15, 1311.75, 15741.00),
    ("Toilet Paper & Seat Covers", "Toilet Seat Covers (Half-Fold)", "Restroom Stall Wall Dispensers", "20 Packs/Case (5,000 Covers)", 60, 5.0, 19.80, 99.00, 1188.00),

    # 3. Trash Bags & Disposal Liners (5 items)
    ("Trash Bags & Disposal Liners", "55-Gallon Heavy Trash Bags (40\"x48\")", "Large Campus Tilt Trucks & Outside Trash Cans", "250 Bags/Case", 264, 22.0, 26.95, 592.90, 7114.80),
    ("Trash Bags & Disposal Liners", "44-Gallon Heavy Trash Bags (37\"x46\")", "Main Hallways, Lobbies & Large Trash Cans", "250 Bags/Case", 264, 22.0, 24.20, 532.40, 6388.80),
    ("Trash Bags & Disposal Liners", "30-Gallon Trash Bags (30\"x37\")", "Classrooms & Restroom Trash Cans", "500 Bags/Case", 264, 22.0, 21.45, 471.90, 5662.80),
    ("Trash Bags & Disposal Liners", "10-Gallon Desk Trash Bags (24\"x24\")", "Faculty Offices & Staff Desk Baskets", "1,000 Bags/Case", 264, 22.0, 15.95, 350.90, 4210.80),
    ("Trash Bags & Disposal Liners", "Waxed Restroom Stall Disposal Bags", "Women's Restroom Stall Disposal Bins", "500 Liners/Case", 24, 2.0, 19.25, 38.50, 462.00),

    # 4. Hand Soap, Fresheners & Batteries (4 items)
    ("Hand Soap, Fresheners & Batteries", "Foaming Hand Soap Refills (1,000 ml)", "Automatic Restroom Soap Dispensers", "4 Bottles/Case (4,000 ml)", 96, 8.0, 27.50, 220.00, 2640.00),
    ("Hand Soap, Fresheners & Batteries", "Urinal Splash Screens & Fresheners", "Men's Restroom Urinals", "12 Screens/Box", 144, 12.0, 9.35, 112.20, 1346.40),
    ("Hand Soap, Fresheners & Batteries", "Automatic Air Freshener Cans", "Wall Air Freshener Dispensers (Restrooms)", "12 Cans/Case (4 Packs of 3)", 120, 10.0, 23.10, 231.00, 2772.00),
    ("Hand Soap, Fresheners & Batteries", "Alkaline D-Batteries for Dispensers", "Automatic Towel & Soap Dispensers", "12 Batteries/Box", 60, 5.0, 17.49, 87.45, 1049.40),
]

r_sup = sec3_start + 4
for s_data in supplies_data:
    ws.row_dimensions[r_sup].height = 34.0
    for c_idx, s_val in enumerate(s_data, start=1):
        cell = ws.cell(row=r_sup, column=c_idx, value=s_val)
        cell.border = thin_border
        cell.font = font_regular
        if c_idx == 1:
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        elif c_idx in [2, 3]:
            cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
            if c_idx == 2:
                cell.font = font_bold
        elif c_idx == 4:
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        elif c_idx == 5:
            cell.alignment = Alignment(horizontal="right", vertical="center")
            cell.number_format = "#,##0"
        elif c_idx == 6:
            cell.alignment = Alignment(horizontal="right", vertical="center")
            cell.number_format = "#,##0.0"
        elif c_idx in [7, 8, 9]:
            cell.alignment = Alignment(horizontal="right", vertical="center")
            cell.number_format = "$#,##0.00"
    r_sup += 1

# Category Grouping in Column A
supply_group_ranges = [
    (sec3_start + 4, sec3_start + 6, "Paper Towels\n& Wipes\n[T&C Supplies]"),
    (sec3_start + 7, sec3_start + 9, "Toilet Paper\n& Covers\n[T&C Supplies]"),
    (sec3_start + 10, sec3_start + 14, "Trash Bags\n& Liners\n[SOW Waste Bins]"),
    (sec3_start + 15, sec3_start + 18, "Soap, Cleaners\n& Batteries\n[T&C Supplies]")
]
for start_row, end_row, grp_label in supply_group_ranges:
    ws.merge_cells(start_row=start_row, start_column=1, end_row=end_row, end_column=1)
    grp_cell = ws.cell(row=start_row, column=1, value=grp_label)
    grp_cell.font = font_bold
    grp_cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for r in range(start_row, end_row + 1):
        ws.cell(row=r, column=1).border = thin_border

# Section 3.0 Totals Row (Matching Executive Blue & Double Underline)
ws.cell(row=r_sup, column=1, value="TOTAL RESTROOM SUPPLIES: COMPLETE CAMPUS MONTHLY PACKAGE (RFP LINE 42)").font = font_bold
ws.merge_cells(start_row=r_sup, start_column=1, end_row=r_sup, end_column=4)
ws.cell(row=r_sup, column=5, value=f"=SUM(E{sec3_start+4}:E{r_sup-1})").number_format = "#,##0 \"Cases\""
ws.cell(row=r_sup, column=6, value=f"=SUM(F{sec3_start+4}:F{r_sup-1})").number_format = "#,##0.0 \"Cases/Mo\""
ws.cell(row=r_sup, column=7, value="Contract Price").alignment = Alignment(horizontal="center", vertical="center")
ws.cell(row=r_sup, column=8, value=f"=SUM(H{sec3_start+4}:H{r_sup-1})").number_format = "$#,##0.00"
ws.cell(row=r_sup, column=9, value=f"=SUM(I{sec3_start+4}:I{r_sup-1})").number_format = "$#,##0.00"
for c_idx in range(1, 10):
    cl = ws.cell(row=r_sup, column=c_idx)
    cl.fill = PatternFill(start_color="BFDBFE", end_color="BFDBFE", fill_type="solid")
    cl.font = font_bold
    cl.border = double_bottom_border
ws.row_dimensions[r_sup].height = 30.0

# Spacer Row between Table 3 and Supply Banner
r_spacer3 = r_sup + 1
ws.row_dimensions[r_spacer3].height = 10.0
ws.merge_cells(f"A{r_spacer3}:I{r_spacer3}")
ws.cell(row=r_spacer3, column=1, value="")

# Supply Inventory Commitment Banner
r_sup_banner = r_spacer3 + 1
ws.cell(row=r_sup_banner, column=1, value=(
    "📦 RESTROOM SUPPLY COMMITMENT: All paper towels, toilet paper, hand soap, trash bags, and batteries are provided for all 10 campus buildings "
    "under one fixed monthly price ($8,332.50/mo). Our cleaning team checks and refills every dispenser daily so the campus never runs out of supplies."
))
ws.merge_cells(start_row=r_sup_banner, start_column=1, end_row=r_sup_banner, end_column=9)
ws.cell(row=r_sup_banner, column=1).font = font_alert_text
ws.cell(row=r_sup_banner, column=1).fill = fill_amber_sub
ws.cell(row=r_sup_banner, column=1).alignment = Alignment(vertical="center", wrap_text=True)
for c_idx in range(1, 10):
    ws.cell(row=r_sup_banner, column=c_idx).border = Border(
        top=Side(style="thin", color=border_amber),
        bottom=Side(style="thin", color=border_amber),
        left=Side(style="thin", color=border_amber),
        right=Side(style="thin", color=border_amber)
    )
ws.row_dimensions[r_sup_banner].height = 40.0

# -------------------------------------------------------------
# 4. SECTION 4.0: PROOF OF HOURS & TIME TRACKING
# -------------------------------------------------------------
sec4_start = r_sup_banner + 1
ws.cell(row=sec4_start, column=1, value="4.0 PROOF OF HOURS WORKED: FINGERPRINT TIME CLOCK & POLICE LOGBOOK RECORDS")
ws.merge_cells(start_row=sec4_start, start_column=1, end_row=sec4_start, end_column=9)
ws.cell(row=sec4_start, column=1).font = font_sec_hdr
ws.cell(row=sec4_start, column=1).fill = fill_sec_hdr
ws.cell(row=sec4_start, column=1).alignment = Alignment(horizontal="left", vertical="center", indent=1)
ws.row_dimensions[sec4_start].height = 26.0

sec4_narrative_factual = (
    "How We Track Daily Hours & Keep Honest Records:\n"
    "• Fingerprint Time Clock: Every cleaner scans their fingerprint in Building S when starting and finishing work. This proves exactly who is on campus and when they worked.\n"
    "• Police Desk Sign-In: Cleaners also sign a paper logbook at the campus police desk each day. Officers see our team arrive and leave, giving the college clear, trusted proof of daily work."
)
ws.cell(row=sec4_start+1, column=1, value=sec4_narrative_factual)
ws.merge_cells(start_row=sec4_start+1, start_column=1, end_row=sec4_start+1, end_column=9)
ws.cell(row=sec4_start+1, column=1).font = font_italic
ws.cell(row=sec4_start+1, column=1).alignment = Alignment(vertical="center", wrap_text=True)
ws.row_dimensions[sec4_start+1].height = 56.0

# Spacer Row: Breathing Room between Narrative and Table 4 Headers
ws.row_dimensions[sec4_start+2].height = 10.0
ws.merge_cells(f"A{sec4_start+2}:I{sec4_start+2}")
ws.cell(row=sec4_start+2, column=1, value="")

tbl4_headers = [
    "Tracking Step", "How It Works", "Campus Location", "Work Hours & Shift Times",
    "Who Is Involved", "Proof Record / Paperwork", "Contract Section & Rule",
    "Who Checks It", "Why This Protects the College"
]
for col_idx, h in enumerate(tbl4_headers, start=1):
    c = ws.cell(row=sec4_start+3, column=col_idx, value=h)
    c.font = font_tbl_hdr
    c.fill = fill_tbl_hdr
    c.border = thin_border
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
ws.row_dimensions[sec4_start+3].height = 28.0

audit_data = [
    ("1. Fingerprint Clock", "Cellular Fingerprint Time Clock", "Custodial Breakroom (Bldg S)", "10:00 PM & 6:30 AM / 8:00 AM & 4:30 PM", "All 28 Cleaners", "Digital Fingerprint Punch Record", "SOW § Biometric Clock", "Campus Police & Facilities Team", "Cleaners scan in personally. No one can clock in for a friend, and every minute worked is saved accurately."),
    ("2. Police Desk Log", "Paper Sign-In Sheet at Police Desk", "Campus Police Desk (Bldg S)", "Start & End of Every Shift", "Cleaners & On-Duty Police Officers", "Signed Paper Sign-In Sheet", "T&C § Police Desk Log", "Collin College Police Officers", "Campus police officers see each cleaner sign in and out, giving independent proof that our team was on campus."),
    ("3. Shift Supervisor", "Building Walks & Key Checks", "All 10 Campus Buildings (478,418 SF)", "Continuous 8-Hour Shift Checks", "Full-Time Shift Supervisor", "Daily Cleaning Checklist", "SOW § Supervisor Walks", "Facilities Director", "Supervisors walk the campus to check cleaning quality, keep master keys safe, and fix any spills within 20 minutes."),
    ("4. Weekly Time Check", "Payroll & Time Sheet Match", "HWB Central Office", "Weekly Payroll Review", "Payroll Manager", "Weekly Hours Report", "SOW § 1,120 Weekly Hours", "Bosanna & College Leadership", "We match digital fingerprint logs with police sign-in sheets every week. All hours are kept to regular time with zero overtime costs."),
    ("5. Monthly Invoice Backup", "Printed Time Records with Bill", "Sent with Monthly Invoice", "Monthly Billing (Line 41)", "Account Director", "Monthly Signed Time Records", "T&C § Monthly Invoices", "College Accounts Payable", "Every monthly bill includes printed proof of all hours worked, so the college can pay invoices with total confidence.")
]

r_aud = sec4_start + 4
for a_data in audit_data:
    ws.row_dimensions[r_aud].height = 34.0
    for c_idx, a_val in enumerate(a_data, start=1):
        cell = ws.cell(row=r_aud, column=c_idx, value=a_val)
        cell.border = thin_border
        cell.font = font_regular
        if c_idx == 1:
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.font = font_bold
        elif c_idx == 2:
            cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
            cell.font = font_bold
        elif c_idx in [3, 9]:
            cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        elif c_idx in [4, 5, 6, 7, 8]:
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            if c_idx == 7:
                cell.font = font_bold
    r_aud += 1

# Section 4.0 Totals Row (Matching Executive Blue & Double Underline)
ws.cell(row=r_aud, column=1, value="TOTAL VERIFIED HOURS: 100% OF 1,120.0 WEEKLY HOURS CONFIRMED BY DUAL RECORDS").font = font_bold
ws.merge_cells(start_row=r_aud, start_column=1, end_row=r_aud, end_column=4)
ws.cell(row=r_aud, column=5, value="28.0 Staff").alignment = Alignment(horizontal="center", vertical="center")
ws.cell(row=r_aud, column=6, value="140 Weekly Shifts").alignment = Alignment(horizontal="center", vertical="center")
ws.cell(row=r_aud, column=7, value="1,120.0 Hrs/Wk").alignment = Alignment(horizontal="center", vertical="center")
ws.cell(row=r_aud, column=8, value="$0.00 Overtime").alignment = Alignment(horizontal="center", vertical="center")
ws.cell(row=r_aud, column=9, value="Printed Time Records Included with Every Monthly Bill").alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
for c_idx in range(1, 10):
    cl = ws.cell(row=r_aud, column=c_idx)
    cl.fill = PatternFill(start_color="BFDBFE", end_color="BFDBFE", fill_type="solid")
    cl.font = font_bold
    cl.border = double_bottom_border
ws.row_dimensions[r_aud].height = 30.0

# Spacer Row between Table 4 and Banner
r_spacer4 = r_aud + 1
ws.row_dimensions[r_spacer4].height = 10.0
ws.merge_cells(f"A{r_spacer4}:I{r_spacer4}")
ws.cell(row=r_spacer4, column=1, value="")

# Verified Hours Promise Banner
r_aud_banner = r_spacer4 + 1
ws.cell(row=r_aud_banner, column=1, value=(
    "🛡️ 100% VERIFIED HOURS PROMISE: All 1,120.0 weekly hours are confirmed with fingerprint time clocks and police desk sign-in sheets "
    "before any invoice is sent. This gives Collin College and Bosanna LLC clear, trusted records for every hour worked, with zero guesswork and zero surprise charges."
))
ws.merge_cells(start_row=r_aud_banner, start_column=1, end_row=r_aud_banner, end_column=9)
ws.cell(row=r_aud_banner, column=1).font = font_alert_text
ws.cell(row=r_aud_banner, column=1).fill = fill_amber_sub
ws.cell(row=r_aud_banner, column=1).alignment = Alignment(vertical="center", wrap_text=True)
for c_idx in range(1, 10):
    ws.cell(row=r_aud_banner, column=c_idx).border = Border(
        top=Side(style="thin", color=border_amber),
        bottom=Side(style="thin", color=border_amber),
        left=Side(style="thin", color=border_amber),
        right=Side(style="thin", color=border_amber)
    )
ws.row_dimensions[r_aud_banner].height = 40.0

# Column Widths
col_widths = {
    "A": 22.0,  # Line # / Shift & Work Days / Supply Category / Layer
    "B": 24.0,  # Job Title / Product Item / Protocol & System (Dedicated Column!)
    "C": 36.0,  # Campus Building Duties / Dispenser & Location / Physical Location (Dedicated Column!)
    "D": 20.0,  # Unit / Working Hours / Packaging / Schedule
    "E": 18.0,  # Billing Schedule / Workers on Duty / Annual Qty / Personnel
    "F": 16.0,  # HWB Price ($) / Weekly Hours / Monthly Qty / Proof Document
    "G": 16.0,  # Monthly Total ($) / Base Hourly Pay / Wholesale Unit Price / SOW Mandate
    "H": 18.0,  # Yearly Total ($) / Loaded Pay / Monthly Passthrough ($) / Authority
    "I": 46.0   # Description / Weekly Base Pay ($) / Annual Passthrough ($) / Legal Defense
}
for c_let, w in col_widths.items():
    ws.column_dimensions[c_let].width = w

# -------------------------------------------------------------
# LANDSCAPE PRINTING & NARROW MARGIN SETUP (MAXIMUM DATA)
# -------------------------------------------------------------
ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
ws.page_setup.paperSize = ws.PAPERSIZE_LETTER
ws.sheet_properties.pageSetUpPr.fitToPage = True
ws.page_setup.fitToWidth = 1
ws.page_setup.fitToHeight = 0

# Narrow margins for maximum printable data
ws.page_margins.left = 0.25
ws.page_margins.right = 0.25
ws.page_margins.top = 0.35
ws.page_margins.bottom = 0.35
ws.page_margins.header = 0.15
ws.page_margins.footer = 0.15

ws.print_options.horizontalCentered = True
ws.print_area = f"A1:I{r_aud_banner}"
ws.print_title_rows = "1:8"

# Clean Page Breaks:
# Page 1: Title, Meta, Top-Line Summary KPI Cards & Section 1.0 Pricing Table 1 (Row 26)
# Page 2: Section 2.0 Staffing Roster Table & Zero-Overtime Banner (Row r_ot)
# Page 3: Section 3.0 Consumable Supplies Breakdown & Inventory Banner (Row r_sup_banner)
# Page 4: Section 4.0 Dual-Layer Biometric Attendance & Audit Defense System (Row r_aud_banner)
ws.row_breaks.append(Break(id=26))
ws.row_breaks.append(Break(id=r_ot))
ws.row_breaks.append(Break(id=r_sup_banner))

# -------------------------------------------------------------
# 4. PREVENT CUTOFF & CONFIGURE PRINT IN CAMPUS BUILDING TAKEOFF
# -------------------------------------------------------------
ws_takeoff = wb["Campus_Building_Takeoff"]
ws_takeoff.views.sheetView[0].showGridLines = True
takeoff_widths = {
    "A": 8.0,
    "B": 24.0,
    "C": 38.0,
    "D": 16.0,
    "E": 18.0,
    "F": 18.0,
    "G": 18.0,
    "H": 16.0,
    "I": 14.0,
    "J": 14.0,
    "K": 36.0,
    "L": 18.0,
    "M": 24.0
}
for c_let, w in takeoff_widths.items():
    ws_takeoff.column_dimensions[c_let].width = w

for r in range(5, 15):
    ws_takeoff.row_dimensions[r].height = 22.0
ws_takeoff.row_dimensions[15].height = 26.0

# Amber Notice rows
ws_takeoff.row_dimensions[17].height = 28.0
ws_takeoff.row_dimensions[18].height = 24.0
for r in range(19, 26):
    ws_takeoff.row_dimensions[r].height = 52.0

ws_takeoff.page_setup.orientation = ws_takeoff.ORIENTATION_LANDSCAPE
ws_takeoff.page_setup.paperSize = ws_takeoff.PAPERSIZE_LETTER
ws_takeoff.sheet_properties.pageSetUpPr.fitToPage = True
ws_takeoff.page_setup.fitToWidth = 1
ws_takeoff.page_setup.fitToHeight = 0
ws_takeoff.page_margins.left = 0.25
ws_takeoff.page_margins.right = 0.25
ws_takeoff.page_margins.top = 0.40
ws_takeoff.page_margins.bottom = 0.40
ws_takeoff.print_options.horizontalCentered = True

# -------------------------------------------------------------
# 5. REBUILD & CONFIGURE PRINT IN COST UNDERWRITING AUDIT
# -------------------------------------------------------------
idx_cost = wb.sheetnames.index("Cost_Underwriting_Audit")
wb.remove(wb["Cost_Underwriting_Audit"])
ws_cost = wb.create_sheet("Cost_Underwriting_Audit", idx_cost)

ws_cost.views.sheetView[0].showGridLines = True

ws_cost.cell(row=1, column=1, value="HWB CLEANING SERVICES LLC — INTERNAL SUBCONTRACT UNDERWRITING AUDIT")
ws_cost.merge_cells("A1:G1")
ws_cost.cell(row=1, column=1).font = font_title
ws_cost.cell(row=1, column=1).fill = fill_navy_title
ws_cost.cell(row=1, column=1).alignment = Alignment(horizontal="center", vertical="center")
ws_cost.row_dimensions[1].height = 30.0

ws_cost.cell(row=2, column=1, value="INTERNAL FINANCIAL BASE, COGS, G&A ALLOCATION & NET EBITDA (EXCLUDING PRIME MARKUP)")
ws_cost.merge_cells("A2:G2")
ws_cost.cell(row=2, column=1).font = font_subtitle
ws_cost.cell(row=2, column=1).fill = fill_navy_sub
ws_cost.cell(row=2, column=1).alignment = Alignment(horizontal="center", vertical="center")
ws_cost.row_dimensions[2].height = 24.0

cost_headers = [
    "Category", "Internal Line Item Description", "Cost Basis / Calculation Detail",
    "Monthly Revenue / Cost ($)", "Annual Commitment ($)", "% of Subcontract Base", "Operational Governance & SOW Traceability Notes"
]
for col_idx, h in enumerate(cost_headers, start=1):
    c = ws_cost.cell(row=4, column=col_idx, value=h)
    c.font = font_tbl_hdr
    c.fill = fill_tbl_hdr
    c.border = thin_border
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
ws_cost.row_dimensions[4].height = 28.0

cost_rows = [
    ("Subcontract Revenue", "HWB Wholesale Subcontract Base (Billed to Bosanna)", "1,120.0 hrs/wk: $17.50/hr Cleaners, $19.50/hr Techs, $23.00/hr Supervisors", 141316.70, 1695800.40, 1.000, "Turnkey subcontract price charged to Bosanna LLC ($3.54/SF/Yr: Labor + Consumables)"),
    ("COGS (Base Labor)", "Direct Base Wages (Cleaners, Techs & Supervisors)", "1,120.0 hrs/wk (28.0 FTEs): 29–32 badged W-2 employees strictly capped at 32-40 straight-time hrs/wk", -88382.67, -1060592.00, -0.625, "Gold Standard Wages: $17.50 Cln/Porter, $19.50 Floor Tech, $23.00 Sup. Zero Overtime."),
    ("COGS (Burden)", "Payroll Burden & Statutory Taxes (+20.0% Loaded Factor)", "FICA (7.65%), SUTA (2.7%), FUTA (0.6%), WC Code 9014 (4.85%), Payroll Admin (4.2%)", -17676.53, -212118.40, -0.125, "Full Texas statutory labor burden, worker compensation & payroll float"),
    ("COGS (Supplies)", "Consumable Restroom Supplies & Paper Goods Baseline", "RFP Line 42: Restroom paper towels, jumbo rolls, soap & trash liners direct wholesale baseline", -7575.00, -90900.00, -0.054, "Direct manufacturer wholesale baseline ($7,575/mo) with 10% price buffer retained in billing"),
    ("COGS (Chemistry)", "Special Projects Chemicals, Stripper & High-Solid Wax", "4-coat high-solid acrylic wax, floor stripper, carpet chemistry, pads", -1400.00, -16800.00, -0.010, "Restorative floor maintenance chemistry & diamond honing consumables"),
    ("COGS (Equipment)", "Heavy Equipment Fleet Amortization & Pad/Parts Service", "28\" Ride-on scrubber, 4 walk-behinds, 4 burnishers, 8 HEPA backpacks", -850.00, -10200.00, -0.006, "3-Year straight-line capital amortization & brush replacement float"),
    ("COGS (Compliance)", "FAST DPS/FBI Fingerprints, Biometric Clock & Uniforms", "TxDPS FAST clearing (§ 22.0834), cellular biometric time clock & apparel", -600.00, -7200.00, -0.004, "Contractually mandated biometric fingerprint clock cellular data plan"),
    ("Gross Profit", "HWB GROSS OPERATING PROFIT", "Subcontract Revenue ($141,316.70) minus Total Direct COGS ($116,484.20)", 24832.50, 297990.00, 0.176, "17.57% Gross Operating Margin on Subcontract Revenue"),
    ("G&A Overhead", "Operations Manager / ISO 9001 Inspections Allocation", "Dedicated field leadership, weekly QMS quality audits, night sweeps", -2000.00, -24000.00, -0.014, "Senior executive quality control & APPA Level 2 audit verification"),
    ("G&A Overhead", "Recruiting, HR Onboarding & Badging Compliance Pipeline", "Continuous pipeline recruiting to sustain zero-overtime badged roster", -1000.00, -12000.00, -0.007, "Dedicated Collin County HR recruiting & background investigation float"),
    ("G&A Overhead", "Janitorial Surety Bond & Specific Insurance Riders", "Janitorial Surety Bond, Waiver of Subrogation, Additional Insured Riders", -600.00, -7200.00, -0.004, "Full insurance compliance per RFP Terms & Conditions"),
    ("G&A Overhead", "Corporate SG&A, Antigravity AI Cloud & Legal/Accounting", "Enterprise software, accounting, legal counsel, banking float", -500.00, -6000.00, -0.004, "Fixed corporate administration overhead allocation"),
    ("Net Profit", "HWB NET OPERATING PROFIT (EBITDA)", "Gross Operating Profit ($24,832.50) minus Total G&A Overhead ($4,100.00)", 20732.50, 248790.00, 0.147, "14.64% Net Operating EBITDA Margin on Wholesale Subcontract Base")
]

for idx, r_data in enumerate(cost_rows, start=5):
    ws_cost.row_dimensions[idx].height = 26.0
    for c_idx, val in enumerate(r_data, start=1):
        cell = ws_cost.cell(row=idx, column=c_idx, value=val)
        cell.border = thin_border
        cell.font = font_regular
        if c_idx == 1:
            cell.alignment = Alignment(horizontal="center", vertical="center")
            if val in ["Subcontract Revenue", "Gross Profit", "Net Profit"]:
                cell.font = font_bold
        elif c_idx in [2, 3]:
            cell.alignment = Alignment(horizontal="left", vertical="center")
            if val in ["HWB GROSS OPERATING PROFIT", "HWB NET OPERATING PROFIT (EBITDA)", "HWB Wholesale Subcontract Base (Billed to Bosanna)"]:
                cell.font = font_bold
        elif c_idx in [4, 5]:
            cell.alignment = Alignment(horizontal="right", vertical="center")
            cell.number_format = "$#,##0.00"
            if r_data[0] in ["Subcontract Revenue", "Gross Profit", "Net Profit"]:
                cell.font = font_bold
        elif c_idx == 6:
            cell.alignment = Alignment(horizontal="right", vertical="center")
            cell.number_format = "0.0%"
            if r_data[0] in ["Subcontract Revenue", "Gross Profit", "Net Profit"]:
                cell.font = font_bold
        elif c_idx == 7:
            cell.alignment = Alignment(horizontal="left", vertical="center")

    if r_data[0] in ["Subcontract Revenue", "Gross Profit"]:
        for c in range(1, 8):
            ws_cost.cell(row=idx, column=c).fill = fill_tbl_hdr
    elif r_data[0] == "Net Profit":
        for c in range(1, 8):
            ws_cost.cell(row=idx, column=c).fill = PatternFill(start_color="BFDBFE", end_color="BFDBFE", fill_type="solid")
            ws_cost.cell(row=idx, column=c).border = double_bottom_border

cost_widths = {
    "A": 22.0,
    "B": 52.0,
    "C": 78.0,
    "D": 26.0,
    "E": 28.0,
    "F": 22.0,
    "G": 78.0
}
for c_let, w in cost_widths.items():
    ws_cost.column_dimensions[c_let].width = w

ws_cost.page_setup.orientation = ws_cost.ORIENTATION_LANDSCAPE
ws_cost.page_setup.paperSize = ws_cost.PAPERSIZE_LETTER
ws_cost.sheet_properties.pageSetUpPr.fitToPage = True
ws_cost.page_setup.fitToWidth = 1
ws_cost.page_setup.fitToHeight = 0
ws_cost.page_margins.left = 0.25
ws_cost.page_margins.right = 0.25
ws_cost.page_margins.top = 0.40
ws_cost.page_margins.bottom = 0.40
ws_cost.print_options.horizontalCentered = True

# -------------------------------------------------------------
# 6. CONFIGURE PRINT IN SERVICE GANTT SCHEDULE
# -------------------------------------------------------------
ws_gantt = wb["Service_Gantt_Schedule"]
ws_gantt.page_setup.orientation = ws_gantt.ORIENTATION_LANDSCAPE
ws_gantt.page_setup.paperSize = ws_gantt.PAPERSIZE_LETTER
ws_gantt.sheet_properties.pageSetUpPr.fitToPage = True
ws_gantt.page_setup.fitToWidth = 1
ws_gantt.page_setup.fitToHeight = 0
ws_gantt.page_margins.left = 0.25
ws_gantt.page_margins.right = 0.25
ws_gantt.page_margins.top = 0.40
ws_gantt.page_margins.bottom = 0.40
ws_gantt.print_options.horizontalCentered = True

# Save master workbook and execute modular sheet builders
wb.save(wb_path)

import subprocess
subprocess.run(["python3", "scripts/add_executive_brief_sheet.py"], check=True)
subprocess.run(["python3", "scripts/add_training_matrix_sheet.py"], check=True)

print("All 6 master worksheets successfully built, professionally formatted, and synchronized!")
