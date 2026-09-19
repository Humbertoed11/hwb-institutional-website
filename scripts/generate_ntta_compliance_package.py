#!/usr/bin/env python3
"""
generate_ntta_compliance_package.py
===================================
Generates the complete, pre-filled, official compliance documents for:
North Texas Tollway Authority (NTTA)
Request for Bids (RFB) 06507-NTT-00-GS-MA
Janitorial Services for Ancillary Facilities

Target Files:
1. NTTA-06507-Service-Dispatch-Location-Form.pdf
2. NTTA-06507-Business-Information-Form.pdf
3. NTTA-06507-COI-Confidentiality-Agreement.pdf
4. NTTA-06507-Form-CIQ-Conflict-of-Interest.pdf
5. NTTA-06507-BDOD-Subcontractor-Plan-GFE.pdf
6. NTTA-06507-MANDATORY-COMPLIANCE-PACKAGE-UNIFIED.pdf
"""

import os
import fitz  # PyMuPDF

SRC_PDF = "HWB-COMPANY/HWB-QUOTES/NTTA-06507-ANCILLARY/06507 RFB solicitation_v1.pdf"
OUT_DIR = "HWB-COMPANY/HWB-QUOTES/NTTA-06507-ANCILLARY/COMPLIANCE_PACKAGE"

os.makedirs(OUT_DIR, exist_ok=True)

def fill_service_dispatch():
    """Extract and fill Page 36 (Appendix C - Service/Dispatch Location Form)"""
    doc = fitz.open(SRC_PDF)
    new_doc = fitz.open()
    new_doc.insert_pdf(doc, from_page=35, to_page=35)
    page = new_doc[0]

    # Typography settings
    font_name = "helv"
    font_bold = "hebo"
    font_size = 10
    color = (0.05, 0.15, 0.35)  # Navy blue for typed clarity

    # Coordinates aligned to Page 36 labels
    # Address Line 1:
    page.insert_text((160, 163), "101 E Park Blvd", fontname=font_bold, fontsize=font_size, color=color)
    # Address Line 2 (if applicable):
    page.insert_text((230, 184), "Suite 600", fontname=font_bold, fontsize=font_size, color=color)
    # City:
    page.insert_text((115, 205), "Plano", fontname=font_bold, fontsize=font_size, color=color)
    # State:
    page.insert_text((115, 225), "Texas", fontname=font_bold, fontsize=font_size, color=color)
    # Zip Code:
    page.insert_text((135, 246), "75074", fontname=font_bold, fontsize=font_size, color=color)
    # County:
    page.insert_text((125, 267), "Collin", fontname=font_bold, fontsize=font_size, color=color)

    # Add vendor banner at bottom
    page.draw_rect(fitz.Rect(65, 300, 545, 345), color=(0.14, 0.39, 0.92), fill=(0.96, 0.98, 1.0), width=1)
    page.insert_text((75, 318), "HWB CLEANING SERVICES LLC - PRIMARY DISPATCH HEADQUARTERS", fontname=font_bold, fontsize=9, color=(0.14, 0.39, 0.92))
    page.insert_text((75, 334), "Operating Base: Collin County | 24/7 Dispatch Control: (817) 600-6467 | Email: hdominguez@hwbcleaning.com", fontname=font_name, fontsize=8, color=(0.2, 0.2, 0.2))

    out_path = os.path.join(OUT_DIR, "NTTA-06507-Service-Dispatch-Location-Form.pdf")
    new_doc.save(out_path)
    new_doc.close()
    doc.close()
    print(f"Generated: {out_path}")

