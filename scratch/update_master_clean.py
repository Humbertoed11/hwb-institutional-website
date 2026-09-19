with open("scratch/build_option1_master.py") as f:
    code = f.read()

# 1. Replace rows 4-7 meta loop in Sheet 1
old_meta_loop = '''    for idx, (lbl1, val1, lbl2, val2) in enumerate(meta_info, start=4):
        ws_quote.row_dimensions[idx].height = 16
        ws_quote["A{0}".format(idx)] = lbl1
        ws_quote["A{0}".format(idx)].font = font_bold
        ws_quote["A{0}".format(idx)].alignment = align_left

        ws_quote.merge_cells("B{0}:E{0}".format(idx))
        ws_quote["B{0}".format(idx)] = val1
        ws_quote["B{0}".format(idx)].font = font_regular
        ws_quote["B{0}".format(idx)].alignment = align_left

        ws_quote.cell(row=idx, column=6).value = "" # spacer Col F

        ws_quote.merge_cells("G{0}:H{0}".format(idx))
        ws_quote["G{0}".format(idx)] = lbl2
        ws_quote["G{0}".format(idx)].font = font_bold
        ws_quote["G{0}".format(idx)].alignment = align_left

        ws_quote.merge_cells("I{0}:K{0}".format(idx))
        ws_quote["I{0}".format(idx)] = val2
        ws_quote["I{0}".format(idx)].font = font_regular
        ws_quote["I{0}".format(idx)].alignment = align_left

        for c in range(1, 12):
            cell = ws_quote.cell(row=idx, column=c)
            cell.border = box_border
            if c in [1, 7, 8]:
                cell.fill = fill_zebra'''

new_meta_loop = '''    for idx, (lbl1, val1, lbl2, val2) in enumerate(meta_info, start=4):
        ws_quote.row_dimensions[idx].height = 18
        ws_quote.merge_cells("A{0}:B{0}".format(idx))
        ws_quote["A{0}".format(idx)] = lbl1
        ws_quote["A{0}".format(idx)].font = font_bold
        ws_quote["A{0}".format(idx)].alignment = Alignment(horizontal="left", vertical="center", indent=1)

        ws_quote.merge_cells("C{0}:F{0}".format(idx))
        ws_quote["C{0}".format(idx)] = val1
        ws_quote["C{0}".format(idx)].font = font_regular
        ws_quote["C{0}".format(idx)].alignment = Alignment(horizontal="left", vertical="center")

        ws_quote.merge_cells("G{0}:H{0}".format(idx))
        ws_quote["G{0}".format(idx)] = lbl2
        ws_quote["G{0}".format(idx)].font = font_bold
        ws_quote["G{0}".format(idx)].alignment = Alignment(horizontal="left", vertical="center", indent=1)

        ws_quote.merge_cells("I{0}:K{0}".format(idx))
        ws_quote["I{0}".format(idx)] = val2
        ws_quote["I{0}".format(idx)].font = font_regular
        ws_quote["I{0}".format(idx)].alignment = Alignment(horizontal="left", vertical="center")

        for c in range(1, 12):
            cell = ws_quote.cell(row=idx, column=c)
            cell.border = box_border
            if c in [1, 2, 7, 8]:
                cell.fill = fill_zebra'''

code = code.replace(old_meta_loop, new_meta_loop)

# 2. Fix $3.00/Stp + $21/Lnd in summary_rows
code = code.replace('"$3.00/Stp + $21/Lnd"', '"$3/Stp + $21/Lnd"')

# 3. Fix Row 3 in Sheet 2
old_s2_row3 = '''    ws_gantt.row_dimensions[3].height = 18
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
    ws_gantt["AG3"].alignment = align_center'''

new_s2_row3 = '''    ws_gantt.row_dimensions[3].height = 18
    ws_gantt.merge_cells("A3:C3")
    ws_gantt["A3"] = "Base Dispatch:"
    ws_gantt["A3"].font = font_bold
    ws_gantt["A3"].alignment = Alignment(horizontal="center", vertical="center")

    ws_gantt.merge_cells("D3:G3")
    ws_gantt["D3"] = "Arlington, TX (Post-7:00 PM)"
    ws_gantt["D3"].font = font_regular
    ws_gantt["D3"].alignment = Alignment(horizontal="left", vertical="center")

    ws_gantt.merge_cells("H3:J3")
    ws_gantt["H3"] = "Start Date:"
    ws_gantt["H3"].font = font_bold
    ws_gantt["H3"].alignment = Alignment(horizontal="center", vertical="center")

    ws_gantt.merge_cells("K3:N3")
    ws_gantt["K3"] = "Sep 01, 2026"
    ws_gantt["K3"].font = font_bold
    ws_gantt["K3"].alignment = Alignment(horizontal="center", vertical="center")

    ws_gantt.merge_cells("O3:R3")
    ws_gantt["O3"] = "Assigned Crew:"
    ws_gantt["O3"].font = font_bold
    ws_gantt["O3"].alignment = Alignment(horizontal="center", vertical="center")

    ws_gantt.merge_cells("S3:X3")
    ws_gantt["S3"] = "2 Specialized Technicians"
    ws_gantt["S3"].font = font_regular
    ws_gantt["S3"].alignment = Alignment(horizontal="left", vertical="center")

    ws_gantt.merge_cells("Y3:AC3")
    ws_gantt["Y3"] = "Mobilization:"
    ws_gantt["Y3"].font = font_bold
    ws_gantt["Y3"].alignment = Alignment(horizontal="center", vertical="center")

    ws_gantt.merge_cells("AD3:AH3")
    ws_gantt["AD3"] = "10 Dedicated Shifts"
    ws_gantt["AD3"].font = font_regular
    ws_gantt["AD3"].alignment = Alignment(horizontal="left", vertical="center")

    ws_gantt.merge_cells("AI3:AN3")
    ws_gantt["AI3"] = "⏰ 100% Flexible Timing"
    ws_gantt["AI3"].font = Font(name="Calibri", size=8.5, bold=True, color="16A34A")
    ws_gantt["AI3"].alignment = Alignment(horizontal="center", vertical="center")'''

code = code.replace(old_s2_row3, new_s2_row3)

# 4. Fix Sheet 2 Row 21 wrap
code = code.replace(
    'ws_gantt["A21"].alignment = align_left',
    'ws_gantt["A21"].alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)'
)
code = code.replace(
    'ws_gantt.row_dimensions[21].height = 16',
    'ws_gantt.row_dimensions[21].height = 24'
)

# 5. Fix Sheet 1 Column widths:
code = code.replace('7: 16.0,  # Phase 1 deep clean', '7: 18.0,  # Phase 1 deep clean')
code = code.replace('8: 13.0,  # Quarterly Rate', '8: 18.0,  # Quarterly Rate & Option B')
code = code.replace('11: 17.5  # Track B: Semi-Annual', '11: 19.5  # Track B: Semi-Annual & Option D')

with open("scratch/build_option1_master.py", "w") as f:
    f.write(code)

print("Updated scratch/build_option1_master.py successfully!")
