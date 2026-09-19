import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter, range_boundaries
from openpyxl.worksheet.pagebreak import Break

wb = openpyxl.load_workbook("HWB-COMPANY/HWB-QUOTES/SUNDANCE-QUOTE-gantt.xlsx")

# -------------------------------------------------------------
# 1. FIX Commercial_Quote
# -------------------------------------------------------------
ws1 = wb["Commercial_Quote"]

# Fix Header Rows 4 to 7 Merges
# Currently: A4:Client, B4:E4:Value, F4:spacer, G4:H4:PropID, I4:K4:Value
# Unmerge and re-merge with A:B for labels!
font_bold = Font(name="Calibri", size=9, bold=True, color="0F172A")
font_reg = Font(name="Calibri", size=9, color="334155")
fill_zebra = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
thin_side = Side(style="thin", color="CBD5E1")
box_border = Border(top=thin_side, bottom=thin_side, left=thin_side, right=thin_side)

meta_data = [
    ("Client:", "Sundance Square & Downtown Commercial Property Management", "Proposal ID:", "HWB-BID-2026-FW01 (v3.7.0)"),
    ("Property:", "Downtown Fort Worth Commercial Portfolio (11 Buildings)", "Effective Date:", "September 03, 2026"),
    ("Central Office:", "425 Houston Street, Suite 250, Fort Worth, TX 76102", "Dispatch Origin:", "Arlington, TX"),
    ("Primary Scope:", "11 Ground-Floor Commercial Lobbies (11,153 Cleanable SF)", "Operational Crew:", "2 Specialized Floor Technicians")
]

# Unmerge existing meta rows 4 to 7
for r in range(4, 8):
    for rng in list(ws1.merged_cells.ranges):
        if rng.min_row <= r <= rng.max_row and rng.max_col <= 11:
            ws1.unmerge_cells(str(rng))