def fill_business_info():
    """Extract and fill Page 38 (Appendix D - Business Information Form)"""
    doc = fitz.open(SRC_PDF)
    new_doc = fitz.open()
    new_doc.insert_pdf(doc, from_page=37, to_page=37)
    page = new_doc[0]

    font_name = "helv"
    font_bold = "hebo"
    font_italic = "heit"
    font_size = 9.5
    color = (0.05, 0.15, 0.35)

    # Firm Name
    page.insert_text((140, 137), "HWB Cleaning Services LLC", fontname=font_bold, fontsize=font_size, color=color)
    # Firm Physical Address
    page.insert_text((195, 159), "101 E Park Blvd, Suite 600", fontname=font_bold, fontsize=font_size, color=color)
    # Physical City/State/Postal Code
    page.insert_text((230, 180), "Plano, TX 75074", fontname=font_bold, fontsize=font_size, color=color)
    # Firm Mailing Address
    page.insert_text((195, 202), "101 E Park Blvd, Suite 600", fontname=font_bold, fontsize=font_size, color=color)
    # Mailing City/State/Postal Code
    page.insert_text((230, 224), "Plano, TX 75074", fontname=font_bold, fontsize=font_size, color=color)
    # Contact Name
    page.insert_text((160, 245), "Humberto Dominguez", fontname=font_bold, fontsize=font_size, color=color)
    # Contact Email Address
    page.insert_text((200, 267), "hdominguez@hwbcleaning.com", fontname=font_bold, fontsize=font_size, color=color)
    # Contact Phone Number
    page.insert_text((205, 289), "(817) 600-6467", fontname=font_bold, fontsize=font_size, color=color)
    
    # Check if same as Mailing Address: [X]
    page.insert_text((200, 314), "[X]", fontname=font_bold, fontsize=10, color=(0.14, 0.39, 0.92))

    # Firm Remit-To Address
    page.insert_text((130, 334), "101 E Park Blvd, Suite 600", fontname=font_bold, fontsize=font_size, color=color)
    page.insert_text((235, 356), "Plano, TX 75074", fontname=font_bold, fontsize=font_size, color=color)
    page.insert_text((280, 378), "Humberto Dominguez  /  (817) 600-6467", fontname=font_bold, fontsize=font_size, color=color)
    page.insert_text((335, 399), "hdominguez@hwbcleaning.com", fontname=font_bold, fontsize=font_size, color=color)

    # Type of Business: Check Limited Liability Company
    # Position of LLC checkbox
    page.insert_text((215, 444), "[X]", fontname=font_bold, fontsize=10, color=(0.14, 0.39, 0.92))

    # State where business was formed
    page.insert_text((255, 477), "Texas", fontname=font_bold, fontsize=font_size, color=color)

    # Authorized Agent Signature Block
    page.insert_text((170, 638), "Humberto Dominguez", fontname=font_bold, fontsize=font_size, color=color)
    page.insert_text((370, 638), "Chief Executive Officer", fontname=font_bold, fontsize=font_size, color=color)
    page.insert_text((120, 661), "hdominguez@hwbcleaning.com", fontname=font_bold, fontsize=font_size, color=color)
    page.insert_text((135, 683), "Humberto Dominguez", fontname="times-bolditalic", fontsize=11, color=(0.0, 0.1, 0.5))
    page.insert_text((410, 683), "10/07/2026", fontname=font_bold, fontsize=font_size, color=color)

    out_path = os.path.join(OUT_DIR, "NTTA-06507-Business-Information-Form.pdf")
    new_doc.save(out_path)
    new_doc.close()
    doc.close()
    print(f"Generated: {out_path}")

