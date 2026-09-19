with open("scratch/build_option1_master.py") as f:
    code = f.read()

# Sheet 2 Row 3 rewrite
old_s2 = """    ws_gantt.row_dimensions[3].height = 18
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
    ws_gantt["AG3"] = "⏰ 100% Flexible Timing"
    ws_gantt["AG3"].font = Font(name="Calibri", size=8.5, bold=True, color="16A34A")
    ws_gantt["AG3"].alignment = align_center"""

new_s2 = """    ws_gantt.row_dimensions[3].height = 18
    ws_gantt.merge_cells("A3:B3")
    ws_gantt["A3"] = "Base Dispatch: Arlington, TX (Post-7:00 PM)"
    ws_gantt["A3"].font = font_bold
    ws_gantt["A3"].alignment = Alignment(horizontal="left", vertical="center", indent=1)

    ws_gantt.merge_cells("C3:D3")
    ws_gantt["C3"] = "Start: Sep 01, 2026"
    ws_gantt["C3"].font = font_bold
    ws_gantt["C3"].alignment = Alignment(horizontal="center", vertical="center")

    ws_gantt.merge_cells("E3:I3")
    ws_gantt["E3"] = "Crew: 2 Specialized Floor Technicians"
    ws_gantt["E3"].font = font_regular
    ws_gantt["E3"].alignment = Alignment(horizontal="left", vertical="center")

    ws_gantt.merge_cells("J3:O3")
    ws_gantt["J3"] = "Mobilization: 10 Dedicated Night Shifts"
    ws_gantt["J3"].font = font_regular
    ws_gantt["J3"].alignment = Alignment(horizontal="left", vertical="center")

    ws_gantt.merge_cells("P3:AN3")
    ws_gantt["P3"] = "⏰ 100% Flexible Shift Timing (Client Choice: Early Starts, Weekends, or Split Buildings at No Extra Cost)"
    ws_gantt["P3"].font = Font(name="Calibri", size=8.5, bold=True, color="16A34A")
    ws_gantt["P3"].alignment = Alignment(horizontal="center", vertical="center")"""

code = code.replace(old_s2, new_s2)

# Sheet 3 Row 16 wrap
old_s3 = """    tot_c_row = 16
    ws_cost.row_dimensions[tot_c_row].height = 20
    ws_cost.merge_cells("A{0}:B{0}".format(tot_c_row))
    ws_cost["A{0}".format(tot_c_row)] = "TOTAL PER QUARTERLY PASS (10 Dedicated Night Shifts)"
    ws_cost["A{0}".format(tot_c_row)].font = font_bold
    ws_cost["A{0}".format(tot_c_row)].alignment = align_center"""

new_s3 = """    tot_c_row = 16
    ws_cost.row_dimensions[tot_c_row].height = 28
    ws_cost.merge_cells("A{0}:B{0}".format(tot_c_row))
    ws_cost["A{0}".format(tot_c_row)] = "TOTAL PER QUARTERLY PASS\\n(10 Dedicated Night Shifts)"
    ws_cost["A{0}".format(tot_c_row)].font = font_bold
    ws_cost["A{0}".format(tot_c_row)].alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)"""

code = code.replace(old_s3, new_s3)

with open("scratch/build_option1_master.py", "w") as f:
    f.write(code)

print("Patched build_option1_master.py successfully!")
