import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.pagebreak import Break
import shutil

wb_path = "HWB-COMPANY/HWB-QUOTES/BOSANNA-COLLIN-COLLEGE/COLLIN-COLLEGE-FRISCO-BID-MODEL.xlsx"
wb = openpyxl.load_workbook(wb_path)

# Colors & Visual Hierarchy
navy_dark = "0F172A"
navy_blue = "1E3A8A"
soft_blue = "DBEAFE"
light_blue = "EFF6FF"
gold_amber = "D97706"
light_amber = "FEF3C7"
bg_gray = "F8FAFC"
border_gray = "CBD5E1"
border_amber = "F59E0B"
card_border_blue = "3B82F6"

# Typographic Standards
font_title = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
font_subtitle = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
font_sec_hdr = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
font_tbl_hdr = Font(name="Calibri", size=10, bold=True, color="1E3A8A")
font_kpi_label = Font(name="Calibri", size=9, bold=True, color="1E3A8A")
font_kpi_val = Font(name="Calibri", size=13, bold=True, color="0F172A")
font_kpi_sub = Font(name="Calibri", size=8.5, italic=True, color="475569")
font_bold = Font(name="Calibri", size=9.5, bold=True, color="0F172A")
font_regular = Font(name="Calibri", size=9.5, color="1E293B")
font_italic = Font(name="Calibri", size=9.5, italic=True, color="334155")
font_alert_text = Font(name="Calibri", size=9.5, bold=True, color="92400E")

fill_navy_title = PatternFill(start_color=navy_dark, end_color=navy_dark, fill_type="solid")
fill_navy_sub = PatternFill(start_color="334155", end_color="334155", fill_type="solid")
fill_sec_hdr = PatternFill(start_color=navy_blue, end_color=navy_blue, fill_type="solid")
fill_tbl_hdr = PatternFill(start_color=soft_blue, end_color=soft_blue, fill_type="solid")
fill_kpi_card = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
fill_kpi_highlight = PatternFill(start_color="E0E7FF", end_color="E0E7FF", fill_type="solid")
fill_amber_sub = PatternFill(start_color=light_amber, end_color=light_amber, fill_type="solid")
fill_soft_blue_banner = PatternFill(start_color=light_blue, end_color=light_blue, fill_type="solid")

thin_border = Border(
    left=Side(style="thin", color=border_gray),
    right=Side(style="thin", color=border_gray),
    top=Side(style="thin", color=border_gray),
    bottom=Side(style="thin", color=border_gray)
)

card_border = Border(
    left=Side(style="medium", color=card_border_blue),
    right=Side(style="medium", color=card_border_blue),
    top=Side(style="medium", color=card_border_blue),
    bottom=Side(style="medium", color=card_border_blue)
)

# -------------------------------------------------------------
# CREATE OR REPLACE EMPLOYEE_TRAINING_MATRIX SHEET AT INDEX 3
# -------------------------------------------------------------
sheet_name = "Employee_Training_Matrix"
if sheet_name in wb.sheetnames:
    wb.remove(wb[sheet_name])

# Insert after Service_Gantt_Schedule (Index 3)
target_idx = 3 if len(wb.sheetnames) >= 3 else len(wb.sheetnames)
ws = wb.create_sheet(sheet_name, target_idx)
ws.views.sheetView[0].showGridLines = True

# Title Block
ws.cell(row=1, column=1, value="HWB CLEANING SERVICES LLC & BOSANNA LLC — MANDATORY EMPLOYEE TRAINING MATRIX")
ws.merge_cells("A1:H1")
ws.cell(row=1, column=1).font = font_title
ws.cell(row=1, column=1).fill = fill_navy_title
ws.cell(row=1, column=1).alignment = Alignment(horizontal="center", vertical="center", wrap_text=False)
ws.row_dimensions[1].height = 30.0

ws.cell(row=2, column=1, value="COLLIN COLLEGE FRISCO CAMPUS — STATUTORY SAFETY, SECURITY, TECHNICAL & APPA LEVEL 2 CERTIFICATIONS")
ws.merge_cells("A2:H2")
ws.cell(row=2, column=1).font = font_subtitle
ws.cell(row=2, column=1).fill = fill_navy_sub
ws.cell(row=2, column=1).alignment = Alignment(horizontal="center", vertical="center", wrap_text=False)
ws.row_dimensions[2].height = 24.0

