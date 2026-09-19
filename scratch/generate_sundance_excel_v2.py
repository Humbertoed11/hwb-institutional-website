import os
import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter, range_boundaries
from openpyxl.drawing.image import Image as OpenpyxlImage
from openpyxl.worksheet.pagebreak import Break
from openpyxl.workbook.defined_name import DefinedName

def generate_sundance_excel():
    target_path = "HWB-COMPANY/HWB-QUOTES/SUNDANCE-QUOTE-gantt.xlsx"
    
    img_paths = {
        "plaza": "scratch/thumb_plaza.jpg",
        "chase": "scratch/thumb_chase.jpg",
        "petroleum": "scratch/thumb_petroleum.jpg",
        "schwarz": "scratch/thumb_schwarz.jpg"
    }

    wb = openpyxl.Workbook()

    # Define Named Ranges
    defined_name_start = DefinedName('Project_Start', attr_text='Service_Gantt_Schedule!$G$4')
    defined_name_week = DefinedName('Display_Week', attr_text='Service_Gantt_Schedule!$G$5')
    wb.defined_names.add(defined_name_start)
    wb.defined_names.add(defined_name_week)

    # Styling Definitions
    font_title = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
    font_section = Font(name="Calibri", size=11, bold=True, color="1E3A8A")
    font_header = Font(name="Calibri", size=9.5, bold=True, color="FFFFFF")
    font_bold = Font(name="Calibri", size=9.5, bold=True, color="0F172A")
    font_bold_sm = Font(name="Calibri", size=9, bold=True, color="0F172A")
    font_regular = Font(name="Calibri", size=9.5, color="334155")
    font_regular_sm = Font(name="Calibri", size=8.5, color="334155")
    font_alert = Font(name="Calibri", size=9.5, bold=True, color="991B1B")
    font_alert_sm = Font(name="Calibri", size=9, bold=True, color="991B1B")
    font_badge = Font(name="Calibri", size=7.5, bold=True, color="FFFFFF")

    fill_title = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    fill_header = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    fill_header_opt = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    fill_subtle = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
    fill_zebra = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    fill_alert = PatternFill(start_color="FEF2F2", end_color="FEF2F2", fill_type="solid")
    fill_green = PatternFill(start_color="F0FDF4", end_color="F0FDF4", fill_type="solid")
    fill_weekend = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")

    fill_p1_deep_clean = PatternFill(start_color="16A34A", end_color="16A34A", fill_type="solid")
    fill_p2_sealer = PatternFill(start_color="0284C7", end_color="0284C7", fill_type="solid")
    fill_p3_quarterly = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
    fill_p3_semiannual = PatternFill(start_color="475569", end_color="475569", fill_type="solid")
    fill_opt_stairs = PatternFill(start_color="B45309", end_color="B45309", fill_type="solid")
    fill_opt_diamond = PatternFill(start_color="9D174D", end_color="9D174D", fill_type="solid")

    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")
    align_right = Alignment(horizontal="right", vertical="center")
    align_header_wrap = Alignment(horizontal="center", vertical="center", wrap_text=True)
    align_desc_wrap = Alignment(horizontal="left", vertical="center", wrap_text=True)

    thin_side = Side(style="thin", color="CBD5E1")
    box_border = Border(top=thin_side, bottom=thin_side, left=thin_side, right=thin_side)
    total_border = Border(top=Side(style="thin", color="0F172A"), bottom=Side(style="double", color="0F172A"), left=thin_side, right=thin_side)

    # =============================================================
    # SHEET 1: Commercial_Quote (Full Span Columns A to AT: 46 Columns)
    # =============================================================
    ws_quote = wb.active
    ws_quote.title = "Commercial_Quote"
    ws_quote.views.sheetView[0].showGridLines = True

    # Title Block (Rows 1 & 2)
    ws_quote.merge_cells("A1:AT1")
    ws_quote["A1"] = "HWB CLEANING SERVICES LLC"
    ws_quote["A1"].font = font_title
    ws_quote["A1"].fill = fill_title
    ws_quote["A1"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws_quote.row_dimensions[1].height = 28

    ws_quote.merge_cells("A2:AT2")
    ws_quote["A2"] = "COMMERCIAL PROPOSAL: DOWNTOWN FORT WORTH 11-BUILDING LOBBY FLOOR CARE PORTFOLIO"
    ws_quote["A2"].font = Font(name="Calibri", size=10.5, bold=True, color="93C5FD")
    ws_quote["A2"].fill = fill_title
    ws_quote["A2"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws_quote.row_dimensions[2].height = 18

    # Spacer Row 3
    ws_quote.row_dimensions[3].height = 6

    # Meta Info Box (Rows 4 to 7) - Spans A to AT
    meta_info = [
        ("Client:", "Sundance Square & Downtown Commercial Property Management", "Proposal ID:", "HWB-BID-2026-FW01 (v3.7.0)"),
        ("Property:", "Downtown Fort Worth Commercial Portfolio (11 Buildings)", "Effective Date:", "September 03, 2026"),
        ("Central Office:", "425 Houston Street, Suite 250, Fort Worth, TX 76102", "Dispatch Origin:", "Arlington, TX"),
        ("Primary Scope:", "11 Ground-Floor Commercial Lobbies (11,153 Cleanable SF)", "Operational Crew:", "2 Specialized Floor Technicians")
    ]
    for idx, (lbl1, val1, lbl2, val2) in enumerate(meta_info, start=4):
        ws_quote.row_dimensions[idx].height = 20
        ws_quote.merge_cells(f"A{idx}:C{idx}")
        ws_quote[f"A{idx}"] = lbl1
        ws_quote[f"A{idx}"].font = font_bold
        ws_quote[f"A{idx}"].alignment = align_left

        ws_quote.merge_cells(f"D{idx}:S{idx}")
        ws_quote[f"D{idx}"] = val1
        ws_quote[f"D{idx}"].font = font_regular
        ws_quote[f"D{idx}"].alignment = align_left

        ws_quote.cell(row=idx, column=20).value = "" # spacer Col T

        ws_quote.merge_cells(f"U{idx}:W{idx}")
        ws_quote[f"U{idx}"] = lbl2
        ws_quote[f"U{idx}"].font = font_bold
        ws_quote[f"U{idx}"].alignment = align_left

        ws_quote.merge_cells(f"X{idx}:AT{idx}")
        ws_quote[f"X{idx}"] = val2
        ws_quote[f"X{idx}"].font = font_regular
        ws_quote[f"X{idx}"].alignment = align_left

        for c in range(1, 47):
            cell = ws_quote.cell(row=idx, column=c)
            cell.border = box_border
            if c in range(1, 4) or c in range(21, 24):
                cell.fill = fill_zebra

    # Row 8: Data Integrity Alert Notice
    ws_quote.merge_cells("A8:AT8")
    ws_quote["A8"] = "DATA INTEGRITY NOTICE (ISO 9001 Clause 8.2.2): Cleanable square footages are reconciled to on-site empirical field measurements (11,153 Cleanable SF)."
    ws_quote["A8"].font = font_alert
    ws_quote["A8"].fill = fill_alert
    ws_quote["A8"].alignment = align_center
    ws_quote.row_dimensions[8].height = 20
    for c in range(1, 47):
        ws_quote.cell(row=8, column=c).border = box_border

    # Spacer Row 9
    ws_quote.row_dimensions[9].height = 10

    # Executive Summary (Rows 10 to 17) - Spans A to AT
    ws_quote.merge_cells("A10:AT10")
    ws_quote["A10"] = "EXECUTIVE SUMMARY: CLIENT NEEDS, GOALS & OUR PROPOSED PLAN"
    ws_quote["A10"].font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    ws_quote["A10"].fill = fill_header
    ws_quote["A10"].alignment = align_center
    ws_quote.row_dimensions[10].height = 24

    ws_quote.merge_cells("A11:AT11")
    ws_quote["A11"] = "1. THE CLIENT'S CURRENT SITUATION & LOBBY NEEDS"
    ws_quote["A11"].font = Font(name="Calibri", size=10, bold=True, color="0F172A")
    ws_quote["A11"].fill = fill_subtle
    ws_quote["A11"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws_quote.row_dimensions[11].height = 18

    ws_quote.merge_cells("A12:AT12")
    ws_quote["A12"] = "Sundance Square and downtown property management oversee 11 landmark commercial buildings in Fort Worth. Every business day, hundreds of office tenants, retail customers, and corporate guests walk through these ground-floor lobbies. Heavy daily foot traffic, tracked-in street grit, and rain have dulled the natural stone, tile, and terrazzo surfaces. Dirt has settled into corners and grout lines, while spills and moving equipment have left scuffs and spots. The management team needs these entrance lobbies to look welcoming, clean, and well-maintained every single morning."
    ws_quote["A12"].font = Font(name="Calibri", size=9.5, color="334155")
    ws_quote["A12"].alignment = align_desc_wrap
    ws_quote.row_dimensions[12].height = 36

    ws_quote.merge_cells("A13:AT13")
    ws_quote["A13"] = "2. CLIENT GOALS & OPERATIONAL OBJECTIVES"
    ws_quote["A13"].font = Font(name="Calibri", size=10, bold=True, color="0F172A")
    ws_quote["A13"].fill = fill_subtle
    ws_quote["A13"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws_quote.row_dimensions[13].height = 18

    ws_quote.merge_cells("A14:AT14")
    ws_quote["A14"] = "• Strip Away Old Dirt: Deep-clean floors down to the bare surface so managers can clearly see actual condition and existing damage.\n• Protect Against Future Stains: Seal stone and grout pores to stop coffee, sodas, and grease from soaking in and ruining floors.\n• Set Up a Reliable Routine: Establish a predictable cleaning schedule (quarterly or semi-annually) that keeps floors shining within budget.\n• Zero Tenant Disruption: Complete all floor operations safely and quietly without interrupting daytime commercial business."
    ws_quote["A14"].font = Font(name="Calibri", size=9.5, color="334155")
    ws_quote["A14"].alignment = align_desc_wrap
    ws_quote.row_dimensions[14].height = 38

    ws_quote.merge_cells("A15:AT15")
    ws_quote["A15"] = "3. WHAT HWB CLEANING SERVICES PROPOSES (3-PHASE PLAN)"
    ws_quote["A15"].font = Font(name="Calibri", size=10, bold=True, color="0F172A")
    ws_quote["A15"].fill = fill_subtle
    ws_quote["A15"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws_quote.row_dimensions[15].height = 18

    ws_quote.merge_cells("A16:AT16")
    ws_quote["A16"] = "HWB Cleaning Services LLC proposes a clear 3-step hard floor program for the 11 downtown lobbies (11,153 Cleanable SF):\n1. Deep Clean Reset (Phase 1): Heavy rotary machine scrub, soil extraction, and edge hand scraping to uncover the real floor.\n2. Stain Protection (Phase 2): Application of LATICRETE® BulletProof® penetrating sealer into pores and grout lines to lock out spills.\n3. Ongoing Scheduled Care (Phase 3): Choice of Track A (Quarterly / 4x Year) or Track B (Semi-Annual / 2x Year) to maintain clean floors."
    ws_quote["A16"].font = Font(name="Calibri", size=9.5, color="334155")
    ws_quote["A16"].alignment = align_desc_wrap
    ws_quote.row_dimensions[16].height = 38

    ws_quote.merge_cells("A17:AT17")
    ws_quote["A17"] = "⏰ 100% FLEXIBLE SHIFT SCHEDULING: Standard operations run on dedicated night shifts (post-7:00 PM) dispatched from Arlington, TX to guarantee zero daytime disruption. All shift hours, nights, and calendar dates are completely flexible based on client preference (earlier evening starts, weekends, or split buildings) to accommodate building security and tenant schedules at no extra charge."
    ws_quote["A17"].font = Font(name="Calibri", size=9.5, bold=True, color="14532D")
    ws_quote["A17"].fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
    ws_quote["A17"].alignment = align_desc_wrap
    ws_quote.row_dimensions[17].height = 30

    for r_idx in range(10, 18):
        for c in range(1, 47):
            ws_quote.cell(row=r_idx, column=c).border = box_border

    ws_quote.row_dimensions[18].height = 12

    # -------------------------------------------------------------
    # TABLE 1: 1.0 COMMERCIAL PRICING SCHEDULE (Rows 19 to 32)
    # -------------------------------------------------------------
    ws_quote.merge_cells("A19:AT19")
    ws_quote["A19"] = "1.0 COMMERCIAL PRICING SCHEDULE: INITIAL RESET & RECURRING MAINTENANCE PROGRAMS"
    ws_quote["A19"].font = font_section
    ws_quote.row_dimensions[19].height = 24

    t1_spans = [
        ("A20", "Item"),
        ("B20", "Building Name"),
        ("C20", "Address"),
        ("D20", "Primary floor system"),
        ("E20", "Cleanable Area\n(SQFT)"),
        ("F20:H20", "Phase 1 Rate\n(Per SF)"),
        ("I20:P20", "Phase 1 deep clean\n(expose damage to\nconsider options)"),
        ("Q20:S20", "Quarterly Rate\n(Per SF)"),
        ("T20:AA20", "Track A: Quarterly\n(Every 3 Months)"),
        ("AB20:AD20", "Semi-Annual Rate\n(Per SF)"),
        ("AE20:AT20", "Track B: Semi-Annual\n(Every 6 Months)")
    ]
    ws_quote.row_dimensions[20].height = 44
    for crange, htext in t1_spans:
        if ":" in crange:
            ws_quote.merge_cells(crange)
            c_top = ws_quote[crange.split(":")[0]]
            c_start, _, c_end, _ = range_boundaries(crange)
            for c in range(c_start, c_end + 1):
                ws_quote.cell(row=20, column=c).border = box_border
                ws_quote.cell(row=20, column=c).fill = fill_header
        else:
            c_top = ws_quote[crange]
            c_top.border = box_border
            c_top.fill = fill_header
        c_top.value = htext
        c_top.font = font_header
        c_top.alignment = align_header_wrap

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

        ws_quote.merge_cells(f"F{idx}:H{idx}")
        c_rmo = ws_quote.cell(row=idx, column=6, value=r_mo)
        c_rmo.number_format = "$#,##0.00"
        c_rmo.alignment = align_right

        ws_quote.merge_cells(f"I{idx}:P{idx}")
        c_mo = ws_quote.cell(row=idx, column=9, value=f"=MAX(E{idx},600)*F{idx}")
        c_mo.number_format = "$#,##0.00"
        c_mo.alignment = align_right

        ws_quote.merge_cells(f"Q{idx}:S{idx}")
        c_rq = ws_quote.cell(row=idx, column=17, value=r_qtr)
        c_rq.number_format = "$#,##0.00"
        c_rq.alignment = align_right

        ws_quote.merge_cells(f"T{idx}:AA{idx}")
        c_qtr = ws_quote.cell(row=idx, column=20, value=f"=MAX(E{idx},600)*Q{idx}")
        c_qtr.number_format = "$#,##0.00"
        c_qtr.alignment = align_right

        ws_quote.merge_cells(f"AB{idx}:AD{idx}")
        c_rs = ws_quote.cell(row=idx, column=28, value=r_semi)
        c_rs.number_format = "$#,##0.00"
        c_rs.alignment = align_right

        ws_quote.merge_cells(f"AE{idx}:AT{idx}")
        c_semi = ws_quote.cell(row=idx, column=31, value=f"=MAX(E{idx},600)*AB{idx}")
        c_semi.number_format = "$#,##0.00"
        c_semi.alignment = align_right

        for c in range(1, 47):
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

    ws_quote.merge_cells(f"F{tot_r1}:H{tot_r1}")
    ws_quote.cell(row=tot_r1, column=6, value="$0.80 avg").alignment = align_center

    ws_quote.merge_cells(f"I{tot_r1}:P{tot_r1}")
    c_tot_mo = ws_quote.cell(row=tot_r1, column=9, value="=SUM(I21:I31)")
    c_tot_mo.number_format = "$#,##0.00"
    c_tot_mo.alignment = align_right

    ws_quote.merge_cells(f"Q{tot_r1}:S{tot_r1}")
    ws_quote.cell(row=tot_r1, column=17, value="$0.54 avg").alignment = align_center

    ws_quote.merge_cells(f"T{tot_r1}:AA{tot_r1}")
    c_tot_qtr = ws_quote.cell(row=tot_r1, column=20, value="=SUM(T21:T31)")
    c_tot_qtr.number_format = "$#,##0.00"
    c_tot_qtr.alignment = align_right

    ws_quote.merge_cells(f"AB{tot_r1}:AD{tot_r1}")
    ws_quote.cell(row=tot_r1, column=28, value="$0.68 avg").alignment = align_center

    ws_quote.merge_cells(f"AE{tot_r1}:AT{tot_r1}")
    c_tot_semi = ws_quote.cell(row=tot_r1, column=31, value="=SUM(AE21:AE31)")
    c_tot_semi.number_format = "$#,##0.00"
    c_tot_semi.alignment = align_right

    for c in range(1, 47):
        cell = ws_quote.cell(row=tot_r1, column=c)
        cell.font = font_bold
        cell.fill = fill_subtle
        cell.border = total_border

    ws_quote.row_dimensions[33].height = 10

    # -------------------------------------------------------------
    # TABLE 2: 2.0 ADDITIONAL CLIENT OPTIONS (Rows 34 to 47)
    # -------------------------------------------------------------
    ws_quote.merge_cells("A34:AT34")
    ws_quote["A34"] = "2.0 ADDITIONAL CLIENT OPTIONS: PENETRATING SEALER, STAIRCARE, DIAMOND RESTORATION & ART HANDLING"
    ws_quote["A34"].font = font_section
    ws_quote.row_dimensions[34].height = 24

    t2_spans = [
        ("A35", "Item"),
        ("B35", "Building Name"),
        ("C35", "Address"),
        ("D35", "Primary floor system"),
        ("E35", "Cleanable Area\n(SQFT)"),
        ("F35:P35", "Option A: Sealer\n(BulletProof®)\n$0.31 / SF"),
        ("Q35:T35", "Option B: Stair Care\n(Unit Rate Add-On\n500 Main St Only)*"),
        ("U35:AA35", "Option C: Capital Diamond Restoration\n(Restores Mirror Shine • Marble & Terrazzo Only)\n$2.65 / SF"),
        ("AB35:AT35", "Option D: Furniture Handling\n(Hourly T&M)\nAvailable Per Hour")
    ]
    ws_quote.row_dimensions[35].height = 44
    for crange, htext in t2_spans:
        if ":" in crange:
            ws_quote.merge_cells(crange)
            c_top = ws_quote[crange.split(":")[0]]
            c_start, _, c_end, _ = range_boundaries(crange)
            for c in range(c_start, c_end + 1):
                ws_quote.cell(row=35, column=c).border = box_border
                ws_quote.cell(row=35, column=c).fill = fill_header_opt
        else:
            c_top = ws_quote[crange]
            c_top.border = box_border
            c_top.fill = fill_header_opt
        c_top.value = htext
        c_top.font = font_header
        c_top.alignment = align_header_wrap

    for idx, item in enumerate(portfolio_data, start=36):
        num, name, addr, sub, sf, _, _, _ = item
        base_row = idx - 15
        ws_quote.row_dimensions[idx].height = 18
        fill_row = fill_zebra if idx % 2 == 0 else PatternFill(fill_type=None)

        ws_quote.cell(row=idx, column=1, value=num).alignment = align_center
        ws_quote.cell(row=idx, column=2, value=name).alignment = align_left
        ws_quote.cell(row=idx, column=3, value=addr).alignment = align_left
        ws_quote.cell(row=idx, column=4, value=sub).alignment = align_left

        c_sf2 = ws_quote.cell(row=idx, column=5, value=f"=E{base_row}")
        c_sf2.number_format = "#,##0"
        c_sf2.alignment = align_center

        ws_quote.merge_cells(f"F{idx}:P{idx}")
        c_seal = ws_quote.cell(row=idx, column=6, value=f"=MAX(E{idx},600)*0.31")
        c_seal.number_format = "$#,##0.00"
        c_seal.alignment = align_right

        ws_quote.merge_cells(f"Q{idx}:T{idx}")
        c_stv = ws_quote.cell(row=idx, column=17)
        if num == 5:
            c_stv.value = "$3/Stp + $21/Lnd"
            c_stv.font = Font(name="Calibri", size=9, bold=True, color="16A34A")
        else:
            c_stv.value = "N/A (Excluded)"
            c_stv.font = Font(name="Calibri", size=9, italic=True, color="64748B")
        c_stv.alignment = align_center

        ws_quote.merge_cells(f"U{idx}:AA{idx}")
        is_grindable = sub in ["Polished Terrazzo", "Terrazzo Tile", "Polished Marble Tile"]
        c_rst = ws_quote.cell(row=idx, column=21)
        if is_grindable:
            c_rst.value = f"=MAX(E{idx},600)*2.65"
            c_rst.number_format = "$#,##0.00"
            c_rst.alignment = align_right
        else:
            c_rst.value = "N/A (Exempt)"
            c_rst.font = Font(name="Calibri", size=9, italic=True, color="64748B")
            c_rst.alignment = align_center

        ws_quote.merge_cells(f"AB{idx}:AT{idx}")
        c_fur = ws_quote.cell(row=idx, column=28, value="Available Per Hour")
        c_fur.alignment = align_center

        for c in range(1, 47):
            cell = ws_quote.cell(row=idx, column=c)
            if c not in range(17, 21) and (c not in range(21, 28) or is_grindable):
                cell.font = font_regular
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

    ws_quote.merge_cells(f"F{tot_r2}:P{tot_r2}")
    c_tot_sl2 = ws_quote.cell(row=tot_r2, column=6, value="=SUM(F36:F46)")
    c_tot_sl2.number_format = "$#,##0.00"
    c_tot_sl2.alignment = align_right

    ws_quote.merge_cells(f"Q{tot_r2}:T{tot_r2}")
    ws_quote.cell(row=tot_r2, column=17, value="Unit Rate Only").alignment = align_center

    ws_quote.merge_cells(f"U{tot_r2}:AA{tot_r2}")
    c_tot_rst2 = ws_quote.cell(row=tot_r2, column=21, value="=SUM(U36:U46)")
    c_tot_rst2.number_format = "$#,##0.00"
    c_tot_rst2.alignment = align_right

    ws_quote.merge_cells(f"AB{tot_r2}:AT{tot_r2}")
    ws_quote.cell(row=tot_r2, column=28, value="Available Per Hour").alignment = align_center

    for c in range(1, 47):
        cell = ws_quote.cell(row=tot_r2, column=c)
        cell.font = font_bold
        cell.fill = fill_subtle
        cell.border = total_border

    ws_quote.row_dimensions[48].height = 10

    # -------------------------------------------------------------
    # TABLE 3: 3.0 EXECUTIVE SUMMARY & BILLING TERMS (Rows 49 to 57)
    # -------------------------------------------------------------
    ws_quote.merge_cells("A49:AT49")
    ws_quote["A49"] = "3.0 COMMERCIAL PROGRAM EXECUTIVE SUMMARY & BILLING TERMS"
    ws_quote["A49"].font = font_section
    ws_quote.row_dimensions[49].height = 24

    ws_quote.row_dimensions[50].height = 20
    t3_headers = [
        ("A50:H50", "Service Phase / Scope Module"),
        ("I50:W50", "Scope of work"),
        ("X50:AA50", "Rate Basis"),
        ("AB50:AI50", "Portfolio Invoiced Investment"),
        ("AJ50:AT50", "Billing Frequency & Program Terms")
    ]
    for crange, htext in t3_headers:
        ws_quote.merge_cells(crange)
        c_top = ws_quote[crange.split(":")[0]]
        c_top.value = htext
        c_top.font = font_header
        c_top.fill = fill_header_opt
        c_top.alignment = align_center
        c_start, _, c_end, _ = range_boundaries(crange)
        for c in range(c_start, c_end + 1):
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

        ws_quote.merge_cells(f"A{s_idx}:H{s_idx}")
        c_p = ws_quote[f"A{s_idx}"]
        c_p.value = p_name
        c_p.font = font_bold
        c_p.alignment = align_desc_wrap

        ws_quote.merge_cells(f"I{s_idx}:W{s_idx}")
        c_d = ws_quote[f"I{s_idx}"]
        c_d.value = p_desc
        c_d.font = font_regular
        c_d.alignment = align_desc_wrap

        ws_quote.merge_cells(f"X{s_idx}:AA{s_idx}")
        c_r = ws_quote.cell(row=s_idx, column=24, value=p_rate)
        c_r.font = font_bold
        c_r.alignment = align_center

        ws_quote.merge_cells(f"AB{s_idx}:AI{s_idx}")
        c_pass = ws_quote.cell(row=s_idx, column=28, value=p_pass)
        c_pass.font = font_bold if ("complete" in p_pass or "pass" in p_pass or "Unit" in p_pass) else font_regular
        c_pass.alignment = Alignment(horizontal="right", vertical="center", wrap_text=True)

        ws_quote.merge_cells(f"AJ{s_idx}:AT{s_idx}")
        c_b = ws_quote.cell(row=s_idx, column=36, value=p_bill)
        c_b.font = font_bold
        c_b.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        for c in range(1, 47):
            cell = ws_quote.cell(row=s_idx, column=c)
            cell.border = box_border
            if fill_r.fill_type:
                cell.fill = fill_r

    ws_quote.row_dimensions[58].height = 10

    # -------------------------------------------------------------
    # SECTION 4: 4.0 ARCHITECTURAL PHOTO INSPECTION (Rows 59 to 75)
    # -------------------------------------------------------------
    ws_quote.merge_cells("A59:AT59")
    ws_quote["A59"] = "4.0 LOBBY FLOOR CONDITION: 4-POINT PHOTO INSPECTION"
    ws_quote["A59"].font = font_section
    ws_quote.row_dimensions[59].height = 24

    ws_quote.merge_cells("A60:AT60")
    ws_quote["A60"] = "Photographic documentation of floor conditions, wear patterns, and recommended services across portfolio lobbies."
    ws_quote["A60"].font = Font(name="Calibri", size=9, italic=True, color="475569")
    ws_quote["A60"].alignment = align_left
    ws_quote.row_dimensions[60].height = 18

    # Photos 1 & 2 (Rows 62–67)
    ws_quote.row_dimensions[62].height = 22
    ws_quote.merge_cells("A62:W62")
    ws_quote["A62"] = "PHOTO 1: PLAZA HOTEL BUILDING (303 MAIN ST)"
    ws_quote["A62"].font = font_header
    ws_quote["A62"].fill = fill_header_opt
    ws_quote["A62"].alignment = align_center

    ws_quote.merge_cells("X62:AT62")
    ws_quote["X62"] = "PHOTO 2: CHASE BANK BUILDING (420 THROCKMORTON ST)"
    ws_quote["X62"].font = font_header
    ws_quote["X62"].fill = fill_header_opt
    ws_quote["X62"].alignment = align_center

    for c in range(1, 47):
        ws_quote.cell(row=62, column=c).border = box_border
        ws_quote.cell(row=62, column=c).fill = fill_header_opt

    ws_quote.row_dimensions[63].height = 180
    ws_quote.merge_cells("A63:W63")
    ws_quote.merge_cells("X63:AT63")
    for c in range(1, 47):
        ws_quote.cell(row=63, column=c).border = box_border
        ws_quote.cell(row=63, column=c).fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")

    img_plaza = OpenpyxlImage(img_paths["plaza"])
    img_plaza.width = 190
    img_plaza.height = 233
    ws_quote.add_image(img_plaza, "D63")

    img_chase = OpenpyxlImage(img_paths["chase"])
    img_chase.width = 190
    img_chase.height = 233
    ws_quote.add_image(img_chase, "AB63")

    ws_quote.row_dimensions[64].height = 20
    ws_quote.merge_cells("A64:W64")
    ws_quote["A64"] = "Primary floor system: Commercial Quarry Tile"
    ws_quote["A64"].font = font_bold_sm
    ws_quote["A64"].fill = fill_zebra
    ws_quote["A64"].alignment = align_left

    ws_quote.merge_cells("X64:AT64")
    ws_quote["X64"] = "Primary floor system: Polished Terrazzo"
    ws_quote["X64"].font = font_bold_sm
    ws_quote["X64"].fill = fill_zebra
    ws_quote["X64"].alignment = align_left

    for c in range(1, 47):
        ws_quote.cell(row=64, column=c).border = box_border
        ws_quote.cell(row=64, column=c).fill = fill_zebra

    ws_quote.row_dimensions[65].height = 20
    ws_quote.merge_cells("A65:W65")
    ws_quote["A65"] = "Floor Issue: Chemical Bleach Stains & Deep Grout Soil Buildup"
    ws_quote["A65"].font = font_alert_sm
    ws_quote["A65"].alignment = align_left

    ws_quote.merge_cells("X65:AT65")
    ws_quote["X65"] = "Floor Issue: Heavy Traffic Wear Pattern & Loss of Floor Shine"
    ws_quote["X65"].font = font_alert_sm
    ws_quote["X65"].alignment = align_left

    for c in range(1, 47):
        ws_quote.cell(row=65, column=c).border = box_border

    ws_quote.row_dimensions[66].height = 48
    ws_quote.merge_cells("A66:W66")
    ws_quote["A66"] = "Condition Observed: Harsh cleaner or bleach stripped the tile finish (white patch); grease soaked into unsealed tile; heavy dirt along grout lines."
    ws_quote["A66"].font = font_regular_sm
    ws_quote["A66"].alignment = align_desc_wrap

    ws_quote.merge_cells("X66:AT66")
    ws_quote["X66"] = "Condition Observed: Heavy foot traffic wore away the surface shine along the center walkway; fine scratches now trap dirt and leave floors looking dull."
    ws_quote["X66"].font = font_regular_sm
    ws_quote["X66"].alignment = align_desc_wrap

    for c in range(1, 47):
        ws_quote.cell(row=66, column=c).border = box_border

    ws_quote.row_dimensions[67].height = 42
    ws_quote.merge_cells("A67:W67")
    ws_quote["A67"] = "Recommended Service: Deep machine scrub to lift embedded soil (Phase 1) + Option A: BulletProof® Sealer to protect tile and grout from stains."
    ws_quote["A67"].font = font_bold_sm
    ws_quote["A67"].fill = fill_green
    ws_quote["A67"].alignment = align_desc_wrap

    ws_quote.merge_cells("X67:AT67")
    ws_quote["X67"] = "Recommended Service: Regular quarterly machine scrub and extraction ($0.54/SF) to remove gritty soil and keep floors clean; deep gouges require Option C: Diamond Restoration."
    ws_quote["X67"].font = font_bold_sm
    ws_quote["X67"].fill = fill_green
    ws_quote["X67"].alignment = align_desc_wrap

    for c in range(1, 47):
        ws_quote.cell(row=67, column=c).border = box_border
        ws_quote.cell(row=67, column=c).fill = fill_green

    # Photos 3 & 4 (Rows 69–74)
    ws_quote.row_dimensions[69].height = 22
    ws_quote.merge_cells("A69:W69")
    ws_quote["A69"] = "PHOTO 3: PETROLEUM BUILDING (210 W 6TH ST)"
    ws_quote["A69"].font = font_header
    ws_quote["A69"].fill = fill_header_opt
    ws_quote["A69"].alignment = align_center

    ws_quote.merge_cells("X69:AT69")
    ws_quote["X69"] = "PHOTO 4: VIRTUOSO BUILDING (505 MAIN ST / HISTORIC SCHWARZ BLDG)"
    ws_quote["X69"].font = font_header
    ws_quote["X69"].fill = fill_header_opt
    ws_quote["X69"].alignment = align_center

    for c in range(1, 47):
        ws_quote.cell(row=69, column=c).border = box_border
        ws_quote.cell(row=69, column=c).fill = fill_header_opt

    ws_quote.row_dimensions[70].height = 180
    ws_quote.merge_cells("A70:W70")
    ws_quote.merge_cells("X70:AT70")
    for c in range(1, 47):
        ws_quote.cell(row=70, column=c).border = box_border
        ws_quote.cell(row=70, column=c).fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")

    img_pet = OpenpyxlImage(img_paths["petroleum"])
    img_pet.width = 190
    img_pet.height = 233
    ws_quote.add_image(img_pet, "D70")

    img_sch = OpenpyxlImage(img_paths["schwarz"])
    img_sch.width = 190
    img_sch.height = 233
    ws_quote.add_image(img_sch, "AB70")

    ws_quote.row_dimensions[71].height = 20
    ws_quote.merge_cells("A71:W71")
    ws_quote["A71"] = "Primary floor system: Polished Marble Tile"
    ws_quote["A71"].font = font_bold_sm
    ws_quote["A71"].fill = fill_zebra
    ws_quote["A71"].alignment = align_left

    ws_quote.merge_cells("X71:AT71")
    ws_quote["X71"] = "Primary floor system: Polished Marble Tile"
    ws_quote["X71"].font = font_bold_sm
    ws_quote["X71"].fill = fill_zebra
    ws_quote["X71"].alignment = align_left

    for c in range(1, 47):
        ws_quote.cell(row=71, column=c).border = box_border
        ws_quote.cell(row=71, column=c).fill = fill_zebra

    ws_quote.row_dimensions[72].height = 20
    ws_quote.merge_cells("A72:W72")
    ws_quote["A72"] = "Floor Issue: Acid Stain Marks & Chemical Etch Rings"
    ws_quote["A72"].font = font_alert_sm
    ws_quote["A72"].alignment = align_left

    ws_quote.merge_cells("X72:AT72")
    ws_quote["X72"] = "Floor Issue: Deep Gouges & Scratches from Moving Equipment"
    ws_quote["X72"].font = font_alert_sm
    ws_quote["X72"].alignment = align_left

    for c in range(1, 47):
        ws_quote.cell(row=72, column=c).border = box_border

    ws_quote.row_dimensions[73].height = 48
    ws_quote.merge_cells("A73:W73")
    ws_quote["A73"] = "Condition Observed: Acidic spills (coffee, citrus drinks, sanitizer drips) ate into polished marble, leaving dull, rough white spots that mopping cannot clean."
    ws_quote["A73"].font = font_regular_sm
    ws_quote["A73"].alignment = align_desc_wrap

    ws_quote.merge_cells("X73:AT73")
    ws_quote["X73"] = "Condition Observed: Heavy equipment, freight carts, or unpadded furniture dragged across the floor cut deep white scratches into the black marble."
    ws_quote["X73"].font = font_regular_sm
    ws_quote["X73"].alignment = align_desc_wrap

    for c in range(1, 47):
        ws_quote.cell(row=73, column=c).border = box_border

    ws_quote.row_dimensions[74].height = 42
    ws_quote.merge_cells("A74:W74")
    ws_quote["A74"] = "Recommended Service: Diamond polishing to smooth out etch marks and restore shine + Option A: BulletProof® Sealer to protect against stains."
    ws_quote["A74"].font = font_bold_sm
    ws_quote["A74"].fill = fill_green
    ws_quote["A74"].alignment = align_desc_wrap

    ws_quote.merge_cells("X74:AT74")
    ws_quote["X74"] = "Recommended Service: Option C: Diamond Restoration ($2.65/SF) to grind out deep scratch valleys and polish back to a high-gloss finish."
    ws_quote["X74"].font = font_bold_sm
    ws_quote["X74"].fill = fill_green
    ws_quote["X74"].alignment = align_desc_wrap

    for c in range(1, 47):
        ws_quote.cell(row=74, column=c).border = box_border
        ws_quote.cell(row=74, column=c).fill = fill_green

    ws_quote.row_dimensions[75].height = 12

    # -------------------------------------------------------------
    # SECTION 5.0: 5.0 OPERATIONAL DISPATCH GANTT SCHEDULE (Rows 76 to 96)
    # Fitted, uncrowded column architecture
    # -------------------------------------------------------------
    ws_quote.merge_cells("A76:AT76")
    ws_quote["A76"] = "5.0 OPERATIONAL DISPATCH GANTT SCHEDULE (10 DEDICATED NIGHT SHIFTS)"
    ws_quote["A76"].font = font_section
    ws_quote.row_dimensions[76].height = 24

    ws_quote.merge_cells("A77:AT77")
    ws_quote["A77"] = "OPERATIONAL DISPATCH GANTT SCHEDULE — DOWNTOWN FORT WORTH 11-BUILDING PORTFOLIO (ARLINGTON, TX DISPATCH)"
    ws_quote["A77"].font = Font(name="Calibri", size=9.5, italic=True, color="475569")
    ws_quote.row_dimensions[77].height = 18

    # Row 78: Metadata Box (Spans A to AT)
    ws_quote.row_dimensions[78].height = 18
    ws_quote.merge_cells("A78:C78")
    ws_quote["A78"] = "Base Dispatch:"
    ws_quote["A78"].font = font_bold

    ws_quote.merge_cells("D78:J78")
    ws_quote["D78"] = "Arlington, TX (Post-7:00 PM)"
    ws_quote["D78"].font = font_regular

    ws_quote.merge_cells("K78:N78")
    ws_quote["K78"] = "Assigned Crew:"
    ws_quote["K78"].font = font_bold

    ws_quote.merge_cells("O78:U78")
    ws_quote["O78"] = "2 Specialized Technicians"
    ws_quote["O78"].font = font_regular

    ws_quote.merge_cells("V78:AA78")
    ws_quote["V78"] = "Dedicated Mobilization:"
    ws_quote["V78"].font = font_bold

    ws_quote.merge_cells("AB78:AG78")
    ws_quote["AB78"] = "10 Dedicated Night Shifts"
    ws_quote["AB78"].font = font_regular

    ws_quote.merge_cells("AH78:AT78")
    ws_quote["AH78"] = "⏰ 100% Flexible Shift Timing (Client Choice)"
    ws_quote["AH78"].font = Font(name="Calibri", size=8.5, bold=True, color="16A34A")
    ws_quote["AH78"].alignment = align_center

    for c in range(1, 47):
        ws_quote.cell(row=78, column=c).border = box_border

    # Row 79: Legend Bar (Spans A to AT)
    ws_quote.row_dimensions[79].height = 20
    ws_quote.merge_cells("A79:E79")
    ws_quote["A79"] = "LEGEND & COLOR CODES:"
    ws_quote["A79"].font = font_bold
    ws_quote["A79"].fill = fill_subtle
    ws_quote["A79"].alignment = align_center

    legend_sec5 = [
        ("F79:K79", "DP: Phase 1 Deep Clean", fill_p1_deep_clean),
        ("L79:Q79", "SL: Modular Sealer", fill_p2_sealer),
        ("R79:W79", "QT: Quarterly Care", fill_p3_quarterly),
        ("X79:AC79", "ST: Stair Detailing", fill_opt_stairs),
        ("AD79:AT79", "WKND: Building Offline / Standby Window", PatternFill(start_color="CBD5E1", end_color="CBD5E1", fill_type="solid"))
    ]
    for crange, ltext, lfill in legend_sec5:
        ws_quote.merge_cells(crange)
        c_top = ws_quote[crange.split(":")[0]]
        c_top.value = ltext
        c_top.font = font_badge
        c_top.fill = lfill
        c_top.alignment = align_center
        c_start, _, c_end, _ = range_boundaries(crange)
        for c in range(c_start, c_end + 1):
            ws_quote.cell(row=79, column=c).border = box_border
            ws_quote.cell(row=79, column=c).fill = lfill

    for c in range(1, 6):
        ws_quote.cell(row=79, column=c).border = box_border

    # Rows 80–82: 3-Tier Headers
    ws_quote.row_dimensions[80].height = 20
    ws_quote.row_dimensions[81].height = 16
    ws_quote.row_dimensions[82].height = 16

    sec5_headers = [
        ("A80:A82", "Item"),
        ("B80:B82", "Building Name"),
        ("C80:C82", "Address"),
        ("D80:D82", "Primary floor system"),
        ("E80:E82", "Total SQF"),
        ("F80:G82", "Shift Window"),
        ("H80:I82", "Crew Hrs"),
        ("J80:K82", "Service Provided\n(Phase 1 Baseline)")
    ]
    for crange, htext in sec5_headers:
        ws_quote.merge_cells(crange)
        c_top = ws_quote[crange.split(":")[0]]
        c_top.value = htext
        c_top.font = font_header
        c_top.fill = fill_header_opt
        c_top.alignment = align_header_wrap
        c_start, r_start, c_end, r_end = range_boundaries(crange)
        for r in range(r_start, r_end + 1):
            for c in range(c_start, c_end + 1):
                ws_quote.cell(row=r, column=c).border = box_border
                ws_quote.cell(row=r, column=c).fill = fill_header_opt

    # 35 Day Timeline Headers (Cols 12 to 46: L to AT)
    weeks = [
        ("L80:R80", 12, 18, "Week 1 (Aug 31–Sep 06)"),
        ("S80:Y80", 19, 25, "Week 2 (Sep 07–Sep 13)"),
        ("Z80:AF80", 26, 32, "Week 3 (Sep 14–Sep 20)"),
        ("AG80:AM80", 33, 39, "Week 4 (Sep 21–Sep 27)"),
        ("AN80:AT80", 40, 46, "Week 5 (Sep 28–Oct 04)")
    ]
    for wrange, start_c, end_c, wtitle in weeks:
        ws_quote.merge_cells(wrange)
        c_w = ws_quote[wrange.split(":")[0]]
        c_w.value = wtitle
        c_w.font = font_header
        c_w.fill = fill_header
        c_w.alignment = align_center
        for c in range(start_c, end_c + 1):
            ws_quote.cell(row=80, column=c).border = box_border
            ws_quote.cell(row=80, column=c).fill = fill_header

    days_dates = [31] + list(range(1, 31)) + list(range(1, 5))
    days_names = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'] * 5

    for d_idx, d_num in enumerate(days_dates):
        col = 12 + d_idx
        c_num = ws_quote.cell(row=81, column=col, value=d_num)
        c_num.font = Font(name="Calibri", size=8.5, bold=True, color="FFFFFF")
        c_num.fill = fill_title
        c_num.alignment = align_center
        c_num.border = box_border

    for d_idx, d_name in enumerate(days_names):
        col = 12 + d_idx
        c_nam = ws_quote.cell(row=82, column=col, value=d_name)
        is_w = d_name in ['Sa', 'Su']
        c_nam.fill = PatternFill(start_color="475569", end_color="475569", fill_type="solid") if is_w else PatternFill(start_color="334155", end_color="334155", fill_type="solid")
        c_nam.font = Font(name="Calibri", size=8, bold=True, color="FFFFFF" if is_w else "94A3B8")
        c_nam.alignment = align_center
        c_nam.border = box_border

    sec5_schedule_data = [
        (1, "Chase Bank Building", "420 Throckmorton St", "Polished Terrazzo", 2126, "Dedicated Night 1 (3.5h)", 3.5, [13], [17], [27], []),
        (2, "The Westbrook", "425 Houston St", "Polished Terrazzo", 1520, "Dedicated Night 2 (3.0h)", 3.0, [14], [17], [28], []),
        (3, "The Carnegie", "421 W 3rd St", "Polished Terrazzo", 1175, "Dedicated Night 3 (2.8h)", 2.8, [15], [17], [29], []),
        (4, "The Cassidy", "407 Throckmorton St", "Polished Terrazzo", 1134, "Dedicated Night 4 (2.6h)", 2.6, [16], [17], [30], []),
        (5, "Burk Burnett Building", "500 Main St", "Ceramic Mosaic Tile", 1108, "Dedicated Night 5 (2.6h)", 2.6, [19], [24], [33], [34]),
        (6, "Sanger Lofts", "222 W 4th St", "Polished Terrazzo", 1071, "Dedicated Night 6 (2.5h)", 2.5, [20], [24], [34], []),
        (7, "Petroleum Building", "210 W 6th St", "Polished Marble Tile", 860, "Dedicated Night 7 (2.2h)", 2.2, [21], [24], [35], []),
        (8, "The Commerce Building", "420 Commerce St", "Terrazzo Tile", 840, "Dedicated Night 8 (2.2h)", 2.2, [22], [24], [36], []),
        (9, "Virtuoso Building", "505 Main St", "Polished Marble Tile", 560, "Boutique Night 9 (1.8h)", 1.8, [23], [24], [37], []),
        (10, "Knights of Pythias Hall", "109-110 E 3rd St", "Ceramic Mosaic Tile", 414, "Boutique Night 9 (1.6h)", 1.6, [23], [24], [37], []),
        (11, "Plaza Hotel Building", "303 Main St", "Commercial Quarry Tile", 345, "Boutique Night 10 (1.5h)", 1.5, [26], [27], [40], [])
    ]

    for b_idx, item in enumerate(sec5_schedule_data, start=83):
        num, name, addr, sub, sf, window, crew_time, p1_cols, seal_cols, rec_cols, stair_cols = item
        ws_quote.row_dimensions[b_idx].height = 18
        fill_row = fill_zebra if b_idx % 2 == 0 else PatternFill(fill_type=None)

        ws_quote.cell(row=b_idx, column=1, value=num).alignment = align_center
        ws_quote.cell(row=b_idx, column=2, value=name).alignment = align_left
        ws_quote.cell(row=b_idx, column=3, value=addr).alignment = align_left
        ws_quote.cell(row=b_idx, column=4, value=sub).alignment = align_left

        c_sf = ws_quote.cell(row=b_idx, column=5, value=sf)
        c_sf.number_format = "#,##0"
        c_sf.alignment = align_center

        ws_quote.merge_cells(f"F{b_idx}:G{b_idx}")
        c_win = ws_quote.cell(row=b_idx, column=6, value=window)
        c_win.alignment = align_left

        ws_quote.merge_cells(f"H{b_idx}:I{b_idx}")
        c_hrs = ws_quote.cell(row=b_idx, column=8, value=crew_time)
        c_hrs.number_format = '0.0 "hrs"'
        c_hrs.alignment = align_center

        ws_quote.merge_cells(f"J{b_idx}:K{b_idx}")
        c_svc = ws_quote.cell(row=b_idx, column=10, value="Phase 1: Initial Deep Clean")
        c_svc.alignment = align_left
        c_svc.font = font_regular

        for c in range(1, 12):
            cell = ws_quote.cell(row=b_idx, column=c)
            cell.font = font_bold if c in [2] else font_regular
            cell.border = box_border
            if fill_row.fill_type:
                cell.fill = fill_row

        for day_i in range(1, 36):
            col = day_i + 11
            cell = ws_quote.cell(row=b_idx, column=col)
            cell.border = box_border

            if col in p1_cols:
                cell.fill = fill_p1_deep_clean
                cell.value = "DP"
                cell.font = font_badge
                cell.alignment = align_center
            elif col in seal_cols:
                cell.fill = fill_p2_sealer
                cell.value = "SL"
                cell.font = font_badge
                cell.alignment = align_center
            elif col in rec_cols:
                cell.fill = fill_p3_quarterly
                cell.value = "QT"
                cell.font = font_badge
                cell.alignment = align_center
            elif col in stair_cols:
                cell.fill = fill_opt_stairs
                cell.value = "ST"
                cell.font = font_badge
                cell.alignment = align_center
            elif (col - 12) % 7 in [5, 6]:
                cell.fill = fill_weekend

    # Total Row Section 5.0 (Row 94)
    tot_r5 = 94
    ws_quote.row_dimensions[tot_r5].height = 20
    ws_quote.merge_cells(f"A{tot_r5}:D{tot_r5}")
    ws_quote[f"A{tot_r5}"] = "TOTAL PORTFOLIO DISPATCH (Phase 1 Deep Clean)"
    ws_quote[f"A{tot_r5}"].font = font_bold
    ws_quote[f"A{tot_r5}"].alignment = align_center

    c_tot_sf5 = ws_quote.cell(row=tot_r5, column=5, value="=SUM(E83:E93)")
    c_tot_sf5.number_format = '#,##0 " SQF"'
    c_tot_sf5.alignment = align_center

    ws_quote.merge_cells(f"F{tot_r5}:G{tot_r5}")
    ws_quote.cell(row=tot_r5, column=6, value="10 Dedicated Shifts").alignment = align_center

    ws_quote.merge_cells(f"H{tot_r5}:I{tot_r5}")
    c_tot_hrs5 = ws_quote.cell(row=tot_r5, column=8, value="=SUM(H83:H93)")
    c_tot_hrs5.number_format = '0.0 "hrs total"'
    c_tot_hrs5.alignment = align_center

    ws_quote.merge_cells(f"J{tot_r5}:K{tot_r5}")
    ws_quote.cell(row=tot_r5, column=10, value="11 Properties Scheduled").alignment = align_center

    for c in range(1, 12):
        cell = ws_quote.cell(row=tot_r5, column=c)
        cell.font = font_bold
        cell.fill = fill_subtle
        cell.border = total_border

    for c in range(12, 47):
        cell = ws_quote.cell(row=tot_r5, column=c)
        cell.border = total_border
        cell.fill = fill_subtle

    # Footnote Row 96
    ws_quote.row_dimensions[95].height = 10
    ws_quote.merge_cells("A96:AT96")
    ws_quote["A96"] = "*Note: Shift timing and scheduled calendar dates are 100% flexible based on client preference. HWB will adapt dispatch hours (earlier start, late night, or weekend windows) to accommodate building security and tenant schedules at no additional cost."
    ws_quote["A96"].font = Font(name="Calibri", size=8.5, italic=True, color="475569")
    ws_quote["A96"].alignment = align_left
    ws_quote.row_dimensions[96].height = 18

    # Column Widths on Sheet 1 (Fitted to data length)
    col_widths_s1 = {
        1: 6.0,   # Item
        2: 26.0,  # Building Name (fits "Knights of Pythias Hall" [23 chars])
        3: 22.0,  # Address (fits "420 Throckmorton St" [19 chars])
        4: 26.0,  # Primary Floor Substrate
        5: 14.0,  # Cleanable Area (SQFT)
        6: 12.0,  # Shift Window F (F:G = 24.0)
        7: 12.0,  # Shift Window G
        8: 8.0,   # Crew Hrs H (H:I = 16.0)
        9: 8.0,   # Crew Hrs I
        10: 14.0, # Service Provided J (J:K = 28.0)
        11: 14.0  # Service Provided K
    }
    for col_idx, width in col_widths_s1.items():
        ws_quote.column_dimensions[get_column_letter(col_idx)].width = width
    for day_col in range(12, 47):
        ws_quote.column_dimensions[get_column_letter(day_col)].width = 4.5

    # PRINT SETUP FOR SHEET 1
    # Mandated by User: Repeat entire page header down to Data Integrity Note ($1:$8)
    ws_quote.print_title_rows = '$1:$8'
    ws_quote.page_setup.orientation = ws_quote.ORIENTATION_LANDSCAPE
    ws_quote.page_setup.paperSize = ws_quote.PAPERSIZE_LETTER
    ws_quote.sheet_properties.pageSetUpPr.fitToPage = True
    ws_quote.page_setup.fitToWidth = 1
    ws_quote.page_setup.fitToHeight = 0
    ws_quote.page_margins.left = 0.25
    ws_quote.page_margins.right = 0.25
    ws_quote.page_margins.top = 0.35
    ws_quote.page_margins.bottom = 0.35

    # Page breaks for Sheet 1
    ws_quote.row_breaks.append(Break(id=18)) # Page 1: Metadata + Executive Summary
    ws_quote.row_breaks.append(Break(id=33)) # Page 2: Section 1.0 Pricing Schedule
    ws_quote.row_breaks.append(Break(id=48)) # Page 3: Section 2.0 Additional Options
    ws_quote.row_breaks.append(Break(id=58)) # Page 4: Section 3.0 Program Terms
    ws_quote.row_breaks.append(Break(id=67)) # Page 5: Photos 1 & 2
    ws_quote.row_breaks.append(Break(id=75)) # Page 6: Photos 3 & 4
    # Page 7: Section 5.0 Gantt Schedule

    # =============================================================
    # SHEET 2: Service_Gantt_Schedule (Dedicated 1-Page Landscape)
    # Fitted, uncrowded column architecture
    # =============================================================
    ws_gantt = wb.create_sheet(title="Service_Gantt_Schedule")
    ws_gantt.views.sheetView[0].showGridLines = True

    ws_gantt.merge_cells("A1:AN1")
    ws_gantt["A1"] = "HWB CLEANING SERVICES LLC"
    ws_gantt["A1"].font = Font(name="Calibri", size=13, bold=True, color="FFFFFF")
    ws_gantt["A1"].fill = fill_title
    ws_gantt["A1"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws_gantt.row_dimensions[1].height = 22

    ws_gantt.merge_cells("A2:AN2")
    ws_gantt["A2"] = "OPERATIONAL DISPATCH GANTT SCHEDULE — DOWNTOWN FORT WORTH 11-BUILDING PORTFOLIO"
    ws_gantt["A2"].font = Font(name="Calibri", size=9.5, bold=True, color="93C5FD")
    ws_gantt["A2"].fill = fill_title
    ws_gantt["A2"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws_gantt.row_dimensions[2].height = 16

    ws_gantt.row_dimensions[3].height = 18
    ws_gantt.merge_cells("A3:B3")
    ws_gantt["A3"] = "Base Dispatch:"
    ws_gantt["A3"].font = font_bold
    ws_gantt.merge_cells("C3:E3")
    ws_gantt["C3"] = "Arlington, TX (Post-7:00 PM)"
    ws_gantt["C3"].font = font_regular

    ws_gantt.merge_cells("F3:H3")
    ws_gantt["F3"] = "Project Start:"
    ws_gantt["F3"].font = font_bold
    ws_gantt.merge_cells("I3:L3")
    ws_gantt["I3"] = datetime.date(2026, 9, 1)
    ws_gantt["I3"].number_format = "yyyy-mm-dd"
    ws_gantt["I3"].font = font_bold

    ws_gantt.merge_cells("M3:P3")
    ws_gantt["M3"] = "Assigned Crew:"
    ws_gantt["M3"].font = font_bold
    ws_gantt.merge_cells("Q3:U3")
    ws_gantt["Q3"] = "2 Specialized Technicians"
    ws_gantt["Q3"].font = font_regular

    ws_gantt.merge_cells("V3:Z3")
    ws_gantt["V3"] = "Dedicated Mobilization:"
    ws_gantt["V3"].font = font_bold
    ws_gantt.merge_cells("AA3:AF3")
    ws_gantt["AA3"] = "10 Dedicated Night Shifts"
    ws_gantt["AA3"].font = font_regular

    ws_gantt.merge_cells("AG3:AN3")
    ws_gantt["AG3"] = "⏰ 100% Flexible Shift Timing"
    ws_gantt["AG3"].font = Font(name="Calibri", size=8.5, bold=True, color="16A34A")
    ws_gantt["AG3"].alignment = align_center

    for c in range(1, 41):
        ws_gantt.cell(row=3, column=c).border = box_border

    ws_gantt.row_dimensions[4].height = 18
    ws_gantt.merge_cells("A4:E4")
    ws_gantt["A4"] = "LEGEND & COLOR CODES:"
    ws_gantt["A4"].font = font_bold
    ws_gantt["A4"].fill = fill_subtle
    ws_gantt["A4"].alignment = align_center

    legend_items_s2 = [
        ("F4:L4", "DP: Phase 1 Deep Clean", fill_p1_deep_clean),
        ("M4:S4", "SL: Modular Sealer", fill_p2_sealer),
        ("T4:Z4", "QT: Quarterly Care", fill_p3_quarterly),
        ("AA4:AG4", "ST: Stair Detailing", fill_opt_stairs),
        ("AH4:AN4", "WKND: Building Offline", PatternFill(start_color="CBD5E1", end_color="CBD5E1", fill_type="solid"))
    ]
    for crange, ltext, lfill in legend_items_s2:
        ws_gantt.merge_cells(crange)
        c_top = ws_gantt[crange.split(":")[0]]
        c_top.value = ltext
        c_top.font = font_badge
        c_top.fill = lfill
        c_top.alignment = align_center
        c_start, _, c_end, _ = range_boundaries(crange)
        for col_i in range(c_start, c_end + 1):
            ws_gantt.cell(row=4, column=col_i).border = box_border
            ws_gantt.cell(row=4, column=col_i).fill = lfill

    for c in range(1, 6):
        ws_gantt.cell(row=4, column=c).border = box_border

    ws_gantt.row_dimensions[5].height = 18
    ws_gantt.row_dimensions[6].height = 15
    ws_gantt.row_dimensions[7].height = 15

    headers_left_s2 = [
        ("A", "Item"),
        ("B", "Building Name"),
        ("C", "Total SQF"),
        ("D", "Shift Window"),
        ("E", "Crew Hrs")
    ]
    for col_let, htext in headers_left_s2:
        ws_gantt.merge_cells(f"{col_let}5:{col_let}7")
        c_h = ws_gantt[f"{col_let}5"]
        c_h.value = htext
        c_h.font = font_header
        c_h.fill = fill_header_opt
        c_h.alignment = align_header_wrap
        for r in range(5, 8):
            ws_gantt[f"{col_let}{r}"].border = box_border
            ws_gantt[f"{col_let}{r}"].fill = fill_header_opt

    weeks_s2 = [
        ("F5:L5", 6, 12, "Week 1 (Aug 31–Sep 06)"),
        ("M5:S5", 13, 19, "Week 2 (Sep 07–Sep 13)"),
        ("T5:Z5", 20, 26, "Week 3 (Sep 14–Sep 20)"),
        ("AA5:AG5", 27, 33, "Week 4 (Sep 21–Sep 27)"),
        ("AH5:AN5", 34, 40, "Week 5 (Sep 28–Oct 04)")
    ]
    for wrange, start_c, end_c, wtitle in weeks_s2:
        ws_gantt.merge_cells(wrange)
        c_w = ws_gantt[wrange.split(":")[0]]
        c_w.value = wtitle
        c_w.font = font_header
        c_w.fill = fill_header
        c_w.alignment = align_center
        for c in range(start_c, end_c + 1):
            ws_gantt.cell(row=5, column=c).border = box_border
            ws_gantt.cell(row=5, column=c).fill = fill_header

    for d_idx, d_num in enumerate(days_dates):
        col = 6 + d_idx
        c_num = ws_gantt.cell(row=6, column=col, value=d_num)
        c_num.font = Font(name="Calibri", size=8.5, bold=True, color="FFFFFF")
        c_num.fill = fill_title
        c_num.alignment = align_center
        c_num.border = box_border

    for d_idx, d_name in enumerate(days_names):
        col = 6 + d_idx
        c_nam = ws_gantt.cell(row=7, column=col, value=d_name)
        is_w = d_name in ['Sa', 'Su']
        c_nam.fill = PatternFill(start_color="475569", end_color="475569", fill_type="solid") if is_w else PatternFill(start_color="334155", end_color="334155", fill_type="solid")
        c_nam.font = Font(name="Calibri", size=8, bold=True, color="FFFFFF" if is_w else "94A3B8")
        c_nam.alignment = align_center
        c_nam.border = box_border

    schedule_data_s2 = [
        (1, "Chase Bank Building", 2126, "Dedicated Night 1 (3.5h)", 3.5, [7], [11], [21], []),
        (2, "The Westbrook", 1520, "Dedicated Night 2 (3.0h)", 3.0, [8], [11], [22], []),
        (3, "The Carnegie", 1175, "Dedicated Night 3 (2.8h)", 2.8, [9], [11], [23], []),
        (4, "The Cassidy", 1134, "Dedicated Night 4 (2.6h)", 2.6, [10], [11], [24], []),
        (5, "Burk Burnett Building", 1108, "Dedicated Night 5 (2.6h)", 2.6, [13], [18], [27], [28]),
        (6, "Sanger Lofts", 1071, "Dedicated Night 6 (2.5h)", 2.5, [14], [18], [28], []),
        (7, "Petroleum Building", 860, "Dedicated Night 7 (2.2h)", 2.2, [15], [18], [29], []),
        (8, "The Commerce Building", 840, "Dedicated Night 8 (2.2h)", 2.2, [16], [18], [30], []),
        (9, "Virtuoso Building", 560, "Boutique Night 9 (1.8h)", 1.8, [17], [18], [31], []),
        (10, "Knights of Pythias Hall", 414, "Boutique Night 9 (1.6h)", 1.6, [17], [18], [31], []),
        (11, "Plaza Hotel Building", 345, "Boutique Night 10 (1.5h)", 1.5, [20], [21], [34], [])
    ]

    for b_idx, item in enumerate(schedule_data_s2, start=8):
        num, name, sf, window, crew_time, p1_cols, seal_cols, rec_cols, stair_cols = item
        ws_gantt.row_dimensions[b_idx].height = 16

        ws_gantt.cell(row=b_idx, column=1, value=num).alignment = align_center
        ws_gantt.cell(row=b_idx, column=2, value=name).alignment = align_left
        
        c_sf = ws_gantt.cell(row=b_idx, column=3, value=sf)
        c_sf.alignment = align_center
        c_sf.number_format = "#,##0"

        ws_gantt.cell(row=b_idx, column=4, value=window).alignment = align_left

        c_hrs = ws_gantt.cell(row=b_idx, column=5, value=crew_time)
        c_hrs.alignment = align_center
        c_hrs.number_format = '0.0 "hrs"'

        for c in range(1, 6):
            cell = ws_gantt.cell(row=b_idx, column=c)
            cell.font = font_bold if c in [2, 3] else font_regular
            cell.border = box_border
            if b_idx % 2 == 1:
                cell.fill = fill_zebra

        for day_i in range(1, 36):
            col = day_i + 5
            cell = ws_gantt.cell(row=b_idx, column=col)
            cell.border = box_border

            if col in p1_cols:
                cell.fill = fill_p1_deep_clean
                cell.value = "DP"
                cell.font = font_badge
                cell.alignment = align_center
            elif col in seal_cols:
                cell.fill = fill_p2_sealer
                cell.value = "SL"
                cell.font = font_badge
                cell.alignment = align_center
            elif col in rec_cols:
                cell.fill = fill_p3_quarterly
                cell.value = "QT"
                cell.font = font_badge
                cell.alignment = align_center
            elif col in stair_cols:
                cell.fill = fill_opt_stairs
                cell.value = "ST"
                cell.font = font_badge
                cell.alignment = align_center
            elif (col - 6) % 7 in [5, 6]:
                cell.fill = fill_weekend

    tot_r_s2 = 19
    ws_gantt.row_dimensions[tot_r_s2].height = 18
    ws_gantt.merge_cells("A19:B19")
    ws_gantt["A19"] = "TOTAL PORTFOLIO DISPATCH"
    ws_gantt["A19"].font = font_bold
    ws_gantt["A19"].alignment = align_center

    c_tsf = ws_gantt.cell(row=tot_r_s2, column=3, value="=SUM(C8:C18)")
    c_tsf.font = font_bold
    c_tsf.number_format = '#,##0 " SQF"'
    c_tsf.alignment = align_center

    ws_gantt.cell(row=tot_r_s2, column=4, value="10 Dedicated Shifts").alignment = align_center
    c_thrs = ws_gantt.cell(row=tot_r_s2, column=5, value="=SUM(E8:E18)")
    c_thrs.font = font_bold
    c_thrs.number_format = '0.0 "hrs total"'
    c_thrs.alignment = align_center

    for c in range(1, 6):
        ws_gantt.cell(row=tot_r_s2, column=c).border = total_border
        ws_gantt.cell(row=tot_r_s2, column=c).fill = fill_subtle

    for c in range(6, 41):
        cell = ws_gantt.cell(row=tot_r_s2, column=c)
        cell.border = total_border
        cell.fill = fill_subtle

    ws_gantt.row_dimensions[20].height = 6
    ws_gantt.merge_cells("A21:AN21")
    ws_gantt["A21"] = "*Note: Shift timing and scheduled calendar dates are 100% flexible based on client preference. HWB will adapt dispatch hours (earlier start, late night, or weekend windows) to accommodate building security and tenant schedules at no additional cost."
    ws_gantt["A21"].font = Font(name="Calibri", size=8, italic=True, color="475569")
    ws_gantt["A21"].alignment = align_left
    ws_gantt.row_dimensions[21].height = 16

    ws_gantt.column_dimensions['A'].width = 6.0
    ws_gantt.column_dimensions['B'].width = 26.0
    ws_gantt.column_dimensions['C'].width = 14.0
    ws_gantt.column_dimensions['D'].width = 24.0
    ws_gantt.column_dimensions['E'].width = 15.0
    for col_idx in range(6, 41):
        ws_gantt.column_dimensions[get_column_letter(col_idx)].width = 4.5

    ws_gantt.print_title_rows = '$1:$4'
    ws_gantt.page_setup.orientation = ws_gantt.ORIENTATION_LANDSCAPE
    ws_gantt.page_setup.paperSize = ws_gantt.PAPERSIZE_LETTER
    ws_gantt.sheet_properties.pageSetUpPr.fitToPage = True
    ws_gantt.page_setup.fitToWidth = 1
    ws_gantt.page_setup.fitToHeight = 1
    ws_gantt.page_margins.left = 0.25
    ws_gantt.page_margins.right = 0.25
    ws_gantt.page_margins.top = 0.35
    ws_gantt.page_margins.bottom = 0.35
    ws_gantt.print_area = 'A1:AN21'

    # =============================================================
    # SHEET 3: Cost_Underwriting_Audit
    # =============================================================
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
    ws_cost.cell(row=tot_c_row, column=7, value="=SUM(G5:F15)").number_format = "$#,##0.00"
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

    ws_cost.print_title_rows = '$1:$4'
    ws_cost.page_setup.orientation = ws_cost.ORIENTATION_LANDSCAPE
    ws_cost.page_setup.paperSize = ws_cost.PAPERSIZE_LETTER
    ws_cost.sheet_properties.pageSetUpPr.fitToPage = True
    ws_cost.page_setup.fitToWidth = 1
    ws_cost.page_setup.fitToHeight = 1
    ws_cost.page_margins.left = 0.25
    ws_cost.page_margins.right = 0.25
    ws_cost.page_margins.top = 0.35
    ws_cost.page_margins.bottom = 0.35

    header_institution = "&B&10HWB CLEANING SERVICES LLC"
    footer_page_no = "Page &P of &N"

    for ws in [ws_quote, ws_gantt, ws_cost]:
        ws.oddHeader.center.text = header_institution
        ws.oddHeader.center.size = 10
        ws.oddHeader.center.font = "Calibri,Bold"
        ws.evenHeader.center.text = header_institution
        ws.oddFooter.right.text = footer_page_no
        ws.evenFooter.right.text = footer_page_no

    wb.save(target_path)
    print(f"SUCCESS: Saved perfectly formatted, fitted, and repeating-header proposal workbook to {target_path}")

if __name__ == "__main__":
    generate_sundance_excel()
