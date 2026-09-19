import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

wb = openpyxl.load_workbook("HWB-COMPANY/HWB-QUOTES/SUNDANCE-QUOTE-gantt.xlsx")

# Modify Service_Gantt_Schedule to be a perfect 1-page landscape sheet
if "Service_Gantt_Schedule" in wb.sheetnames:
    del wb["Service_Gantt_Schedule"]

ws_gantt = wb.create_sheet(title="Service_Gantt_Schedule", index=1)
ws_gantt.views.sheetView[0].showGridLines = True

# Styling
font_title = Font(name="Calibri", size=13, bold=True, color="FFFFFF")
font_sub = Font(name="Calibri", size=9.5, bold=True, color="93C5FD")
font_sec = Font(name="Calibri", size=9, bold=True, color="0F172A")
font_hdr = Font(name="Calibri", size=8.5, bold=True, color="FFFFFF")
font_bold = Font(name="Calibri", size=8.5, bold=True, color="0F172A")
font_reg = Font(name="Calibri", size=8.5, color="334155")
font_badge = Font(name="Calibri", size=7, bold=True, color="FFFFFF")

fill_navy = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
fill_blue = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
fill_subtle = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
fill_zebra = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
fill_weekend = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")

fill_deep = PatternFill(start_color="16A34A", end_color="16A34A", fill_type="solid") # Forest Green
fill_seal = PatternFill(start_color="0284C7", end_color="0284C7", fill_type="solid") # Deep Cyan
fill_qtr = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")  # Blue
fill_stair = PatternFill(start_color="B45309", end_color="B45309", fill_type="solid")# Amber

align_c = Alignment(horizontal="center", vertical="center")
align_l = Alignment(horizontal="left", vertical="center")
align_r = Alignment(horizontal="right", vertical="center")
align_wrap = Alignment(horizontal="center", vertical="center", wrap_text=True)

thin_side = Side(style="thin", color="CBD5E1")
border_box = Border(top=thin_side, bottom=thin_side, left=thin_side, right=thin_side)
border_tot = Border(top=Side(style="thin", color="0F172A"), bottom=Side(style="double", color="0F172A"), left=thin_side, right=thin_side)