# Spacer Row 3
ws.row_dimensions[3].height = 12.0
ws.merge_cells("A3:H3")
ws.cell(row=3, column=1, value="")

# Project Metadata Block
meta = [
    ("Client / Prime Contractor:", "Bosanna LLC (Attn: Angelica Hudgins)", "School / Project Name:", "Collin College Frisco Campus Custodial Replacement"),
    ("Training Compliance Mandate:", "District Custodial T&C § 130–140 & Frisco SOW § 181", "Governing Safety Authorities:", "OSHA, EPA, Texas DSHS, TxDPS & Texas Education Code"),
    ("Mandatory Onboarding Window:", "Within Seven (7) Days of Hire (Before Unsupervised Work)", "Annual Refresher Standard:", "100% Annual Re-Certification for All Active Personnel"),
    ("Covered Campus Workforce:", "28.0 FTEs (29–32 Badged Cleaners, Techs & Shift Leads)", "Compliance Verification:", "Signed Roster & Digital Certificates Filed with District Facilities")
]

for idx, (k1, v1, k2, v2) in enumerate(meta, start=4):
    ws.cell(row=idx, column=1, value=k1).font = font_bold
    ws.cell(row=idx, column=1).alignment = Alignment(horizontal="left", vertical="center", indent=1, wrap_text=True)
    ws.cell(row=idx, column=1).border = thin_border
    
    ws.cell(row=idx, column=2, value=v1).font = font_regular
    ws.cell(row=idx, column=2).alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    ws.merge_cells(start_row=idx, start_column=2, end_row=idx, end_column=4)
    for c in range(2, 5):
        ws.cell(row=idx, column=c).border = thin_border

    ws.cell(row=idx, column=5, value=k2).font = font_bold
    ws.cell(row=idx, column=5).alignment = Alignment(horizontal="left", vertical="center", indent=1, wrap_text=True)
    ws.cell(row=idx, column=5).border = thin_border
    
    ws.cell(row=idx, column=6, value=v2).font = font_regular
    ws.cell(row=idx, column=6).alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    ws.merge_cells(start_row=idx, start_column=6, end_row=idx, end_column=8)
    for c in range(6, 9):
        ws.cell(row=idx, column=c).border = thin_border
    ws.row_dimensions[idx].height = 22.0

# Spacer Row 8
ws.row_dimensions[8].height = 14.0
ws.merge_cells("A8:H8")
ws.cell(row=8, column=1, value="")

# -------------------------------------------------------------
# EXECUTIVE KPI SUMMARY CARDS (ROWS 9 TO 11)
# -------------------------------------------------------------
kpis = [
    (1, 2, "TOTAL CERTIFIED MODULES", "15 Mandatory Courses", "Safety, Security, Chemical & APPA Level 2", fill_kpi_card),
    (3, 4, "NEW HIRE ONBOARDING", "Within 7 Days of Hire", "Mandatory Before Unsupervised Floor Work", fill_kpi_card),
    (5, 6, "SUPERVISOR REQUIREMENT", "First Aid, CPR & AED", "Mandatory for Shift Supervisors (T&C § 140)", fill_kpi_highlight),
    (7, 8, "DISTRICT AUDIT STANDARD", "100% Verified Records", "Certificates Submitted to Facilities Staff", fill_kpi_card)
]

ws.row_dimensions[9].height = 20.0
ws.row_dimensions[10].height = 32.0
ws.row_dimensions[11].height = 24.0

for c_start, c_end, label, val, subtext, fill_type in kpis:
    # Label Row
    ws.cell(row=9, column=c_start, value=label).font = font_kpi_label
    ws.merge_cells(start_row=9, start_column=c_start, end_row=9, end_column=c_end)
    ws.cell(row=9, column=c_start).alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    
    # Value Row (Big Font)
    ws.cell(row=10, column=c_start, value=val).font = font_kpi_val
    ws.merge_cells(start_row=10, start_column=c_start, end_row=10, end_column=c_end)
    ws.cell(row=10, column=c_start).alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    
    # Subtext Row
    ws.cell(row=11, column=c_start, value=subtext).font = font_kpi_sub
    ws.merge_cells(start_row=11, start_column=c_start, end_row=11, end_column=c_end)
    ws.cell(row=11, column=c_start).alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    
    # Borders & Fills
    for r in range(9, 12):
        for c in range(c_start, c_end + 1):
            cl = ws.cell(row=r, column=c)
            cl.fill = fill_type
            top_b = Side(style="medium", color=card_border_blue) if r == 9 else Side(style="thin", color=border_gray)
            bot_b = Side(style="medium", color=card_border_blue) if r == 11 else Side(style="thin", color=border_gray)
            left_b = Side(style="medium", color=card_border_blue) if c == c_start else Side(style="thin", color=border_gray)
            right_b = Side(style="medium", color=card_border_blue) if c == c_end else Side(style="thin", color=border_gray)
            cl.border = Border(top=top_b, bottom=bot_b, left=left_b, right=right_b)

