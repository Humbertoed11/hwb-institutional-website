"""
SigmaFidelity™ Enterprise QMS Document Generator (Word & PDF)
Standard: ISO 9001:2015 & HWB-QMS-1.0 v2.0
Author: George (Systems Architect, mbB, Senior ISO 9001 Auditor)
Approved By: Humberto Dominguez, CEO
Purpose: Compiles publication-grade Word (.docx) and PDF (.pdf) editions of the
         Master Quality Management System Manual (HWB-QMS-MASTER v3.1.0).
"""

import os
import shutil
from datetime import datetime

# Docx generation
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

# PDF generation via ReportLab
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

HWB_QMS_DIR = "/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-QMS"
STATIC_QMS_DIR = "/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/static/qms"

DOCX_FILENAME = "HWB-QMS-MASTER-Quality-Management-System-Manual.docx"
PDF_FILENAME = "HWB-QMS-MASTER-Quality-Management-System-Manual.pdf"

NAVY_BLUE = RGBColor(0, 51, 102)
SLATE_GREY = RGBColor(71, 85, 105)
DARK_TEXT = RGBColor(15, 23, 42)

def set_cell_background(cell, fill_hex: str):
    """Applies background color shading to a docx table cell."""
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tc_pr.append(shd)

def set_cell_margins(cell, top=120, bottom=120, left=180, right=180):
    """Sets internal padding for docx table cell in twips."""
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
    tc_pr.append(tc_mar)

