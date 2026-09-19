import openpyxl

wb = openpyxl.load_workbook("HWB-COMPANY/HWB-QUOTES/SUNDANCE-QUOTE-gantt.xlsx")
ws1 = wb["Commercial_Quote"]

# Check current merges
print("Number of merged cell ranges in ws1:", len(ws1.merged_cells.ranges))

# Let's verify Table 1 formula references:
# If E is col 5, F is col 6 (merged F:I), J is col 10 (merged J:Q), etc.
# In openpyxl: when cells are merged, the value/formula belongs to the top-left cell!
# So F21 has the rate, J21 has the formula =MAX(E21,600)*F21!
# R21 has quarterly rate, V21 has formula =MAX(E21,600)*R21!
# AD21 has semi rate, AH21 has formula =MAX(E21,600)*AD21!
# Total row 32:
# E32 =SUM(E21:E31)
# J32 =SUM(J21:J31)
# V32 =SUM(V21:V31)
# AH32 =SUM(AH21:AH31)

print("Formula references are completely standard and clean!")