# Spacer Row 12
ws.row_dimensions[12].height = 14.0
ws.merge_cells("A12:H12")
ws.cell(row=12, column=1, value="")

# -------------------------------------------------------------
# SECTION 1.0: MANDATORY OSHA & SAFETY COMPLIANCE TRAINING
# -------------------------------------------------------------
ws.cell(row=13, column=1, value="1.0 MANDATORY OSHA & SAFETY COMPLIANCE TRAINING (DISTRICT T&C § 130–140)")
ws.merge_cells("A13:H13")
ws.cell(row=13, column=1).font = font_sec_hdr
ws.cell(row=13, column=1).fill = fill_sec_hdr
ws.cell(row=13, column=1).alignment = Alignment(horizontal="left", vertical="center", indent=1, wrap_text=True)
ws.row_dimensions[13].height = 28.0

sec1_desc = (
    "Safety training is contractually mandatory under Collin College Special Terms & Conditions Section 130–140. Every new cleaning employee "
    "must complete this curriculum within seven (7) days of hire, followed by annual refreshers. All non-cleaning supervisors must maintain "
    "active First Aid, CPR, and AED emergency certifications prior to commencing on-site duties."
)
ws.cell(row=14, column=1, value=sec1_desc)
ws.merge_cells("A14:H14")
ws.cell(row=14, column=1).font = font_italic
ws.cell(row=14, column=1).fill = fill_soft_blue_banner
ws.cell(row=14, column=1).alignment = Alignment(vertical="center", wrap_text=True)
ws.row_dimensions[14].height = 44.0

tbl_headers = [
    (1, "Module ID"),
    (2, "Training Course Title"),
    (3, "Required Job Roles"),
    (4, "Completion Timeline"),
    (5, "Contract & Legal Rule"),
    (6, "Training Content & Core Competencies"),
    (7, "Verification & Testing"),
    (8, "Compliance Proof & Deliverable")
]

def render_table_headers(row_num):
    for col_idx, h in tbl_headers:
        c = ws.cell(row=row_num, column=col_idx, value=h)
        c.font = font_tbl_hdr
        c.fill = fill_tbl_hdr
        c.border = thin_border
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[row_num].height = 28.0

render_table_headers(15)

tbl1_data = [
    ("TRN-SAF-01", "Safe Work Habits & Ergonomic Injury Prevention", "All Cleaners, Porters, Techs & Supervisors", "Within 7 Days / Annual", "T&C § 132 & SOW § 127", "Proper lifting of loads >30 lbs, safe ladder use, bending/squatting posture, slip/trip prevention, three points of contact on stairs", "Practical Lifting & Ladder Demonstration", "Signed Attendance Roster & Safety Logbook"),
    ("TRN-SAF-02", "Chemical Safety & Closed-Loop Dilution Systems", "All Cleaners, Porters, Techs & Supervisors", "Within 7 Days / Annual", "T&C § 133, 136 & OSHA 1910.1200", "OSHA Hazard Communication (HazCom), reading GHS pictograms, automatic proportioner calibration, PPE requirements, secondary container labeling", "Written Quiz (100% Pass) & Proportioner Audit", "Safety Data Sheet (SDS) Binder Sign-Off"),
    ("TRN-SAF-03", "Bloodborne Pathogens & Bodily Fluid Protocol", "All Cleaners, Porters, Techs & Supervisors", "Within 7 Days / Annual", "T&C § 137, 139 & OSHA 1910.1030", "Exposure control plan, universal precautions, bodily fluid spill kits, biohazard red bags, disinfectant contact times (10-min dwell), sharps safety", "Practical Spill Simulation & PPE Don/Doff Exam", "Texas DSHS Bloodborne Pathogen Certificate"),
    ("TRN-SAF-04", "Restroom Barrier Protection & Safety Signage", "All Day Porters & Restroom Cleaners", "Within 7 Days / Annual", "T&C § 134 & SOW § 197", "Mandatory placement of 'Closed for Cleaning' tension poles across restroom doorways; wet floor caution cones; prohibition of propping doors open with trash cans", "On-Site Barrier Setup Verification", "Field Supervisor Inspection Sign-Off"),
    ("TRN-SAF-05", "Hazardous & Prohibited Materials Recognition", "All Cleaners, Porters, Techs & Supervisors", "Within 7 Days / Annual", "T&C § 135", "Recognizing hazardous waste, asbestos tiles, biohazard lab chemicals not covered by contract; reporting protocols for suspicious or dangerous spills", "Visual Hazard Identification Quiz", "Hazard Recognition Acknowledgment Form"),
    ("TRN-SAF-06", "First Aid, Adult CPR & AED Certification", "All Non-Cleaning Supervisors & Shift Leads", "Before On-Site Placement / Biennial", "T&C § 140", "American Red Cross / AHA certified First Aid, CPR, and automated external defibrillator (AED) operation for campus medical emergencies", "AHA / Red Cross Certified Practical Skills Exam", "Official AHA / Red Cross First Aid & AED Card")
]