def fill_coi_agreement():
    """Extract and fill Pages 39-40 (Appendix C - Respondent's Agreement Regarding COI & Disclosures)"""
    doc = fitz.open(SRC_PDF)
    new_doc = fitz.open()
    new_doc.insert_pdf(doc, from_page=38, to_page=39)

    # Page 1 (Page 39 of RFB)
    p1 = new_doc[0]
    # Procurement Title and Number are pre-filled by NTTA widgets, let's also ensure crisp text
    p1.insert_text((145, 154), "Janitorial Services for Ancillary Facilities", fontname="hebo", fontsize=9, color=(0.05, 0.15, 0.35))
    p1.insert_text((160, 168), "06507-NTT-00-GS-MA", fontname="hebo", fontsize=9, color=(0.05, 0.15, 0.35))

    # Page 2 (Page 40 of RFB)
    p2 = new_doc[1]
    font_bold = "hebo"
    font_size = 9.5
    navy = (0.05, 0.15, 0.35)
    check_blue = (0.14, 0.39, 0.92)

    # Question (c) 1: NTTA rep financial interest -> Check NO
    p2.insert_text((125, 172), "X", fontname=font_bold, fontsize=12, color=check_blue)
    # Question (c) 2: NTTA rep is respondent party -> Check NO
    p2.insert_text((125, 204), "X", fontname=font_bold, fontsize=12, color=check_blue)

    # Section C Disclosures (Past 5 Years) -> ALL NO
    # Q1: Debarment -> NO
    p2.insert_text((518, 442), "X", fontname=font_bold, fontsize=11, color=check_blue)
    # Q2: Misrepresentation/Damages >= 10% -> NO
    p2.insert_text((518, 485), "X", fontname=font_bold, fontsize=11, color=check_blue)
    # Q3: Contract terminated for cause -> NO
    p2.insert_text((518, 529), "X", fontname=font_bold, fontsize=11, color=check_blue)
    # Q4: Prohibited from doing business -> NO
    p2.insert_text((518, 560), "X", fontname=font_bold, fontsize=11, color=check_blue)
    # Q5: License suspended/revoked -> NO
    p2.insert_text((518, 583), "X", fontname=font_bold, fontsize=11, color=check_blue)
    # Q6: Felony criminal conviction -> NO
    p2.insert_text((518, 602), "X", fontname=font_bold, fontsize=11, color=check_blue)
    # Q7: Bankruptcy protection -> NO
    p2.insert_text((518, 624), "X", fontname=font_bold, fontsize=11, color=check_blue)

    # Representation & Warranties Bottom Line:
    # "The undersigned represents and warrants, under penalty of perjury, that: (1) (s)he is the [Chief Executive Officer] of [HWB Cleaning Services LLC]"
    p2.insert_text((400, 654), "Chief Executive Officer", fontname=font_bold, fontsize=9.5, color=navy)
    p2.insert_text((85, 664), "HWB Cleaning Services LLC", fontname=font_bold, fontsize=9.5, color=navy)

    # Signature and Date
    p2.insert_text((130, 712), "Humberto Dominguez", fontname="times-bolditalic", fontsize=11, color=(0.0, 0.1, 0.5))
    p2.insert_text((330, 712), "10/07/2026", fontname=font_bold, fontsize=9.5, color=navy)

    out_path = os.path.join(OUT_DIR, "NTTA-06507-COI-Confidentiality-Agreement.pdf")
    new_doc.save(out_path)
    new_doc.close()
    doc.close()
    print(f"Generated: {out_path}")

def fill_form_ciq():
    """Extract and fill Page 41-42 (Conflict of Interest Questionnaire - Form CIQ)"""
    doc = fitz.open(SRC_PDF)
    new_doc = fitz.open()
    new_doc.insert_pdf(doc, from_page=40, to_page=41)

    p1 = new_doc[0]
    font_bold = "hebo"
    navy = (0.05, 0.15, 0.35)
    check_blue = (0.14, 0.39, 0.92)

    # Box 1: Name of vendor
    p1.insert_text((60, 205), "HWB Cleaning Services LLC", fontname=font_bold, fontsize=11, color=navy)
    p1.insert_text((60, 220), "101 E Park Blvd, Suite 600, Plano, TX 75074", fontname="helv", fontsize=9, color=(0.3, 0.3, 0.3))

    # Box 2: Update box (leave unchecked - initial filing)

    # Box 3: Name of local government officer
    p1.insert_text((60, 318), "NONE - No reportable officer relationships or conflicts exist", fontname=font_bold, fontsize=9.5, color=navy)

    # Box 4: Describe each employment/business relationship
    p1.insert_text((60, 420), "NONE. HWB Cleaning Services LLC maintains no employment, business, or family", fontname="helv", fontsize=9, color=navy)
    p1.insert_text((60, 434), "relationship with any member of the NTTA Board of Directors or local government officer.", fontname="helv", fontsize=9, color=navy)

    # Subpart A: Check NO
    p1.insert_text((253, 502), "X", fontname=font_bold, fontsize=12, color=check_blue)
    # Subpart B: Check NO
    p1.insert_text((253, 574), "X", fontname=font_bold, fontsize=12, color=check_blue)

    # Box 5: Describe entity where officer serves
    p1.insert_text((60, 638), "NONE", fontname=font_bold, fontsize=9.5, color=navy)

    # Box 6: Gifts (leave unchecked)

    # Box 7: Signature of vendor
    p1.insert_text((115, 730), "Humberto Dominguez", fontname="times-bolditalic", fontsize=11, color=(0.0, 0.1, 0.5))
    p1.insert_text((410, 730), "10/07/2026", fontname=font_bold, fontsize=9.5, color=navy)

    out_path = os.path.join(OUT_DIR, "NTTA-06507-Form-CIQ-Conflict-of-Interest.pdf")
    new_doc.save(out_path)
    new_doc.close()
    doc.close()
    print(f"Generated: {out_path}")