# Total columns: A to AN (1 to 40)
# Row 1: Title
ws_gantt.merge_cells("A1:AN1")
ws_gantt["A1"] = "HWB CLEANING SERVICES LLC"
ws_gantt["A1"].font = font_title
ws_gantt["A1"].fill = fill_navy
ws_gantt["A1"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
ws_gantt.row_dimensions[1].height = 22

# Row 2: Subtitle
ws_gantt.merge_cells("A2:AN2")
ws_gantt["A2"] = "OPERATIONAL DISPATCH GANTT SCHEDULE — DOWNTOWN FORT WORTH 11-BUILDING PORTFOLIO"
ws_gantt["A2"].font = font_sub
ws_gantt["A2"].fill = fill_navy
ws_gantt["A2"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
ws_gantt.row_dimensions[2].height = 16

# Row 3: Metadata Info
ws_gantt.row_dimensions[3].height = 18
ws_gantt.merge_cells("A3:B3")
ws_gantt["A3"] = "Base Dispatch:"
ws_gantt["A3"].font = font_bold
ws_gantt["A3"].alignment = align_l

ws_gantt.merge_cells("C3:E3")
ws_gantt["C3"] = "Arlington, TX (Post-7:00 PM)"
ws_gantt["C3"].font = font_reg
ws_gantt["C3"].alignment = align_l

ws_gantt.merge_cells("F3:H3")
ws_gantt["F3"] = "Project Start:"
ws_gantt["F3"].font = font_bold
ws_gantt["F3"].alignment = align_l

ws_gantt.merge_cells("I3:L3")
import datetime
ws_gantt["I3"] = datetime.date(2026, 9, 1)
ws_gantt["I3"].number_format = "yyyy-mm-dd"
ws_gantt["I3"].font = font_bold
ws_gantt["I3"].alignment = align_l

ws_gantt.merge_cells("M3:P3")
ws_gantt["M3"] = "Assigned Crew:"
ws_gantt["M3"].font = font_bold
ws_gantt["M3"].alignment = align_l

ws_gantt.merge_cells("Q3:U3")
ws_gantt["Q3"] = "2 Specialized Technicians"
ws_gantt["Q3"].font = font_reg
ws_gantt["Q3"].alignment = align_l

ws_gantt.merge_cells("V3:Z3")
ws_gantt["V3"] = "Dedicated Mobilization:"
ws_gantt["V3"].font = font_bold
ws_gantt["V3"].alignment = align_l

ws_gantt.merge_cells("AA3:AF3")
ws_gantt["AA3"] = "10 Dedicated Night Shifts"
ws_gantt["AA3"].font = font_reg
ws_gantt["AA3"].alignment = align_l

ws_gantt.merge_cells("AG3:AN3")
ws_gantt["AG3"] = "⏰ 100% Flexible Shift Timing"
ws_gantt["AG3"].font = Font(name="Calibri", size=8.5, bold=True, color="16A34A")
ws_gantt["AG3"].alignment = align_c

for c in range(1, 41):
    ws_gantt.cell(row=3, column=c).border = border_box

# Row 4: Legend Bar
ws_gantt.row_dimensions[4].height = 18
ws_gantt.merge_cells("A4:E4")
ws_gantt["A4"] = "LEGEND & COLOR CODES:"
ws_gantt["A4"].font = font_bold
ws_gantt["A4"].fill = fill_subtle
ws_gantt["A4"].alignment = align_c

legend_items = [
    ("F4:L4", "DP: Phase 1 Deep Clean", fill_deep),
    ("M4:S4", "SL: Modular Sealer", fill_seal),
    ("T4:Z4", "QT: Quarterly Care", fill_qtr),
    ("AA4:AG4", "ST: Stair Detailing", fill_stair),
    ("AH4:AN4", "WKND: Building Offline", PatternFill(start_color="CBD5E1", end_color="CBD5E1", fill_type="solid"))
]
for crange, ltext, lfill in legend_items:
    ws_gantt.merge_cells(crange)
    c_top = ws_gantt[crange.split(":")[0]]
    c_top.value = ltext
    c_top.font = font_badge
    c_top.fill = lfill
    c_top.alignment = align_c
    c_start = openpyxl.utils.column_index_from_string(crange.split(":")[0][:1] if len(crange.split(":")[0])==2 else crange.split(":")[0][:2])
    c_end = openpyxl.utils.column_index_from_string(crange.split(":")[1][:1] if len(crange.split(":")[1])==2 else crange.split(":")[1][:2])
    for col_i in range(c_start, c_end + 1):
        ws_gantt.cell(row=4, column=col_i).border = border_box
        ws_gantt.cell(row=4, column=col_i).fill = lfill

for c in range(1, 6):
    ws_gantt.cell(row=4, column=c).border = border_box

# Rows 5–7: 3-Tier Table Headers
ws_gantt.row_dimensions[5].height = 18
ws_gantt.row_dimensions[6].height = 15
ws_gantt.row_dimensions[7].height = 15

headers_left = [
    ("A", "Item"),
    ("B", "Building Name"),
    ("C", "Total SQF"),
    ("D", "Shift Window"),
    ("E", "Crew Hrs")
]
for col_let, htext in headers_left:
    ws_gantt.merge_cells(f"{col_let}5:{col_let}7")
    c_h = ws_gantt[f"{col_let}5"]
    c_h.value = htext
    c_h.font = font_hdr
    c_h.fill = fill_navy
    c_h.alignment = align_wrap
    for r in range(5, 8):
        ws_gantt[f"{col_let}{r}"].border = border_box
        ws_gantt[f"{col_let}{r}"].fill = fill_navy

# Week Blocks (Cols F to AN: 6 to 40)
weeks = [
    ("F5:L5", 6, 12, "Week 1 (Aug 31–Sep 06)"),
    ("M5:S5", 13, 19, "Week 2 (Sep 07–Sep 13)"),
    ("T5:Z5", 20, 26, "Week 3 (Sep 14–Sep 20)"),
    ("AA5:AG5", 27, 33, "Week 4 (Sep 21–Sep 27)"),
    ("AH5:AN5", 34, 40, "Week 5 (Sep 28–Oct 04)")
]
for wrange, start_c, end_c, wtitle in weeks:
    ws_gantt.merge_cells(wrange)
    c_w = ws_gantt[wrange.split(":")[0]]
    c_w.value = wtitle
    c_w.font = font_hdr
    c_w.fill = fill_blue
    c_w.alignment = align_c
    for c in range(start_c, end_c + 1):
        ws_gantt.cell(row=5, column=c).border = border_box
        ws_gantt.cell(row=5, column=c).fill = fill_blue

days_dates = [31] + list(range(1, 31)) + list(range(1, 5))
days_names = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'] * 5

for d_idx, d_num in enumerate(days_dates):
    col = 6 + d_idx
    c_num = ws_gantt.cell(row=6, column=col, value=d_num)
    c_num.font = Font(name="Calibri", size=8, bold=True, color="FFFFFF")
    c_num.fill = fill_navy
    c_num.alignment = align_c
    c_num.border = border_box

for d_idx, d_name in enumerate(days_names):
    col = 6 + d_idx
    c_nam = ws_gantt.cell(row=7, column=col, value=d_name)
    is_w = d_name in ['Sa', 'Su']
    c_nam.fill = PatternFill(start_color="475569", end_color="475569", fill_type="solid") if is_w else PatternFill(start_color="334155", end_color="334155", fill_type="solid")
    c_nam.font = Font(name="Calibri", size=7.5, bold=True, color="FFFFFF" if is_w else "94A3B8")
    c_nam.alignment = align_c
    c_nam.border = border_box

# Data Rows 8 to 18 (11 Buildings)
schedule_data = [
    (1, "Chase Bank Building", 2126, "Night 1 (3.5h)", 3.5, [7], [11], [21], []),
    (2, "The Westbrook", 1520, "Night 2 (3.0h)", 3.0, [8], [11], [22], []),
    (3, "The Carnegie", 1175, "Night 3 (2.8h)", 2.8, [9], [11], [23], []),
    (4, "The Cassidy", 1134, "Night 4 (2.6h)", 2.6, [10], [11], [24], []),
    (5, "Burk Burnett Building", 1108, "Night 5 (2.6h)", 2.6, [13], [18], [27], [28]),
    (6, "Sanger Lofts", 1071, "Night 6 (2.5h)", 2.5, [14], [18], [28], []),
    (7, "Petroleum Building", 860, "Night 7 (2.2h)", 2.2, [15], [18], [29], []),
    (8, "The Commerce Building", 840, "Night 8 (2.2h)", 2.2, [16], [18], [30], []),
    (9, "Virtuoso Building", 560, "Night 9 (1.8h)", 1.8, [17], [18], [31], []),
    (10, "Knights of Pythias Hall", 414, "Night 9 (1.6h)", 1.6, [17], [18], [31], []),
    (11, "Plaza Hotel Building", 345, "Night 10 (1.5h)", 1.5, [20], [21], [34], [])
]

for b_idx, item in enumerate(schedule_data, start=8):
    num, name, sf, window, crew_time, p1_cols, seal_cols, rec_cols, stair_cols = item
    ws_gantt.row_dimensions[b_idx].height = 16

    c1 = ws_gantt.cell(row=b_idx, column=1, value=num)
    c1.alignment = align_c
    c1.font = font_reg

    c2 = ws_gantt.cell(row=b_idx, column=2, value=name)
    c2.alignment = align_l
    c2.font = font_bold

    c3 = ws_gantt.cell(row=b_idx, column=3, value=sf)
    c3.alignment = align_c
    c3.font = font_bold
    c3.number_format = "#,##0"

    c4 = ws_gantt.cell(row=b_idx, column=4, value=window)
    c4.alignment = align_l
    c4.font = font_reg

    c5 = ws_gantt.cell(row=b_idx, column=5, value=crew_time)
    c5.alignment = align_c
    c5.font = font_reg
    c5.number_format = '0.0 "h"'

    for c in range(1, 6):
        ws_gantt.cell(row=b_idx, column=c).border = border_box
        if b_idx % 2 == 1:
            ws_gantt.cell(row=b_idx, column=c).fill = fill_zebra

    # Days (Cols 6 to 40)
    for day_i in range(1, 36):
        col = day_i + 5
        cell = ws_gantt.cell(row=b_idx, column=col)
        cell.border = border_box

        if col in p1_cols:
            cell.fill = fill_deep
            cell.value = "DP"
            cell.font = font_badge
            cell.alignment = align_c
        elif col in seal_cols:
            cell.fill = fill_seal
            cell.value = "SL"
            cell.font = font_badge
            cell.alignment = align_c
        elif col in rec_cols:
            cell.fill = fill_qtr
            cell.value = "QT"
            cell.font = font_badge
            cell.alignment = align_c
        elif col in stair_cols:
            cell.fill = fill_stair
            cell.value = "ST"
            cell.font = font_badge
            cell.alignment = align_c
        elif (col - 6) % 7 in [5, 6]:
            cell.fill = fill_weekend

# Row 19: Total Row
tot_r = 19
ws_gantt.row_dimensions[tot_r].height = 18
ws_gantt.merge_cells("A19:B19")
ws_gantt["A19"] = "TOTAL PORTFOLIO DISPATCH"
ws_gantt["A19"].font = font_bold
ws_gantt["A19"].alignment = align_c

c_tsf = ws_gantt.cell(row=tot_r, column=3, value="=SUM(C8:C18)")
c_tsf.font = font_bold
c_tsf.number_format = '#,##0 " SQF"'
c_tsf.alignment = align_c

c_tsh = ws_gantt.cell(row=tot_r, column=4, value="10 Dedicated Shifts")
c_tsh.font = font_bold
c_tsh.alignment = align_c

c_thrs = ws_gantt.cell(row=tot_r, column=5, value="=SUM(E8:E18)")
c_thrs.font = font_bold
c_thrs.number_format = '0.0 "hrs total"'
c_thrs.alignment = align_c

for c in range(1, 6):
    ws_gantt.cell(row=tot_r, column=c).border = border_tot
    ws_gantt.cell(row=tot_r, column=c).fill = fill_subtle

for c in range(6, 41):
    cell = ws_gantt.cell(row=tot_r, column=c)
    cell.border = border_tot
    cell.fill = fill_subtle

# Row 20: Blank spacer
ws_gantt.row_dimensions[20].height = 6

# Row 21: Footnote
ws_gantt.merge_cells("A21:AN21")
ws_gantt["A21"] = "*Note: Shift timing and scheduled calendar dates are 100% flexible based on client preference. HWB will adapt dispatch hours (earlier start, late night, or weekend windows) to accommodate building security and tenant schedules at no additional cost."
ws_gantt["A21"].font = Font(name="Calibri", size=8, italic=True, color="475569")
ws_gantt["A21"].alignment = align_l
ws_gantt.row_dimensions[21].height = 16

# Set exact column widths (Total Width = 153.5 units)
ws_gantt.column_dimensions['A'].width = 4.0
ws_gantt.column_dimensions['B'].width = 20.0
ws_gantt.column_dimensions['C'].width = 10.0
ws_gantt.column_dimensions['D'].width = 13.5
ws_gantt.column_dimensions['E'].width = 8.0

for col_idx in range(6, 41):
    col_let = get_column_letter(col_idx)
    ws_gantt.column_dimensions[col_let].width = 2.8

# Strict 1-Page Landscape Print Setup
ws_gantt.page_setup.orientation = ws_gantt.ORIENTATION_LANDSCAPE
ws_gantt.page_setup.paperSize = ws_gantt.PAPERSIZE_LETTER
ws_gantt.sheet_properties.pageSetUpPr.fitToPage = True
ws_gantt.page_setup.fitToWidth = 1
ws_gantt.page_setup.fitToHeight = 1

ws_gantt.page_margins.left = 0.25
ws_gantt.page_margins.right = 0.25
ws_gantt.page_margins.top = 0.35
ws_gantt.page_margins.bottom = 0.35
ws_gantt.page_margins.header = 0.2
ws_gantt.page_margins.footer = 0.2

ws_gantt.print_area = 'A1:AN21'

ws_gantt.oddHeader.center.text = "&B&10HWB CLEANING SERVICES LLC"
ws_gantt.evenHeader.center.text = "&B&10HWB CLEANING SERVICES LLC"
ws_gantt.oddFooter.right.text = "Page &P of &N"
ws_gantt.evenFooter.right.text = "Page &P of &N"

wb.save("HWB-COMPANY/HWB-QUOTES/SUNDANCE-QUOTE-gantt.xlsx")
print("SUCCESS: Master workbook updated with 1-page formatted Service_Gantt_Schedule!")