for idx, (l1, v1, l2, v2) in enumerate(meta_data, start=4):
    ws1.row_dimensions[idx].height = 18
    # Left Label: A:B (width 5.5 + 25 = 30.5)
    ws1.merge_cells(f"A{idx}:B{idx}")
    ws1[f"A{idx}"] = l1
    ws1[f"A{idx}"].font = font_bold
    ws1[f"A{idx}"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    
    # Left Value: C:F (width 22 + 24 + 14 + 13 = 73.0)
    ws1.merge_cells(f"C{idx}:F{idx}")
    ws1[f"C{idx}"] = v1
    ws1[f"C{idx}"].font = font_reg
    ws1[f"C{idx}"].alignment = Alignment(horizontal="left", vertical="center")

    # Right Label: G:H (width 16 + 13 = 29.0)
    ws1.merge_cells(f"G{idx}:H{idx}")
    ws1[f"G{idx}"] = l2
    ws1[f"G{idx}"].font = font_bold
    ws1[f"G{idx}"].alignment = Alignment(horizontal="left", vertical="center", indent=1)

    # Right Value: I:K (width 16 + 14 + 19 = 49.0)
    ws1.merge_cells(f"I{idx}:K{idx}")
    ws1[f"I{idx}"] = v2
    ws1[f"I{idx}"].font = font_reg
    ws1[f"I{idx}"].alignment = Alignment(horizontal="left", vertical="center")

    for c in range(1, 12):
        cell = ws1.cell(row=idx, column=c)
        cell.border = box_border
        if c in [1, 2, 7, 8]:
            cell.fill = fill_zebra

# Fix Row 14 height (Exec Summary Callout)
ws1.row_dimensions[14].height = 30

# Fix Table 1 Header Row 17 height
ws1.row_dimensions[17].height = 44

# Fix Table 2 Column widths & heights
# Col H: width 16.0 (fits $3/Stp + $21/Lnd)
ws1.column_dimensions['H'].width = 16.0
# Col K: width 19.5 (fits Available Per Hour)
ws1.column_dimensions['K'].width = 19.5
ws1.row_dimensions[32].height = 44

# Fix Table 3 Rows 48 to 54 heights (allow multi-line text to display without vertical clipping)
for r in range(48, 55):
    ws1.row_dimensions[r].height = 46

# Fix Photo Inspection Row 64 & 71 (Recommended service)
ws1.row_dimensions[64].height = 42
ws1.row_dimensions[71].height = 42

# -------------------------------------------------------------
# 2. FIX Service_Gantt_Schedule
# -------------------------------------------------------------
ws2 = wb["Service_Gantt_Schedule"]

# Fix Row 3 Meta Box
for rng in list(ws2.merged_cells.ranges):
    if rng.min_row <= 3 <= rng.max_row:
        ws2.unmerge_cells(str(rng))

ws2.row_dimensions[3].height = 18
ws2.merge_cells("A3:C3")
ws2["A3"] = "Base Dispatch:"
ws2["A3"].font = font_bold
ws2["A3"].alignment = Alignment(horizontal="center", vertical="center")

ws2.merge_cells("D3:H3")
ws2["D3"] = "Arlington, TX (Post-7:00 PM)"
ws2["D3"].font = font_reg
ws2["D3"].alignment = Alignment(horizontal="left", vertical="center")

ws2.merge_cells("I3:K3")
ws2["I3"] = "Project Start:"
ws2["I3"].font = font_bold
ws2["I3"].alignment = Alignment(horizontal="center", vertical="center")

ws2.merge_cells("L3:O3")
ws2["L3"] = "Sep 01, 2026"
ws2["L3"].font = font_bold
ws2["L3"].alignment = Alignment(horizontal="center", vertical="center")

ws2.merge_cells("P3:S3")
ws2["P3"] = "Assigned Crew:"
ws2["P3"].font = font_bold
ws2["P3"].alignment = Alignment(horizontal="center", vertical="center")

ws2.merge_cells("T3:X3")
ws2["T3"] = "2 Specialized Technicians"
ws2["T3"].font = font_reg
ws2["T3"].alignment = Alignment(horizontal="left", vertical="center")

ws2.merge_cells("Y3:AC3")
ws2["Y3"] = "Dedicated Mobilization:"
ws2["Y3"].font = font_bold
ws2["Y3"].alignment = Alignment(horizontal="center", vertical="center")

ws2.merge_cells("AD3:AG3")
ws2["AD3"] = "10 Dedicated Night Shifts"
ws2["AD3"].font = font_reg
ws2["AD3"].alignment = Alignment(horizontal="left", vertical="center")

ws2.merge_cells("AH3:AN3")
ws2["AH3"] = "⏰ 100% Flexible Shift Timing"
ws2["AH3"].font = Font(name="Calibri", size=8.5, bold=True, color="16A34A")
ws2["AH3"].alignment = Alignment(horizontal="center", vertical="center")

for c in range(1, 41):
    ws2.cell(row=3, column=c).border = box_border

# Expand Col D on Sheet 2 to 26.0 so "Dedicated Night 1 (3.5h)" never touches edges
ws2.column_dimensions['D'].width = 26.0

# Fix Footnote Row 21 wrap
ws2["A21"].alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
ws2.row_dimensions[21].height = 24

# -------------------------------------------------------------
# 3. FIX Cost_Underwriting_Audit
# -------------------------------------------------------------
ws3 = wb["Cost_Underwriting_Audit"]
ws3.column_dimensions['B'].width = 26.0
for rng in list(ws3.merged_cells.ranges):
    if rng.min_row <= 16 <= rng.max_row:
        ws3.unmerge_cells(str(rng))
ws3.merge_cells("A16:C16")
ws3["A16"] = "TOTAL PER QUARTERLY PASS (10 Dedicated Night Shifts)"
ws3["A16"].font = Font(name="Calibri", size=9.5, bold=True)
ws3["A16"].alignment = Alignment(horizontal="center", vertical="center")

wb.save("HWB-COMPANY/HWB-QUOTES/SUNDANCE-QUOTE-gantt.xlsx")
print("SUCCESS: Applied all zero-cutoff fixes to SUNDANCE-QUOTE-gantt.xlsx!")