row_heights_t1 = [42.0, 44.0, 44.0, 42.0, 42.0, 42.0]

for idx, (r_data, h_val) in enumerate(zip(tbl1_data, row_heights_t1), start=16):
    ws.row_dimensions[idx].height = h_val
    for c_idx, val in enumerate(r_data, start=1):
        cell = ws.cell(row=idx, column=c_idx, value=val)
        cell.border = thin_border
        cell.font = font_regular
        if c_idx == 1:
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.font = font_bold
        elif c_idx == 2:
            cell.alignment = Alignment(horizontal="left", vertical="center", indent=1, wrap_text=True)
            cell.font = font_bold
        elif c_idx in [3, 4, 5]:
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        elif c_idx == 6:
            cell.alignment = Alignment(horizontal="left", vertical="center", indent=1, wrap_text=True)
        elif c_idx in [7, 8]:
            cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

# Banner Row 22
b1_text = (
    "⚠️ MANDATORY FIRST AID CLAUSE (T&C § 140): Collin College mandates that all non-cleaning supervisors have active First Aid certification. "
    "No shift leader may supervise campus cleaning without current First Aid, CPR, and AED credentials on file with District Facilities Operations."
)
ws.cell(row=22, column=1, value=b1_text)
ws.merge_cells("A22:H22")
ws.cell(row=22, column=1).font = font_alert_text
ws.cell(row=22, column=1).fill = fill_amber_sub
ws.cell(row=22, column=1).alignment = Alignment(vertical="center", indent=1, wrap_text=True)
for c in range(1, 9):
    ws.cell(row=22, column=c).border = Border(
        top=Side(style="thin", color=border_amber),
        bottom=Side(style="thin", color=border_amber),
        left=Side(style="thin", color=border_amber),
        right=Side(style="thin", color=border_amber)
    )
ws.row_dimensions[22].height = 46.0

# Spacer Row 23
ws.row_dimensions[23].height = 14.0
ws.merge_cells("A23:H23")
ws.cell(row=23, column=1, value="")

# -------------------------------------------------------------
# SECTION 2.0: CAMPUS SECURITY, KEY CONTROL & LEGAL POLICIES
# -------------------------------------------------------------
ws.cell(row=24, column=1, value="2.0 CAMPUS SECURITY, KEY CONTROL & LEGAL COMPLIANCE (DISTRICT T&C § 142–152)")
ws.merge_cells("A24:H24")
ws.cell(row=24, column=1).font = font_sec_hdr
ws.cell(row=24, column=1).fill = fill_sec_hdr
ws.cell(row=24, column=1).alignment = Alignment(horizontal="left", vertical="center", indent=1, wrap_text=True)
ws.row_dimensions[24].height = 28.0