def generate_docx(output_path: str):
    """Compiles the Master QMS Manual into publication-grade Microsoft Word format."""
    doc = docx.Document()

    # Set page margins
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)
        
        # Header & Footer
        header = section.header
        hp = header.paragraphs[0]
        hp.text = "HWB CLEANING SERVICES LLC  |  QUALITY MANAGEMENT SYSTEM (ISO 9001:2015)"
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hp.runs[0].font.size = Pt(8)
        hp.runs[0].font.color.rgb = SLATE_GREY
        
        footer = section.footer
        fp = footer.paragraphs[0]
        fp.text = "HWB-QMS-MASTER v3.1.0  |  Controlled Document  |  Humberto Dominguez, CEO"
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        fp.runs[0].font.size = Pt(8)
        fp.runs[0].font.color.rgb = SLATE_GREY

    # Title Block
    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_before = Pt(0)
    title_p.paragraph_format.space_after = Pt(4)
    run_org = title_p.add_run("HWB CLEANING SERVICES LLC\n")
    run_org.font.size = Pt(12)
    run_org.font.bold = True
    run_org.font.color.rgb = NAVY_BLUE

    run_title = title_p.add_run("MASTER QUALITY MANAGEMENT SYSTEM (QMS) MANUAL")
    run_title.font.size = Pt(20)
    run_title.font.bold = True
    run_title.font.color.rgb = NAVY_BLUE

    sub_p = doc.add_paragraph()
    sub_p.paragraph_format.space_after = Pt(14)
    r_sub = sub_p.add_run("Standard: ISO 9001:2015  |  Everyday Words Standard (HWB-QMS-1.0 v2.0)")
    r_sub.font.size = Pt(10)
    r_sub.font.color.rgb = SLATE_GREY

    # Document Control Table
    table = doc.add_table(rows=8, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    doc_ctrl_data = [
        ("Document Title", "Master Quality Management System Manual"),
        ("Document ID", "HWB-QMS-MASTER"),
        ("Version", "3.1.0 (Enterprise Hardening & Sensitive PII Vault Protocol)"),
        ("Status", "APPROVED (100% ISO 9001:2015 Compliant)"),
        ("Author", "George, Systems Architect (mbB, Senior ISO 9001 Auditor)"),
        ("Approved By", "Humberto Dominguez, Chief Executive Officer"),
        ("Effective Date", "09/21/2026"),
        ("Governing Standard", "ISO 9001:2015 (Clauses 1.0 through 10.0)")
    ]

    for idx, (label, val) in enumerate(doc_ctrl_data):
        row = table.rows[idx]
        c0, c1 = row.cells[0], row.cells[1]
        c0.width = Inches(2.2)
        c1.width = Inches(4.6)
        set_cell_background(c0, "F1F5F9")
        set_cell_background(c1, "FFFFFF" if idx % 2 == 0 else "F8FAFC")
        set_cell_margins(c0)
        set_cell_margins(c1)

        p0 = c0.paragraphs[0]
        p0.paragraph_format.space_after = Pt(0)
        r0 = p0.add_run(label)
        r0.font.bold = True
        r0.font.size = Pt(9.5)
        r0.font.color.rgb = DARK_TEXT

        p1 = c1.paragraphs[0]
        p1.paragraph_format.space_after = Pt(0)
        r1 = p1.add_run(val)
        r1.font.size = Pt(9.5)
        r1.font.color.rgb = DARK_TEXT
        if label == "Status":
            r1.font.bold = True
            r1.font.color.rgb = RGBColor(22, 163, 74)

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # 1.0 Introduction
    h1 = doc.add_heading("1.0 Introduction & Company Overview", level=1)
    h1.runs[0].font.color.rgb = NAVY_BLUE
    p = doc.add_paragraph(
        "This Quality Management System Manual defines the operational policies, procedures, and quality standards for HWB Cleaning Services LLC. "
        "It serves as our official blueprint to ensure all commercial cleaning, post-construction sanitization, institutional facility services, "
        "and technology workflows meet the international requirements of ISO 9001:2015.\n\n"
        "HWB Cleaning Services LLC operates across Texas metropolitan areas, managing over 516,785 square feet of high-stakes public infrastructure, "
        "regional facilities, daycare centers, and corporate office environments. Every workflow is designed to ensure zero defects, protect worker safety, "
        "and deliver repeatable clinical quality."
    )
    p.paragraph_format.line_spacing = 1.15

    # 2.0 Universal Mandates
    h2 = doc.add_heading("2.0 Universal Mandates (2026 Baseline)", level=1)
    h2.runs[0].font.color.rgb = NAVY_BLUE
    mandates = [
        ("Physical Truth (Zero Synthetic Data): ", "All reports, telemetry, customer files, and audit logs must represent verified physical facts. Fabricated or placeholder data is strictly prohibited across all databases."),
        ("Everyday Words Standard (HWB-QMS-1.0 v2.0): ", "All customer-facing documents, technician work instructions, and backoffice manuals must use plain, clear language suitable for a 20-year-old reading level. Technical jargon is eliminated to prevent miscommunication."),
        ("Pre-Handover Empirical Verification: ", "All systems, code changes, and clean work areas must be tested and physically verified before turning over to clients or executive leadership."),
        ("Activity Tracking & Neural Persistence: ", "Every operational decision, friction log, and quality inspection must be logged to our central database for permanent traceability.")
    ]
    for bold_prefix, text in mandates:
        mp = doc.add_paragraph(style='List Bullet')
        r_b = mp.add_run(bold_prefix)
        r_b.bold = True
        mp.add_run(text)

    # 3.0 Terms & Definitions
    h3 = doc.add_heading("3.0 Terms & Definitions (Everyday Words)", level=1)
    h3.runs[0].font.color.rgb = NAVY_BLUE
    defs = [
        ("Quality Management System (QMS): ", "The organized collection of policies, procedures, and checks that ensure our cleaning services consistently satisfy clients and meet state standards."),
        ("Standard Operating Procedure (SOP): ", "Step-by-step written instructions that guide technicians to perform a routine task safely and with zero defects."),
        ("Corrective Action Request (CAR): ", "A formal investigation and fix triggered whenever a mistake, quality gap, or equipment breakdown occurs."),
        ("Non-Conformance: ", "Any service delivery, chemical use, or safety practice that fails to meet written specifications.")
    ]
    for b_pre, txt in defs:
        dp = doc.add_paragraph(style='List Bullet')
        dp.add_run(b_pre).bold = True
        dp.add_run(txt)

    # 4.0 Context of the Organization
    h4 = doc.add_heading("4.0 Context of the Organization (Clause 4)", level=1)
    h4.runs[0].font.color.rgb = NAVY_BLUE
    doc.add_paragraph(
        "HWB monitors external economic trends, regulatory updates from OSHA and the Texas Department of State Health Services (DSHS), and regional commercial construction pipelines. "
        "The QMS encompasses all commercial janitorial cleaning, institutional maintenance, construction final cleaning, specialized high-stakes sanitation, and digital backoffice operations conducted throughout Texas."
    )
    
    doc.add_heading("4.2 Interested Parties Matrix", level=2)
    tbl_parties = doc.add_table(rows=6, cols=3)
    tbl_parties.alignment = WD_TABLE_ALIGNMENT.CENTER
    party_headers = ["Interested Party", "Core Requirements", "How HWB Guarantees Compliance"]
    for c_idx, head in enumerate(party_headers):
        c = tbl_parties.rows[0].cells[c_idx]
        set_cell_background(c, "003366")
        set_cell_margins(c)
        hp = c.paragraphs[0]
        hr = hp.add_run(head)
        hr.bold = True
        hr.font.color.rgb = RGBColor(255, 255, 255)
        hr.font.size = Pt(9)

    party_rows = [
        ("Clients & Facility Directors", "Clean, sanitized, secure buildings; reliable schedules; prompt communication.", "Digital Work Orders, Scope of Work engines, supervisor sign-offs, <24h issue response."),
        ("Public Agencies (NTTA, Collin College)", "Strict badging, background checks, non-disclosure, certified safety plans.", "HWB-EHS-003 Institutional Safety Plan, daily sign-in sheets, badging verification."),
        ("Cleaning Technicians & Crew Leads", "Safe working conditions, proper PPE, clear instructions, fair compensation.", "Job Hazard Analyses (JHAs), chemical Safety Data Sheets (SDS), ergonomic training."),
        ("Regulators (OSHA, TCEQ, Texas DSHS)", "Workplace safety, chemical disposal compliance, hazard communication.", "HWB-EHS-001 Master Safety Manual, OSHA 300 logs, certified training records."),
        ("Chemical & Equipment Vendors", "Accurate purchasing specifications, safe handling, timely payments.", "Approved Vendor Registry, verified SDS sheets on file, standardized equipment use logs.")
    ]
    for r_idx, (p_name, p_req, p_comp) in enumerate(party_rows):
        row = tbl_parties.rows[r_idx + 1]
        for c_idx, val in enumerate([p_name, p_req, p_comp]):
            c = row.cells[c_idx]
            set_cell_background(c, "F8FAFC" if r_idx % 2 == 1 else "FFFFFF")
            set_cell_margins(c)
            cp = c.paragraphs[0]
            cr = cp.add_run(val)
            cr.font.size = Pt(8.5)
            if c_idx == 0:
                cr.bold = True

    # 5.0 Leadership & Governance
    h5 = doc.add_heading("5.0 Leadership & Governance (Clause 5)", level=1)
    h5.runs[0].font.color.rgb = NAVY_BLUE
    
    # Callout Box for Quality Policy
    q_box = doc.add_table(rows=1, cols=1)
    q_box.alignment = WD_TABLE_ALIGNMENT.CENTER
    q_cell = q_box.rows[0].cells[0]
    q_cell.width = Inches(6.8)
    set_cell_background(q_cell, "F1F5F9")
    set_cell_margins(q_cell, top=180, bottom=180, left=240, right=240)
    
    qp_p0 = q_cell.paragraphs[0]
    qp_r0 = qp_p0.add_run("OFFICIAL CORPORATE QUALITY POLICY STATEMENT (ISO 9001:2015 Clause 5.2)\n")
    qp_r0.bold = True
    qp_r0.font.size = Pt(11)
    qp_r0.font.color.rgb = NAVY_BLUE

    qp_p1 = q_cell.add_paragraph()
    qp_r1 = qp_p1.add_run(
        '"HWB Cleaning Services LLC is dedicated to providing flawless, verifiable commercial and institutional cleaning services that protect public health, safeguard physical infrastructure, and exceed client expectations. We achieve operational excellence by training disciplined technicians, enforcing strict safety controls, eliminating waste through Lean Six Sigma principles, and continually improving our Quality Management System."'
    )
    qp_r1.font.italic = True
    qp_r1.font.size = Pt(10)

    qp_p2 = q_cell.add_paragraph()
    qp_r2 = qp_p2.add_run("\nHumberto Dominguez\nChief Executive Officer, HWB Cleaning Services LLC\nApproved & Effective: September 21, 2026")
    qp_r2.bold = True
    qp_r2.font.size = Pt(9.5)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # 6.0 Planning & Risk Management
    h6 = doc.add_heading("6.0 Planning & Measurable Quality Objectives (Clause 6)", level=1)
    h6.runs[0].font.color.rgb = NAVY_BLUE
    doc.add_paragraph(
        "HWB applies ISO 31000 risk management guidelines to evaluate operational, commercial, and safety risks. "
        "Top management has established measurable quality targets for the 2026/2027 operational cycle:"
    )

    tbl_objs = doc.add_table(rows=6, cols=4)
    tbl_objs.alignment = WD_TABLE_ALIGNMENT.CENTER
    obj_headers = ["Quality Objective", "Target Metric", "Monitoring Method", "Responsible Lead"]
    for c_idx, head in enumerate(obj_headers):
        c = tbl_objs.rows[0].cells[c_idx]
        set_cell_background(c, "003366")
        set_cell_margins(c)
        hp = c.paragraphs[0]
        hr = hp.add_run(head)
        hr.bold = True
        hr.font.color.rgb = RGBColor(255, 255, 255)
        hr.font.size = Pt(9)

    obj_rows = [
        ("Workplace Safety", "0.00 TRIR (Zero injuries)", "Daily site JHAs & monthly safety audits", "Safety Manager"),
        ("Service Delivery Pass Rate", ">= 99.2% first-pass score", "Supervisor Inspection Checklists", "Operations Leads"),
        ("Client Issue Response Time", "< 24 Hours to resolution", "Backoffice Ticket Core", "CRM Specialist"),
        ("Corrective Action Closure", "100% closed in 14 days", "Monthly Friction Log Review", "Quality Manager (George)"),
        ("Document Integrity", "100% compliance; 0 outdated", "Automated Catalog Audits", "Systems Architect (George)")
    ]
    for r_idx, (o_name, o_targ, o_meth, o_lead) in enumerate(obj_rows):
        row = tbl_objs.rows[r_idx + 1]
        for c_idx, val in enumerate([o_name, o_targ, o_meth, o_lead]):
            c = row.cells[c_idx]
            set_cell_background(c, "F8FAFC" if r_idx % 2 == 1 else "FFFFFF")
            set_cell_margins(c)
            cp = c.paragraphs[0]
            cr = cp.add_run(val)
            cr.font.size = Pt(8.5)
            if c_idx in [0, 1]:
                cr.bold = True

    # 7.0 Support & Resources
    h7 = doc.add_heading("7.0 Support & Resources (Clause 7)", level=1)
    h7.runs[0].font.color.rgb = NAVY_BLUE
    doc.add_paragraph(
        "HWB maintains strict resource controls across technology, field equipment, chemicals, and personnel competence. "
        "Workforce intake is governed by standardized public intake validation (PROC-002 phone masking) and an automated Candidate Pool (ATS). "
        "All worker Personally Identifiable Information (SSN/ITIN, Direct Deposit Banking) is safeguarded by the Sensitive PII Vault Protocol "
        "(SEC-001: AES-256 Fernet column encryption, deterministic key derivation, ephemeral client-side reveal, and zero-plaintext API serialization, "
        "fulfilling Texas Bus. & Com. Code § 521.053 safe harbor standards). "
        "All procedures are maintained in HTML format following HWB-QMS-1.0 v2.0 standards, version-controlled, and stored in HWB-COMPANY/HWB-QMS/."
    )

    # 8.0 Operation & Service Delivery
    h8 = doc.add_heading("8.0 Operation & Service Delivery (Clause 8)", level=1)
    h8.runs[0].font.color.rgb = NAVY_BLUE
    doc.add_paragraph(
        "Service execution is governed by standardized Work Orders and blueprinted Scopes of Work managed in the Operations Hub (/admin/operations). "
        "Dispatching synchronizes field shifts, gate access codes, and sub-contractor allocations through the Bosanna Prime Contractor Cockpit. "
        "Field crews undergo badging, background checks, and weapon-free verification when servicing public agency facilities (NTTA Toll Operations, Collin College campuses). "
        "Technicians who fail compliance, background checks, or safety certifications are immediately barred from dispatch via the Automated Security Lockout Protocol. "
        "If a defect is identified, immediate re-cleaning is performed and tracked."
    )

    # 9.0 Performance Evaluation
    h9 = doc.add_heading("9.0 Performance Evaluation (Clause 9)", level=1)
    h9.runs[0].font.color.rgb = NAVY_BLUE
    doc.add_paragraph(
        "Performance is evaluated through supervisor walkthroughs, client feedback telemetry, quarterly internal audits led by George (mbB), "
        "and an annual Executive Management Review chaired by CEO Humberto Dominguez. "
        "Systemic integrity and data access are permanently recorded in the immutable GlobalActivities audit log. "
        "Disaster recovery and business continuity are strictly enforced under the Continuous Recovery Mandate (HWB-QMS-9.3) through Peter's 6 Recovery Directives, "
        "hourly database snapshots, and automated dependency validation."
    )

    # 10.0 Improvement & Corrective Action
    h10 = doc.add_heading("10.0 Continual Improvement & Corrective Action (Clause 10)", level=1)
    h10.runs[0].font.color.rgb = NAVY_BLUE
    doc.add_paragraph(
        "HWB employs the Plan-Do-Check-Act (PDCA) cycle to drive continual improvement. All operational frictions, equipment breakdowns, "
        "and customer inquiries are logged into PROBLEMS-TO-SOLVE.md and embedded into PostgreSQL vector storage to prevent recurrence."
    )

    # 11.0 Revision History Table
    h11 = doc.add_heading("11.0 Revision History", level=1)
    h11.runs[0].font.color.rgb = NAVY_BLUE
    tbl_rev = doc.add_table(rows=6, cols=4)
    tbl_rev.alignment = WD_TABLE_ALIGNMENT.CENTER
    rev_heads = ["Version", "Date", "Author", "Change Description"]
    for c_idx, head in enumerate(rev_heads):
        c = tbl_rev.rows[0].cells[c_idx]
        set_cell_background(c, "003366")
        set_cell_margins(c)
        hp = c.paragraphs[0]
        hr = hp.add_run(head)
        hr.bold = True
        hr.font.color.rgb = RGBColor(255, 255, 255)
        hr.font.size = Pt(9)

    rev_rows = [
        ("1.0.0", "02/21/2026", "Gemini", "Initial Markdown Release."),
        ("2.0.0", "06/23/2026", "George", "Modernized to HTML format, Everyday Words standard, and basic ISO 9001 alignment."),
        ("2.1.0", "07/24/2026", "George", "Added Everyday Words Mandate (no jargon) and Pre-Handover Verification rules."),
        ("3.0.0", "09/21/2026", "George (Systems Architect)", "Full 10-Clause ISO 9001:2015 Enterprise Expansion: added Interested Parties Matrix (4.2), formal signed Quality Policy (5.2), Measurable Quality Objectives (6.2), Support & Operation governance (7.0, 8.0), Performance Evaluation & Audit Calendar (9.0), and Appendix A SOP Matrix. Approved by Humberto Dominguez, CEO."),
        ("3.1.0", "09/21/2026", "George (Systems Architect)", "Integrated Sensitive PII Vault Protocol (SEC-001 AES-256 Fernet encryption, Texas Bus. & Com. Code § 521.053 safe harbor), ATS Candidate Pool, Operations Hub Dispatching, Bosanna Cockpit sync, and Continuous Disaster Recovery Mandate. Approved by Humberto Dominguez, CEO.")
    ]
    for r_idx, (v, d, a, desc) in enumerate(rev_rows):
        row = tbl_rev.rows[r_idx + 1]
        for c_idx, val in enumerate([v, d, a, desc]):
            c = row.cells[c_idx]
            set_cell_background(c, "F8FAFC" if r_idx % 2 == 1 else "FFFFFF")
            set_cell_margins(c)
            cp = c.paragraphs[0]
            cr = cp.add_run(val)
            cr.font.size = Pt(8.5)
            if c_idx == 0:
                cr.bold = True

    # Save docx
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc.save(output_path)
    print(f"[DOCX GENERATED] Successfully written to {output_path}")

class NumberedCanvas(canvas.Canvas):
    """Custom canvas that tracks and prints running header and dynamic total page numbers."""
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header_footer(num_pages)
            super(NumberedCanvas, self).showPage()
        super(NumberedCanvas, self).save()

    def draw_header_footer(self, page_count):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#475569"))
        
        # Running header (pages 2+)
        if self._pageNumber > 1:
            self.drawString(54, 750, "HWB CLEANING SERVICES LLC  |  QUALITY MANAGEMENT SYSTEM (ISO 9001:2015)")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(54, 742, 558, 742)

        # Running footer
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(54, 48, 558, 48)
        self.setFont("Helvetica", 8)
        self.drawString(54, 36, "HWB-QMS-MASTER v3.1.0 | Controlled Document | Approved: Humberto Dominguez, CEO")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 36, page_str)
        self.restoreState()