def generate_bdod_gfe_letter():
    """Generate the official BDOD Subcontractor Plan / Good Faith Effort (GFE) Letter"""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)  # Standard Letter size

    navy = (0.05, 0.15, 0.35)
    brand_blue = (0.14, 0.39, 0.92)
    gray = (0.35, 0.35, 0.35)
    black = (0.1, 0.1, 0.1)

    # Header Border Strip
    page.draw_rect(fitz.Rect(54, 50, 558, 54), fill=brand_blue, color=brand_blue)

    # Header Typography
    page.insert_text((54, 75), "HWB CLEANING SERVICES LLC", fontname="hebo", fontsize=14, color=navy)
    page.insert_text((54, 88), "SIGMAFIDELITY™ INSTITUTIONAL JANITORIAL SERVICES | ISO 9001:2015 REGISTERED", fontname="hebo", fontsize=7.5, color=brand_blue)
    page.insert_text((400, 72), "101 E Park Blvd, Suite 600", fontname="helv", fontsize=8, color=gray)
    page.insert_text((400, 83), "Plano, TX 75074 | (817) 600-6467", fontname="helv", fontsize=8, color=gray)
    page.insert_text((400, 94), "Email: hdominguez@hwbcleaning.com", fontname="helv", fontsize=8, color=gray)

    page.draw_rect(fitz.Rect(54, 105, 558, 106), fill=(0.85, 0.85, 0.85), color=(0.85, 0.85, 0.85))

    # Date and Recipient
    page.insert_text((54, 128), "Date: October 7, 2026", fontname="hebo", fontsize=9.5, color=black)
    page.insert_text((54, 145), "North Texas Tollway Authority (NTTA)", fontname="hebo", fontsize=9.5, color=navy)
    page.insert_text((54, 157), "Business Development and Opportunities Department (BDOD)", fontname="helv", fontsize=9, color=black)
    page.insert_text((54, 169), "Attn: Procurement Services | bidpurchasing@ntta.org", fontname="helv", fontsize=9, color=black)
    page.insert_text((54, 181), "Post Office Box 260729, Plano, Texas 75026", fontname="helv", fontsize=9, color=black)

    # Subject
    page.draw_rect(fitz.Rect(54, 195, 558, 222), fill=(0.96, 0.98, 1.0), color=brand_blue, width=0.8)
    page.insert_text((62, 208), "SUBJECT: EXHIBIT D - BDOD SMALL BUSINESS PROGRAM COMPLIANCE & GFE STATEMENT", fontname="hebo", fontsize=8.5, color=navy)
    page.insert_text((62, 218), "Contract No.: 06507-NTT-00-GS-MA | Janitorial Services for Ancillary Facilities", fontname="helv", fontsize=8, color=black)

    # Body Content
    lines = [
        "To the NTTA Business Development and Opportunities Department & Procurement Selection Committee:",
        "",
        "HWB Cleaning Services LLC ('HWB') is pleased to submit this official Small Business Program Good Faith Effort (GFE)",
        "Compliance Statement and Subcontractor Utilization Plan for Contract No. 06507-NTT-00-GS-MA (Janitorial Services",
        "for Ancillary Facilities).",
        "",
        "1. 100% PRIME CONTRACTOR SELF-PERFORMANCE COMMITMENT",
        "HWB Cleaning Services LLC hereby certifies that it will SELF-PERFORM ONE HUNDRED PERCENT (100%) of all janitorial",
        "operations, recurring scheduled cleanings, 2,080 hours/year Day Porter services, and emergency infection control scope",
        "utilizing its direct, vetted, W-2 employed custodial workforce. HWB maintains dedicated operational infrastructure,",
        "fleet vehicles, and direct supervision headquartered locally in Plano, Texas (Collin County), fully equipped to execute",
        "the complete Scope of Work across all designated facilities (Frisco Ops, Plano Ops, MLP-3, MLP-4, and Tollway Stockpiles).",
        "",
        "2. ZERO SUBCONTRACTING PLAN & SMALL BUSINESS PROGRAM GOAL ADHERENCE",
        "Per NTTA Solicitation Exhibit D (Pages 97-100), the designated Small Business Goal for this procurement is 'GFE of total",
        "contract amount.' Because HWB will self-perform 100% of all labor production without utilizing second-tier subcontracting,",
        "zero percent (0%) of the direct janitorial scope is subcontracted. Exhibit D Page 100 of the solicitation confirms the",
        "Subcontractor Plan Form is designated as [N/A] at bid submission.",
        "",
        "3. PROACTIVE GOOD FAITH EFFORT (GFE) VENDOR INCLUSION COMMITMENT",
        "In strict alignment with NTTA BDOD's Small Business Program Policy and Contracting & Compliance Manual (CCM), HWB",
        "covenants to execute active Good Faith Efforts across all discretionary procurement and supply chain touchpoints:",
        "   a. Specialty Chemicals & Equipment Maintenance: HWB will prioritize NTTA-certified D/M/W/SBE suppliers for local",
        "      cleaning chemical procurement, machine parts, and equipment maintenance.",
        "   b. Monthly Compliance Portal Reporting: HWB will maintain active registration and monthly reporting via NTTA's vendor",
        "      compliance system (NTTA.gob2g.com) by the 15th of each calendar month, as mandated by NTTA BDOD rules.",
        "   c. Post-Award Vendor Expansion: If contingency scope or specialty trade services are required during the contract term,",
        "      HWB guarantees certified small business solicitation outreach prior to award.",
        "",
        "HWB Cleaning Services LLC affirms its uncompromised commitment to partnering with the NTTA to champion regional",
        "economic participation and deliver flawless institutional maintenance standards."
    ]

    y = 240
    for line in lines:
        if line.startswith("1. ") or line.startswith("2. ") or line.startswith("3. "):
            page.insert_text((54, y), line, fontname="hebo", fontsize=8.5, color=navy)
            y += 12
        elif line.strip() == "":
            y += 5
        else:
            page.insert_text((54, y), line, fontname="helv", fontsize=8.2, color=black)
            y += 11.5

    # Signature Block
    y += 15
    page.insert_text((54, y), "RESPECTFULLY SUBMITTED & CERTIFIED UNDER PENALTY OF PERJURY,", fontname="hebo", fontsize=8, color=gray)
    y += 20
    page.insert_text((54, y), "Humberto Dominguez", fontname="times-bolditalic", fontsize=13, color=(0.0, 0.1, 0.5))
    y += 15
    page.insert_text((54, y), "Humberto Dominguez, Chief Executive Officer", fontname="hebo", fontsize=9, color=navy)
    y += 12
    page.insert_text((54, y), "HWB Cleaning Services LLC", fontname="helv", fontsize=8.5, color=black)
    y += 12
    page.insert_text((54, y), "Corporate Headquarters: 101 E Park Blvd, Suite 600, Plano, TX 75074 | Phone: (817) 600-6467", fontname="helv", fontsize=8, color=gray)

    # Footer
    page.draw_rect(fitz.Rect(54, 740, 558, 741), fill=(0.85, 0.85, 0.85), color=(0.85, 0.85, 0.85))
    page.insert_text((54, 754), "NTTA Solicitation 06507-NTT-00-GS-MA | Exhibit D - BDOD Small Business Program Compliance Statement", fontname="helv", fontsize=7.5, color=gray)
    page.insert_text((475, 754), "Page 1 of 1", fontname="hebo", fontsize=7.5, color=brand_blue)

    out_path = os.path.join(OUT_DIR, "NTTA-06507-BDOD-Subcontractor-Plan-GFE.pdf")
    doc.save(out_path)
    doc.close()
    print(f"Generated: {out_path}")

