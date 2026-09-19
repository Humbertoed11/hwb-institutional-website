import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.drawing.image import Image as OpenpyxlImage
from openpyxl.worksheet.pagebreak import Break
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.workbook.defined_name import DefinedName

def generate_unified_workbook():
    target_path = "HWB-COMPANY/HWB-QUOTES/SUNDANCE-QUOTE-gantt.xlsx"
    
    # -------------------------------------------------------------
    # IMAGE SOURCES (Damage Survey)
    # -------------------------------------------------------------
    img_paths = {
        "plaza": "scratch/thumb_plaza.jpg",
        "chase": "scratch/thumb_chase.jpg",
        "petroleum": "scratch/thumb_petroleum.jpg",
        "schwarz": "scratch/thumb_schwarz.jpg"
    }

    wb = openpyxl.Workbook()
    
    # Define Dynamic Named Ranges for Gantt Calendar Calculations
    defined_name_start = DefinedName('Project_Start', attr_text='Service_Gantt_Schedule!$G$4')
    defined_name_week = DefinedName('Display_Week', attr_text='Service_Gantt_Schedule!$G$5')
    wb.defined_names.add(defined_name_start)
    wb.defined_names.add(defined_name_week)

    # -------------------------------------------------------------
    # STYLING DEFINITIONS (SigmaFidelity High-Density Standard)
    # -------------------------------------------------------------
    font_title = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
    font_section = Font(name="Calibri", size=11, bold=True, color="1E3A8A")
    font_header = Font(name="Calibri", size=9.5, bold=True, color="FFFFFF")
    font_bold = Font(name="Calibri", size=9.5, bold=True, color="0F172A")
    font_bold_sm = Font(name="Calibri", size=9, bold=True, color="0F172A")
    font_regular = Font(name="Calibri", size=9.5, color="334155")
    font_regular_sm = Font(name="Calibri", size=8.5, color="334155")
    font_alert = Font(name="Calibri", size=9.5, bold=True, color="991B1B")
    font_alert_sm = Font(name="Calibri", size=9, bold=True, color="991B1B")
    font_badge_white = Font(name="Calibri", size=8, bold=True, color="FFFFFF")

    fill_title = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid") # Dark Slate Navy
    fill_header = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid") # Royal Blue
    fill_header_opt = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid") # Slate
    fill_subtle = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
    fill_zebra = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    fill_alert = PatternFill(start_color="FEF2F2", end_color="FEF2F2", fill_type="solid")
    fill_green = PatternFill(start_color="F0FDF4", end_color="F0FDF4", fill_type="solid")
    fill_weekend = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")

    # Service & Option Color Palette
    fill_p1_deep_clean = PatternFill(start_color="16A34A", end_color="16A34A", fill_type="solid") # Forest Green
    fill_p2_sealer = PatternFill(start_color="0284C7", end_color="0284C7", fill_type="solid")     # Deep Cyan
    fill_p3_quarterly = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")  # Corporate Blue
    fill_p3_semiannual = PatternFill(start_color="475569", end_color="475569", fill_type="solid") # Dark Slate
    fill_opt_stairs = PatternFill(start_color="B45309", end_color="B45309", fill_type="solid")    # Amber Bronze
    fill_opt_diamond = PatternFill(start_color="9D174D", end_color="9D174D", fill_type="solid")   # Crimson Plum

    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")
    align_right = Alignment(horizontal="right", vertical="center")
    align_header_wrap = Alignment(horizontal="center", vertical="center", wrap_text=True)
    align_desc_wrap = Alignment(horizontal="left", vertical="center", wrap_text=True)

    thin_side = Side(style="thin", color="CBD5E1")
    box_border = Border(top=thin_side, bottom=thin_side, left=thin_side, right=thin_side)
    total_border = Border(top=Side(style="thin", color="0F172A"), bottom=Side(style="double", color="0F172A"))

    # -------------------------------------------------------------
    # SHEET 1: Commercial_Quote
    # -------------------------------------------------------------
    ws_quote = wb.active
    ws_quote.title = "Commercial_Quote"
    ws_quote.views.sheetView[0].showGridLines = True
    
    # Title Block
    ws_quote.merge_cells("A1:K1")
    ws_quote["A1"] = "HWB CLEANING SERVICES LLC"
    ws_quote["A1"].font = font_title
    ws_quote["A1"].fill = fill_title
    ws_quote["A1"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws_quote.row_dimensions[1].height = 28
    
    ws_quote.merge_cells("A2:K2")
    ws_quote["A2"] = "COMMERCIAL PROPOSAL: DOWNTOWN FORT WORTH 11-BUILDING LOBBY FLOOR CARE PORTFOLIO"
    ws_quote["A2"].font = Font(name="Calibri", size=10.5, bold=True, color="93C5FD")
    ws_quote["A2"].fill = fill_title
    ws_quote["A2"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws_quote.row_dimensions[2].height = 18

    # Meta Info Box
    meta_info = [
        ("Client:", "Sundance Square & Downtown Commercial Property Management", "Proposal ID:", "HWB-BID-2026-FW01 (v3.7.0)"),
        ("Property:", "Downtown Fort Worth Commercial Portfolio (11 Buildings)", "Effective Date:", "September 03, 2026"),
        ("Central Office:", "425 Houston Street, Suite 250, Fort Worth, TX 76102", "Dispatch Origin:", "Arlington, TX"),
        ("Primary Scope:", "11 Ground-Floor Commercial Lobbies (11,153 Cleanable SF)", "Operational Crew:", "2 Specialized Floor Technicians")
    ]
    for idx, (lbl1, val1, lbl2, val2) in enumerate(meta_info, start=4):
        ws_quote.row_dimensions[idx].height = 20
        ws_quote.merge_cells(f"A{idx}:B{idx}")
        ws_quote[f"A{idx}"] = lbl1
        ws_quote[f"A{idx}"].font = font_bold
        ws_quote[f"A{idx}"].alignment = align_left
        
        ws_quote.merge_cells(f"C{idx}:E{idx}")
        ws_quote[f"C{idx}"] = val1
        ws_quote[f"C{idx}"].font = font_regular
        ws_quote[f"C{idx}"].alignment = align_left
        
        ws_quote.cell(row=idx, column=6).value = ""

        ws_quote.merge_cells(f"G{idx}:H{idx}")
        ws_quote[f"G{idx}"] = lbl2
        ws_quote[f"G{idx}"].font = font_bold
        ws_quote[f"G{idx}"].alignment = align_left
        
        ws_quote.merge_cells(f"I{idx}:K{idx}")
        ws_quote[f"I{idx}"] = val2
        ws_quote[f"I{idx}"].font = font_regular
        ws_quote[f"I{idx}"].alignment = align_left

        for c in list(range(1, 6)) + list(range(7, 12)):
            cell = ws_quote.cell(row=idx, column=c)
            cell.border = box_border
            if c in [1, 2, 7, 8]:
                cell.fill = fill_zebra

    # Data Integrity Alert Notice
    ws_quote.merge_cells("A8:K8")
    ws_quote["A8"] = "DATA INTEGRITY NOTICE (ISO 9001 Clause 8.2.2): Cleanable square footages are reconciled to on-site empirical field measurements (11,153 Cleanable SF)."
    ws_quote["A8"].font = font_alert
    ws_quote["A8"].fill = fill_alert
    ws_quote["A8"].alignment = align_center
    ws_quote.row_dimensions[8].height = 20

    # -------------------------------------------------------------
    # PRE-SECTION 1.0: EXECUTIVE SUMMARY BLOCK (Rows 10 to 17)
    # -------------------------------------------------------------
    ws_quote.row_dimensions[9].height = 10 # spacer

    ws_quote.merge_cells("A10:K10")
    ws_quote["A10"] = "EXECUTIVE SUMMARY: CLIENT NEEDS, GOALS & OUR PROPOSED PLAN"
    ws_quote["A10"].font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    ws_quote["A10"].fill = fill_header
    ws_quote["A10"].alignment = align_center
    ws_quote.row_dimensions[10].height = 24

    ws_quote.merge_cells("A11:K11")
    ws_quote["A11"] = "1. THE CLIENT'S CURRENT SITUATION & LOBBY NEEDS"
    ws_quote["A11"].font = Font(name="Calibri", size=10, bold=True, color="0F172A")
    ws_quote["A11"].fill = fill_subtle
    ws_quote["A11"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws_quote.row_dimensions[11].height = 18

    ws_quote.merge_cells("A12:K12")
    ws_quote["A12"] = "Sundance Square and downtown property management oversee 11 landmark commercial buildings in Fort Worth. Every business day, hundreds of office tenants, retail customers, and corporate guests walk through these ground-floor lobbies. Heavy daily foot traffic, tracked-in street grit, and rain have dulled the natural stone, tile, and terrazzo surfaces. Dirt has settled into corners and grout lines, while spills and moving equipment have left scuffs and spots. The management team needs these entrance lobbies to look welcoming, clean, and well-maintained every single morning."
    ws_quote["A12"].font = Font(name="Calibri", size=9.5, color="334155")
    ws_quote["A12"].alignment = align_desc_wrap
    ws_quote.row_dimensions[12].height = 42

    ws_quote.merge_cells("A13:K13")
    ws_quote["A13"] = "2. CLIENT GOALS & OPERATIONAL OBJECTIVES"
    ws_quote["A13"].font = Font(name="Calibri", size=10, bold=True, color="0F172A")
    ws_quote["A13"].fill = fill_subtle
    ws_quote["A13"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws_quote.row_dimensions[13].height = 18

    ws_quote.merge_cells("A14:K14")
    ws_quote["A14"] = "• Strip Away Old Dirt: Deep-clean floors down to the bare surface so managers can clearly see actual condition and existing damage.\n• Protect Against Future Stains: Seal stone and grout pores to stop coffee, sodas, and grease from soaking in and ruining floors.\n• Set Up a Reliable Routine: Establish a predictable cleaning schedule (quarterly or semi-annually) that keeps floors shining within budget.\n• Zero Tenant Disruption: Complete all floor operations safely and quietly without interrupting daytime commercial business."
    ws_quote["A14"].font = Font(name="Calibri", size=9.5, color="334155")
    ws_quote["A14"].alignment = align_desc_wrap
    ws_quote.row_dimensions[14].height = 42

    ws_quote.merge_cells("A15:K15")
    ws_quote["A15"] = "3. WHAT HWB CLEANING SERVICES PROPOSES (3-PHASE PLAN)"
    ws_quote["A15"].font = Font(name="Calibri", size=10, bold=True, color="0F172A")
    ws_quote["A15"].fill = fill_subtle
    ws_quote["A15"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws_quote.row_dimensions[15].height = 18

    ws_quote.merge_cells("A16:K16")
    ws_quote["A16"] = "HWB Cleaning Services LLC proposes a clear 3-step hard floor program for the 11 downtown lobbies (11,153 Cleanable SF):\n1. Deep Clean Reset (Phase 1): Heavy rotary machine scrub, soil extraction, and edge hand scraping to uncover the real floor.\n2. Stain Protection (Phase 2): Application of LATICRETE® BulletProof® penetrating sealer into pores and grout lines to lock out spills.\n3. Ongoing Scheduled Care (Phase 3): Choice of Track A (Quarterly / 4x Year) or Track B (Semi-Annual / 2x Year) to maintain clean floors."
    ws_quote["A16"].font = Font(name="Calibri", size=9.5, color="334155")
    ws_quote["A16"].alignment = align_desc_wrap
    ws_quote.row_dimensions[16].height = 42

    ws_quote.merge_cells("A17:K17")
    ws_quote["A17"] = "⏰ 100% FLEXIBLE SHIFT SCHEDULING: Standard operations run on dedicated night shifts (post-7:00 PM) dispatched from Arlington, TX to guarantee zero daytime disruption. All shift hours, nights, and calendar dates are completely flexible based on client preference (earlier evening starts, weekends, or split buildings) to accommodate building security and tenant schedules at no extra charge."
    ws_quote["A17"].font = Font(name="Calibri", size=9.5, bold=True, color="14532D")
    ws_quote["A17"].fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
    ws_quote["A17"].alignment = align_desc_wrap
    ws_quote.row_dimensions[17].height = 34

    for r_idx in range(10, 18):
        for c in range(1, 12):
            ws_quote.cell(row=r_idx, column=c).border = box_border

    ws_quote.row_dimensions[18].height = 12 # spacer

    # -------------------------------------------------------------
    # TABLE 1: 1.0 COMMERCIAL PRICING SCHEDULE (Rows 19 to 32)
    # -------------------------------------------------------------
    ws_quote.cell(row=19, column=1, value="1.0 COMMERCIAL PRICING SCHEDULE: INITIAL RESET & RECURRING MAINTENANCE PROGRAMS").font = font_section
    ws_quote.row_dimensions[19].height = 24

    t1_headers = [
        "Item",
        "Building Name",
        "Address",
        "Primary floor system",
        "Cleanable Area\n(SQFT)",
        "Phase 1 Rate\n(Per SF)",
        "Phase 1 deep clean\n(expose damage to\nconsider options)",
        "Quarterly Rate\n(Per SF)",
        "Track A: Quarterly\n(Every 3 Months)",
        "Semi-Annual Rate\n(Per SF)",
        "Track B: Semi-Annual\n(Every 6 Months)"
    ]
    ws_quote.row_dimensions[20].height = 44
    for col_num, h_text in enumerate(t1_headers, 1):
        cell = ws_quote.cell(row=20, column=col_num, value=h_text)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = align_header_wrap
        cell.border = box_border

    portfolio_data = [
        (1, "Chase Bank Building", "420 Throckmorton St", "Polished Terrazzo", 2126, 0.80, 0.54, 0.68),
        (2, "The Westbrook", "425 Houston St", "Polished Terrazzo", 1520, 0.80, 0.54, 0.68),
        (3, "The Carnegie", "421 W 3rd St", "Polished Terrazzo", 1175, 0.80, 0.54, 0.68),
        (4, "The Cassidy", "407 Throckmorton St", "Polished Terrazzo", 1134, 0.80, 0.54, 0.68),
        (5, "Burk Burnett Building", "500 Main St", "Ceramic Mosaic Tile", 1108, 0.80, 0.54, 0.68),
        (6, "Sanger Lofts", "222 W 4th St", "Polished Terrazzo", 1071, 0.80, 0.54, 0.68),
        (7, "Petroleum Building", "210 W 6th St", "Polished Marble Tile", 860, 0.80, 0.54, 0.68),
        (8, "The Commerce Building", "420 Commerce St", "Terrazzo Tile", 840, 0.80, 0.54, 0.68),
        (9, "Virtuoso Building", "505 Main St", "Polished Marble Tile", 560, 0.80, 0.54, 0.68),
        (10, "Knights of Pythias Hall", "109-110 E 3rd St", "Ceramic Mosaic Tile", 414, 0.80, 0.54, 0.68),
        (11, "Plaza Hotel Building", "303 Main St", "Commercial Quarry Tile", 345, 0.80, 0.54, 0.68)
    ]

    for idx, item in enumerate(portfolio_data, start=21):
        r_num, b_name, b_addr, b_sub, b_sf, r_mo, r_qtr, r_semi = item
        ws_quote.row_dimensions[idx].height = 18
        fill_row = fill_zebra if idx % 2 == 0 else PatternFill(fill_type=None)

        ws_quote.cell(row=idx, column=1, value=r_num).alignment = align_center
        ws_quote.cell(row=idx, column=2, value=b_name).alignment = align_left
        ws_quote.cell(row=idx, column=3, value=b_addr).alignment = align_left
        ws_quote.cell(row=idx, column=4, value=b_sub).alignment = align_left
        
        c_sf = ws_quote.cell(row=idx, column=5, value=b_sf)
        c_sf.number_format = "#,##0"
        c_sf.alignment = align_center
        
        c_rmo = ws_quote.cell(row=idx, column=6, value=r_mo)
        c_rmo.number_format = "$#,##0.00"
        c_rmo.alignment = align_right

        c_mo = ws_quote.cell(row=idx, column=7, value=f"=MAX(E{idx},600)*F{idx}")
        c_mo.number_format = "$#,##0.00"
        c_mo.alignment = align_right

        c_rq = ws_quote.cell(row=idx, column=8, value=r_qtr)
        c_rq.number_format = "$#,##0.00"
        c_rq.alignment = align_right

        c_qtr = ws_quote.cell(row=idx, column=9, value=f"=MAX(E{idx},600)*H{idx}")
        c_qtr.number_format = "$#,##0.00"
        c_qtr.alignment = align_right

        c_rs = ws_quote.cell(row=idx, column=10, value=r_semi)
        c_rs.number_format = "$#,##0.00"
        c_rs.alignment = align_right

        c_semi = ws_quote.cell(row=idx, column=11, value=f"=MAX(E{idx},600)*J{idx}")
        c_semi.number_format = "$#,##0.00"
        c_semi.alignment = align_right

        for c in range(1, 12):
            cell = ws_quote.cell(row=idx, column=c)
            cell.font = font_regular
            cell.border = box_border
            if fill_row.fill_type:
                cell.fill = fill_row

    # Total Row Table 1 (Row 32)
    tot_r1 = 32
    ws_quote.row_dimensions[tot_r1].height = 22
    ws_quote.merge_cells(f"A{tot_r1}:D{tot_r1}")
    ws_quote[f"A{tot_r1}"] = "GRAND TOTAL SQUARE FOOTAGE (11 Lobbies)"
    ws_quote[f"A{tot_r1}"].font = font_bold
    ws_quote[f"A{tot_r1}"].alignment = align_center

    c_tot_sf1 = ws_quote.cell(row=tot_r1, column=5, value="=SUM(E21:E31)")
    c_tot_sf1.number_format = '#,##0 " SQF"'
    c_tot_sf1.alignment = align_center

    ws_quote.cell(row=tot_r1, column=6, value="$0.80 avg").alignment = align_center

    c_tot_mo = ws_quote.cell(row=tot_r1, column=7, value="=SUM(G21:G31)")
    c_tot_mo.number_format = "$#,##0.00"
    c_tot_mo.alignment = align_right

    ws_quote.cell(row=tot_r1, column=8, value="$0.54 avg").alignment = align_center

    c_tot_qtr = ws_quote.cell(row=tot_r1, column=9, value="=SUM(I21:I31)")
    c_tot_qtr.number_format = "$#,##0.00"
    c_tot_qtr.alignment = align_right

    ws_quote.cell(row=tot_r1, column=10, value="$0.68 avg").alignment = align_center

    c_tot_semi = ws_quote.cell(row=tot_r1, column=11, value="=SUM(K21:K31)")
    c_tot_semi.number_format = "$#,##0.00"
    c_tot_semi.alignment = align_right

    for c in range(1, 12):
        cell = ws_quote.cell(row=tot_r1, column=c)
        cell.font = font_bold
        cell.fill = fill_subtle
        cell.border = total_border

    ws_quote.row_dimensions[33].height = 10 # spacer

    # -------------------------------------------------------------
    # TABLE 2: 2.0 ADDITIONAL CLIENT OPTIONS (Rows 34 to 47)
    # -------------------------------------------------------------
    ws_quote.cell(row=34, column=1, value="2.0 ADDITIONAL CLIENT OPTIONS: PENETRATING SEALER, STAIRCARE, DIAMOND RESTORATION & ART HANDLING").font = font_section
    ws_quote.row_dimensions[34].height = 24

    t2_headers = [
        "Item",
        "Building Name",
        "Address",
        "Primary floor system",
        "Cleanable Area\n(SQFT)",
        "Option A: Sealer\n(BulletProof®)\n$0.31 / SF",
        "Option B: Stair Care\n(Unit Rate Add-On\n500 Main St Only)*",
        "Option C: Capital Diamond Restoration\n(Restores Mirror Shine • Marble & Terrazzo Only)\n$2.65 / SF",
        None,
        "Option D: Furniture Handling\n(Hourly T&M)\nAvailable Per Hour",
        None
    ]
    ws_quote.row_dimensions[35].height = 44
    for col_num, h_text in enumerate(t2_headers, 1):
        if h_text is not None:
            cell = ws_quote.cell(row=35, column=col_num, value=h_text)
            cell.font = font_header
            cell.fill = fill_header_opt
            cell.alignment = align_header_wrap
            cell.border = box_border
            
    ws_quote.merge_cells("H35:I35")
    ws_quote.merge_cells("J35:K35")
    for c in [9, 11]:
        ws_quote.cell(row=35, column=c).border = box_border
        ws_quote.cell(row=35, column=c).fill = fill_header_opt

    for idx, item in enumerate(portfolio_data, start=36):
        num, name, addr, sub, sf, _, _, _ = item
        base_row = idx - 15  # maps row 36 back to row 21 in Table 1
        ws_quote.row_dimensions[idx].height = 18
        fill_row = fill_zebra if idx % 2 == 0 else PatternFill(fill_type=None)

        ws_quote.cell(row=idx, column=1, value=num).alignment = align_center
        ws_quote.cell(row=idx, column=2, value=name).alignment = align_left
        ws_quote.cell(row=idx, column=3, value=addr).alignment = align_left
        ws_quote.cell(row=idx, column=4, value=sub).alignment = align_left

        c_sf2 = ws_quote.cell(row=idx, column=5, value=f"=E{base_row}")
        c_sf2.number_format = "#,##0"
        c_sf2.alignment = align_center

        c_seal = ws_quote.cell(row=idx, column=6, value=f"=MAX(E{idx},600)*0.31")
        c_seal.number_format = "$#,##0.00"
        c_seal.alignment = align_right

        if num == 5:
            c_stv = ws_quote.cell(row=idx, column=7, value="$3/Stp + $21/Lnd")
            c_stv.alignment = align_center
            c_stv.font = Font(name="Calibri", size=9, bold=True, color="16A34A")
        else:
            c_stv = ws_quote.cell(row=idx, column=7, value="N/A (Excluded)")
            c_stv.alignment = align_center
            c_stv.font = Font(name="Calibri", size=9, italic=True, color="64748B")

        ws_quote.merge_cells(f"H{idx}:I{idx}")
        is_grindable = sub in ["Polished Terrazzo", "Terrazzo Tile", "Polished Marble Tile"]
        if is_grindable:
            c_rst = ws_quote.cell(row=idx, column=8, value=f"=MAX(E{idx},600)*2.65")
            c_rst.number_format = "$#,##0.00"
            c_rst.alignment = align_right
        else:
            c_rst = ws_quote.cell(row=idx, column=8, value="N/A (Exempt)")
            c_rst.alignment = align_center
            c_rst.font = Font(name="Calibri", size=9, italic=True, color="64748B")

        ws_quote.merge_cells(f"J{idx}:K{idx}")
        c_fur = ws_quote.cell(row=idx, column=10, value="Available Per Hour")
        c_fur.alignment = align_center

        for c in range(1, 12):
            cell = ws_quote.cell(row=idx, column=c)
            if c == 7: pass
            elif c in [8, 9] and not is_grindable: pass
            else: cell.font = font_regular
            cell.border = box_border
            if fill_row.fill_type:
                cell.fill = fill_row

    # Total Row Table 2 (Row 47)
    tot_r2 = 47
    ws_quote.row_dimensions[tot_r2].height = 22
    ws_quote.merge_cells(f"A{tot_r2}:D{tot_r2}")
    ws_quote[f"A{tot_r2}"] = "GRAND TOTAL SQUARE FOOTAGE (Additional Options)"
    ws_quote[f"A{tot_r2}"].font = font_bold
    ws_quote[f"A{tot_r2}"].alignment = align_center

    c_tot_sf2 = ws_quote.cell(row=tot_r2, column=5, value="=SUM(E36:E46)")
    c_tot_sf2.number_format = '#,##0 " SQF"'
    c_tot_sf2.alignment = align_center

    c_tot_sl2 = ws_quote.cell(row=tot_r2, column=6, value="=SUM(F36:F46)")
    c_tot_sl2.number_format = "$#,##0.00"
    c_tot_sl2.alignment = align_right

    ws_quote.cell(row=tot_r2, column=7, value="Unit Rate Only").alignment = align_center

    ws_quote.merge_cells(f"H{tot_r2}:I{tot_r2}")
    c_tot_rst2 = ws_quote.cell(row=tot_r2, column=8, value="=SUM(H36:H46)")
    c_tot_rst2.number_format = "$#,##0.00"
    c_tot_rst2.alignment = align_right

    ws_quote.merge_cells(f"J{tot_r2}:K{tot_r2}")
    c_tot_fur = ws_quote.cell(row=tot_r2, column=10, value="Available Per Hour")
    c_tot_fur.alignment = align_center

    for c in range(1, 12):
        cell = ws_quote.cell(row=tot_r2, column=c)
        cell.font = font_bold
        cell.fill = fill_subtle
        cell.border = total_border

    ws_quote.row_dimensions[48].height = 10 # spacer

    # -------------------------------------------------------------
    # TABLE 3: 3.0 EXECUTIVE SUMMARY & BILLING TERMS (Rows 49 to 57)
    # -------------------------------------------------------------
    ws_quote.cell(row=49, column=1, value="3.0 COMMERCIAL PROGRAM EXECUTIVE SUMMARY & BILLING TERMS").font = font_section
    ws_quote.row_dimensions[49].height = 24

    ws_quote.row_dimensions[50].height = 20
    ws_quote.merge_cells("A50:C50")
    ws_quote["A50"] = "Service Phase / Scope Module"
    ws_quote["A50"].font = font_header
    ws_quote["A50"].fill = fill_header_opt
    ws_quote["A50"].alignment = align_center

    ws_quote.merge_cells("D50:F50")
    ws_quote["D50"] = "Scope of work"
    ws_quote["D50"].font = font_header
    ws_quote["D50"].fill = fill_header_opt
    ws_quote["D50"].alignment = align_center

    ws_quote.merge_cells("G50:G50")
    ws_quote["G50"] = "Rate Basis"
    ws_quote["G50"].font = font_header
    ws_quote["G50"].fill = fill_header_opt
    ws_quote["G50"].alignment = align_center

    ws_quote.merge_cells("H50:I50")
    ws_quote["H50"] = "Portfolio Invoiced Investment"
    ws_quote["H50"].font = font_header
    ws_quote["H50"].fill = fill_header_opt
    ws_quote["H50"].alignment = align_center

    ws_quote.merge_cells("J50:K50")
    ws_quote["J50"] = "Billing Frequency & Program Terms"
    ws_quote["J50"].font = font_header
    ws_quote["J50"].fill = fill_header_opt
    ws_quote["J50"].alignment = align_center

    for c in range(1, 12):
        ws_quote.cell(row=50, column=c).border = box_border
        ws_quote.cell(row=50, column=c).fill = fill_header_opt

    summary_rows = [
        ("Phase 1 deep clean (expose damage to consider options)", "Rotary machine scrub, deep cleaning solution, edge hand scraping, and extraction across 11 lobbies (600 SF min baseline). Strips surface dirt down to the bare floor to expose existing damage for mutual review; does not grind stone or remove scratches.", "$0.80 / SF", "$9,307.20 complete", "One-Time Baseline Service"),
        ("Phase 2: Modular Sub-Surface Sealer (STONETECH® BulletProof®)", "Deep penetrating sealer applied after cleaning into stone and grout lines (600 SF baseline). Repels water and oil spills; does not create a wax film or shine, and does not stop acid etch marks on polished marble.", "$0.31 / SF", "$3,606.54 complete", "Post-Clean Protection\n(12–24 Month Lifecycle)"),
        ("Phase 3 (Track A): Quarterly Maintenance (Recommended Program)", "Recurring 90-day maintenance scrub across 8 Terrazzo/Marble lobbies; deep brush scrub and grout extraction across 3 Mosaic/Quarry lobbies (600 SF min). Routine cleaning only; does not include diamond grinding.", "$0.54 / SF", "$6,282.36 / pass", "Every 3 Months\n(4x / Year • Recommended)"),
        ("Phase 3 (Track B): Every Six Months Deep Restorative Scrub", "Intensive 180-day deep scrub, heavy cleaner dwell time, and machine extraction across 11 lobbies (600 SF min baseline). Removes 6 months of ground-in traffic dirt; does not include diamond grinding.", "$0.68 / SF", "$7,911.12 / pass", "Every 6 Months\n(2x / Year Semi-Annual)"),
        ("Add-On Option B: Dedicated Marble Staircase Care (500 Main St Only)", "Step machine scrub ($3.00/step), riser wipe-down, brass nosing polish, landing deep clean ($21.00/landing), and sealer at 500 Main St only. Billed strictly by actual step count on site; excludes repairs and other 10 buildings.", "$3.00/Stp + $21/Lnd", "Unit Rate Only\n(T&M Count)", "Optional Per Service Pass\n(500 Main St Only)"),
        ("Add-On Option C: Capital Diamond Restoration", "Multi-step diamond grinding and polishing with wall protection across 8 stone lobbies (9,326 Billing SF). The only service that cuts out deep scratches and restores a high-gloss shine; ceramic and quarry tile are exempt.", "$2.65 / SF", "$24,713.90 complete", "As-Needed Capital Project\n(8 Stone Lobbies)"),
        ("Add-On Option D: Furniture & Artwork Handling", "Building staff clears and replaces lobby furniture before and after service. Crew moving assistance is available upon written request on an hourly basis; HWB is not responsible for unmoved furniture.", "Available Per Hour", "Hourly T&M\n(Upon Request)", "Client-Managed Default\n(Hourly Moving Option)")
    ]

    for s_idx, s_item in enumerate(summary_rows, start=51):
        ws_quote.row_dimensions[s_idx].height = 48
        p_name, p_desc, p_rate, p_pass, p_bill = s_item
        fill_r = fill_green if s_idx == 51 else (fill_zebra if s_idx % 2 == 0 else PatternFill(fill_type=None))
        
        ws_quote.merge_cells(f"A{s_idx}:C{s_idx}")
        ws_quote.merge_cells(f"D{s_idx}:F{s_idx}")
        ws_quote.merge_cells(f"H{s_idx}:I{s_idx}")
        ws_quote.merge_cells(f"J{s_idx}:K{s_idx}")
        
        c_p = ws_quote[f"A{s_idx}"]
        c_p.value = p_name
        c_p.font = font_bold
        c_p.alignment = align_desc_wrap

        c_d = ws_quote[f"D{s_idx}"]
        c_d.value = p_desc
        c_d.font = font_regular
        c_d.alignment = align_desc_wrap

        c_r = ws_quote.cell(row=s_idx, column=7, value=p_rate)
        c_r.font = font_bold
        c_r.alignment = align_center

        c_pass = ws_quote.cell(row=s_idx, column=8, value=p_pass)
        c_pass.font = font_bold if ("complete" in p_pass or "pass" in p_pass or "Unit" in p_pass) else font_regular
        c_pass.alignment = Alignment(horizontal="right", vertical="center", wrap_text=True)
        ws_quote.cell(row=s_idx, column=9).alignment = Alignment(horizontal="right", vertical="center", wrap_text=True)

        c_b = ws_quote.cell(row=s_idx, column=10, value=p_bill)
        c_b.font = font_bold
        c_b.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws_quote.cell(row=s_idx, column=11).alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        for c in range(1, 12):
            cell = ws_quote.cell(row=s_idx, column=c)
            cell.border = box_border
            if fill_r.fill_type:
                cell.fill = fill_r

    ws_quote.row_dimensions[58].height = 10 # spacer

    # -------------------------------------------------------------
    # SECTION 4: 4.0 ARCHITECTURAL PHOTO INSPECTION (Rows 59 to 75)
    # -------------------------------------------------------------
    ws_quote.cell(row=59, column=1, value="4.0 LOBBY FLOOR CONDITION: 4-POINT PHOTO INSPECTION").font = font_section
    ws_quote.row_dimensions[59].height = 24

    ws_quote.merge_cells("A60:K60")
    ws_quote["A60"] = "Photographic documentation of floor conditions, wear patterns, and recommended services across portfolio lobbies."
    ws_quote["A60"].font = Font(name="Calibri", size=9, italic=True, color="475569")
    ws_quote["A60"].alignment = align_left
    ws_quote.row_dimensions[60].height = 18

    # Row 62: Header Bar 1 & 2
    ws_quote.row_dimensions[62].height = 22
    ws_quote.merge_cells("A62:E62")
    ws_quote["A62"] = "PHOTO 1: PLAZA HOTEL BUILDING (303 MAIN ST)"
    ws_quote["A62"].font = font_header
    ws_quote["A62"].fill = fill_header_opt
    ws_quote["A62"].alignment = align_center
    for c in range(1, 6):
        ws_quote.cell(row=62, column=c).border = box_border
        ws_quote.cell(row=62, column=c).fill = fill_header_opt

    ws_quote.cell(row=62, column=6).border = box_border

    ws_quote.merge_cells("G62:K62")
    ws_quote["G62"] = "PHOTO 2: CHASE BANK BUILDING (420 THROCKMORTON ST)"
    ws_quote["G62"].font = font_header
    ws_quote["G62"].fill = fill_header_opt
    ws_quote["G62"].alignment = align_center
    for c in range(7, 12):
        ws_quote.cell(row=62, column=c).border = box_border
        ws_quote.cell(row=62, column=c).fill = fill_header_opt

    # Row 63: Image Container 1 & 2
    ws_quote.row_dimensions[63].height = 180
    ws_quote.merge_cells("A63:E63")
    ws_quote.merge_cells("G63:K63")
    for c in list(range(1, 6)) + [6] + list(range(7, 12)):
        ws_quote.cell(row=63, column=c).border = box_border
        ws_quote.cell(row=63, column=c).fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid") if c != 6 else PatternFill(fill_type=None)

    img_plaza = OpenpyxlImage(img_paths["plaza"])
    img_plaza.width = 175
    img_plaza.height = 233
    ws_quote.add_image(img_plaza, "B63")

    img_chase = OpenpyxlImage(img_paths["chase"])
    img_chase.width = 175
    img_chase.height = 233
    ws_quote.add_image(img_chase, "H63")

    # Row 64: Substrate
    ws_quote.row_dimensions[64].height = 20
    ws_quote.merge_cells("A64:E64")
    ws_quote["A64"] = "Primary floor system: Commercial Quarry Tile"
    ws_quote["A64"].font = font_bold_sm
    ws_quote["A64"].fill = fill_zebra
    ws_quote["A64"].alignment = align_left

    ws_quote.merge_cells("G64:K64")
    ws_quote["G64"] = "Primary floor system: Polished Terrazzo"
    ws_quote["G64"].font = font_bold_sm
    ws_quote["G64"].fill = fill_zebra
    ws_quote["G64"].alignment = align_left

    for c in list(range(1, 6)) + [6] + list(range(7, 12)):
        ws_quote.cell(row=64, column=c).border = box_border
        if c in list(range(1, 6)) + list(range(7, 12)):
            ws_quote.cell(row=64, column=c).fill = fill_zebra

    # Row 65: Floor Issue
    ws_quote.row_dimensions[65].height = 20
    ws_quote.merge_cells("A65:E65")
    ws_quote["A65"] = "Floor Issue: Chemical Bleach Stains & Deep Grout Soil Buildup"
    ws_quote["A65"].font = font_alert_sm
    ws_quote["A65"].alignment = align_left

    ws_quote.merge_cells("G65:K65")
    ws_quote["G65"] = "Floor Issue: Heavy Traffic Wear Pattern & Loss of Floor Shine"
    ws_quote["G65"].font = font_alert_sm
    ws_quote["G65"].alignment = align_left

    for c in list(range(1, 6)) + [6] + list(range(7, 12)):
        ws_quote.cell(row=65, column=c).border = box_border

    # Row 66: Condition Observed
    ws_quote.row_dimensions[66].height = 48
    ws_quote.merge_cells("A66:E66")
    ws_quote["A66"] = "Condition Observed: Harsh cleaner or bleach stripped the tile finish (white patch); grease soaked into unsealed tile; heavy dirt along grout lines."
    ws_quote["A66"].font = font_regular_sm
    ws_quote["A66"].alignment = align_desc_wrap

    ws_quote.merge_cells("G66:K66")
    ws_quote["G66"] = "Condition Observed: Heavy foot traffic wore away the surface shine along the center walkway; fine scratches now trap dirt and leave floors looking dull."
    ws_quote["G66"].font = font_regular_sm
    ws_quote["G66"].alignment = align_desc_wrap

    for c in list(range(1, 6)) + [6] + list(range(7, 12)):
        ws_quote.cell(row=66, column=c).border = box_border

    # Row 67: Recommended Service
    ws_quote.row_dimensions[67].height = 42
    ws_quote.merge_cells("A67:E67")
    ws_quote["A67"] = "Recommended Service: Deep machine scrub to lift embedded soil (Phase 1) + Option A: BulletProof® Sealer to protect tile and grout from stains."
    ws_quote["A67"].font = font_bold_sm
    ws_quote["A67"].fill = fill_green
    ws_quote["A67"].alignment = align_desc_wrap

    ws_quote.merge_cells("G67:K67")
    ws_quote["G67"] = "Recommended Service: Regular quarterly machine scrub and extraction ($0.54/SF) to remove gritty soil and keep floors clean; deep gouges require Option C: Diamond Restoration."
    ws_quote["G67"].font = font_bold_sm
    ws_quote["G67"].fill = fill_green
    ws_quote["G67"].alignment = align_desc_wrap

    for c in list(range(1, 6)) + [6] + list(range(7, 12)):
        ws_quote.cell(row=67, column=c).border = box_border
        if c in list(range(1, 6)) + list(range(7, 12)):
            ws_quote.cell(row=67, column=c).fill = fill_green

    # Row 69: Header Bar 3 & 4
    ws_quote.row_dimensions[69].height = 22
    ws_quote.merge_cells("A69:E69")
    ws_quote["A69"] = "PHOTO 3: PETROLEUM BUILDING (210 W 6TH ST)"
    ws_quote["A69"].font = font_header
    ws_quote["A69"].fill = fill_header_opt
    ws_quote["A69"].alignment = align_center
    for c in range(1, 6):
        ws_quote.cell(row=69, column=c).border = box_border
        ws_quote.cell(row=69, column=c).fill = fill_header_opt

    ws_quote.cell(row=69, column=6).border = box_border

    ws_quote.merge_cells("G69:K69")
    ws_quote["G69"] = "PHOTO 4: VIRTUOSO BUILDING (505 MAIN ST / HISTORIC SCHWARZ BLDG)"
    ws_quote["G69"].font = font_header
    ws_quote["G69"].fill = fill_header_opt
    ws_quote["G69"].alignment = align_center
    for c in range(7, 12):
        ws_quote.cell(row=69, column=c).border = box_border
        ws_quote.cell(row=69, column=c).fill = fill_header_opt

    # Row 70: Image Container 3 & 4
    ws_quote.row_dimensions[70].height = 180
    ws_quote.merge_cells("A70:E70")
    ws_quote.merge_cells("G70:K70")
    for c in list(range(1, 6)) + [6] + list(range(7, 12)):
        ws_quote.cell(row=70, column=c).border = box_border
        ws_quote.cell(row=70, column=c).fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid") if c != 6 else PatternFill(fill_type=None)

    img_pet = OpenpyxlImage(img_paths["petroleum"])
    img_pet.width = 175
    img_pet.height = 233
    ws_quote.add_image(img_pet, "B70")

    img_sch = OpenpyxlImage(img_paths["schwarz"])
    img_sch.width = 175
    img_sch.height = 233
    ws_quote.add_image(img_sch, "H70")

    # Row 71: Substrate
    ws_quote.row_dimensions[71].height = 20
    ws_quote.merge_cells("A71:E71")
    ws_quote["A71"] = "Primary floor system: Polished Marble Tile"
    ws_quote["A71"].font = font_bold_sm
    ws_quote["A71"].fill = fill_zebra
    ws_quote["A71"].alignment = align_left

    ws_quote.merge_cells("G71:K71")
    ws_quote["G71"] = "Primary floor system: Polished Marble Tile"
    ws_quote["G71"].font = font_bold_sm
    ws_quote["G71"].fill = fill_zebra
    ws_quote["G71"].alignment = align_left

    for c in list(range(1, 6)) + [6] + list(range(7, 12)):
        ws_quote.cell(row=71, column=c).border = box_border
        if c in list(range(1, 6)) + list(range(7, 12)):
            ws_quote.cell(row=71, column=c).fill = fill_zebra

    # Row 72: Floor Issue
    ws_quote.row_dimensions[72].height = 20
    ws_quote.merge_cells("A72:E72")
    ws_quote["A72"] = "Floor Issue: Acid Stain Marks & Chemical Etch Rings"
    ws_quote["A72"].font = font_alert_sm
    ws_quote["A72"].alignment = align_left

    ws_quote.merge_cells("G72:K72")
    ws_quote["G72"] = "Floor Issue: Deep Gouges & Scratches from Moving Equipment"
    ws_quote["G72"].font = font_alert_sm
    ws_quote["G72"].alignment = align_left

    for c in list(range(1, 6)) + [6] + list(range(7, 12)):
        ws_quote.cell(row=72, column=c).border = box_border

    # Row 73: Condition Observed
    ws_quote.row_dimensions[73].height = 48
    ws_quote.merge_cells("A73:E73")
    ws_quote["A73"] = "Condition Observed: Acidic spills (coffee, citrus drinks, sanitizer drips) ate into polished marble, leaving dull, rough white spots that mopping cannot clean."
    ws_quote["A73"].font = font_regular_sm
    ws_quote["A73"].alignment = align_desc_wrap

    ws_quote.merge_cells("G73:K73")
    ws_quote["G73"] = "Condition Observed: Heavy equipment, freight carts, or unpadded furniture dragged across the floor cut deep white scratches into the black marble."
    ws_quote["G73"].font = font_regular_sm
    ws_quote["G73"].alignment = align_desc_wrap

    for c in list(range(1, 6)) + [6] + list(range(7, 12)):
        ws_quote.cell(row=73, column=c).border = box_border

    # Row 74: Recommended Service
    ws_quote.row_dimensions[74].height = 42
    ws_quote.merge_cells("A74:E74")
    ws_quote["A74"] = "Recommended Service: Diamond polishing to smooth out etch marks and restore shine + Option A: BulletProof® Sealer to protect against stains."
    ws_quote["A74"].font = font_bold_sm
    ws_quote["A74"].fill = fill_green
    ws_quote["A74"].alignment = align_desc_wrap

    ws_quote.merge_cells("G74:K74")
    ws_quote["G74"] = "Recommended Service: Option C: Diamond Restoration ($2.65/SF) to grind out deep scratch valleys and polish back to a high-gloss finish."
    ws_quote["G74"].font = font_bold_sm
    ws_quote["G74"].fill = fill_green
    ws_quote["G74"].alignment = align_desc_wrap

    for c in list(range(1, 6)) + [6] + list(range(7, 12)):
        ws_quote.cell(row=74, column=c).border = box_border
        if c in list(range(1, 6)) + list(range(7, 12)):
            ws_quote.cell(row=74, column=c).fill = fill_green

    ws_quote.row_dimensions[75].height = 12 # spacer

    # -------------------------------------------------------------
    # SECTION 5.0: 5.0 OPERATIONAL DISPATCH GANTT SCHEDULE (Rows 76 to 97)
    # -------------------------------------------------------------
    ws_quote.cell(row=76, column=1, value="5.0 OPERATIONAL DISPATCH GANTT SCHEDULE (10 DEDICATED NIGHT SHIFTS)").font = font_section
    ws_quote.row_dimensions[76].height = 24

    ws_quote.merge_cells("A77:K77")
    ws_quote["A77"] = "OPERATIONAL DISPATCH GANTT SCHEDULE — DOWNTOWN FORT WORTH 11-BUILDING PORTFOLIO"
    ws_quote["A77"].font = Font(name="Calibri", size=9.5, italic=True, color="475569")
    ws_quote.row_dimensions[77].height = 18

    # Metadata Row 78
    ws_quote.row_dimensions[78].height = 18
    ws_quote.merge_cells("A78:B78")
    ws_quote["A78"] = "Base Dispatch Origin:"
    ws_quote["A78"].font = font_bold
    ws_quote.merge_cells("C78:D78")
    ws_quote["C78"] = "Arlington, TX"
    ws_quote["C78"].font = font_regular

    ws_quote.merge_cells("E78:F78")
    ws_quote["E78"] = "Assigned Crew Unit:"
    ws_quote["E78"].font = font_bold
    ws_quote.merge_cells("G78:H78")
    ws_quote["G78"] = "2 Specialized Floor Technicians"
    ws_quote["G78"].font = font_regular

    ws_quote.merge_cells("I78:J78")
    ws_quote["I78"] = "Dedicated Mobilization:"
    ws_quote["I78"].font = font_bold
    ws_quote["K78"] = "10 Dedicated Night Shifts"
    ws_quote["K78"].font = font_regular
    for c in range(1, 12):
        ws_quote.cell(row=78, column=c).border = box_border

    # Legend Row 79
    ws_quote.row_dimensions[79].height = 20
    ws_quote.merge_cells("A79:D79")
    ws_quote["A79"] = "LEGEND & SERVICE COLOR CODING:"
    ws_quote["A79"].font = font_bold
    ws_quote["A79"].alignment = align_center
    ws_quote["A79"].fill = fill_subtle

    ws_quote.merge_cells("E79:F79")
    ws_quote["E79"] = "Phase 1: Initial Deep Clean"
    ws_quote["E79"].font = font_badge_white
    ws_quote["E79"].fill = fill_p1_deep_clean
    ws_quote["E79"].alignment = align_center

    ws_quote.merge_cells("G79:H79")
    ws_quote["G79"] = "Phase 2: Modular Sealer"
    ws_quote["G79"].font = font_badge_white
    ws_quote["G79"].fill = fill_p2_sealer
    ws_quote["G79"].alignment = align_center

    ws_quote.merge_cells("I79:J79")
    ws_quote["I79"] = "Track A: Quarterly Care"
    ws_quote["I79"].font = font_badge_white
    ws_quote["I79"].fill = fill_p3_quarterly
    ws_quote["I79"].alignment = align_center

    ws_quote["K79"] = "Option B: Stairs"
    ws_quote["K79"].font = font_badge_white
    ws_quote["K79"].fill = fill_opt_stairs
    ws_quote["K79"].alignment = align_center
    for c in range(1, 12):
        ws_quote.cell(row=79, column=c).border = box_border

    # 3-Tier Headers (Rows 80 to 82)
    ws_quote.row_dimensions[80].height = 20
    ws_quote.row_dimensions[81].height = 16
    ws_quote.row_dimensions[82].height = 16

    gantt_sec5_headers = [
        ("A", "Item"),
        ("B", "Building Name"),
        ("C", "Address"),
        ("D", "Total SQF"),
        ("E", "Shift Allocation"),
        ("F", "Crew Hours")
    ]
    for col_letter, h_text in gantt_sec5_headers:
        ws_quote.merge_cells(f"{col_letter}80:{col_letter}82")
        cell = ws_quote[f"{col_letter}80"]
        cell.value = h_text
        cell.font = font_header
        cell.fill = fill_header_opt
        cell.alignment = align_header_wrap
        for r_h in range(80, 83):
            ws_quote[f"{col_letter}{r_h}"].border = box_border
            ws_quote[f"{col_letter}{r_h}"].fill = fill_header_opt

    ws_quote.merge_cells("G80:K82")
    ws_quote["G80"] = "Service Provided (Phase 1 Baseline)"
    ws_quote["G80"].font = font_header
    ws_quote["G80"].fill = fill_header_opt
    ws_quote["G80"].alignment = align_header_wrap
    for r_h in range(80, 83):
        for c_h in range(7, 12):
            ws_quote.cell(row=r_h, column=c_h).border = box_border
            ws_quote.cell(row=r_h, column=c_h).fill = fill_header_opt

    # Calendar Grid Columns L to AT (Cols 12 to 46)
    days_dates = [31] + list(range(1, 31)) + list(range(1, 5))
    days_names = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'] * 5
    weeks = [
        ("Week 1: Aug 31, 2026", 12, 18),
        ("Week 2: Sep 07, 2026", 19, 25),
        ("Week 3: Sep 14, 2026", 26, 32),
        ("Week 4: Sep 21, 2026", 33, 39),
        ("Week 5: Sep 28, 2026", 40, 46)
    ]
    for w_title, c_start, c_end in weeks:
        ws_quote.merge_cells(start_row=80, start_column=c_start, end_row=80, end_column=c_end)
        w_cell = ws_quote.cell(row=80, column=c_start, value=w_title)
        w_cell.font = font_header
        w_cell.fill = fill_header
        w_cell.alignment = align_center
        for c in range(c_start, c_end + 1):
            ws_quote.cell(row=80, column=c).border = box_border
            ws_quote.cell(row=80, column=c).fill = fill_header

    for d_idx, d_num in enumerate(days_dates):
        c_col = 12 + d_idx
        c_d = ws_quote.cell(row=81, column=c_col, value=d_num)
        c_d.font = font_bold
        c_d.fill = fill_title
        c_d.font = Font(name="Calibri", size=9, bold=True, color="FFFFFF")
        c_d.alignment = align_center
        c_d.border = box_border

    for d_idx, d_name in enumerate(days_names):
        c_col = 12 + d_idx
        c_name = ws_quote.cell(row=82, column=c_col, value=d_name)
        is_wknd = d_name in ['Sa', 'Su']
        c_name.fill = PatternFill(start_color="475569", end_color="475569", fill_type="solid") if is_wknd else PatternFill(start_color="334155", end_color="334155", fill_type="solid")
        c_name.font = Font(name="Calibri", size=8.5, bold=True, color="FFFFFF" if is_wknd else "94A3B8")
        c_name.alignment = align_center
        c_name.border = box_border

    # Building Data Rows 83 to 93
    schedule_rows = [
        (1, "Chase Bank Building", "420 Throckmorton St", 2126, "Dedicated Night 1 (3.5h)", 3.5, "Phase 1: Initial Deep Clean", [13], [17], [27], []),
        (2, "The Westbrook", "425 Houston St", 1520, "Dedicated Night 2 (3.0h)", 3.0, "Phase 1: Initial Deep Clean", [14], [17], [28], []),
        (3, "The Carnegie", "421 W 3rd St", 1175, "Dedicated Night 3 (2.8h)", 2.8, "Phase 1: Initial Deep Clean", [15], [17], [29], []),
        (4, "The Cassidy", "407 Throckmorton St", 1134, "Dedicated Night 4 (2.6h)", 2.6, "Phase 1: Initial Deep Clean", [16], [17], [30], []),
        (5, "Burk Burnett Building", "500 Main St", 1108, "Dedicated Night 5 (2.6h)", 2.6, "Phase 1: Initial Deep Clean", [19], [24], [33], [34]),
        (6, "Sanger Lofts", "222 W 4th St", 1071, "Dedicated Night 6 (2.5h)", 2.5, "Phase 1: Initial Deep Clean", [20], [24], [34], []),
        (7, "Petroleum Building", "210 W 6th St", 860, "Dedicated Night 7 (2.2h)", 2.2, "Phase 1: Initial Deep Clean", [21], [24], [35], []),
        (8, "The Commerce Building", "420 Commerce St", 840, "Dedicated Night 8 (2.2h)", 2.2, "Phase 1: Initial Deep Clean", [22], [24], [36], []),
        (9, "Virtuoso Building", "505 Main St", 560, "Boutique Night 9 (1.8h)", 1.8, "Phase 1: Initial Deep Clean", [23], [24], [37], []),
        (10, "Knights of Pythias Hall", "109-110 E 3rd St", 414, "Boutique Night 9 (1.6h)", 1.6, "Phase 1: Initial Deep Clean", [23], [24], [37], []),
        (11, "Plaza Hotel Building", "303 Main St", 345, "Boutique Night 10 (1.5h)", 1.5, "Phase 1: Initial Deep Clean", [26], [27], [40], [])
    ]

    for b_idx, item in enumerate(schedule_rows, start=83):
        num, name, addr, sf, window, crew_time, default_service, p1_cols, seal_cols, rec_cols, stair_cols = item
        ws_quote.row_dimensions[b_idx].height = 18

        ws_quote.cell(row=b_idx, column=1, value=num).alignment = align_center
        ws_quote.cell(row=b_idx, column=2, value=name).alignment = align_left
        ws_quote.cell(row=b_idx, column=3, value=addr).alignment = align_left
        
        c_sf = ws_quote.cell(row=b_idx, column=4, value=sf)
        c_sf.number_format = "#,##0"
        c_sf.alignment = align_center
        
        ws_quote.cell(row=b_idx, column=5, value=window).alignment = align_left
        
        c_hrs = ws_quote.cell(row=b_idx, column=6, value=crew_time)
        c_hrs.number_format = '0.0 "hrs"'
        c_hrs.alignment = align_center
        
        ws_quote.merge_cells(f"G{b_idx}:K{b_idx}")
        c_svc = ws_quote.cell(row=b_idx, column=7, value=default_service)
        c_svc.alignment = align_left
        c_svc.font = font_regular

        for c in range(1, 12):
            cell = ws_quote.cell(row=b_idx, column=c)
            cell.font = font_bold if c in [2] else font_regular
            cell.border = box_border
            if b_idx % 2 == 0:
                cell.fill = fill_zebra

        # Calendar cells (Cols 12 to 46)
        for day_idx in range(1, 36):
            col = day_idx + 11
            cell = ws_quote.cell(row=b_idx, column=col)
            cell.border = box_border
            
            if col in p1_cols:
                cell.fill = fill_p1_deep_clean
                cell.value = "DEEP"
                cell.font = font_badge_white
                cell.alignment = align_center
            elif col in seal_cols:
                cell.fill = fill_p2_sealer
                cell.value = "SEAL"
                cell.font = font_badge_white
                cell.alignment = align_center
            elif col in rec_cols:
                cell.fill = fill_p3_quarterly
                cell.value = "QTR"
                cell.font = font_badge_white
                cell.alignment = align_center
            elif col in stair_cols:
                cell.fill = fill_opt_stairs
                cell.value = "STAIR"
                cell.font = font_badge_white
                cell.alignment = align_center
            elif (col - 12) % 7 in [5, 6]:
                cell.fill = fill_weekend

    # Data Validation Dropdown for G83:G93
    dv_svc_quote = DataValidation(
        type="list",
        formula1='"Phase 1: Initial Deep Clean,Phase 2: Modular Sealer,Track A: Quarterly Care,Track B: Semi-Annual Care,Option B: Stair Detailing,Option C: Diamond Restoration"',
        allow_blank=True
    )
    ws_quote.add_data_validation(dv_svc_quote)
    dv_svc_quote.add("G83:G93")

    # Total Row 94
    tot_g_row = 94
    ws_quote.row_dimensions[tot_g_row].height = 20
    ws_quote.merge_cells(f"A{tot_g_row}:C{tot_g_row}")
    ws_quote[f"A{tot_g_row}"] = "TOTAL PORTFOLIO DISPATCH (Phase 1 Deep Clean)"
    ws_quote[f"A{tot_g_row}"].font = font_bold
    ws_quote[f"A{tot_g_row}"].alignment = align_center

    c_tot_sf = ws_quote.cell(row=tot_g_row, column=4, value="=SUM(D83:D93)")
    c_tot_sf.number_format = '#,##0 " SQF"'
    c_tot_sf.alignment = align_center

    ws_quote.cell(row=tot_g_row, column=5, value="10 Dedicated Shifts / Pass").alignment = align_center
    c_tot_hrs = ws_quote.cell(row=tot_g_row, column=6, value="=SUM(F83:F93)")
    c_tot_hrs.number_format = '0.0 "hrs total"'
    c_tot_hrs.alignment = align_center

    ws_quote.merge_cells(f"G{tot_g_row}:K{tot_g_row}")
    c_tot_svc = ws_quote.cell(row=tot_g_row, column=7, value="11 Properties Scheduled")
    c_tot_svc.alignment = align_center
    c_tot_svc.font = font_bold

    for c in range(1, 12):
        cell = ws_quote.cell(row=tot_g_row, column=c)
        cell.font = font_bold
        cell.fill = fill_subtle
        cell.border = total_border

    for c in range(12, 47):
        cell = ws_quote.cell(row=tot_g_row, column=c)
        cell.border = total_border
        cell.fill = fill_subtle

    # Flexible shift note at Row 96
    ws_quote.row_dimensions[95].height = 10 # spacer
    ws_quote.merge_cells("A96:K96")
    ws_quote["A96"] = "*Note: Shift timing and scheduled calendar dates are 100% flexible based on client preference. HWB will adapt dispatch hours (earlier start, late night, or weekend windows) to accommodate building security and tenant schedules at no additional cost."
    ws_quote["A96"].font = Font(name="Calibri", size=8.5, italic=True, color="475569")
    ws_quote["A96"].alignment = Alignment(horizontal="left", vertical="center")
    ws_quote.row_dimensions[96].height = 18

    # Column widths for Sheet 1
    col_widths_s1 = {
        1: 5,   # Item
        2: 24,  # Building Name
        3: 20,  # Address
        4: 38,  # Primary Floor Substrate / Scope Col D
        5: 18,  # Cleanable Area (SQFT) / Scope Col E
        6: 13,  # Monthly Rate (Per SF) / Scope Col F
        7: 15,  # Monthly Option (1x/Mo) / Unit Rate Col G
        8: 14,  # Quarterly Rate (Per SF) / Inv Col H
        9: 16,  # Quarterly Option (Every 3 Mo) / Inv Col I
        10: 17, # Semi-Annual Rate (Per SF) / Terms Col J
        11: 21  # Every 6 Months (Semi-Annual) / Terms Col K
    }
    for col_idx, width in col_widths_s1.items():
        ws_quote.column_dimensions[get_column_letter(col_idx)].width = width
    for day_col in range(12, 47):
        ws_quote.column_dimensions[get_column_letter(day_col)].width = 4.8

    # Page breaks for Option A Printing
    ws_quote.row_breaks.append(Break(id=18)) # Page 1: Metadata + Executive Summary
    ws_quote.row_breaks.append(Break(id=33)) # Page 2: Section 1.0 Pricing Schedule
    ws_quote.row_breaks.append(Break(id=48)) # Page 3: Section 2.0 Additional Options
    ws_quote.row_breaks.append(Break(id=58)) # Page 4: Section 3.0 Executive Terms
    ws_quote.row_breaks.append(Break(id=75)) # Page 5: Section 4.0 Photos
    # Page 6: Section 5.0 Gantt Schedule

    # -------------------------------------------------------------
    # SHEET 2: Service_Gantt_Schedule (Dedicated Fullscreen View)
    # -------------------------------------------------------------
    ws_gantt = wb.create_sheet(title="Service_Gantt_Schedule")
    ws_gantt.views.sheetView[0].showGridLines = True

    ws_gantt.merge_cells("A1:AP1")
    ws_gantt["A1"] = "HWB CLEANING SERVICES LLC"
    ws_gantt["A1"].font = font_title
    ws_gantt["A1"].fill = fill_title
    ws_gantt["A1"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws_gantt.row_dimensions[1].height = 28

    ws_gantt.merge_cells("A2:AP2")
    ws_gantt["A2"] = "OPERATIONAL DISPATCH GANTT SCHEDULE — DOWNTOWN FORT WORTH 11-BUILDING PORTFOLIO"
    ws_gantt["A2"].font = Font(name="Calibri", size=10.5, bold=True, color="93C5FD")
    ws_gantt["A2"].fill = fill_title
    ws_gantt["A2"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws_gantt.row_dimensions[2].height = 18

    # Row 4: Base Dispatch & Project Start
    ws_gantt.merge_cells("A4:B4")
    ws_gantt["A4"] = "Base Dispatch Origin:"
    ws_gantt["A4"].font = font_bold
    ws_gantt.merge_cells("C4:D4")
    ws_gantt["C4"] = "Arlington, TX"
    ws_gantt["C4"].font = font_regular

    ws_gantt.merge_cells("E4:F4")
    ws_gantt["E4"] = "Project Start Date:"
    ws_gantt["E4"].font = font_bold
    import datetime
    c_start_g = ws_gantt.cell(row=4, column=7, value=datetime.date(2026, 9, 1))
    c_start_g.font = font_bold
    c_start_g.number_format = "yyyy-mm-dd"
    c_start_g.alignment = Alignment(horizontal="left", vertical="center")
    ws_gantt.row_dimensions[4].height = 17

    # Row 5: Assigned Crew Unit & Display Week
    ws_gantt.merge_cells("A5:B5")
    ws_gantt["A5"] = "Assigned Crew Unit:"
    ws_gantt["A5"].font = font_bold
    ws_gantt.merge_cells("C5:D5")
    ws_gantt["C5"] = "2 Specialized Floor Technicians"
    ws_gantt["C5"].font = font_regular

    ws_gantt.merge_cells("E5:F5")
    ws_gantt["E5"] = "Display Week:"
    ws_gantt["E5"].font = font_bold
    c_disp = ws_gantt.cell(row=5, column=7, value=1)
    c_disp.font = font_bold
    c_disp.number_format = "0"
    c_disp.alignment = Alignment(horizontal="left", vertical="center")
    ws_gantt.row_dimensions[5].height = 17

    # Row 6: Scope Target & Shift Mobilization
    ws_gantt.merge_cells("A6:B6")
    ws_gantt["A6"] = "Primary Service Target:"
    ws_gantt["A6"].font = font_bold
    ws_gantt.merge_cells("C6:D6")
    ws_gantt["C6"] = "Phase 1: Initial Deep Clean"
    ws_gantt["C6"].font = font_regular

    ws_gantt.merge_cells("E6:F6")
    ws_gantt["E6"] = "Dedicated Shift Mobilization:"
    ws_gantt["E6"].font = font_bold
    c_tot_q = ws_gantt.cell(row=6, column=7, value="10 Dedicated Night Shifts")
    c_tot_q.font = font_regular
    c_tot_q.alignment = Alignment(horizontal="left", vertical="center")
    ws_gantt.row_dimensions[6].height = 17

    # Row 8: Legend
    ws_gantt.row_dimensions[8].height = 20
    ws_gantt.merge_cells("H8:I8")
    ws_gantt["H8"] = "LEGEND"
    ws_gantt["H8"].font = font_bold
    ws_gantt["H8"].alignment = align_center
    ws_gantt["H8"].fill = fill_subtle
    ws_gantt["H8"].border = box_border
    ws_gantt["I8"].border = box_border

    legend_items = [
        ("J8:N8", "Phase 1: Initial Deep Clean", fill_p1_deep_clean),
        ("O8:S8", "Phase 2: Modular Sealer (BulletProof®)", fill_p2_sealer),
        ("T8:X8", "Track A: Quarterly Floor Care", fill_p3_quarterly),
        ("Y8:AC8", "Track B: Semi-Annual Deep Scrub", fill_p3_semiannual),
        ("AD8:AH8", "Option B: Stair Detailing (500 Main)", fill_opt_stairs),
        ("AI8:AM8", "Option C: Diamond Restoration", fill_opt_diamond)
    ]
    for cell_range, label, fill_bg in legend_items:
        ws_gantt.merge_cells(cell_range)
        top_left = cell_range.split(":")[0]
        c_box = ws_gantt[top_left]
        c_box.value = label
        c_box.font = font_badge_white
        c_box.fill = fill_bg
        c_box.alignment = align_center
        cols_in_range = range(openpyxl.utils.column_index_from_string(cell_range.split(":")[0][:1] if len(cell_range.split(":")[0])==2 else cell_range.split(":")[0][:2]), openpyxl.utils.column_index_from_string(cell_range.split(":")[1][:1] if len(cell_range.split(":")[1])==2 else cell_range.split(":")[1][:2]) + 1)
        for col_idx in cols_in_range:
            ws_gantt.cell(row=8, column=col_idx).border = box_border
            ws_gantt.cell(row=8, column=col_idx).fill = fill_bg

    # Rows 9-11: Headers
    ws_gantt.row_dimensions[9].height = 20
    ws_gantt.row_dimensions[10].height = 16
    ws_gantt.row_dimensions[11].height = 16

    gantt_headers = [
        ("A", "Item"),
        ("B", "Building Name"),
        ("C", "Address"),
        ("D", "Total SQF"),
        ("E", "Shift Allocation"),
        ("F", "Crew Hours"),
        ("G", "Service Provided")
    ]
    for col_letter, h_text in gantt_headers:
        ws_gantt.merge_cells(f"{col_letter}9:{col_letter}11")
        cell = ws_gantt[f"{col_letter}9"]
        cell.value = h_text
        cell.font = font_header
        cell.fill = fill_header_opt
        cell.alignment = align_header_wrap
        for r_h in range(9, 12):
            ws_gantt[f"{col_letter}{r_h}"].border = box_border
            ws_gantt[f"{col_letter}{r_h}"].fill = fill_header_opt

    week_blocks = [
        ("H9:N9", 8, "H10"),
        ("O9:U9", 15, "O10"),
        ("V9:AB9", 22, "V10"),
        ("AC9:AI9", 29, "AC10"),
        ("AJ9:AP9", 36, "AJ10")
    ]
    for w_range, start_col, ref_cell in week_blocks:
        ws_gantt.merge_cells(w_range)
        top_cell = ws_gantt[w_range.split(":")[0]]
        top_cell.value = f"={ref_cell}"
        top_cell.number_format = 'mmm d, yyyy'
        top_cell.font = font_header
        top_cell.fill = fill_header
        top_cell.alignment = align_center
        end_col = start_col + 6
        for c in range(start_col, end_col + 1):
            ws_gantt.cell(row=9, column=c).border = box_border
            ws_gantt.cell(row=9, column=c).fill = fill_header

    ws_gantt["H10"] = "=Project_Start-WEEKDAY(Project_Start,1)+2+7*(Display_Week-1)"
    ws_gantt["H10"].number_format = "d"
    ws_gantt["H10"].alignment = align_center
    ws_gantt["H10"].font = font_bold
    ws_gantt["H10"].border = box_border
    ws_gantt["H10"].fill = fill_subtle

    for col in range(9, 43):
        prev_col_letter = get_column_letter(col - 1)
        cell = ws_gantt.cell(row=10, column=col, value=f"={prev_col_letter}10+1")
        cell.number_format = "d"
        cell.alignment = align_center
        cell.font = font_bold
        cell.border = box_border
        cell.fill = fill_subtle

    for col in range(8, 43):
        col_letter = get_column_letter(col)
        cell = ws_gantt.cell(row=11, column=col, value=f'=LEFT(TEXT({col_letter}10,"ddd"),2)')
        cell.font = font_bold_sm
        cell.border = box_border
        day_offset = (col - 8) % 7
        if day_offset in [5, 6]:
            cell.fill = PatternFill(start_color="475569", end_color="475569", fill_type="solid")
            cell.font = Font(name="Calibri", size=8.5, bold=True, color="FFFFFF")
        else:
            cell.fill = PatternFill(start_color="334155", end_color="334155", fill_type="solid")
            cell.font = Font(name="Calibri", size=8.5, bold=True, color="94A3B8")
        cell.alignment = align_center

    schedule_rows_s2 = [
        (1, "Chase Bank Building", "420 Throckmorton St", 2126, "Dedicated Night 1 (3.5h)", 3.5, "Phase 1: Initial Deep Clean", [9], [13], [23], []),
        (2, "The Westbrook", "425 Houston St", 1520, "Dedicated Night 2 (3.0h)", 3.0, "Phase 1: Initial Deep Clean", [10], [13], [24], []),
        (3, "The Carnegie", "421 W 3rd St", 1175, "Dedicated Night 3 (2.8h)", 2.8, "Phase 1: Initial Deep Clean", [11], [13], [25], []),
        (4, "The Cassidy", "407 Throckmorton St", 1134, "Dedicated Night 4 (2.6h)", 2.6, "Phase 1: Initial Deep Clean", [12], [13], [26], []),
        (5, "Burk Burnett Building", "500 Main St", 1108, "Dedicated Night 5 (2.6h)", 2.6, "Phase 1: Initial Deep Clean", [15], [20], [29], [30]),
        (6, "Sanger Lofts", "222 W 4th St", 1071, "Dedicated Night 6 (2.5h)", 2.5, "Phase 1: Initial Deep Clean", [16], [20], [30], []),
        (7, "Petroleum Building", "210 W 6th St", 860, "Dedicated Night 7 (2.2h)", 2.2, "Phase 1: Initial Deep Clean", [17], [20], [31], []),
        (8, "The Commerce Building", "420 Commerce St", 840, "Dedicated Night 8 (2.2h)", 2.2, "Phase 1: Initial Deep Clean", [18], [20], [32], []),
        (9, "Virtuoso Building", "505 Main St", 560, "Boutique Night 9 (1.8h)", 1.8, "Phase 1: Initial Deep Clean", [19], [20], [33], []),
        (10, "Knights of Pythias Hall", "109-110 E 3rd St", 414, "Boutique Night 9 (1.6h)", 1.6, "Phase 1: Initial Deep Clean", [19], [20], [33], []),
        (11, "Plaza Hotel Building", "303 Main St", 345, "Boutique Night 10 (1.5h)", 1.5, "Phase 1: Initial Deep Clean", [22], [23], [36], [])
    ]

    for b_idx, item in enumerate(schedule_rows_s2, start=12):
        num, name, addr, sf, window, crew_time, default_service, p1_cols, seal_cols, rec_cols, stair_cols = item
        ws_gantt.row_dimensions[b_idx].height = 18
        
        ws_gantt.cell(row=b_idx, column=1, value=num).alignment = align_center
        ws_gantt.cell(row=b_idx, column=2, value=name).alignment = align_left
        ws_gantt.cell(row=b_idx, column=3, value=addr).alignment = align_left
        
        c_sf = ws_gantt.cell(row=b_idx, column=4, value=sf)
        c_sf.number_format = "#,##0"
        c_sf.alignment = align_center
        
        ws_gantt.cell(row=b_idx, column=5, value=window).alignment = align_left
        
        c_hrs = ws_gantt.cell(row=b_idx, column=6, value=crew_time)
        c_hrs.number_format = '0.0 "hrs"'
        c_hrs.alignment = align_center
        
        c_svc = ws_gantt.cell(row=b_idx, column=7, value=default_service)
        c_svc.alignment = align_left
        c_svc.font = font_regular

        for c in range(1, 8):
            cell = ws_gantt.cell(row=b_idx, column=c)
            cell.font = font_bold if c in [2] else font_regular
            cell.border = box_border
            if b_idx % 2 == 0:
                cell.fill = fill_zebra

        for day_idx in range(1, 36):
            col = day_idx + 7
            cell = ws_gantt.cell(row=b_idx, column=col)
            cell.border = box_border
            
            if col in p1_cols:
                cell.fill = fill_p1_deep_clean
                cell.value = "DEEP"
                cell.font = font_badge_white
                cell.alignment = align_center
            elif col in seal_cols:
                cell.fill = fill_p2_sealer
                cell.value = "SEAL"
                cell.font = font_badge_white
                cell.alignment = align_center
            elif col in rec_cols:
                cell.fill = fill_p3_quarterly
                cell.value = "QTR"
                cell.font = font_badge_white
                cell.alignment = align_center
            elif col in stair_cols:
                cell.fill = fill_opt_stairs
                cell.value = "STAIR"
                cell.font = font_badge_white
                cell.alignment = align_center
            elif (col - 8) % 7 in [5, 6]:
                cell.fill = fill_weekend

    dv_service = DataValidation(
        type="list",
        formula1='"Phase 1: Initial Deep Clean,Phase 2: Modular Sealer,Track A: Quarterly Care,Track B: Semi-Annual Care,Option B: Stair Detailing,Option C: Diamond Restoration"',
        allow_blank=True
    )
    ws_gantt.add_data_validation(dv_service)
    dv_service.add("G12:G22")

    tot_g_row2 = 23
    ws_gantt.row_dimensions[tot_g_row2].height = 20
    ws_gantt.merge_cells(f"A{tot_g_row2}:C{tot_g_row2}")
    ws_gantt[f"A{tot_g_row2}"] = "TOTAL PORTFOLIO DISPATCH (Phase 1 Deep Clean)"
    ws_gantt[f"A{tot_g_row2}"].font = font_bold
    ws_gantt[f"A{tot_g_row2}"].alignment = align_center

    c_tot_sf_g = ws_gantt.cell(row=tot_g_row2, column=4, value="=SUM(D12:D22)")
    c_tot_sf_g.number_format = '#,##0 " SQF"'
    c_tot_sf_g.alignment = align_center

    ws_gantt.cell(row=tot_g_row2, column=5, value="10 Dedicated Shifts / Pass").alignment = align_center
    c_tot_hrs_g = ws_gantt.cell(row=tot_g_row2, column=6, value="=SUM(F12:F22)")
    c_tot_hrs_g.number_format = '0.0 "hrs total"'
    c_tot_hrs_g.alignment = align_center
    c_tot_svc_g = ws_gantt.cell(row=tot_g_row2, column=7, value="11 Properties Scheduled")
    c_tot_svc_g.alignment = align_center
    c_tot_svc_g.font = font_bold

    for c in range(1, 8):
        cell = ws_gantt.cell(row=tot_g_row2, column=c)
        cell.font = font_bold
        cell.fill = fill_subtle
        cell.border = total_border

    for c in range(8, 43):
        cell = ws_gantt.cell(row=tot_g_row2, column=c)
        cell.border = total_border
        cell.fill = fill_subtle

    gantt_widths = {1: 6, 2: 26, 3: 24, 4: 20, 5: 24, 6: 15, 7: 28}
    for col_idx, width in gantt_widths.items():
        ws_gantt.column_dimensions[get_column_letter(col_idx)].width = width
    for day_col in range(8, 43):
        ws_gantt.column_dimensions[get_column_letter(day_col)].width = 4.8

    # Flexible shift note row 25
    ws_gantt.merge_cells("A25:N25")
    ws_gantt["A25"] = "*Note: Shift timing and scheduled calendar dates are 100% flexible based on client preference. HWB will adapt dispatch hours (earlier start, late night, or weekend windows) to accommodate building security and tenant schedules at no additional cost."
    ws_gantt["A25"].font = Font(name="Calibri", size=8.5, italic=True, color="64748B")
    ws_gantt["A25"].alignment = Alignment(horizontal="left", vertical="center")
    ws_gantt.row_dimensions[25].height = 18

    # -------------------------------------------------------------
    # SHEET 3: Cost_Underwriting_Audit
    # -------------------------------------------------------------
    ws_cost = wb.create_sheet(title="Cost_Underwriting_Audit")
    ws_cost.views.sheetView[0].showGridLines = True

    ws_cost.merge_cells("A1:K1")
    ws_cost["A1"] = "HWB CLEANING SERVICES LLC"
    ws_cost["A1"].font = font_title
    ws_cost["A1"].fill = fill_title
    ws_cost["A1"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws_cost.row_dimensions[1].height = 28

    ws_cost.merge_cells("A2:K2")
    ws_cost["A2"] = "INTERNAL OPERATIONAL UNDERWRITING AUDIT — ARLINGTON, TX DISPATCH BASIS"
    ws_cost["A2"].font = Font(name="Calibri", size=10.5, bold=True, color="93C5FD")
    ws_cost["A2"].fill = fill_title
    ws_cost["A2"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws_cost.row_dimensions[2].height = 18

    cost_headers = [
        "Item",
        "Building Name",
        "Area (SF)",
        "Crew Hours\n(2 Techs)",
        "Labor Cost\n($57.50/hr)",
        "Chemicals\n& Supplies",
        "Transit & Equip",
        "Supervision\n& Admin",
        "Total Cost\nBasis",
        "Quarterly Quote\n($0.54/SF)",
        "Gross Profit\nMargin %"
    ]
    ws_cost.row_dimensions[4].height = 36
    for col_num, h_text in enumerate(cost_headers, 1):
        cell = ws_cost.cell(row=4, column=col_num, value=h_text)
        cell.font = font_header
        cell.fill = fill_header_opt
        cell.alignment = align_header_wrap
        cell.border = box_border

    cost_data = [
        (1, "Chase Bank Building", 2126, 3.50, 45.0, 95.0, 60.0, 1148.04),
        (2, "The Westbrook", 1520, 3.00, 35.0, 95.0, 50.0, 820.80),
        (3, "The Carnegie", 1175, 2.75, 28.0, 95.0, 45.0, 634.50),
        (4, "The Cassidy", 1134, 2.60, 26.0, 95.0, 45.0, 612.36),
        (5, "Burk Burnett Building", 1108, 2.60, 26.0, 95.0, 45.0, 598.32),
        (6, "Sanger Lofts", 1071, 2.50, 25.0, 95.0, 40.0, 578.34),
        (7, "Petroleum Building", 860, 2.20, 20.0, 95.0, 35.0, 464.40),
        (8, "The Commerce Building", 840, 2.20, 20.0, 95.0, 35.0, 453.60),
        (9, "Virtuoso Building", 560, 1.80, 15.0, 95.0, 30.0, 324.00),
        (10, "Knights of Pythias Hall", 414, 1.60, 12.0, 95.0, 25.0, 324.00),
        (11, "Plaza Hotel Building", 345, 1.50, 10.0, 95.0, 25.0, 324.00)
    ]

    for idx, item in enumerate(cost_data, start=5):
        num, name, sf, hrs, chem, tr_eq, misc, quote = item
        ws_cost.row_dimensions[idx].height = 18
        fill_r = fill_zebra if idx % 2 == 0 else PatternFill(fill_type=None)

        ws_cost.cell(row=idx, column=1, value=num).alignment = align_center
        ws_cost.cell(row=idx, column=2, value=name).alignment = align_left
        
        c_sf = ws_cost.cell(row=idx, column=3, value=sf)
        c_sf.number_format = "#,##0"
        c_sf.alignment = align_center

        c_hrs = ws_cost.cell(row=idx, column=4, value=hrs)
        c_hrs.number_format = "0.00"
        c_hrs.alignment = align_right

        c_lab = ws_cost.cell(row=idx, column=5, value=f"=D{idx}*57.50")
        c_lab.number_format = "$#,##0.00"
        c_lab.alignment = align_right

        c_ch = ws_cost.cell(row=idx, column=6, value=chem)
        c_ch.number_format = "$#,##0.00"
        c_ch.alignment = align_right

        c_tr = ws_cost.cell(row=idx, column=7, value=tr_eq)
        c_tr.number_format = "$#,##0.00"
        c_tr.alignment = align_right

        c_mi = ws_cost.cell(row=idx, column=8, value=misc)
        c_mi.number_format = "$#,##0.00"
        c_mi.alignment = align_right

        c_tot = ws_cost.cell(row=idx, column=9, value=f"=SUM(E{idx}:H{idx})")
        c_tot.number_format = "$#,##0.00"
        c_tot.alignment = align_right

        c_qp = ws_cost.cell(row=idx, column=10, value=quote)
        c_qp.number_format = "$#,##0.00"
        c_qp.alignment = align_right

        c_gm = ws_cost.cell(row=idx, column=11, value=f"=(J{idx}-I{idx})/J{idx}")
        c_gm.number_format = "0.0%"
        c_gm.alignment = align_right

        for c in range(1, 12):
            cell = ws_cost.cell(row=idx, column=c)
            cell.font = font_bold if c in [2, 9, 10, 11] else font_regular
            cell.border = box_border
            if fill_r.fill_type:
                cell.fill = fill_r

    tot_c_row = 16
    ws_cost.row_dimensions[tot_c_row].height = 20
    ws_cost.merge_cells(f"A{tot_c_row}:B{tot_c_row}")
    ws_cost[f"A{tot_c_row}"] = "TOTAL PER QUARTERLY PASS (10 Dedicated Night Shifts)"
    ws_cost[f"A{tot_c_row}"].font = font_bold
    ws_cost[f"A{tot_c_row}"].alignment = align_center

    c_tot_csf = ws_cost.cell(row=tot_c_row, column=3, value="=SUM(C5:C15)")
    c_tot_csf.number_format = '#,##0 " SQF"'
    c_tot_csf.alignment = align_center

    ws_cost.cell(row=tot_c_row, column=4, value="=SUM(D5:D15)").number_format = "0.00"
    ws_cost.cell(row=tot_c_row, column=5, value="=SUM(E5:E15)").number_format = "$#,##0.00"
    ws_cost.cell(row=tot_c_row, column=6, value="=SUM(F5:F15)").number_format = "$#,##0.00"
    ws_cost.cell(row=tot_c_row, column=7, value="=SUM(G5:G15)").number_format = "$#,##0.00"
    ws_cost.cell(row=tot_c_row, column=8, value="=SUM(H5:H15)").number_format = "$#,##0.00"
    ws_cost.cell(row=tot_c_row, column=9, value="=SUM(I5:I15)").number_format = "$#,##0.00"
    ws_cost.cell(row=tot_c_row, column=10, value="=SUM(J5:J15)").number_format = "$#,##0.00"
    ws_cost.cell(row=tot_c_row, column=11, value=f"=(J{tot_c_row}-I{tot_c_row})/J{tot_c_row}").number_format = "0.0%"

    for c in range(1, 12):
        cell = ws_cost.cell(row=tot_c_row, column=c)
        cell.font = font_bold
        cell.fill = fill_subtle
        cell.border = total_border
        if c >= 4:
            cell.alignment = align_right

    cost_widths = {1: 6, 2: 24, 3: 18, 4: 18, 5: 18, 6: 14, 7: 22, 8: 16, 9: 18, 10: 16, 11: 16}
    for col_idx, width in cost_widths.items():
        ws_cost.column_dimensions[get_column_letter(col_idx)].width = width

    # Configure Landscape Print and Mandatory Institutional Page Headers
    header_institution = "&B&10HWB CLEANING SERVICES LLC"
    footer_page_no = "Page &P of &N"

    for ws in [ws_quote, ws_gantt, ws_cost]:
        ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
        ws.page_setup.paperSize = ws.PAPERSIZE_LETTER
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.oddHeader.center.text = header_institution
        ws.oddHeader.center.size = 10
        ws.oddHeader.center.font = "Calibri,Bold"
        ws.evenHeader.center.text = header_institution
        ws.oddFooter.right.text = footer_page_no
        ws.evenFooter.right.text = footer_page_no

    ws_quote.print_title_rows = '1:2'
    ws_gantt.print_title_rows = '1:2'
    ws_cost.print_title_rows = '1:2'

    wb.save(target_path)
    print(f"SUCCESS: Saved unified master proposal workbook to {target_path}")

if __name__ == "__main__":
    generate_unified_workbook()