def generate_pdf(output_path: str):
    """Compiles the Master QMS Manual into high-fidelity standalone PDF format using ReportLab."""
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()
    
    style_org = ParagraphStyle(
        'OrgHeader',
        fontName='Helvetica-Bold',
        fontSize=11,
        textColor=colors.HexColor('#003366'),
        spaceAfter=2
    )
    style_title = ParagraphStyle(
        'DocTitle',
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#003366'),
        spaceAfter=4
    )
    style_sub = ParagraphStyle(
        'DocSub',
        fontName='Helvetica',
        fontSize=9,
        textColor=colors.HexColor('#64748B'),
        spaceAfter=12
    )
    style_h1 = ParagraphStyle(
        'Heading1_Custom',
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#003366'),
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )
    style_h2 = ParagraphStyle(
        'Heading2_Custom',
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor('#0F172A'),
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    )
    style_body = ParagraphStyle(
        'Body_Custom',
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#1E293B'),
        spaceAfter=6
    )
    style_policy = ParagraphStyle(
        'Policy_Custom',
        fontName='Helvetica-Oblique',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#0F172A')
    )
    style_tbl_cell = ParagraphStyle(
        'TblCell',
        fontName='Helvetica',
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor('#1E293B')
    )
    style_tbl_cell_bold = ParagraphStyle(
        'TblCellBold',
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor('#0F172A')
    )
    style_tbl_head = ParagraphStyle(
        'TblHead',
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10.5,
        textColor=colors.white
    )

    story = []

    # Title Banner
    story.append(Paragraph("HWB CLEANING SERVICES LLC", style_org))
    story.append(Paragraph("MASTER QUALITY MANAGEMENT SYSTEM (QMS) MANUAL", style_title))
    story.append(Paragraph("Standard: ISO 9001:2015  |  Everyday Words Standard (HWB-QMS-1.0 v2.0)", style_sub))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#003366'), spaceAfter=10))

    # Document Control Table
    ctrl_data = [
        [Paragraph("<b>Document Title</b>", style_tbl_cell), Paragraph("Master Quality Management System Manual", style_tbl_cell)],
        [Paragraph("<b>Document ID</b>", style_tbl_cell), Paragraph("HWB-QMS-MASTER", style_tbl_cell)],
        [Paragraph("<b>Version</b>", style_tbl_cell), Paragraph("3.1.0 (Enterprise Hardening & Sensitive PII Vault Protocol)", style_tbl_cell)],
        [Paragraph("<b>Status</b>", style_tbl_cell), Paragraph("<font color='#16a34a'><b>● APPROVED (100% ISO 9001:2015 Compliant)</b></font>", style_tbl_cell)],
        [Paragraph("<b>Author</b>", style_tbl_cell), Paragraph("George, Systems Architect (mbB, Senior ISO 9001 Auditor)", style_tbl_cell)],
        [Paragraph("<b>Approved By</b>", style_tbl_cell), Paragraph("Humberto Dominguez, Chief Executive Officer", style_tbl_cell)],
        [Paragraph("<b>Effective Date</b>", style_tbl_cell), Paragraph("09/21/2026", style_tbl_cell)],
        [Paragraph("<b>Governing Standard</b>", style_tbl_cell), Paragraph("ISO 9001:2015 (Clauses 1.0 through 10.0)", style_tbl_cell)],
    ]
    t_ctrl = Table(ctrl_data, colWidths=[130, 374])
    t_ctrl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F1F5F9')),
        ('BACKGROUND', (1, 0), (1, -1), colors.HexColor('#FFFFFF')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t_ctrl)
    story.append(Spacer(1, 12))

    # 1.0 Introduction
    story.append(Paragraph("1.0 Introduction & Company Overview", style_h1))
    story.append(Paragraph(
        "This Quality Management System Manual defines the operational policies, procedures, and quality standards for "
        "<b>HWB Cleaning Services LLC</b>. It serves as our official blueprint to ensure all commercial cleaning, post-construction "
        "sanitization, institutional facility services, and technology workflows meet the international requirements of <b>ISO 9001:2015</b>.<br/><br/>"
        "HWB Cleaning Services LLC operates across Texas metropolitan areas, managing over <b>516,785 square feet</b> of high-stakes public infrastructure, "
        "regional facilities, daycare centers, and corporate office environments. Every workflow is designed to ensure zero defects, protect worker safety, "
        "and deliver repeatable clinical quality.",
        style_body
    ))

    # 2.0 Universal Mandates
    story.append(Paragraph("2.0 Universal Mandates (2026 Baseline)", style_h1))
    story.append(Paragraph("• <b>Physical Truth (Zero Synthetic Data):</b> All reports, telemetry, customer files, and audit logs must represent verified physical facts. Fabricated or placeholder data is strictly prohibited across all databases.", style_body))
    story.append(Paragraph("• <b>Everyday Words Standard (HWB-QMS-1.0 v2.0):</b> All customer-facing documents, technician work instructions, and backoffice manuals must use plain, clear language suitable for a 20-year-old reading level.", style_body))
    story.append(Paragraph("• <b>Pre-Handover Empirical Verification:</b> All systems, code changes, and clean work areas must be tested and physically verified before turning over to clients or executive leadership.", style_body))
    story.append(Paragraph("• <b>Activity Tracking & Neural Persistence:</b> Every operational decision, friction log, and quality inspection must be logged to our central database for permanent traceability.", style_body))

    # 3.0 Terms & Definitions
    story.append(Paragraph("3.0 Terms & Definitions (Everyday Words)", style_h1))
    story.append(Paragraph("• <b>Quality Management System (QMS):</b> The organized collection of policies, procedures, and checks that ensure our cleaning services consistently satisfy clients and meet state standards.", style_body))
    story.append(Paragraph("• <b>Standard Operating Procedure (SOP):</b> Step-by-step written instructions that guide technicians to perform a routine task safely and with zero defects.", style_body))
    story.append(Paragraph("• <b>Corrective Action Request (CAR):</b> A formal investigation and fix triggered whenever a mistake, quality gap, or equipment breakdown occurs.", style_body))
    story.append(Paragraph("• <b>Non-Conformance:</b> Any service delivery, chemical use, or safety practice that fails to meet written specifications.", style_body))

    # 4.0 Context of Organization & Interested Parties Table
    story.append(Paragraph("4.0 Context of the Organization & Interested Parties (Clause 4)", style_h1))
    story.append(Paragraph("HWB monitors external economic trends, regulatory updates from OSHA and the Texas Department of State Health Services (DSHS), and regional commercial construction pipelines. The QMS encompasses all operations across Texas.", style_body))
    
    party_data = [
        [Paragraph("Interested Party", style_tbl_head), Paragraph("Core Requirements", style_tbl_head), Paragraph("How HWB Guarantees Compliance", style_tbl_head)],
        [Paragraph("Clients & Facility Directors", style_tbl_cell_bold), Paragraph("Clean, sanitized, secure buildings; reliable schedules; prompt communication.", style_tbl_cell), Paragraph("Digital Work Orders, Scope of Work engines, supervisor sign-offs, <24h issue response.", style_tbl_cell)],
        [Paragraph("Public Agencies (NTTA, Collin College)", style_tbl_cell_bold), Paragraph("Strict badging, background checks, non-disclosure, certified safety plans.", style_tbl_cell), Paragraph("HWB-EHS-003 Institutional Safety Plan, daily sign-in sheets, badging verification.", style_tbl_cell)],
        [Paragraph("Cleaning Technicians & Crew Leads", style_tbl_cell_bold), Paragraph("Safe working conditions, proper PPE, clear instructions, fair compensation.", style_tbl_cell), Paragraph("Job Hazard Analyses (JHAs), chemical Safety Data Sheets (SDS), ergonomic training.", style_tbl_cell)],
        [Paragraph("Regulators (OSHA, TCEQ, Texas DSHS)", style_tbl_cell_bold), Paragraph("Workplace safety, chemical disposal compliance, hazard communication.", style_tbl_cell), Paragraph("HWB-EHS-001 Master Safety Manual, OSHA 300 logs, certified training records.", style_tbl_cell)],
        [Paragraph("Chemical & Equipment Vendors", style_tbl_cell_bold), Paragraph("Accurate purchasing specifications, safe handling, timely payments.", style_tbl_cell), Paragraph("Approved Vendor Registry, verified SDS sheets on file, standardized equipment logs.", style_tbl_cell)],
    ]
    t_party = Table(party_data, colWidths=[120, 184, 200])
    t_party.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t_party)
    story.append(Spacer(1, 10))

    # 5.0 Leadership & Quality Policy
    story.append(Paragraph("5.0 Leadership & Governance (Clause 5)", style_h1))
    policy_content = [
        [Paragraph("<b>OFFICIAL CORPORATE QUALITY POLICY STATEMENT (ISO 9001:2015 Clause 5.2)</b>", style_tbl_cell_bold)],
        [Paragraph(
            '<i>"HWB Cleaning Services LLC is dedicated to providing flawless, verifiable commercial and institutional cleaning services that protect public health, safeguard physical infrastructure, and exceed client expectations. We achieve operational excellence by training disciplined technicians, enforcing strict safety controls, eliminating waste through Lean Six Sigma principles, and continually improving our Quality Management System."</i><br/><br/>'
            '<b>Humberto Dominguez</b><br/>Chief Executive Officer, HWB Cleaning Services LLC<br/>Approved & Effective: September 21, 2026',
            style_policy
        )]
    ]
    t_pol = Table(policy_content, colWidths=[504])
    t_pol.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F1F5F9')),
        ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor('#003366')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(t_pol)
    story.append(Spacer(1, 10))

    # 6.0 Planning & Objectives Table
    story.append(Paragraph("6.0 Planning & Measurable Quality Objectives (Clause 6)", style_h1))
    story.append(Paragraph("HWB applies ISO 31000 risk management guidelines. Top management enforces quantifiable quality targets:", style_body))
    
    obj_data = [
        [Paragraph("Quality Objective", style_tbl_head), Paragraph("Target Metric", style_tbl_head), Paragraph("Monitoring Method", style_tbl_head), Paragraph("Responsible Lead", style_tbl_head)],
        [Paragraph("Workplace Safety", style_tbl_cell_bold), Paragraph("<b>0.00 TRIR</b> (Zero injuries)", style_tbl_cell), Paragraph("Daily site JHAs & monthly audits", style_tbl_cell), Paragraph("Safety Manager", style_tbl_cell)],
        [Paragraph("Service Delivery Pass Rate", style_tbl_cell_bold), Paragraph("<b>&ge; 99.2%</b> first-pass score", style_tbl_cell), Paragraph("Supervisor Inspection Checklists", style_tbl_cell), Paragraph("Operations Leads", style_tbl_cell)],
        [Paragraph("Client Issue Response Time", style_tbl_cell_bold), Paragraph("<b>&lt; 24 Hours</b> to resolution", style_tbl_cell), Paragraph("Backoffice Ticket Core", style_tbl_cell), Paragraph("CRM Specialist", style_tbl_cell)],
        [Paragraph("Corrective Action Closure", style_tbl_cell_bold), Paragraph("<b>100%</b> closed in 14 days", style_tbl_cell), Paragraph("Monthly Friction Log Review", style_tbl_cell), Paragraph("Quality Manager", style_tbl_cell)],
        [Paragraph("Document Integrity", style_tbl_cell_bold), Paragraph("<b>100%</b> compliant; 0 outdated", style_tbl_cell), Paragraph("Automated Catalog Audits", style_tbl_cell), Paragraph("Systems Architect", style_tbl_cell)],
    ]
    t_obj = Table(obj_data, colWidths=[120, 114, 150, 120])
    t_obj.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t_obj)
    story.append(Spacer(1, 10))

    # 7.0 - 10.0 Overview
    story.append(Paragraph("7.0 Support, Operations, Evaluation & Continual Improvement", style_h1))
    story.append(Paragraph("• <b>Support (Clause 7):</b> Commercial equipment maintenance tracked on HWB-FORM-7.1-001. Public workforce intake is protected with PROC-002 phone masking. Candidate vetting and technician hiring are managed via the automated ATS Candidate Pool. Sensitive PII (SSN/ITIN, Direct Deposit Banking) is strictly encrypted under SEC-001 (AES-256 Fernet column encryption, deterministic key derivation, ephemeral 30-second audited reveal, and Texas Bus. & Com. Code § 521.053 safe harbor compliance).", style_body))
    story.append(Paragraph("• <b>Operation (Clause 8):</b> SOW engines and Operations Hub (/admin/operations) govern field delivery. Sub-contractor operations synchronize through the Bosanna Prime Contractor Cockpit. Badging, background checks, and Automated Security Lockout Protocol strictly enforce field access.", style_body))
    story.append(Paragraph("• <b>Performance Evaluation (Clause 9):</b> Quarterly internal audits led by George (Lead Auditor) across Operations, IT, EHSQ, and Governance. Annual Management Review chaired by CEO Humberto Dominguez. Data access and administrative mutations are immutably recorded in GlobalActivities audit logs. Continuous recovery is guaranteed via Peter's 6 Recovery Directives and hourly database backups.", style_body))
    story.append(Paragraph("• <b>Continual Improvement (Clause 10):</b> Plan-Do-Check-Act Lean Six Sigma model applied. Friction events logged to PROBLEMS-TO-SOLVE.md and embedded in PostgreSQL vector memory.", style_body))

    # 11.0 Revision History Table
    story.append(Paragraph("11.0 Revision History", style_h1))
    rev_data = [
        [Paragraph("Version", style_tbl_head), Paragraph("Date", style_tbl_head), Paragraph("Author", style_tbl_head), Paragraph("Change Description", style_tbl_head)],
        [Paragraph("1.0.0", style_tbl_cell_bold), Paragraph("02/21/2026", style_tbl_cell), Paragraph("Gemini", style_tbl_cell), Paragraph("Initial Markdown Release.", style_tbl_cell)],
        [Paragraph("2.0.0", style_tbl_cell_bold), Paragraph("06/23/2026", style_tbl_cell), Paragraph("George", style_tbl_cell), Paragraph("Modernized to HTML format, Everyday Words standard, basic ISO 9001 alignment.", style_tbl_cell)],
        [Paragraph("2.1.0", style_tbl_cell_bold), Paragraph("07/24/2026", style_tbl_cell), Paragraph("George", style_tbl_cell), Paragraph("Added Everyday Words Mandate and Pre-Handover Verification rules.", style_tbl_cell)],
        [Paragraph("3.0.0", style_tbl_cell_bold), Paragraph("09/21/2026", style_tbl_cell), Paragraph("George (mbB)", style_tbl_cell), Paragraph("Full 10-Clause ISO 9001:2015 Enterprise Expansion: Quality Policy (5.2), Interested Parties (4.2), Objectives (6.2), Audit Calendar (9.0). Approved by Humberto Dominguez, CEO.", style_tbl_cell)],
        [Paragraph("3.1.0", style_tbl_cell_bold), Paragraph("09/21/2026", style_tbl_cell), Paragraph("George (mbB)", style_tbl_cell), Paragraph("Integrated Sensitive PII Vault Protocol (SEC-001 AES-256 Fernet encryption, Texas Bus. & Com. Code § 521.053 safe harbor), ATS Candidate Pool, Operations Hub Dispatching, Bosanna Cockpit sync, and Continuous Disaster Recovery Mandate. Approved by Humberto Dominguez, CEO.", style_tbl_cell)],
    ]
    t_rev = Table(rev_data, colWidths=[50, 70, 84, 300])
    t_rev.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t_rev)

    # Build PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[PDF GENERATED] Successfully written to {output_path}")

def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] --- Starting QMS Master Document Generation ---")
    
    # Target file paths
    hwb_docx = os.path.join(HWB_QMS_DIR, DOCX_FILENAME)
    static_docx = os.path.join(STATIC_QMS_DIR, DOCX_FILENAME)
    
    hwb_pdf = os.path.join(HWB_QMS_DIR, PDF_FILENAME)
    static_pdf = os.path.join(STATIC_QMS_DIR, PDF_FILENAME)

    # 1. Generate Word Document (.docx)
    generate_docx(hwb_docx)
    shutil.copy2(hwb_docx, static_docx)
    print(f"[MIRRORED] Staged Word document in static/qms: {static_docx}")

    # 2. Generate PDF Document (.pdf)
    generate_pdf(hwb_pdf)
    shutil.copy2(hwb_pdf, static_pdf)
    print(f"[MIRRORED] Staged PDF document in static/qms: {static_pdf}")

    print("--- FULL QMS MASTER DOCUMENT GENERATION COMPLETE ---")

if __name__ == '__main__':
    main()
