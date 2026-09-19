#!/usr/bin/env python3
"""
SigmaFidelity™ NTTA 06507 Ancillary Facilities Bid Modeling Engine
Standard: HWB-QMS-1.0 v2.0 / 2026 High-Density Industrial Standards
Author: George (Systems Architect)

Generates:
1. 06507-NTTA-BID-SHEET-HWB-SUBMISSION.xlsx (Official locked NTTA sheet populated with Quote 1)
2. NTTA-06507-EXECUTIVE-BID-MODEL.xlsx (Comprehensive 5-tab executive underwriting model)
"""

import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUOTES_DIR = os.path.join(BASE_DIR, "HWB-COMPANY", "HWB-QUOTES", "NTTA-06507-ANCILLARY")
OFFICIAL_LOCKED_PATH = os.path.join(QUOTES_DIR, "06507 Bid Sheet LOCKED.xlsx")
SUBMISSION_PATH = os.path.join(QUOTES_DIR, "06507-NTTA-BID-SHEET-HWB-SUBMISSION.xlsx")
EXECUTIVE_MODEL_PATH = os.path.join(QUOTES_DIR, "NTTA-06507-EXECUTIVE-BID-MODEL.xlsx")

# --- PRICING CALIBRATION (QUOTE OPTION 1: AGGRESSIVE WIN) ---
RATES_Q1 = {
    "frisco_yr1": 0.195,
    "frisco_yr2": 0.200,
    "plano_yr1": 0.190,
    "plano_yr2": 0.195,
    "mlp3_yr1": 0.200,
    "mlp3_yr2": 0.205,
    "mlp4_yr1": 0.210,
    "mlp4_yr2": 0.215,
    "porter_yr1": 21.75,
    "porter_yr2": 22.25,
    "deep_clean": 650.00,
    "company_name": "HWB Cleaning Services LLC",
    "authorized_agent": "Humberto Dominguez, CEO",
    "quote_date": "09/18/2026"
}

def populate_official_submission_sheet():
    """Populates only the unlocked vendor cells in the official NTTA workbook."""
    print(f"Loading official locked template: {OFFICIAL_LOCKED_PATH}...")
    wb = openpyxl.load_workbook(OFFICIAL_LOCKED_PATH)
    ws = wb["BID SHEET "]

    # Item 1: Frisco Operations Center (10,846 SF)
    ws["E9"] = RATES_Q1["frisco_yr1"]
    ws["I9"] = RATES_Q1["frisco_yr2"]

    # Item 2: Plano Maintenance Center (17,393 SF)
    ws["E14"] = RATES_Q1["plano_yr1"]
    ws["I14"] = RATES_Q1["plano_yr2"]

    # Item 3: MLP-3 Offices (7,083 SF)
    ws["E19"] = RATES_Q1["mlp3_yr1"]
    ws["I19"] = RATES_Q1["mlp3_yr2"]

    # Item 4: MLP-4 Offices (3,045 SF)
    ws["E24"] = RATES_Q1["mlp4_yr1"]
    ws["I24"] = RATES_Q1["mlp4_yr2"]

    # Item 5: Dedicated Day Porter (2,080 Hours/Year)
    ws["F29"] = RATES_Q1["porter_yr1"]
    ws["J29"] = RATES_Q1["porter_yr2"]

    # Deep Clean Infection Control
    ws["D33"] = RATES_Q1["deep_clean"]

    # Signature Block (Populating top-left cells of merged ranges)
    ws["B37"] = RATES_Q1["company_name"]
    ws["B39"] = RATES_Q1["authorized_agent"]
    ws["F39"] = RATES_Q1["quote_date"]

    wb.save(SUBMISSION_PATH)
    print(f"SUCCESS: Official NTTA submission workbook generated: {SUBMISSION_PATH}")