sec2_desc = (
    "Security compliance is strictly enforced under Collin College Special Terms & Conditions Section 142–152. All custodial staff must complete "
    "training in master key custody, electronic access cards, biometric fingerprint verification, and strict zero-tolerance policies regarding weapons, "
    "drugs, alcohol, tobacco, and unauthorized campus visitors."
)
ws.cell(row=25, column=1, value=sec2_desc)
ws.merge_cells("A25:H25")
ws.cell(row=25, column=1).font = font_italic
ws.cell(row=25, column=1).fill = fill_soft_blue_banner
ws.cell(row=25, column=1).alignment = Alignment(vertical="center", wrap_text=True)
ws.row_dimensions[25].height = 44.0

render_table_headers(26)

tbl2_data = [
    ("TRN-SEC-01", "Zero-Tolerance Weapons & Substance-Free Campus", "All Cleaners, Porters, Techs & Supervisors", "Day 1 Orientation / Annual", "T&C § 143, 144 & 151", "Strict ban on firearms, knives, or dangerous weapons on campus; alcohol and illegal drug prohibition; 100% tobacco-free and vape-free campus policy (including parking lots)", "Signed Drug & Weapons Policy Acknowledgment", "Signed District Security Acknowledgment"),
    ("TRN-SEC-02", "Master Key Control & Electronic Access Protocols", "All Shift Supervisors & Day Porters", "Day 1 Orientation / Semi-Annual", "T&C § 145–149", "Key ring management; zero key duplication; keys never left in doors or on janitor carts; locking all exterior doors before leaving; $100 penalty per lost key; daily police desk key return", "Key Control Protocol Walkthrough & Audit", "Daily Key Log Sheet Signed at Police Desk"),
    ("TRN-SEC-03", "Biometric Fingerprint Clock & Police Desk Sign-In", "All Cleaners, Porters, Techs & Supervisors", "Day 1 Orientation / Refresher", "SOW § 202 & T&C § 150", "Mandatory dual time-recording: scanning fingerprint at Building S biometric clock at shift start/end, plus signing the official paper attendance roster at the Collin College Police desk", "Live Biometric Punch & Signature Verification", "Monthly Biometric Audit Report for Invoicing"),
    ("TRN-SEC-04", "Non-Employee Campus Access & Family Ban Policy", "All Cleaners, Porters, Techs & Supervisors", "Day 1 Orientation / Annual", "T&C § 152", "Strict prohibition of family members, children, friends, or non-badged individuals accompanying workers on campus during shifts; unauthorized visitors grounds for immediate removal", "Signed Non-Employee Policy Form", "HR File Security Acknowledgment Document"),
    ("TRN-SEC-05", "Uniform Standards, Photo Badging & Student Protection", "All Cleaners, Porters, Techs & Supervisors", "Day 1 Orientation / Annual", "T&C § 178 & Texas Ed Code § 22.0834", "Wearing clean company uniform with visible embroidered logo; displaying Collin College photo ID badge at all times; maintaining professional student/faculty boundaries; zero fraternization", "Visual Uniform & Badge Inspection on Shift", "FAST DPS/FBI Fingerprint Clearance Record")
]

row_heights_t2 = [42.0, 44.0, 42.0, 42.0, 42.0]

for idx, (r_data, h_val) in enumerate(zip(tbl2_data, row_heights_t2), start=27):
    ws.row_dimensions[idx].height = h_val
    for c_idx, val in enumerate(r_data, start=1):
        cell = ws.cell(row=idx, column=c_idx, value=val)
        cell.border = thin_border
        cell.font = font_regular
        if c_idx == 1:
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.font = font_bold
        elif c_idx == 2:
            cell.alignment = Alignment(horizontal="left", vertical="center", indent=1, wrap_text=True)
            cell.font = font_bold
        elif c_idx in [3, 4, 5]:
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        elif c_idx == 6:
            cell.alignment = Alignment(horizontal="left", vertical="center", indent=1, wrap_text=True)
        elif c_idx in [7, 8]:
            cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

# Banner Row 32
b2_text = (
    "🔒 ZERO-TOLERANCE KEY & ACCESS SECURITY: Leaving keys in doors or failing to lock exterior doors creates immediate campus safety risks. "
    "Any unreturned key triggers an automatic $100.00 contractual penalty and re-keying liability per District T&C § 149."
)
ws.cell(row=32, column=1, value=b2_text)
ws.merge_cells("A32:H32")
ws.cell(row=32, column=1).font = font_alert_text
ws.cell(row=32, column=1).fill = fill_amber_sub
ws.cell(row=32, column=1).alignment = Alignment(vertical="center", indent=1, wrap_text=True)
for c in range(1, 9):
    ws.cell(row=32, column=c).border = Border(
        top=Side(style="thin", color=border_amber),
        bottom=Side(style="thin", color=border_amber),
        left=Side(style="thin", color=border_amber),
        right=Side(style="thin", color=border_amber)
    )