def build_unified_package():
    """Merge all compliance documents into a single master PDF package"""
    unified_doc = fitz.open()

    order = [
        "NTTA-06507-Service-Dispatch-Location-Form.pdf",
        "NTTA-06507-Business-Information-Form.pdf",
        "NTTA-06507-COI-Confidentiality-Agreement.pdf",
        "NTTA-06507-Form-CIQ-Conflict-of-Interest.pdf",
        "NTTA-06507-BDOD-Subcontractor-Plan-GFE.pdf"
    ]

    for fname in order:
        fpath = os.path.join(OUT_DIR, fname)
        sub_doc = fitz.open(fpath)
        unified_doc.insert_pdf(sub_doc)
        sub_doc.close()

    out_path = os.path.join(OUT_DIR, "NTTA-06507-MANDATORY-COMPLIANCE-PACKAGE-UNIFIED.pdf")
    page_count = unified_doc.page_count
    unified_doc.save(out_path)
    unified_doc.close()
    print(f"Generated Unified Package: {out_path} ({len(order)} documents, {page_count} pages)")

if __name__ == "__main__":
    print("Beginning NTTA Mandatory Compliance Package Generation...")
    fill_service_dispatch()
    fill_business_info()
    fill_coi_agreement()
    fill_form_ciq()
    generate_bdod_gfe_letter()
    build_unified_package()
    print("ALL COMPLIANCE ASSETS SUCCESSFULLY GENERATED.")