def build_executive_model():
    """Builds the comprehensive 5-tab executive underwriting master workbook."""
    print("Building Executive Underwriting Master Workbook...")
    wb = openpyxl.Workbook()
    # Remove default sheet
    wb.remove(wb.active)

    # Styling Palettes (SigmaFidelity Standard)
    navy_dark = "0F172A"
    navy_blue = "1E3A8A"
    soft_blue = "DBEAFE"
    light_blue = "EFF6FF"
    bg_gray = "F8FAFC"
    border_gray = "CBD5E1"
    emerald_dark = "065F46"
    emerald_fill = "ECFDF5"
    amber_dark = "92400E"
    amber_fill = "FEF3C7"

    font_title = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
    font_sec_hdr = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_tbl_hdr = Font(name="Calibri", size=10, bold=True, color="1E3A8A")
    font_bold = Font(name="Calibri", size=9.5, bold=True, color="0F172A")
    font_regular = Font(name="Calibri", size=9.5, color="1E293B")
    font_sub = Font(name="Calibri", size=8.5, italic=True, color="64748B")
    font_kpi_val = Font(name="Calibri", size=14, bold=True, color="0F172A")
    font_kpi_lbl = Font(name="Calibri", size=9, bold=True, color="1E3A8A")
    font_emerald = Font(name="Calibri", size=9.5, bold=True, color=emerald_dark)
    font_amber = Font(name="Calibri", size=9.5, bold=True, color=amber_dark)

    fill_navy_title = PatternFill(start_color=navy_dark, end_color=navy_dark, fill_type="solid")
    fill_sec_hdr = PatternFill(start_color=navy_blue, end_color=navy_blue, fill_type="solid")
    fill_tbl_hdr = PatternFill(start_color=soft_blue, end_color=soft_blue, fill_type="solid")
    fill_kpi = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
    fill_zebra = PatternFill(start_color=bg_gray, end_color=bg_gray, fill_type="solid")
    fill_emerald = PatternFill(start_color=emerald_fill, end_color=emerald_fill, fill_type="solid")
    fill_amber = PatternFill(start_color=amber_fill, end_color=amber_fill, fill_type="solid")

    thin_border = Border(
        left=Side(style="thin", color=border_gray),
        right=Side(style="thin", color=border_gray),
        top=Side(style="thin", color=border_gray),
        bottom=Side(style="thin", color=border_gray)
    )
    double_bottom_border = Border(
        left=Side(style="thin", color=border_gray),
        right=Side(style="thin", color=border_gray),
        top=Side(style="thin", color=border_gray),
        bottom=Side(style="double", color=navy_blue)
    )

    # -------------------------------------------------------------------------
    # TAB 1: EXECUTIVE_SUMMARY
    # -------------------------------------------------------------------------
    ws1 = wb.create_sheet("Executive_Summary", 0)
    ws1.views.sheetView[0].showGridLines = True

    # Title Block
    ws1.merge_cells("A1:H1")
    tcell = ws1.cell(row=1, column=1, value="HWB CLEANING SERVICES LLC — NTTA CONTRACT 06507 EXECUTIVE BID MODEL")
    tcell.font = font_title
    tcell.fill = fill_navy_title
    tcell.alignment = Alignment(horizontal="center", vertical="center")
    ws1.row_dimensions[1].height = 36.0

    ws1.merge_cells("A2:H2")
    stcell = ws1.cell(row=2, column=1, value="Sol. B2600001083 | Ancillary Janitorial (Frisco, Plano, MLP-3, MLP-4 & 5 Stockpile Restrooms)")
    stcell.font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    stcell.fill = PatternFill(start_color="334155", end_color="334155", fill_type="solid")
    stcell.alignment = Alignment(horizontal="center", vertical="center")
    ws1.row_dimensions[2].height = 22.0

    # KPI Summary Cards (Row 4 to 6)
    kpis = [
        ("TOTAL 2-YEAR BID", "$273,238.58", "NTTA Budget: $276,323.00", "A", "B"),
        ("YEAR 1 COMMITMENT", "$134,948.28", "$11,245.69 / Month", "C", "D"),
        ("YEAR 2 COMMITMENT", "$138,290.30", "$11,524.19 / Month (+2.5%)", "E", "F"),
        ("60-DAY FLOAT REQUIRED", "$21,000.00", "2 Months Payroll + Mobilization", "G", "H"),
    ]
    ws1.row_dimensions[4].height = 18.0
    ws1.row_dimensions[5].height = 26.0
    ws1.row_dimensions[6].height = 16.0

    for lbl, val, sub, c1, c2 in kpis:
        col_start = openpyxl.utils.column_index_from_string(c1)
        col_end = openpyxl.utils.column_index_from_string(c2)
        ws1.merge_cells(start_row=4, start_column=col_start, end_row=4, end_column=col_end)
        ws1.merge_cells(start_row=5, start_column=col_start, end_row=5, end_column=col_end)
        ws1.merge_cells(start_row=6, start_column=col_start, end_row=6, end_column=col_end)

        c_lbl = ws1.cell(row=4, column=col_start, value=lbl)
        c_lbl.font = font_kpi_lbl
        c_lbl.fill = fill_kpi
        c_lbl.alignment = Alignment(horizontal="center", vertical="center")

        c_val = ws1.cell(row=5, column=col_start, value=val)
        c_val.font = font_kpi_val
        c_val.fill = fill_kpi
        c_val.alignment = Alignment(horizontal="center", vertical="center")

        c_sub = ws1.cell(row=6, column=col_start, value=sub)
        c_sub.font = font_sub
        c_sub.fill = fill_kpi
        c_sub.alignment = Alignment(horizontal="center", vertical="center")

        for r in range(4, 7):
            for c in range(col_start, col_end + 1):
                ws1.cell(row=r, column=c).border = thin_border

    # Section Header: Comparison Audit
    ws1.merge_cells("A8:H8")
    sec_cell = ws1.cell(row=8, column=1, value="1.0 STRATEGIC BUDGET COMPARISON: HWB PROPOSAL VS. NTTA ESTIMATE")
    sec_cell.font = font_sec_hdr
    sec_cell.fill = fill_sec_hdr
    sec_cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws1.row_dimensions[8].height = 24.0

    comp_headers = ["Metric / Component", "NTTA Published Estimate", "HWB Option 1 Proposal", "Variance ($)", "Variance (%)", "Operational Impact & Strategic Rationale"]
    comp_cols = [("A", "C"), ("D", "D"), ("E", "E"), ("F", "F"), ("G", "G"), ("H", "H")]

    ws1.row_dimensions[9].height = 22.0
    for idx, (col_a, col_b) in enumerate(comp_cols):
        ca = openpyxl.utils.column_index_from_string(col_a)
        cb = openpyxl.utils.column_index_from_string(col_b)
        if ca != cb:
            ws1.merge_cells(start_row=9, start_column=ca, end_row=9, end_column=cb)
        c = ws1.cell(row=9, column=ca, value=comp_headers[idx])
        c.font = font_tbl_hdr
        c.fill = fill_tbl_hdr
        c.alignment = Alignment(horizontal="center" if idx in [1,2,3,4] else "left", vertical="center")
        for ci in range(ca, cb + 1):
            ws1.cell(row=9, column=ci).border = thin_border

    comp_rows = [
        ("Total 2-Year Contract Value", "$276,323.00", "$273,238.58", "-$3,084.42", "-1.12%", "Lands surgically under NTTA budget to guarantee lowest responsible bid status."),
        ("Average Annual Commitment", "$138,161.50", "$136,619.29", "-$1,542.21", "-1.12%", "Fixed firm-pricing structure per contract terms ($134.9k Yr 1 / $138.3k Yr 2)."),
        ("Average Monthly Billing", "$11,513.46", "$11,384.94", "-$128.52", "-1.12%", "Predictable Net 30 recurring municipal cash flow directly from toll authority."),
        ("Consumable Paper & Soap Debt", "$0.00", "$0.00", "$0.00", "0.00%", "NTTA furnishes 100% of paper towels, toilet paper, hand soap, and liners."),
        ("2-Year Direct Operating Hard Costs", "N/A", "$232,729.84", "N/A", "N/A", "Includes 103 weekly labor hours, W-2 payroll burden, fuel, and chemical dilution."),
        ("2-Year HWB Net Operating Profit (EBITDA)", "N/A", "$40,508.74", "N/A", "14.82%", "Pure net margin captured with zero equipment debt and zero supply debt."),
    ]

    curr_row = 10
    for rdata in comp_rows:
        ws1.row_dimensions[curr_row].height = 22.0
        ws1.merge_cells(f"A{curr_row}:C{curr_row}")
        ws1.cell(row=curr_row, column=1, value=rdata[0]).font = font_bold
        ws1.cell(row=curr_row, column=4, value=rdata[1]).font = font_regular
        ws1.cell(row=curr_row, column=5, value=rdata[2]).font = font_emerald if "$" in rdata[2] else font_regular
        ws1.cell(row=curr_row, column=6, value=rdata[3]).font = font_emerald
        ws1.cell(row=curr_row, column=7, value=rdata[4]).font = font_emerald
        ws1.cell(row=curr_row, column=8, value=rdata[5]).font = font_regular

        for c in range(1, 9):
            cell = ws1.cell(row=curr_row, column=c)
            cell.border = thin_border
            if c in [4, 5, 6, 7]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")
            if curr_row % 2 == 1:
                cell.fill = fill_zebra
        curr_row += 1

    # Section Header: 2-Year Cost Waterfall
    curr_row += 1
    ws1.merge_cells(f"A{curr_row}:H{curr_row}")
    sec_cell2 = ws1.cell(row=curr_row, column=1, value="2.0 TWO-YEAR OPERATING COST & MARGIN UNDERWRITING BREAKDOWN")
    sec_cell2.font = font_sec_hdr
    sec_cell2.fill = fill_sec_hdr
    sec_cell2.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws1.row_dimensions[curr_row].height = 24.0

    curr_row += 1
    wf_headers = ["Budget Component / Expense Category", "Basis & Volume", "Year 1 Total", "Year 2 Total", "2-Year Total", "% of Revenue", "Notes & Operational Controls"]
    wf_cols = [("A", "C"), ("D", "D"), ("E", "E"), ("F", "F"), ("G", "G"), ("H", "H")]
    ws1.row_dimensions[curr_row].height = 22.0
    for idx, (col_a, col_b) in enumerate(wf_cols[:6]):
        ca = openpyxl.utils.column_index_from_string(col_a)
        cb = openpyxl.utils.column_index_from_string(col_b)
        if ca != cb:
            ws1.merge_cells(start_row=curr_row, start_column=ca, end_row=curr_row, end_column=cb)
        c = ws1.cell(row=curr_row, column=ca, value=wf_headers[idx])
        c.font = font_tbl_hdr
        c.fill = fill_tbl_hdr
        c.alignment = Alignment(horizontal="center" if idx in [2,3,4,5] else "left", vertical="center")
        for ci in range(ca, cb + 1):
            ws1.cell(row=curr_row, column=ci).border = thin_border
    ws1.cell(row=curr_row, column=8, value=wf_headers[6]).font = font_tbl_hdr
    ws1.cell(row=curr_row, column=8).fill = fill_tbl_hdr
    ws1.cell(row=curr_row, column=8).border = thin_border

    wf_rows = [
        ("1. Direct Day Porter Labor (W-2)", "2,080 Hrs/Yr @ $16.50 base ($19.47 loaded)", "$40,497.60", "$41,510.04", "$82,007.64", "30.01%", "Dedicated full-time Day Porter (Mon-Fri 7:00am-3:30pm)."),
        ("2. Direct Night Cleaning Labor (W-2)", "3,276 Hrs/Yr @ $15.50-$17.00 base ($19.17 loaded)", "$62,817.56", "$64,388.00", "$127,205.56", "46.56%", "Mobile 2-person crew covering Frisco, Plano, MLP-3, MLP-4."),
        ("3. Mobile Field Supervision", "156 Hrs/Yr @ $22.00 base ($25.96 loaded)", "$4,049.76", "$4,151.00", "$8,200.76", "3.00%", "Daily audit checks and digital photo quality sign-offs."),
        ("4. Vehicle Travel, Fuel & Logistics", "12 miles/night sweep + weekly stockpiles", "$3,000.00", "$3,075.00", "$6,075.00", "2.22%", "Covers route gas across DNT/SRT corridor (All-inclusive rate)."),
        ("5. Chemicals, Disinfectants & Mops", "Mondo neutral cleaners, glass, disinfectant", "$3,000.00", "$3,100.00", "$6,100.00", "2.23%", "Chemical dilution systems; zero paper/soap expense (NTTA supplied)."),
        ("6. Insurance, Uniforms & Overhead", "CGL, Auto, WC allocation, badging & tests", "$3,140.88", "$3,000.00", "$6,140.88", "2.25%", "Satisfies all NTTA insurance, statewide background checks & drugs."),
        ("TOTAL OPERATING EXPENSES", "Total Out-of-Pocket Hard Costs", "$116,505.80", "$119,224.04", "$235,729.84", "86.27%", "All-inclusive operational delivery burden."),
        ("NET OPERATING PROFIT (EBITDA)", "Pure Subcontractor / Prime Margin", "$18,442.48", "$19,066.26", "$37,508.74", "13.73%", "Net bottom-line earnings retained by HWB Cleaning Services."),
        ("TOTAL BILLED TO NTTA", "Official Contract Schedule Amount", "$134,948.28", "$138,290.30", "$273,238.58", "100.00%", "Target proposal value submitted on official Bid Sheet."),
    ]

    curr_row += 1
    for rdata in wf_rows:
        ws1.row_dimensions[curr_row].height = 22.0
        ws1.merge_cells(f"A{curr_row}:C{curr_row}")
        ws1.cell(row=curr_row, column=1, value=rdata[0]).font = font_bold
        ws1.cell(row=curr_row, column=4, value=rdata[1]).font = font_regular
        ws1.cell(row=curr_row, column=5, value=rdata[2]).font = font_regular
        ws1.cell(row=curr_row, column=6, value=rdata[3]).font = font_regular
        ws1.cell(row=curr_row, column=7, value=rdata[4]).font = font_bold if "TOTAL" in rdata[0] else font_regular
        ws1.cell(row=curr_row, column=8, value=rdata[5]).font = font_bold if "TOTAL" in rdata[0] else font_regular

        is_tot = "TOTAL" in rdata[0] or "PROFIT" in rdata[0]
        for c in range(1, 9):
            cell = ws1.cell(row=curr_row, column=c)
            cell.border = double_bottom_border if "BILLED" in rdata[0] else thin_border
            if c in [4, 5, 6, 7]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")
            if "PROFIT" in rdata[0]:
                cell.fill = fill_emerald
            elif "BILLED" in rdata[0]:
                cell.fill = fill_tbl_hdr
            elif is_tot:
                cell.fill = fill_amber
            elif curr_row % 2 == 1:
                cell.fill = fill_zebra
        curr_row += 1

    # Column widths for Tab 1
    col_widths1 = {"A": 14, "B": 18, "C": 18, "D": 26, "E": 18, "F": 18, "G": 18, "H": 42}
    for col, width in col_widths1.items():
        ws1.column_dimensions[col].width = width

    # -------------------------------------------------------------------------
    # TAB 2: NTTA_OFFICIAL_BID_SHEET
    # -------------------------------------------------------------------------
    ws2 = wb.create_sheet("NTTA_Official_Bid_Sheet", 1)
    ws2.views.sheetView[0].showGridLines = True

    # Mirror official sheet header
    ws2.merge_cells("B1:L1")
    ws2["B1"] = "NORTH TEXAS TOLLWAY AUTHORITY"
    ws2["B1"].font = Font(name="Calibri", size=13, bold=True, color="0F172A")
    ws2["B1"].alignment = Alignment(horizontal="center")

    ws2.merge_cells("B2:L2")
    ws2["B2"] = "BID SHEET"
    ws2["B2"].font = Font(name="Calibri", size=11, bold=True, color="0F172A")
    ws2["B2"].alignment = Alignment(horizontal="center")

    ws2.merge_cells("B3:L3")
    ws2["B3"] = "06507-NTT-00-GS-MA"
    ws2["B3"].font = Font(name="Calibri", size=10, bold=True, color="0F172A")
    ws2["B3"].alignment = Alignment(horizontal="center")

    ws2.merge_cells("B4:L4")
    ws2["B4"] = "Janitorial Services for Ancillary Facilities"
    ws2["B4"].font = Font(name="Calibri", size=10, italic=True)
    ws2["B4"].alignment = Alignment(horizontal="center")

    ws2.merge_cells("B5:L5")
    ws2["B5"] = "This quote will remain valid for 180 days from receipt."
    ws2["B5"].font = Font(name="Calibri", size=9, italic=True, color="475569")
    ws2["B5"].alignment = Alignment(horizontal="center")

    # Table 1: Frisco Operations Center
    ws2.merge_cells("B6:L6")
    ws2["B6"] = "FRISCO OPERATIONS CENTER - 11110 RESEARCH RD, FRISCO TEXAS 75033"
    ws2["B6"].font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    ws2["B6"].fill = fill_sec_hdr

    ws2.merge_cells("D7:G7")
    ws2["D7"] = "YEAR 1"
    ws2["D7"].font = font_tbl_hdr
    ws2["D7"].fill = fill_tbl_hdr
    ws2["D7"].alignment = Alignment(horizontal="center")

    ws2.merge_cells("H7:K7")
    ws2["H7"] = "YEAR 2"
    ws2["H7"].font = font_tbl_hdr
    ws2["H7"].fill = fill_tbl_hdr
    ws2["H7"].alignment = Alignment(horizontal="center")

    hdrs = ["ITEM No.", "DESCRIPTION", "TOTAL CLEANING SQ. FT.", "COST PER SQ. FT.", "MONTHLY COST", "TOTAL YEAR 1", "TOTAL CLEANING SQ. FT.", "COST PER SQ. FT.", "MONTHLY COST", "TOTAL YEAR 2", "EXTENDED TOTAL FOR 2 YEARS"]
    cols = ["B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"]
    for idx, col in enumerate(cols):
        ws2[f"{col}8"] = hdrs[idx]
        ws2[f"{col}8"].font = Font(name="Calibri", size=9, bold=True, color="1E3A8A")
        ws2[f"{col}8"].fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")
        ws2[f"{col}8"].alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    ws2["B9"] = 1
    ws2["C9"] = "6 Days of Cleaning (Sunday - Friday Night)"
    ws2["D9"] = 10846
    ws2["E9"] = RATES_Q1["frisco_yr1"]
    ws2["F9"] = "=D9*E9"
    ws2["G9"] = "=F9*12"
    ws2["H9"] = 10846
    ws2["I9"] = RATES_Q1["frisco_yr2"]
    ws2["J9"] = "=H9*I9"
    ws2["K9"] = "=J9*12"
    ws2["L9"] = "=G9+K9"

    ws2["J10"] = "SUBTOTAL"
    ws2["L10"] = "=L9"

    # Table 2: Plano Operations Center
    ws2.merge_cells("B11:L11")
    ws2["B11"] = "PLANO OPERATIONS CENTER - 1080 OHIO DR, PLANO TEXAS 75093"
    ws2["B11"].font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    ws2["B11"].fill = fill_sec_hdr

    ws2.merge_cells("D12:G12")
    ws2["D12"] = "YEAR 1"
    ws2["D12"].font = font_tbl_hdr
    ws2["D12"].fill = fill_tbl_hdr
    ws2["D12"].alignment = Alignment(horizontal="center")

    ws2.merge_cells("H12:K12")
    ws2["H12"] = "YEAR 2"
    ws2["H12"].font = font_tbl_hdr
    ws2["H12"].fill = fill_tbl_hdr
    ws2["H12"].alignment = Alignment(horizontal="center")

    for idx, col in enumerate(cols):
        ws2[f"{col}13"] = hdrs[idx]
        ws2[f"{col}13"].font = Font(name="Calibri", size=9, bold=True, color="1E3A8A")
        ws2[f"{col}13"].fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")
        ws2[f"{col}13"].alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    ws2["B14"] = 2
    ws2["C14"] = "6 Days of Cleaning (Sunday - Friday Night)"
    ws2["D14"] = 17393
    ws2["E14"] = RATES_Q1["plano_yr1"]
    ws2["F14"] = "=D14*E14"
    ws2["G14"] = "=F14*12"
    ws2["H14"] = 17393
    ws2["I14"] = RATES_Q1["plano_yr2"]
    ws2["J14"] = "=H14*I14"
    ws2["K14"] = "=J14*12"
    ws2["L14"] = "=G14+K14"

    ws2["J15"] = "SUBTOTAL"
    ws2["L15"] = "=L14"

    # Table 3: MLP-3 Offices
    ws2.merge_cells("B16:L16")
    ws2["B16"] = "MLP-3 OFFICES - 2803 DALLAS PARKWAY, PLANO TEXAS 75093"
    ws2["B16"].font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    ws2["B16"].fill = fill_sec_hdr

    ws2.merge_cells("D17:G17")
    ws2["D17"] = "YEAR 1"
    ws2["D17"].font = font_tbl_hdr
    ws2["D17"].fill = fill_tbl_hdr
    ws2["D17"].alignment = Alignment(horizontal="center")

    ws2.merge_cells("H17:K17")
    ws2["H17"] = "YEAR 2"
    ws2["H17"].font = font_tbl_hdr
    ws2["H17"].fill = fill_tbl_hdr
    ws2["H17"].alignment = Alignment(horizontal="center")

    for idx, col in enumerate(cols):
        ws2[f"{col}18"] = hdrs[idx]
        ws2[f"{col}18"].font = Font(name="Calibri", size=9, bold=True, color="1E3A8A")
        ws2[f"{col}18"].fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")
        ws2[f"{col}18"].alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    ws2["B19"] = 3
    ws2["C19"] = "5 Days of Cleaning (Sunday - Thursday Night)"
    ws2["D19"] = 7083
    ws2["E19"] = RATES_Q1["mlp3_yr1"]
    ws2["F19"] = "=D19*E19"
    ws2["G19"] = "=F19*12"
    ws2["H19"] = 7083
    ws2["I19"] = RATES_Q1["mlp3_yr2"]
    ws2["J19"] = "=H19*I19"
    ws2["K19"] = "=J19*12"
    ws2["L19"] = "=G19+K19"

    ws2["J20"] = "SUBTOTAL"
    ws2["L20"] = "=L19"

    # Table 4: MLP-4 Offices
    ws2.merge_cells("B21:L21")
    ws2["B21"] = "MLP-4 OFFICES - 10350 DALLAS PARKWAY, FRISCO TEXAS 75034"
    ws2["B21"].font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    ws2["B21"].fill = fill_sec_hdr

    ws2.merge_cells("D22:G22")
    ws2["D22"] = "YEAR 1"
    ws2["D22"].font = font_tbl_hdr
    ws2["D22"].fill = fill_tbl_hdr
    ws2["D22"].alignment = Alignment(horizontal="center")

    ws2.merge_cells("H22:K22")
    ws2["H22"] = "YEAR 2"
    ws2["H22"].font = font_tbl_hdr
    ws2["H22"].fill = fill_tbl_hdr
    ws2["H22"].alignment = Alignment(horizontal="center")

    for idx, col in enumerate(cols):
        ws2[f"{col}23"] = hdrs[idx]
        ws2[f"{col}23"].font = Font(name="Calibri", size=9, bold=True, color="1E3A8A")
        ws2[f"{col}23"].fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")
        ws2[f"{col}23"].alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    ws2["B24"] = 4
    ws2["C24"] = "5 Days of Cleaning (Sunday - Thursday Night)"
    ws2["D24"] = 3045
    ws2["E24"] = RATES_Q1["mlp4_yr1"]
    ws2["F24"] = "=D24*E24"
    ws2["G24"] = "=F24*12"
    ws2["H24"] = 3045
    ws2["I24"] = RATES_Q1["mlp4_yr2"]
    ws2["J24"] = "=H24*I24"
    ws2["K24"] = "=J24*12"
    ws2["L24"] = "=G24+K24"

    ws2["J25"] = "SUBTOTAL"
    ws2["L25"] = "=L24"

    # Table 5: Day Porter
    ws2.merge_cells("B26:L26")
    ws2["B26"] = "DAY PORTER SERVICE"
    ws2["B26"].font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    ws2["B26"].fill = fill_sec_hdr

    ws2.merge_cells("D27:G27")
    ws2["D27"] = "YEAR 1"
    ws2["D27"].font = font_tbl_hdr
    ws2["D27"].fill = fill_tbl_hdr
    ws2["D27"].alignment = Alignment(horizontal="center")

    ws2.merge_cells("H27:K27")
    ws2["H27"] = "YEAR 2"
    ws2["H27"].font = font_tbl_hdr
    ws2["H27"].fill = fill_tbl_hdr
    ws2["H27"].alignment = Alignment(horizontal="center")

    porter_hdrs = ["ITEM No.", "DESCRIPTION", "ANNUAL HOURS", "", "HOURLY RATE", "TOTAL YEAR 1", "ANNUAL HOURS", "", "HOURLY RATE", "TOTAL YEAR 2", "EXTENDED TOTAL FOR 2 YEARS"]
    for idx, col in enumerate(cols):
        ws2[f"{col}28"] = porter_hdrs[idx]
        ws2[f"{col}28"].font = Font(name="Calibri", size=9, bold=True, color="1E3A8A")
        ws2[f"{col}28"].fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")
        ws2[f"{col}28"].alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    ws2["B29"] = 5
    ws2["C29"] = "5 Days of cleaning, day porter service for 2,080 hours per year"
    ws2["D29"] = 2080
    ws2["F29"] = RATES_Q1["porter_yr1"]
    ws2["G29"] = "=D29*F29"
    ws2["H29"] = 2080
    ws2["J29"] = RATES_Q1["porter_yr2"]
    ws2["K29"] = "=H29*J29"
    ws2["L29"] = "=G29+K29"

    ws2["J30"] = "SUBTOTAL"
    ws2["L30"] = "=L29"

    # Grand Total
    ws2.merge_cells("J32:K32")
    ws2["J32"] = "TOTAL 2-YEAR BID AMOUNT"
    ws2["J32"].font = Font(name="Calibri", size=10, bold=True, color="1E3A8A")
    ws2["L32"] = "=L10+L15+L20+L25+L30"
    ws2["L32"].font = Font(name="Calibri", size=11, bold=True, color="0F172A")
    ws2["L32"].fill = fill_amber

    # Infection Control
    ws2["C33"] = "Deep Clean Infection Control"
    ws2["D33"] = RATES_Q1["deep_clean"]
    ws2["D33"].font = font_bold

    # Signature Block
    ws2["B36"] = "COMPANY NAME (PRINTED)"
    ws2["F36"] = "SIGNATURE"
    ws2["B37"] = RATES_Q1["company_name"]
    ws2["F37"] = "— Approved by Humberto Dominguez (CEO) —"
    ws2["B38"] = "AUTHORIZED AGENT (PRINTED)"
    ws2["F38"] = "DATE"
    ws2["B39"] = RATES_Q1["authorized_agent"]
    ws2["F39"] = RATES_Q1["quote_date"]

    for r in [9, 14, 19, 24, 29, 32, 33]:
        for c in range(2, 13):
            col_ltr = openpyxl.utils.get_column_letter(c)
            cell = ws2[f"{col_ltr}{r}"]
            cell.border = thin_border
            if col_ltr in ["E", "F", "G", "I", "J", "K", "L"]:
                cell.number_format = "$#,##0.00"
                cell.alignment = Alignment(horizontal="right", vertical="center")
            elif col_ltr in ["D", "H"]:
                cell.number_format = "#,##0"
                cell.alignment = Alignment(horizontal="center", vertical="center")

    col_widths2 = {"A": 4, "B": 8, "C": 36, "D": 14, "E": 14, "F": 16, "G": 16, "H": 14, "I": 14, "J": 16, "K": 16, "L": 22}
    for col, width in col_widths2.items():
        ws2.column_dimensions[col].width = width

    # -------------------------------------------------------------------------
    # TAB 3: SHIFT_LABOR_MODEL
    # -------------------------------------------------------------------------
    ws3 = wb.create_sheet("Shift_Labor_Model", 2)
    ws3.views.sheetView[0].showGridLines = True

    ws3.merge_cells("A1:G1")
    ws3["A1"] = "NTTA 06507 — HOURLY LABOR & SHIFT COST BREAKDOWN"
    ws3["A1"].font = font_title
    ws3["A1"].fill = fill_navy_title
    ws3["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws3.row_dimensions[1].height = 30.0

    l_hdrs = ["Position / Assignment", "Weekly Hours", "Base Wage ($/Hr)", "FICA/Taxes (11%)", "Workers Comp (7%)", "Loaded Bill Rate", "Weekly Cost", "Annual Cost"]
    ws3.row_dimensions[3].height = 22.0
    for idx, hdr in enumerate(l_hdrs):
        col_letter = openpyxl.utils.get_column_letter(idx + 1)
        c = ws3.cell(row=3, column=idx+1, value=hdr)
        c.font = font_tbl_hdr
        c.fill = fill_tbl_hdr
        c.border = thin_border
        c.alignment = Alignment(horizontal="center" if idx > 0 else "left", vertical="center")

    labor_data = [
        ("Full-Time Day Porter (Mon-Fri 7am-3:30pm)", 40.0, 16.50, 1.82, 1.16, 19.47, 778.80, 40497.60),
        ("Night Crew Lead / Driver (Sun-Fri Night)", 31.5, 17.00, 1.87, 1.19, 20.06, 631.89, 32858.28),
        ("Night Technician / Cleaner (Sun-Fri Night)", 31.5, 15.50, 1.71, 1.09, 18.29, 576.14, 29959.02),
        ("Mobile Shift Supervisor (1 Audit/Night)", 3.0, 22.00, 2.42, 1.54, 25.96, 77.88, 4049.76),
        ("TOTALS / WEIGHTED AVERAGES", 106.0, 16.63, 1.83, 1.16, 19.62, 2064.71, 107364.66)
    ]

    for idx, rdata in enumerate(labor_data):
        row_num = 4 + idx
        ws3.row_dimensions[row_num].height = 20.0
        for c_idx, val in enumerate(rdata):
            cell = ws3.cell(row=row_num, column=c_idx+1, value=val)
            cell.border = thin_border
            if idx == len(labor_data) - 1:
                cell.font = font_bold
                cell.fill = fill_amber
            else:
                cell.font = font_regular
                if idx % 2 == 1:
                    cell.fill = fill_zebra

            if c_idx == 0:
                cell.alignment = Alignment(horizontal="left", vertical="center")
            elif c_idx == 1:
                cell.number_format = "0.0"
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.number_format = "$#,##0.00"
                cell.alignment = Alignment(horizontal="right", vertical="center")

    col_widths3 = {"A": 36, "B": 14, "C": 16, "D": 16, "E": 16, "F": 16, "G": 16, "H": 18}
    for col, width in col_widths3.items():
        ws3.column_dimensions[col].width = width

    # -------------------------------------------------------------------------
    # TAB 4: FACILITY_SQFT_TAKEOFF
    # -------------------------------------------------------------------------
    ws4 = wb.create_sheet("Facility_SqFt_Takeoff", 3)
    ws4.views.sheetView[0].showGridLines = True

    ws4.merge_cells("A1:G1")
    ws4["A1"] = "NTTA 06507 — FACILITY PORTFOLIO TAKEOFF & PRODUCTION RATES"
    ws4["A1"].font = font_title
    ws4["A1"].fill = fill_navy_title
    ws4["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws4.row_dimensions[1].height = 30.0

    f_hdrs = ["Facility Name", "Physical Address", "Cleanable Sq. Ft.", "Service Days / Wk", "Production Rate (SF/Hr)", "Crew Hours / Night", "Floor Substrates & Key Features"]
    ws4.row_dimensions[3].height = 22.0
    for idx, hdr in enumerate(f_hdrs):
        c = ws4.cell(row=3, column=idx+1, value=hdr)
        c.font = font_tbl_hdr
        c.fill = fill_tbl_hdr
        c.border = thin_border
        c.alignment = Alignment(horizontal="center" if idx in [2,3,4,5] else "left", vertical="center")

    fac_data = [
        ("Frisco Operations Center (FOC)", "11110 Research Rd, Frisco, TX 75033", 10846, "6 Days (Sun-Fri)", 3500, 3.10, "Mondo rubber flooring in maintenance shop, VCT, restrooms."),
        ("Plano Maintenance Center (POC)", "1080 Ohio Dr, Plano, TX 75093", 17393, "6 Days (Sun-Fri)", 3500, 4.97, "Mondo rubber flooring, administrative offices, dispatch, tile restrooms."),
        ("MLP-3 Office Complex", "2803 Dallas Pkwy, Plano, TX 75093", 7083, "5 Days (Sun-Thu)", 3500, 2.02, "Offices, mezzanine, tunnel cleanable area, carpet and ceramic tile."),
        ("MLP-4 Office Complex", "10350 Dallas Pkwy, Frisco, TX 75034", 3045, "5 Days (Sun-Thu)", 3500, 0.87, "Offices, entry lobby, 145 window panes, breakroom."),
        ("SRT @ I-35E Satellite Restroom", "851 Texas 121, Lewisville, TX 75067", 100, "1 Day / Week", "N/A", 0.33, "Single person controlled access restroom facility."),
        ("SRT @ DNT Satellite Restroom", "1601 Dallas Pkwy, Frisco, TX 75034", 100, "1 Day / Week", "N/A", 0.33, "Single person controlled access restroom facility."),
        ("SRT @ Exchange Pkwy Satellite", "8400 State Hwy 121 S, McKinney, TX 75070", 100, "1 Day / Week", "N/A", 0.33, "Single person controlled access restroom facility."),
        ("DNT @ MLP-2 Satellite Restroom", "15909A Dallas Pkwy, Addison, TX 75001", 100, "1 Day / Week", "N/A", 0.33, "Single person controlled access restroom facility."),
        ("Addison Airport Toll Tunnel Restroom", "4140 Keller Springs Rd, Addison, TX 75001", 100, "1 Day / Week", "N/A", 0.33, "Single person controlled access restroom facility."),
        ("PORTFOLIO TOTAL", "All Primary Facilities + 5 Stockpiles", 38867, "—", "—", 12.61, "38,367 primary cleanable SF + 500 SF satellite restrooms.")
    ]

    for idx, rdata in enumerate(fac_data):
        row_num = 4 + idx
        ws4.row_dimensions[row_num].height = 20.0
        for c_idx, val in enumerate(rdata):
            cell = ws4.cell(row=row_num, column=c_idx+1, value=val)
            cell.border = thin_border
            if idx == len(fac_data) - 1:
                cell.font = font_bold
                cell.fill = fill_amber
            else:
                cell.font = font_regular
                if idx % 2 == 1:
                    cell.fill = fill_zebra

            if c_idx in [2, 3, 4, 5]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
                if c_idx == 2 and isinstance(val, (int, float)):
                    cell.number_format = "#,##0"
                elif c_idx == 5 and isinstance(val, (int, float)):
                    cell.number_format = "0.00"
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    col_widths4 = {"A": 30, "B": 36, "C": 16, "D": 16, "E": 18, "F": 16, "G": 40}
    for col, width in col_widths4.items():
        ws4.column_dimensions[col].width = width

    # -------------------------------------------------------------------------
    # TAB 5: CASH_FLOW_FLOAT
    # -------------------------------------------------------------------------
    ws5 = wb.create_sheet("Cash_Flow_Float", 4)
    ws5.views.sheetView[0].showGridLines = True

    ws5.merge_cells("A1:F1")
    ws5["A1"] = "NTTA 06507 — 60-DAY WORKING CAPITAL FLOAT TIMELINE"
    ws5["A1"].font = font_title
    ws5["A1"].fill = fill_navy_title
    ws5["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws5.row_dimensions[1].height = 30.0

    cf_hdrs = ["Timeline Milestone", "Operational Event & Activity", "Cash Outflow ($)", "Cash Inflow ($)", "Cumulative Net Cash Flow", "Working Capital Status"]
    ws5.row_dimensions[3].height = 22.0
    for idx, hdr in enumerate(cf_hdrs):
        c = ws5.cell(row=3, column=idx+1, value=hdr)
        c.font = font_tbl_hdr
        c.fill = fill_tbl_hdr
        c.border = thin_border
        c.alignment = Alignment(horizontal="center" if idx in [0, 2, 3, 4] else "left", vertical="center")

    cf_data = [
        ("Day 0 (Pre-Launch)", "Mobilization: 4 Criminal Checks, 10-Panel Drugs, Uniforms & Dilution Chem", -1800.00, 0.0, -1800.00, "Initial Setup Capital Deployed"),
        ("Day 15 (Month 1)", "Payroll Run #1 (2 Weeks Day Porter + Night Crew)", -3973.00, 0.0, -5773.00, "Operating Float Active"),
        ("Day 30 (Month 1)", "Payroll Run #2 (2 Weeks Day Porter + Night Crew) + Route Fuel", -4223.00, 0.0, -9996.00, "Month 1 Services Complete"),
        ("Day 31 (Billing)", "Submit Month 1 Invoice + 30-Day Photo Documentation to NTTA", 0.0, 0.0, -9996.00, "Net 30 Review Clock Starts"),
        ("Day 45 (Month 2)", "Payroll Run #3 (2 Weeks Day Porter + Night Crew)", -3973.00, 0.0, -13969.00, "Month 2 In Progress"),
        ("Day 60 (Month 2)", "Payroll Run #4 (2 Weeks Day Porter + Night Crew) + Route Fuel", -4223.00, 0.0, -18192.00, "PEAK CAPITAL EXPOSURE POINT"),
        ("Day 60-65 (Remittance)", "NTTA ACH Wire Received for Month 1 Invoice", 0.0, 11245.69, -6946.31, "First Payment Cleared (Capital Recycling Begins)"),
        ("Day 75 (Month 3)", "Payroll Run #5 (Funded by NTTA Month 1 Wire)", -3973.00, 0.0, -10919.31, "Self-Funding Active"),
        ("Day 90-95 (Remittance)", "NTTA ACH Wire Received for Month 2 Invoice", 0.0, 11245.69, 326.38, "100% CAPITAL RECOVERED (Net Positive Cash Flow)")
    ]

    for idx, rdata in enumerate(cf_data):
        row_num = 4 + idx
        ws5.row_dimensions[row_num].height = 20.0
        for c_idx, val in enumerate(rdata):
            cell = ws5.cell(row=row_num, column=c_idx+1, value=val)
            cell.border = thin_border
            if "PEAK" in str(val):
                cell.font = font_bold
                cell.fill = fill_amber
            elif "RECOVERED" in str(val):
                cell.font = font_emerald
                cell.fill = fill_emerald
            else:
                cell.font = font_regular
                if idx % 2 == 1:
                    cell.fill = fill_zebra

            if c_idx in [0, 5]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif c_idx in [2, 3, 4]:
                cell.number_format = "$#,##0.00"
                cell.alignment = Alignment(horizontal="right", vertical="center")
                if val < 0:
                    cell.font = Font(name="Calibri", size=9.5, color="991B1B")
                elif val > 0:
                    cell.font = font_emerald
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    col_widths5 = {"A": 22, "B": 42, "C": 16, "D": 16, "E": 20, "F": 32}
    for col, width in col_widths5.items():
        ws5.column_dimensions[col].width = width

    wb.save(EXECUTIVE_MODEL_PATH)
    print(f"SUCCESS: Executive Underwriting Master Workbook generated: {EXECUTIVE_MODEL_PATH}")

if __name__ == "__main__":
    populate_official_submission_sheet()
    build_executive_model()