ws.row_dimensions[32].height = 46.0

# Spacer Row 33
ws.row_dimensions[33].height = 14.0
ws.merge_cells("A33:H33")
ws.cell(row=33, column=1, value="")

# -------------------------------------------------------------
# SECTION 3.0: TECHNICAL CLEANING & APPA LEVEL 2 STANDARDS
# -------------------------------------------------------------
ws.cell(row=34, column=1, value="3.0 TECHNICAL CLEANING, EQUIPMENT OPERATION & APPA LEVEL 2 STANDARDS (SOW § 2–126 & § 182–205)")
ws.merge_cells("A34:H34")
ws.cell(row=34, column=1).font = font_sec_hdr
ws.cell(row=34, column=1).fill = fill_sec_hdr
ws.cell(row=34, column=1).alignment = Alignment(horizontal="left", vertical="center", indent=1, wrap_text=True)
ws.row_dimensions[34].height = 28.0

sec3_desc = (
    "Technical excellence ensures Collin College maintains APPA Level 2 'Ordinary Tidiness' every morning. Staff are certified in color-coded "
    "microfiber sanitization, heavy machinery operation, deep floor stripping and waxing, and the mandatory 20-minute rapid deficiency correction protocol."
)
ws.cell(row=35, column=1, value=sec3_desc)
ws.merge_cells("A35:H35")
ws.cell(row=35, column=1).font = font_italic
ws.cell(row=35, column=1).fill = fill_soft_blue_banner
ws.cell(row=35, column=1).alignment = Alignment(vertical="center", wrap_text=True)
ws.row_dimensions[35].height = 44.0

render_table_headers(36)

tbl3_data = [
    ("TRN-TEC-01", "APPA Level 2 Standards & 20-Minute Correction Protocol", "All Cleaners, Porters, Techs & Supervisors", "Within 14 Days / Quarterly", "SOW § 2, 20 & T&C § 159", "APPA Level 2 visual inspection rubric: spotless washrooms, stain-free surfaces, dust-free corners; 20-minute rapid response to customer complaints before 2-hour District clawbacks apply", "Mock Inspection Audit Across 10 Buildings", "Weekly APPA Level 2 Digitized QA Inspection Form"),
    ("TRN-TEC-02", "Restroom Sanitization & Microfiber Color-Coding", "All Day Porters & Restroom Cleaners", "Within 7 Days / Semi-Annual", "SOW Appendix A", "Color-coded microfiber cross-contamination system (Red: Toilets/Urinals; Yellow: Sinks/Counters; Blue: Mirrors/Glass); dual-chamber mop buckets; disinfectant dwell times; dispenser refills", "Fluorescent Marking Gel Restroom Inspection", "Daily Restroom Restocking & Cleaning Checklist"),
    ("TRN-TEC-03", "Commercial Machinery Operation & Preventative Care", "Floor Technicians & Machine Operators", "Before Operating / Annual", "SOW § 182–205", "Operating 20\" walk-behind scrubbers, 28\" riding auto-scrubbers, 2000 RPM burnishers, commercial HEPA backpack vacuums, carpet extractors; daily cleanout, pad centering, cord/battery care", "Hands-On Machinery Driving & Safety Test", "HWB Machine Operator Certification Card"),
    ("TRN-TEC-04", "Deep Floor Care: Strip-and-Wax & Carpet Extraction", "Dedicated Night Floor Technicians", "Before Floor Projects / Semi-Annual", "SOW § 46–47, 76", "Proper floor stripper dilution, baseboard edging, wet vacuum recovery, neutralizing rinse, 4-coat high-solid acrylic wax application; HOST dry carpet extraction and spot treatment", "Gloss Meter Reflectivity Test (Minimum 80 Gloss)", "Project Sign-Off Sheet Signed by District Staff")
]

row_heights_t3 = [44.0, 44.0, 44.0, 44.0]

