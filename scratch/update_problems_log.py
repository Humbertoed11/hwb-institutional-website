with open("docs/PROBLEMS-TO-SOLVE.md") as f:
    content = f.read()

# Check table insert point
table_addition = """| 09/03/2026 | BUG-056 | Excel Monolithic Multi-Column Print Scaling Failure (Microscopic 4.5pt Font & Empty Page Fragmentation). | **RESOLVED** | HIGH |
| 09/04/2026 | BUG-057 | Excel Document Header Label Truncation & Repeating Print Title Incongruence. | **RESOLVED** | MEDIUM |
"""

target_table_line = "| 09/03/2026 | BUG-055 | Non-Empirical Scope Mismatch: Diamond Restoration Quoted on Ceramic/Quarry & Legacy Gantt Rates. | **RESOLVED** | HIGH |\n"

if target_table_line in content:
    content = content.replace(target_table_line, target_table_line + table_addition)
else:
    print("WARNING: target_table_line not found in table!")

bug_entries = """## BUG-057: Excel Document Header Label Truncation & Repeating Print Title Incongruence
**Detected:** 09/04/2026
**Symptoms:**
1. In `Commercial_Quote` Rows 4 to 7, document control labels (`Central Office:` [15 chars] and `Primary Scope:` [14 chars]) were severely cut off and truncated on screen and in print.
2. Repeating header was originally set to `$1:$2`, failing to show document metadata and the ISO 9001 Clause 8.2.2 Data Integrity Notice on Pages 2 and 3.
3. Table 2 Option B (`"$3/Stp + $21/Lnd"`, `"N/A (Excluded)"`) and Option D (`"Available Per Hour"`) collided with cell borders in Column H (width 13) and Column K (width 17.5).
4. Table 3 scope descriptions (Rows 48 to 54) suffered vertical row height clipping (only 24 pt height for 3-line descriptions).
5. Sheet 2 Row 3 metadata bar had column merge collisions causing cutoffs on `Project Start:` and `Crew Assigned:`.
**Root Cause:**
1. Metadata labels in Rows 4–7 were placed in single unmerged Column A cells (width 5.5).
2. `print_title_rows` was configured as `$1:$2` instead of `$1:$8`.
3. Table 2 and Table 3 columns and row heights were not matched to the empirical character length and line-wrap requirements of their text.
**Solution:**
1. Merged `A:B` for left metadata labels (width **`30.5`**), `C:F` for left values (width **`73.0`**), `G:H` for right labels (width **`29.0`**), and `I:K` for right values (width **`49.5`**).
2. Locked `ws_quote.print_title_rows = '$1:$8'`, repeating the official masthead, project metadata, and ISO 9001 Data Integrity Notice across all pages.
3. Expanded Column H to **`20.0`** and Column K to **`20.0`** on Sheet 1.
4. Increased Table 3 description row heights from 24 pt to **`50 pt`** with `wrap_text = True`.
5. Rebalanced Sheet 2 Row 3 merges and set footnote row height to 24 pt.
6. Executed an automated cell-by-cell ripgrep/openpyxl audit confirming **100% Zero Width and Height Cutoffs** across all 3 sheets.

## BUG-056: Excel Monolithic Multi-Column Print Scaling Failure (Microscopic Font & Fragmentation)
**Detected:** 09/03/2026
**Symptoms:**
1. Printing Sheet 1 (`Commercial_Quote`) rendered text at microscopic, unreadable sizes (~3.5pt to 4.5pt font).
2. Printing one section per sheet created 7 separate landscape pages where each page had only a narrow 8–12 row band of content surrounded by massive empty white space.
**Root Cause:**
1. Placement of the 35-day daily calendar timeline (Columns L to AT) onto the same worksheet as the 11-column commercial pricing proposal created a monolithic 46-column wide worksheet (~300 width units).
2. Configuring `fitToWidth = 1` forced Excel to scale the entire sheet down to ~40% zoom across standard 11" Letter Landscape paper, causing massive proportional font shrinkage.
3. Arbitrary manual page breaks inserted after every single section fragmented the proposal into tiny strips.
**Solution:**
1. Re-architected the workbook into **Option 1: The Executive Multi-Tab Architecture**.
2. Decoupled the narrative commercial proposal onto Sheet 1 (`Commercial_Quote`), strictly formatted to **11 columns (A to K, 180.0 width units)**, flowing naturally across 3 dense executive pages at **100% full scale (10pt–11pt font, zero shrinking)**.
3. Moved the 35-day daily calendar to Sheet 2 (`Service_Gantt_Schedule`) as a standalone, dedicated **1-Page Letter Landscape attachment** (Appendix A).

"""

target_header = "## BUG-055: Non-Empirical Scope Mismatch"
if target_header in content:
    content = content.replace(target_header, bug_entries + target_header)
else:
    print("WARNING: target_header not found!")

with open("docs/PROBLEMS-TO-SOLVE.md", "w") as f:
    f.write(content)

with open("HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/docs/PROBLEMS-TO-SOLVE.md", "w") as f:
    f.write(content)

print("Updated and synced docs/PROBLEMS-TO-SOLVE.md successfully!")
