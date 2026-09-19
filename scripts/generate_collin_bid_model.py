import os
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

def build_bid_model():
    wb = openpyxl.Workbook()
    wb.remove(wb.active) # Remove default sheet

    # Color Palette & Styles
    navy_header_fill = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")
    dark_blue_fill = PatternFill(start_color="2C5282", end_color="2C5282", fill_type="solid")
    steel_fill = PatternFill(start_color="4A5568", end_color="4A5568", fill_type="solid")
    light_blue_fill = PatternFill(start_color="EBF8FF", end_color="EBF8FF", fill_type="solid")
    light_grey_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    accent_gold_fill = PatternFill(start_color="FEFCBF", end_color="FEFCBF", fill_type="solid")
    alert_amber_fill = PatternFill(start_color="FFF3CD", end_color="FFF3CD", fill_type="solid")
    success_green_fill = PatternFill(start_color="D1E7DD", end_color="D1E7DD", fill_type="solid")
    gantt_sp_fill = PatternFill(start_color="3182CE", end_color="3182CE", fill_type="solid") # Blue for SP
    gantt_fc_fill = PatternFill(start_color="DD6B20", end_color="DD6B20", fill_type="solid") # Orange for Floor Care
    gantt_rt_fill = PatternFill(start_color="38A169", end_color="38A169", fill_type="solid") # Green for Routine

    font_title = Font(name="Calibri", size=15, bold=True, color="FFFFFF")
    font_sub_title = Font(name="Calibri", size=11, bold=True, color="E2E8F0")
    font_section = Font(name="Calibri", size=12, bold=True, color="1B365D")
    font_section_dark = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_header = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    font_bold = Font(name="Calibri", size=10, bold=True, color="1E293B")
    font_regular = Font(name="Calibri", size=10, color="1E293B")
    font_small = Font(name="Calibri", size=9, color="4A5568")
    font_small_bold = Font(name="Calibri", size=9, bold=True, color="1E293B")
    font_callout_title = Font(name="Calibri", size=10, bold=True, color="856404")
    font_callout_body = Font(name="Calibri", size=9, color="533F03")
    font_green_bold = Font(name="Calibri", size=11, bold=True, color="0F5132")
    font_white_bold = Font(name="Calibri", size=10, bold=True, color="FFFFFF")

    thin_border_side = Side(style='thin', color='CBD5E0')
    thick_bottom_side = Side(style='medium', color='1B365D')
    double_bottom_side = Side(style='double', color='1B365D')
    
    cell_border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)
    header_border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thick_bottom_side)
    total_border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=double_bottom_side)

    # -------------------------------------------------------------
    # TAB 1: Commercial_Proposal
    # -------------------------------------------------------------
    ws1 = wb.create_sheet(title="Commercial_Proposal")
    ws1.views.sheetView[0].showGridLines = True

    # Title Block
    ws1.merge_cells("A1:H1")
    ws1["A1"] = "HWB CLEANING SERVICES LLC"
    ws1["A1"].font = font_title
    ws1["A1"].fill = navy_header_fill
    ws1["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws1.row_dimensions[1].height = 28

    ws1.merge_cells("A2:H2")
    ws1["A2"] = "INSTITUTIONAL COMMERCIAL SUBCONTRACT BID: COLLIN COLLEGE — FRISCO CAMPUS (478,418 CLEANABLE SF)"
    ws1["A2"].font = font_sub_title
    ws1["A2"].fill = dark_blue_fill
    ws1["A2"].alignment = Alignment(horizontal="center", vertical="center")
    ws1.row_dimensions[2].height = 22

    metadata = [
        ("Prime Contractor:", "Bosanna LLC (Attn: Angelica Hudgins)", "Solicitation:", "Collin College Frisco Custodial Replacement"),
        ("TIPS Purchasing Contracts:", "TIPS #260103 / #260102", "Effective Term:", "Three (3) Year Base + Two (2) One-Year Options"),
        ("Cleanable Square Footage:", "478,418 Cleanable SF across 10 Campus Buildings", "Cleaning Standard:", "APPA Level 2 (Ordinary Tidiness Guaranteed)"),
        ("Mandated Campus Staffing:", "904.0 Hours/Week (22.6 FTEs: 17 Weekdays / 15 Sat / 13 Sun)", "Time Audit Protocol:", "Dual Biometric Fingerprint + Police Desk Logbook")
    ]
    for idx, (k1, v1, k2, v2) in enumerate(metadata, start=4):
        ws1[f"A{idx}"] = k1; ws1[f"A{idx}"].font = font_bold
        ws1[f"B{idx}"] = v1; ws1[f"B{idx}"].font = font_regular
        ws1.merge_cells(f"B{idx}:D{idx}")
        ws1[f"E{idx}"] = k2; ws1[f"E{idx}"].font = font_bold
        ws1[f"F{idx}"] = v2; ws1[f"F{idx}"].font = font_regular
        ws1.merge_cells(f"F{idx}:H{idx}")
        ws1.row_dimensions[idx].height = 18

    # Section: Executive Narrative & Pritchard Mitigation
    ws1.cell(9, 1, "1.0 EXECUTIVE PRICING & OPERATIONS ARCHITECTURE (SCENARIO A — RECOMMENDED)").font = font_section
    ws1.merge_cells("A9:H9")
    narrative_1 = (
        "Bosanna LLC Subcontract Partnership Structure: HWB Cleaning Services LLC provides full turnkey operational execution, "
        "supplying all 904.0 weekly labor hours, 23-25 badged employees, heavy floor equipment, and chemistry. HWB's wholesale subcontract base "
        "is $104,518.00/month ($1,254,216.00/year). In Scenario A, Bosanna LLC applies the 1.0% mandatory TIPS fee ($1,244.26/mo) and a 15.0% "
        "prime contract fee ($18,663.93/mo) onto the District proposal, yielding a total District price of $124,426.19/month ($1,493,114.28/year = $3.12/SF). "
        "Bosanna pockets $223,967.14 annually with zero field labor. Collin College is fully authorized under T&C Section 41 to backcharge the difference over "
        "Pritchard Industries Southwest's defaulted contract."
    )
    ws1.cell(10, 1, narrative_1).font = font_small
    ws1.cell(10, 1).alignment = Alignment(wrap_text=True, vertical="top")
    ws1.merge_cells("A10:H10")
    ws1.row_dimensions[10].height = 50

    # Pricing Table Header
    headers_ws1 = ["Line #", "RFP Line Item Description", "Unit of Measure", "HWB Wholesale Subcontract", "TIPS Fee (1.0%)", "Bosanna Prime (15%)", "Total District Submittal", "Annual District Commitment"]
    ws1.row_dimensions[12].height = 26
    for col_idx, h in enumerate(headers_ws1, start=1):
        c = ws1.cell(12, col_idx, h)
        c.font = font_header
        c.fill = navy_header_fill
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = header_border

    bid_lines = [
        (41, "Scheduled Custodial Labor (904 hrs/wk, 12+1 Night, 4 Day Porters M-F, 2 Sat)", "Month", 96943.00, 1153.92, 17308.77, 115405.69, 1384868.28),
        (42, "Consumable Cleaning Supplies & Restroom Paper Products Passthrough", "Month", 7575.00, 90.34, 1355.16, 9020.50, 108246.00),
        (43, "Unscheduled Custodial Help: Monday - Friday (Per Person-Hour)", "Hour", 28.50, 0.34, 5.10, 33.94, None),
        (44, "Unscheduled Custodial Help: Saturday (Per Person-Hour)", "Hour", 32.00, 0.38, 5.72, 38.10, None),
        (45, "Unscheduled Custodial Help: Sunday & Holidays (Per Person-Hour)", "Hour", 38.00, 0.45, 6.79, 45.24, None),
        (46, "Unscheduled Floor Care: Tile Deep Stripping & 4-Coat Wax (SOW § 7.16)", "Sq. Ft.", 0.25, 0.003, 0.045, 0.298, None),
        (47, "Unscheduled Floor Care: Carpet Deep Hot-Water Extraction (SOW § 7.16)", "Sq. Ft.", 0.28, 0.003, 0.050, 0.333, None),
        (48, "Deduction/Addition Rate per Square Foot (SOW Section 7.17)", "Sq. Ft./Yr", 2.62, 0.031, 0.469, 3.120, None)
    ]

    for row_offset, data in enumerate(bid_lines, start=13):
        ws1.row_dimensions[row_offset].height = 20
        for col_idx, val in enumerate(data, start=1):
            c = ws1.cell(row_offset, col_idx, val)
            c.border = cell_border
            c.font = font_regular
            if col_idx == 1:
                c.alignment = Alignment(horizontal="center")
                c.font = font_bold
            elif col_idx in [2, 3]:
                c.alignment = Alignment(horizontal="left" if col_idx == 2 else "center")
            else:
                c.alignment = Alignment(horizontal="right")
                if isinstance(val, float):
                    if val >= 100:
                        c.number_format = "$#,##0.00"
                    elif val > 1:
                        c.number_format = "$#,##0.00"
                    else:
                        c.number_format = "$#,##0.000"

    # Scheduled Base Total Row
    ws1.row_dimensions[21].height = 24
    ws1.cell(21, 1, "").border = total_border
    ws1.cell(21, 2, "SCHEDULED BASE CONTRACT ANNUAL TOTAL (LINES 41 & 42)").font = font_bold
    ws1.cell(21, 2).border = total_border
    ws1.cell(21, 3, "12 Months").font = font_bold
    ws1.cell(21, 3).alignment = Alignment(horizontal="center")
    ws1.cell(21, 3).border = total_border
    ws1.cell(21, 4, "=SUM(D13:D14)*12").font = font_bold
    ws1.cell(21, 4).number_format = "$#,##0.00"
    ws1.cell(21, 4).border = total_border
    ws1.cell(21, 5, "=SUM(E13:E14)*12").font = font_bold
    ws1.cell(21, 5).number_format = "$#,##0.00"
    ws1.cell(21, 5).border = total_border
    ws1.cell(21, 6, "=SUM(F13:F14)*12").font = font_bold
    ws1.cell(21, 6).number_format = "$#,##0.00"
    ws1.cell(21, 6).border = total_border
    ws1.cell(21, 7, "=SUM(G13:G14)*12").font = font_green_bold
    ws1.cell(21, 7).number_format = "$#,##0.00"
    ws1.cell(21, 7).border = total_border
    ws1.cell(21, 7).fill = success_green_fill
    ws1.cell(21, 8, "=SUM(H13:H14)").font = font_green_bold
    ws1.cell(21, 8).number_format = "$#,##0.00"
    ws1.cell(21, 8).border = total_border
    ws1.cell(21, 8).fill = success_green_fill

    # Monthly Summary Row
    ws1.row_dimensions[22].height = 22
    ws1.cell(22, 2, "SCHEDULED BASE MONTHLY BILLING (LINES 41 + 42)").font = font_bold
    ws1.cell(22, 4, "=D13+D14").font = font_bold
    ws1.cell(22, 4).number_format = "$#,##0.00"
    ws1.cell(22, 6, "=F13+F14").font = font_bold
    ws1.cell(22, 6).number_format = "$#,##0.00"
    ws1.cell(22, 7, "=G13+G14").font = font_green_bold
    ws1.cell(22, 7).number_format = "$#,##0.00"
    ws1.cell(22, 7).fill = success_green_fill

    # Biometric Time Clock & Punch Card Contract Compliance Box
    ws1.cell(24, 1, "2.0 CONTRACT MANDATE: BIOMETRIC FINGERPRINT TIME CLOCK & POLICE LOGBOOK").font = font_section
    ws1.merge_cells("A24:H24")

    biometric_quote = (
        "EXACT SOW MANDATE (§ Equipment & Verification): 'On-site biometric time (or approved equivalent) clock capable of recording "
        "day, date, and hour. The time clock shall utilize a fingerprint method. It shall record employee attendance and display status "
        "and total hours worked. Each custodial employee shall additionally sign a log book on arrival and departure along with clocking in on "
        "the biometric time clock. The designated Facilities Operations staff member or Collin College Police Officers shall have access to view "
        "attendance and which employees are presently on duty by viewing the log book. The vendor shall furnish a printout of all hours worked "
        "for each employee along with the monthly bill.'\n\n"
        "HWB OPERATIONAL COMPLIANCE PROTOCOL: HWB deploys an enterprise-grade cellular biometric fingerprint clock at the Frisco campus Central "
        "Staging Office. Every technician must clock in via fingerprint and physically sign the Collin College Police desk logbook at 10:00 PM "
        "and 6:30 AM (Night Shift) and 8:00 AM and 4:30 PM (Day Shift). A certified digital audit printout is appended to every monthly invoice "
        "(Line 41), permanently guaranteeing 100% attendance audit defensibility and insulating Bosanna from District liquidated penalties."
    )
    ws1.cell(25, 1, biometric_quote).font = font_callout_body
    ws1.cell(25, 1).fill = alert_amber_fill
    ws1.cell(25, 1).alignment = Alignment(wrap_text=True, vertical="top")
    ws1.merge_cells("A25:H25")
    ws1.row_dimensions[25].height = 95

    # -------------------------------------------------------------
    # TAB 2: Service_Gantt_Schedule
    # -------------------------------------------------------------
    ws2 = wb.create_sheet(title="Service_Gantt_Schedule")
    ws2.views.sheetView[0].showGridLines = True

    # Title Block
    ws2.merge_cells("A1:R1")
    ws2["A1"] = "HWB CLEANING SERVICES LLC — MASTER OPERATIONAL DISPATCH GANTT"
    ws2["A1"].font = font_title
    ws2["A1"].fill = navy_header_fill
    ws2["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws2.row_dimensions[1].height = 28

    ws2.merge_cells("A2:R2")
    ws2["A2"] = "COLLIN COLLEGE FRISCO CAMPUS: SPECIAL PROJECTS GANTT, 3-SECTOR FLOOR CARE & 24-HR SHIFT PROTOCOL"
    ws2["A2"].font = font_sub_title
    ws2["A2"].fill = dark_blue_fill
    ws2["A2"].alignment = Alignment(horizontal="center", vertical="center")
    ws2.row_dimensions[2].height = 22

    # STAGE 1: TRI-ANNUAL SPECIAL PROJECTS GANTT
    ws2.cell(4, 1, "STAGE 1: TRI-ANNUAL SPECIAL PROJECTS RESTORATIVE GANTT (SOW §§ 117-124)").font = font_section
    ws2.merge_cells("A4:R4")

    # Special Projects Timeline Header
    sp_headers = ["Item", "Special Project Description (SOW Scope)", "Primary Campus Target Zones", "Assigned Crew", "Direct Cost", 
                  "Jan", "Feb", "Mar", "Apr", "MAY (Shutdown 1)", "Jun", "JUL/AUG (Shutdown 2)", "Sep", "Oct", "Nov", "DEC (Shutdown 3)"]
    ws2.row_dimensions[5].height = 26
    for c_idx, h in enumerate(sp_headers[:5], start=1):
        c = ws2.cell(5, c_idx, h)
        c.font = font_header; c.fill = navy_header_fill; c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True); c.border = header_border
    
    # Months 6 to 16
    for c_idx, h in enumerate(sp_headers[5:], start=6):
        c = ws2.cell(5, c_idx, h)
        c.font = font_header
        c.fill = dark_blue_fill if "Shutdown" in h else steel_fill
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = header_border

    special_projects_data = [
        (1, "VCT Deep Stripping & 4-Coat High-Gloss Finish", "Founders, Heritage, University & Lawler Corridors", "6 Techs (Night)", "$8,450", [10, 12, 16]),
        (2, "Terrazzo Rotary Scrub & Diamond Mechanical Hone", "Founders Atrium, Heritage Concourse & Student Center", "4 Techs (Night)", "$4,200", [10, 12, 16]),
        (3, "High-Performance Hot-Water Carpet Deep Extraction", "Library (62k SF), Classrooms, Lecture Halls, Offices", "6 Techs (Night)", "$6,800", [10, 12, 16]),
        (4, "Ceramic Tile & Grout Acidic Restorative Scrubbing", "41 Restroom Banks Campus-Wide (180 Fixtures)", "4 Techs (Kaivac)", "$3,100", [10, 12, 16]),
        (5, "High-Level Dusting (>8 ft to 25 ft: HVAC/Beams)", "Atria, Auditoriums, Gym, Concourse Light Fixtures", "2 Techs (Lift/Pole)", "$1,850", [10, 12, 16]),
        (6, "Architectural Interior & Sloped Atrium Glass Wash", "42 Double-Glass Vestibules & Multi-Story Interior Glass", "2 Techs (Pure Water)", "$1,600", [10, 12, 16]),
        (7, "Lecture Hall / Auditorium Upholstered Seat Shampoo", "Large Lecture Halls (Founders & Lawler Auditoriums)", "2 Techs (Extractor)", "$1,450", [10, 16]),
        (8, "Alumni Hall Locker Deep Descaling & Shower Disinfection", "180 Lockers, 16 Showers, Athletic Wet Areas", "3 Techs (Kaivac)", "$2,200", [10, 12, 16]),
        (9, "Facilities Shop & Concrete Lab Rotary Degreasing", "Facilities Operations (M) & Science Prep Labs", "2 Techs (Scrubber)", "$1,150", [12, 16]),
        (10, "Exterior Vestibule Power Washing & Gum Removal", "Campus Entrances, Perimeter Concrete & Courtyards", "2 Techs (3500 PSI)", "$1,965", [10, 12])
    ]

    for r_idx, (num, desc, zone, crew, cost, active_cols) in enumerate(special_projects_data, start=6):
        ws2.row_dimensions[r_idx].height = 20
        ws2.cell(r_idx, 1, num).alignment = Alignment(horizontal="center")
        ws2.cell(r_idx, 2, desc).alignment = Alignment(horizontal="left")
        ws2.cell(r_idx, 3, zone).alignment = Alignment(horizontal="left")
        ws2.cell(r_idx, 4, crew).alignment = Alignment(horizontal="center")
        ws2.cell(r_idx, 5, cost).alignment = Alignment(horizontal="right")
        for col in range(1, 6):
            ws2.cell(r_idx, col).font = font_regular
            ws2.cell(r_idx, col).border = cell_border

        for m_idx in range(6, 17):
            c = ws2.cell(r_idx, m_idx)
            c.border = cell_border
            if m_idx in active_cols:
                c.fill = gantt_sp_fill
                c.value = "ACTIVE"
                c.font = font_white_bold
                c.alignment = Alignment(horizontal="center", vertical="center")
            else:
                c.value = "—"
                c.font = font_small
                c.alignment = Alignment(horizontal="center", vertical="center")

    # STAGE 2: CAMPUS FLOOR CARE PROGRAM PER BUILDING & EQUIPMENT MATRIX (SPATIALLY SECTORED)
    start_row_s2 = 18
    ws2.cell(start_row_s2, 1, "STAGE 2: CAMPUS FLOOR CARE PROGRAM PER BUILDING & EQUIPMENT MATRIX (SPATIALLY SECTORED)").font = font_section
    ws2.merge_cells(f"A{start_row_s2}:R{start_row_s2}")

    fc_headers = ["Item", "Campus Sector", "Building Name & Code", "Cleanable SF", "Primary Floor Surfaces", "Scheduled Floor Care Scope", 
                  "Dedicated Equipment Assigned", "Shift & Cadence", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun", "Dispatch & Staging Logistics"]
    ws2.row_dimensions[start_row_s2+1].height = 26
    for c_idx, h in enumerate(fc_headers[:8], start=1):
        c = ws2.cell(start_row_s2+1, c_idx, h)
        c.font = font_header; c.fill = navy_header_fill; c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True); c.border = header_border

    for c_idx, h in enumerate(fc_headers[8:15], start=9):
        c = ws2.cell(start_row_s2+1, c_idx, h)
        c.font = font_header; c.fill = dark_blue_fill; c.alignment = Alignment(horizontal="center", vertical="center"); c.border = header_border

    c_note = ws2.cell(start_row_s2+1, 16, fc_headers[15])
    c_note.font = font_header; c_note.fill = steel_fill; c_note.alignment = Alignment(horizontal="center", vertical="center"); c_note.border = header_border

    building_floors = [
        (1, "Sector Alpha (Spine)", "Founders Hall (F)", 92105, "VCT, Terrazzo, Carpet", "Concourse auto-scrub; corridor high-speed burnish", "28\" Riding Auto-Scrubber / 2000 RPM Burnisher", "Night Shift (Daily/2x Wk)", [9, 10, 11, 12, 13, 14, 15], "Station 28\" Rider in Central Custodial Room F-102; Ramp access to concourse"),
        (2, "Sector Alpha (Spine)", "University Hall (U)", 84320, "VCT, Carpet, Ceramic", "Corridor auto-scrub; classroom rotary scrub & spray buff", "20\" Walk-Behind Auto-Scrubber / 175 RPM Machine", "Night Shift (Daily/3x Wk)", [9, 10, 11, 12, 13, 14, 15], "Direct covered concourse connection from Founders Hall"),
        (3, "Sector Bravo (Hub)", "Heritage Hall (H)", 78450, "VCT, Terrazzo Concourse", "Terrazzo daily auto-scrub; VCT corridor burnish", "28\" Riding Auto-Scrubber / 2000 RPM Burnisher", "Night Shift (Daily/2x Wk)", [9, 10, 11, 12, 13, 14, 15], "Student Services Hub; Rider mobilized via south academic link"),
        (4, "Sector Charlie (Special)", "Library & LRC (L)", 62180, "85% Carpet, VCT Entry", "High-velocity backpack HEPA vac; carpet extraction", "Hot-Water Carpet Extractor / Backpack HEPA Vacs", "Night Shift (Nightly Vac / Extract)", [9, 10, 11, 12, 13, 14, 15], "2-Story Quiet Stacks; Dedicated extractor stationed in L-114"),
        (5, "Sector Charlie (Special)", "Lawler Hall (J)", 48260, "VCT Corridors, Carpet", "Corridor auto-scrubbing; classroom spot buffing", "20\" Walk-Behind Auto-Scrubber / Burnisher", "Night Shift (3x/Week Alternate)", [9, 11, 13, 15], "Lecture Halls & Seminar Rooms; 20\" scrubber assigned"),
        (6, "Sector Charlie (Athletic)", "Alumni Hall & PE (A)", 38940, "Ceramic Tile, Concrete", "Locker tile power scrub; shower descaling; gym track", "Kaivac Touchless Unit / 175 RPM Machine & Wet-Vac", "Night Shift (Nightly Deep Scrub)", [9, 10, 11, 12, 13, 14, 15], "Standalone Athletic Facility; Permanent Kaivac station inside locker storage"),
        (7, "Sector Bravo (Hub)", "Student Center (C)", 32150, "Terrazzo, VCT Dining", "Food-court degrease; dining concourse auto-scrub", "20\" Walk-Behind Scrubber / Degreasing Pads", "Night Shift (Post-Close Daily)", [9, 10, 11, 12, 13, 14, 15], "High Grease & Food Traffic; Loading dock service corridor adjacent"),
        (8, "Sector Bravo (Hub)", "IT Infrastructure (IT)", 18420, "Raised Tile, Carpet", "Anti-static dry microfiber; HEPA vacuuming", "Anti-Static HEPA Canister Vac / Microfiber", "Night Shift (2x/Week Strict)", [10, 12], "Strict Static-Control Zone; Clean-agent server rooms"),
        (9, "Operations / Shops", "Facilities Maint. (M)", 14200, "Industrial Concrete", "Shop rotary degreasing scrub; tire mark removal", "20\" Walk-Behind Scrubber / Stripping Brush", "Night Shift (Weekly Deep Scrub)", [13], "Central Campus Compactor & Dumpster staging area"),
        (10, "Operations / 24-7", "Campus Safety (S)", 9393, "VCT Dispatch, Carpet", "Continuous lobby upkeep; dispatch floor buffing", "2000 RPM Electric Burnisher / Upright Vac", "Night Shift + Day Porter Spot", [9, 10, 11, 12, 13, 14, 15], "24/7 Police Dispatch Wing; Sign-in police desk location")
    ]

    for r_idx, (num, sector, bldg, sf, surf, scope, equip, cadence, active_days, notes) in enumerate(building_floors, start=start_row_s2+2):
        ws2.row_dimensions[r_idx].height = 20
        ws2.cell(r_idx, 1, num).alignment = Alignment(horizontal="center")
        ws2.cell(r_idx, 2, sector).alignment = Alignment(horizontal="left")
        ws2.cell(r_idx, 2).font = font_bold
        ws2.cell(r_idx, 3, bldg).alignment = Alignment(horizontal="left")
        ws2.cell(r_idx, 4, sf).alignment = Alignment(horizontal="right")
        ws2.cell(r_idx, 4).number_format = "#,##0"
        ws2.cell(r_idx, 5, surf).alignment = Alignment(horizontal="left")
        ws2.cell(r_idx, 6, scope).alignment = Alignment(horizontal="left")
        ws2.cell(r_idx, 7, equip).alignment = Alignment(horizontal="left")
        ws2.cell(r_idx, 8, cadence).alignment = Alignment(horizontal="center")
        for col in range(1, 9):
            if col != 2: ws2.cell(r_idx, col).font = font_regular
            ws2.cell(r_idx, col).border = cell_border

        for d_idx in range(9, 16):
            c = ws2.cell(r_idx, d_idx)
            c.border = cell_border
            if d_idx in active_days:
                c.fill = gantt_fc_fill
                c.value = "RUN"
                c.font = font_white_bold
                c.alignment = Alignment(horizontal="center", vertical="center")
            else:
                c.value = "—"
                c.font = font_small
                c.alignment = Alignment(horizontal="center", vertical="center")

        c_n = ws2.cell(r_idx, 16, notes)
        c_n.font = font_small
        c_n.border = cell_border
        c_n.alignment = Alignment(horizontal="left", vertical="center")

    # STAGE 3: RECURRING SHIFT OPERATIONS, 3-SECTOR PORTER ALLOCATION & BIOMETRIC PUNCH PROTOCOL
    start_row_s3 = 31
    ws2.cell(start_row_s3, 1, "STAGE 3: 24-HR SHIFT CADENCE, 3-SECTOR DAY PORTER COVERAGE & BIOMETRIC PUNCH PROTOCOL").font = font_section
    ws2.merge_cells(f"A{start_row_s3}:R{start_row_s3}")

    shift_headers = ["Shift", "Sector / Coverage Zone", "Operating Window", "Mandated Posts", "Biometric Punch & Security Sign-In Protocol", "Core Chores & Spatial Responsibilities"]
    ws2.row_dimensions[start_row_s3+1].height = 24
    for c_idx, h in enumerate(shift_headers, start=1):
        c = ws2.cell(start_row_s3+1, c_idx, h)
        c.font = font_header; c.fill = navy_header_fill; c.alignment = Alignment(horizontal="center", vertical="center"); c.border = header_border

    shifts_data = [
        ("Day Porters (M-F)", "Sector Alpha (Academic Spine)", "8:00 AM - 4:30 PM", "2 Porters Dedicated", "Biometric finger clock-in at 8:00 AM; Police logbook sign-in at Bldg S. Midday check; Clock out at 4:30 PM.", "Founders Hall + University Hall (176,425 SF). Continuous restroom checks, class turnover trash, lecture hall touchpoints, and main drop-off entrance glass."),
        ("Day Porter (M-F)", "Sector Bravo (Student Life Hub)", "8:00 AM - 4:30 PM", "1 Porter Dedicated", "Biometric finger clock-in at 8:00 AM; Police logbook sign-in at Bldg S. Clock out at 4:30 PM.", "Heritage Hall + Student Center + IT (129,020 SF). Food court dining cleanup, trash pulls post-lunch, admissions/testing lobby glass, spill response."),
        ("Day Porter (M-F)", "Sector Charlie (Specialty/Athletics)", "8:00 AM - 4:30 PM", "1 Porter Dedicated", "Biometric finger clock-in at 8:00 AM; Police logbook sign-in at Bldg S. Clock out at 4:30 PM.", "Library LRC + Lawler Hall + Alumni PE + Campus Safety (172,973 SF). Library study carrels, gym corridor trash, perimeter entrance mats, urgent spill dispatch."),
        ("Day Porters (Sat)", "Campus-Wide Dual Patrol", "8:00 AM - 4:30 PM", "2 Porters Dedicated", "Biometric finger clock-in at 8:00 AM; Police logbook sign-in. Clock out at 4:30 PM.", "Porter 1 covers Academic Spine (F + U); Porter 2 covers Student Center, Library & Alumni Hall. Weekend events and exam trash."),
        ("Night Custodians (Mon-Sun)", "All 10 Campus Facilities (7 Days)", "10:00 PM - 6:30 AM", "12 Custodians Dedicated", "Mandatory biometric finger clock-in at 10:00 PM; Police logbook signing. Biometric clock-out at 6:30 AM.", "Heavy production: 136 classrooms/labs, 41 restroom banks deep sanitized, auto-scrubbers running, tilt-cart trash hauled to Bldg M compactor."),
        ("Night Supervisor (Mon-Sun)", "Campus-Wide Quality Assurance", "10:00 PM - 6:30 AM", "1 Non-Cleaning Sup", "Biometric sign-in; Police desk logbook check; Daily Task Check Sheet completion; Campus walkthrough before exit.", "Quality control inspections across all 10 buildings, biometric punch verification, key control log, 2-hr emergency call response.")
    ]

    for r_idx, (sh, sec, win, posts, punch, focus) in enumerate(shifts_data, start=start_row_s3+2):
        ws2.row_dimensions[r_idx].height = 30
        ws2.cell(r_idx, 1, sh).alignment = Alignment(horizontal="left", vertical="center"); ws2.cell(r_idx, 1).font = font_bold
        ws2.cell(r_idx, 2, sec).alignment = Alignment(horizontal="left", vertical="center"); ws2.cell(r_idx, 2).font = font_bold
        ws2.cell(r_idx, 3, win).alignment = Alignment(horizontal="center", vertical="center")
        ws2.cell(r_idx, 4, posts).alignment = Alignment(horizontal="center", vertical="center"); ws2.cell(r_idx, 4).font = font_bold
        ws2.cell(r_idx, 5, punch).alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        ws2.cell(r_idx, 6, focus).alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        for col in range(1, 7):
            if col not in [1, 2, 4]: ws2.cell(r_idx, col).font = font_regular
            ws2.cell(r_idx, col).border = cell_border

    # -------------------------------------------------------------
    # TAB 3: Campus_Building_Takeoff (SPATIALLY ENRICHED)
    # -------------------------------------------------------------
    ws3 = wb.create_sheet(title="Campus_Building_Takeoff")
    ws3.views.sheetView[0].showGridLines = True

    ws3.merge_cells("A1:M1")
    ws3["A1"] = "HWB CLEANING SERVICES LLC — PHYSICAL TAKEOFF & SPATIAL SECTOR AUDIT"
    ws3["A1"].font = font_title; ws3["A1"].fill = navy_header_fill; ws3["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws3.row_dimensions[1].height = 28

    ws3.merge_cells("A2:M2")
    ws3["A2"] = "COLLIN COLLEGE FRISCO CAMPUS (10 BUILDINGS / 478,418 CLEANABLE SF / 3 LOGISTICAL SECTORS)"
    ws3["A2"].font = font_sub_title; ws3["A2"].fill = dark_blue_fill; ws3["A2"].alignment = Alignment(horizontal="center", vertical="center")
    ws3.row_dimensions[2].height = 22

    takeoff_headers = ["Code", "Campus Sector", "Building Name", "Cleanable SF", "Classrooms / Labs", "Offices & Conf", "Restroom Banks", 
                       "Total Fixtures", "Showers", "Lockers", "Day Porter Assigned", "Night Crew FTE", "Nightly Prod (SF/Hr)"]
    ws3.row_dimensions[4].height = 26
    for c_idx, h in enumerate(takeoff_headers, start=1):
        c = ws3.cell(4, c_idx, h)
        c.font = font_header; c.fill = navy_header_fill; c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True); c.border = header_border

    takeoff_data = [
        ("F", "Sector Alpha (Spine)", "Founders Hall", 92105, 32, 45, 8, 36, 0, 0, "Porter 1 & 2 (Shared)", 2.5, 5263),
        ("U", "Sector Alpha (Spine)", "University Hall", 84320, 28, 50, 7, 32, 0, 0, "Porter 1 & 2 (Shared)", 2.0, 6023),
        ("H", "Sector Bravo (Hub)", "Heritage Hall", 78450, 24, 40, 6, 28, 0, 0, "Porter 3 (Dedicated)", 2.0, 5604),
        ("L", "Sector Charlie (Special)", "Library & Learning Resource Center", 62180, 8, 25, 4, 18, 0, 0, "Porter 4 (Dedicated)", 1.5, 5922),
        ("J", "Sector Charlie (Special)", "Lawler Hall", 48260, 20, 18, 4, 18, 0, 0, "Porter 4 (Dedicated)", 1.2, 5745),
        ("A", "Sector Charlie (Athletic)", "Alumni Hall & Physical Education", 38940, 4, 12, 4, 24, 16, 180, "Porter 4 (Dedicated)", 1.2, 4636),
        ("C", "Sector Bravo (Hub)", "Student Center & Cafeteria", 32150, 6, 15, 4, 16, 0, 0, "Porter 3 (Dedicated)", 0.8, 5741),
        ("IT", "Sector Bravo (Hub)", "Information Technology Infrastructure", 18420, 6, 10, 2, 8, 0, 0, "Porter 3 (Dedicated)", 0.4, 6579),
        ("M", "Operations / Shops", "Facilities Operations & Maintenance", 14200, 4, 8, 1, 4, 0, 0, "On-Call / Rover", 0.2, 10143),
        ("S", "Operations / 24-7", "Campus Safety & Central Plant", 9393, 4, 6, 1, 4, 0, 0, "On-Call / Rover", 0.2, 6709)
    ]

    for r_idx, (code, sec, name, sf, cls, off, r_banks, fixt, shw, lck, porter, techs, prod) in enumerate(takeoff_data, start=5):
        ws3.row_dimensions[r_idx].height = 20
        ws3.cell(r_idx, 1, code).alignment = Alignment(horizontal="center")
        ws3.cell(r_idx, 2, sec).alignment = Alignment(horizontal="left"); ws3.cell(r_idx, 2).font = font_bold
        ws3.cell(r_idx, 3, name).alignment = Alignment(horizontal="left")
        ws3.cell(r_idx, 4, sf).alignment = Alignment(horizontal="right"); ws3.cell(r_idx, 4).number_format = "#,##0"
        ws3.cell(r_idx, 5, cls).alignment = Alignment(horizontal="center")
        ws3.cell(r_idx, 6, off).alignment = Alignment(horizontal="center")
        ws3.cell(r_idx, 7, r_banks).alignment = Alignment(horizontal="center")
        ws3.cell(r_idx, 8, fixt).alignment = Alignment(horizontal="center")
        ws3.cell(r_idx, 9, shw).alignment = Alignment(horizontal="center")
        ws3.cell(r_idx, 10, lck).alignment = Alignment(horizontal="center")
        ws3.cell(r_idx, 11, porter).alignment = Alignment(horizontal="left")
        ws3.cell(r_idx, 12, techs).alignment = Alignment(horizontal="center")
        ws3.cell(r_idx, 13, prod).alignment = Alignment(horizontal="right"); ws3.cell(r_idx, 13).number_format = "#,##0"
        for col in range(1, 14):
            if col != 2: ws3.cell(r_idx, col).font = font_regular
            ws3.cell(r_idx, col).border = cell_border

    # Takeoff Total Row
    ws3.row_dimensions[15].height = 24
    ws3.cell(15, 1, "").border = total_border
    ws3.cell(15, 2, "CAMPUS TOTALS").font = font_bold; ws3.cell(15, 2).border = total_border
    ws3.cell(15, 3, "10 Buildings").font = font_bold; ws3.cell(15, 3).alignment = Alignment(horizontal="center"); ws3.cell(15, 3).border = total_border
    ws3.cell(15, 4, "=SUM(D5:D14)").font = font_bold; ws3.cell(15, 4).number_format = "#,##0"; ws3.cell(15, 4).border = total_border
    ws3.cell(15, 5, "=SUM(E5:E14)").font = font_bold; ws3.cell(15, 5).border = total_border
    ws3.cell(15, 6, "=SUM(F5:F14)").font = font_bold; ws3.cell(15, 6).border = total_border
    ws3.cell(15, 7, "=SUM(G5:G14)").font = font_bold; ws3.cell(15, 7).border = total_border
    ws3.cell(15, 8, "=SUM(H5:H14)").font = font_bold; ws3.cell(15, 8).border = total_border
    ws3.cell(15, 9, "=SUM(I5:I14)").font = font_bold; ws3.cell(15, 9).border = total_border
    ws3.cell(15, 10, "=SUM(J5:J14)").font = font_bold; ws3.cell(15, 10).border = total_border
    ws3.cell(15, 11, "4 Porters M-F / 2 Sat").font = font_bold; ws3.cell(15, 11).border = total_border
    ws3.cell(15, 12, "=SUM(L5:L14)").font = font_bold; ws3.cell(15, 12).border = total_border
    ws3.cell(15, 13, "=AVERAGE(M5:M14)").font = font_bold; ws3.cell(15, 13).number_format = "#,##0"; ws3.cell(15, 13).border = total_border

    # -------------------------------------------------------------
    # TAB 4: Cost_Underwriting_Audit
    # -------------------------------------------------------------
    ws4 = wb.create_sheet(title="Cost_Underwriting_Audit")
    ws4.views.sheetView[0].showGridLines = True

    ws4.merge_cells("A1:G1")
    ws4["A1"] = "HWB CLEANING SERVICES LLC — FINANCIAL UNDERWRITING & PROFIT RECONCILIATION"
    ws4["A1"].font = font_title; ws4["A1"].fill = navy_header_fill; ws4["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws4.row_dimensions[1].height = 28

    ws4.merge_cells("A2:G2")
    ws4["A2"] = "INTERNAL COST BASIS, OVERHEAD ALLOCATION & BOSANNA/HWB PROFIT DISTRIBUTION"
    ws4["A2"].font = font_sub_title; ws4["A2"].fill = dark_blue_fill; ws4["A2"].alignment = Alignment(horizontal="center", vertical="center")
    ws4.row_dimensions[2].height = 22

    uw_headers = ["Category", "Financial Line Item Description", "Cost Basis / Calculation Detail", "Monthly Cost ($)", "Annual Total ($)", "% of Top-Line Revenue", "Notes"]
    ws4.row_dimensions[4].height = 26
    for c_idx, h in enumerate(uw_headers, start=1):
        c = ws4.cell(4, c_idx, h)
        c.font = font_header; c.fill = navy_header_fill; c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True); c.border = header_border

    uw_data = [
        ("Gross Revenue", "Billed to Collin College (Scenario A)", "Top-line proposal submitted by Bosanna LLC", 124426.19, 1493114.28, 1.0000, "Official Subcontract Price + Markups"),
        ("Deduction", "TIPS Administrative Cooperative Fee (1.0%)", "Mandatory State Co-op Fee paid by Bosanna", -1244.26, -14931.14, -0.0100, "Paid direct to TIPS Co-op"),
        ("Deduction", "Bosanna LLC Prime Partner Fee (15.0%)", "Bosanna Prime Contract Holder finder margin", -18663.93, -223967.14, -0.1500, "Pure profit to Bosanna LLC"),
        ("HWB Revenue", "HWB Wholesale Subcontract Revenue", "Line 41 ($96,943.00) + Line 42 ($7,575.00)", 104518.00, 1254216.00, 0.8400, "Funds HWB Operations & Margin"),
        ("COGS (Labor)", "Direct Base Wages (Cleaners & Supervisors)", "904 hrs/wk: $16.00/hr Techs, $18.50/hr Sup", -63284.52, -759414.24, -0.5086, "22.6 FTEs (23-25 Badged Workers)"),
        ("COGS (Burden)", "Payroll Burden (20.0% Loaded Factor)", "FICA (7.65%), SUTA (2.7%), FUTA (0.6%), WC (4.85%), GL (4.2%)", -12656.90, -151882.85, -0.1017, "Full Texas WC Code 9014 Covered"),
        ("COGS (Supplies)", "Consumable Restroom Supplies Passthrough", "District Historical Usage: 2,400 cs paper, 1,056 cs liners", -6675.00, -80100.00, -0.0536, "Recovered under Line 42"),
        ("COGS (Chemistry)", "Special Projects Chemicals, Wax & Stripper", "Floor stripper, 4-coat wax, extraction detergent, pads", -900.00, -10800.00, -0.0072, "Tri-annual restorative supplies"),
        ("COGS (Equipment)", "Equipment Amortization & Pad/Parts Service", "2 Riders, 4 Autoscrubbers, 4 Burnishers, 8 HEPA Backpacks", -1400.00, -16800.00, -0.0112, "3-Year straight-line capital amortization"),
        ("COGS (Support)", "Badging, DPS/FBI Fingerprints & Cellular Clock", "FAST Fingerprint (§ 22.0834), Uniforms, Radio system", -710.00, -8525.00, -0.0057, "Biometric clock cellular plan included"),
        ("Gross Margin", "HWB GROSS OPERATING PROFIT", "HWB Subcontract ($104,518) minus Direct COGS ($85,626.42)", 18891.58, 226693.91, 0.1518, "18.07% Margin on Subcontract"),
        ("G&A Overhead", "Operations Manager / ISO 9001 Inspections", "Weekly QMS field audits, client liaison, night sweeps", -2000.00, -24000.00, -0.0161, "Senior Management Quality Control"),
        ("G&A Overhead", "Payroll Admin, Recruiting & HR Onboarding", "Continuous turnover recruiting & badging pipeline", -1200.00, -14400.00, -0.0096, "HR Compliance & FAST clearing"),
        ("G&A Overhead", "Surety Bond & Specific Insurance Riders", "Janitorial Surety Bond, Waiver of Subrogation, Additional Insured", -600.00, -7200.00, -0.0048, "Collin College T&C Compliance"),
        ("G&A Overhead", "Corporate Office Allocation & Legal/Software", "Enterprise software, accounting, legal & communication float", -800.00, -9600.00, -0.0064, "Fixed Corporate SG&A"),
        ("Net Profit", "HWB NET OPERATING PROFIT (EBITDA)", "Gross Profit ($18,891.58) minus G&A Overhead ($4,600.00)", 14291.58, 171498.91, 0.1149, "13.67% of Subcontract Top-Line")
    ]

    for r_idx, (cat, desc, basis, mo, yr, pct, notes) in enumerate(uw_data, start=5):
        ws4.row_dimensions[r_idx].height = 20
        ws4.cell(r_idx, 1, cat).alignment = Alignment(horizontal="left")
        ws4.cell(r_idx, 1).font = font_bold if "Profit" in cat or "Revenue" in cat else font_regular
        ws4.cell(r_idx, 2, desc).alignment = Alignment(horizontal="left")
        ws4.cell(r_idx, 2).font = font_bold if "Profit" in cat or "Revenue" in cat else font_regular
        ws4.cell(r_idx, 3, basis).alignment = Alignment(horizontal="left")
        ws4.cell(r_idx, 3).font = font_small
        ws4.cell(r_idx, 4, mo).alignment = Alignment(horizontal="right")
        ws4.cell(r_idx, 4).number_format = "$#,##0.00"
        ws4.cell(r_idx, 5, yr).alignment = Alignment(horizontal="right")
        ws4.cell(r_idx, 5).number_format = "$#,##0.00"
        ws4.cell(r_idx, 6, pct).alignment = Alignment(horizontal="right")
        ws4.cell(r_idx, 6).number_format = "0.00%"
        ws4.cell(r_idx, 7, notes).alignment = Alignment(horizontal="left")
        ws4.cell(r_idx, 7).font = font_small

        for col in range(1, 8):
            c = ws4.cell(r_idx, col)
            c.border = cell_border
            if "Net Profit" in cat:
                c.fill = success_green_fill
                c.font = font_green_bold
            elif "Gross Margin" in cat or "HWB Revenue" in cat:
                c.fill = light_blue_fill
                c.font = font_bold

    # Auto-fit Column Widths across all sheets
    for ws in [ws1, ws2, ws3, ws4]:
        for col in ws.columns:
            col_letter = get_column_letter(col[0].column)
            max_len = 0
            for cell in col:
                if cell.row in [1, 2, 9, 10, 24, 25] and ws == ws1: continue
                if cell.row in [1, 2, 4, 18, 31] and ws == ws2: continue
                if cell.row in [1, 2] and ws in [ws3, ws4]: continue
                val_str = str(cell.value or '')
                if len(val_str) > max_len:
                    max_len = len(val_str)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 11)

    # Specific manual adjustments for clean look
    ws1.column_dimensions['A'].width = 12
    ws1.column_dimensions['B'].width = 46
    ws1.column_dimensions['C'].width = 16
    ws1.column_dimensions['D'].width = 24
    ws1.column_dimensions['E'].width = 18
    ws1.column_dimensions['F'].width = 20
    ws1.column_dimensions['G'].width = 24
    ws1.column_dimensions['H'].width = 26

    ws2.column_dimensions['A'].width = 8
    ws2.column_dimensions['B'].width = 24
    ws2.column_dimensions['C'].width = 32
    ws2.column_dimensions['D'].width = 16
    ws2.column_dimensions['E'].width = 24
    ws2.column_dimensions['F'].width = 38
    ws2.column_dimensions['G'].width = 38
    ws2.column_dimensions['H'].width = 26

    ws3.column_dimensions['A'].width = 8
    ws3.column_dimensions['B'].width = 26
    ws3.column_dimensions['C'].width = 36
    ws3.column_dimensions['D'].width = 16
    ws3.column_dimensions['E'].width = 18
    ws3.column_dimensions['F'].width = 16
    ws3.column_dimensions['G'].width = 16
    ws3.column_dimensions['H'].width = 16
    ws3.column_dimensions['I'].width = 12
    ws3.column_dimensions['J'].width = 12
    ws3.column_dimensions['K'].width = 24
    ws3.column_dimensions['L'].width = 16
    ws3.column_dimensions['M'].width = 20

    output_path = "/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-QUOTES/BOSANNA-COLLIN-COLLEGE/COLLIN-COLLEGE-FRISCO-BID-MODEL.xlsx"
    wb.save(output_path)
    print(f"SUCCESS: Spatially enriched master bid model saved to {output_path}")

if __name__ == "__main__":
    build_bid_model()