for idx, (r_data, h_val) in enumerate(zip(tbl3_data, row_heights_t3), start=37):
    ws.row_dimensions[idx].height = h_val
    for c_idx, val in enumerate(r_data, start=1):
        cell = ws.cell(row=idx, column=c_idx, value=val)
        cell.border = thin_border
        cell.font = font_regular
        if c_idx == 1:
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.font = font_bold
        elif c_idx == 2:
            cell.alignment = Alignment(horizontal="left", vertical="center", indent=1, wrap_text=True)
            cell.font = font_bold
        elif c_idx in [3, 4, 5]:
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        elif c_idx == 6:
            cell.alignment = Alignment(horizontal="left", vertical="center", indent=1, wrap_text=True)
        elif c_idx in [7, 8]:
            cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

# Banner Row 41
b3_text = (
    "🎓 TRAINING RECORD RETENTION: Complete digital training logs, employee signatures, and practical test scores must be maintained "
    "in the central custodial staging office (Building S) and submitted to Collin College Facilities Operations upon request per SOW § 181."
)
ws.cell(row=41, column=1, value=b3_text)
ws.merge_cells("A41:H41")
ws.cell(row=41, column=1).font = font_alert_text
ws.cell(row=41, column=1).fill = fill_amber_sub
ws.cell(row=41, column=1).alignment = Alignment(vertical="center", indent=1, wrap_text=True)
for c in range(1, 9):
    ws.cell(row=41, column=c).border = Border(
        top=Side(style="thin", color=border_amber),
        bottom=Side(style="thin", color=border_amber),
        left=Side(style="thin", color=border_amber),
        right=Side(style="thin", color=border_amber)
    )
ws.row_dimensions[41].height = 46.0

# Spacer Row 42
ws.row_dimensions[42].height = 14.0
ws.merge_cells("A42:H42")
ws.cell(row=42, column=1, value="")

# Banner Row 43 (Final Executive Commitment)
b4_text = (
    "🤝 INSTITUTIONAL QUALITY COMMITMENT: Every cleaner and technician on Collin College Frisco Campus completes 100% of these mandatory "
    "modules before working unsupervised. This guarantees a safe campus, zero OSHA violations, verified security compliance, and an immaculate APPA Level 2 learning environment for students and faculty every single day."
)
ws.cell(row=43, column=1, value=b4_text)
ws.merge_cells("A43:H43")
ws.cell(row=43, column=1).font = font_alert_text
ws.cell(row=43, column=1).fill = fill_amber_sub
ws.cell(row=43, column=1).alignment = Alignment(vertical="center", indent=1, wrap_text=True)
for c in range(1, 9):
    ws.cell(row=43, column=c).border = Border(
        top=Side(style="thin", color=border_amber),
        bottom=Side(style="thin", color=border_amber),
        left=Side(style="thin", color=border_amber),
        right=Side(style="thin", color=border_amber)
    )
ws.row_dimensions[43].height = 48.0

# -------------------------------------------------------------
# COLUMN WIDTHS & PRINT CONFIGURATION
# -------------------------------------------------------------
col_widths = {
    "A": 16.0,
    "B": 28.0,
    "C": 24.0,
    "D": 20.0,
    "E": 22.0,
    "F": 46.0,
    "G": 24.0,
    "H": 36.0
}
for c_let, w in col_widths.items():
    ws.column_dimensions[c_let].width = w

ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
ws.page_setup.paperSize = ws.PAPERSIZE_LETTER
ws.sheet_properties.pageSetUpPr.fitToPage = True
ws.page_setup.fitToWidth = 1
ws.page_setup.fitToHeight = 0

ws.page_margins.left = 0.25
ws.page_margins.right = 0.25
ws.page_margins.top = 0.35
ws.page_margins.bottom = 0.35
ws.page_margins.header = 0.15
ws.page_margins.footer = 0.15

ws.print_options.horizontalCentered = True
ws.print_area = "A1:H43"
ws.print_title_rows = "1:8"

# Page breaks for 3 crisp landscape pages
ws.row_breaks.append(Break(id=23))
ws.row_breaks.append(Break(id=33))

# Save master workbook and mirror to web static directory
wb.save(wb_path)
shutil.copyfile(wb_path, "HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/static/proposals/COLLIN-COLLEGE-FRISCO-BID-MODEL.xlsx")
print("Employee_Training_Matrix worksheet successfully created and integrated at Sheet Index 3!")
