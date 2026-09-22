"""
SigmaFidelity™ Safety Documentation Generator
Standard: HWB-QMS-1.0 & ISO 45001:2018
Author: George (Systems Architect)
Approved By: Humberto Dominguez, CEO
Purpose: Generates institutional-grade DOCX manuals for Master EHS, Construction Site Safety (CSSP),
         and Institutional Facilities Health & Safety (IFSP).
"""

import os
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

NAVY = RGBColor(15, 41, 74)       # #0F294A
BLUE = RGBColor(37, 99, 235)      # #2563EB
SLATE = RGBColor(71, 85, 105)     # #475569
DARK = RGBColor(15, 23, 42)       # #0F172A

def set_cell_shading(cell, color_hex: str):
    """Applies background color to a table cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Sets inner padding for table cells."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
    tcPr.append(tcMar)

def add_header_banner(doc: Document, doc_id: str, title: str, subtitle: str, standard: str):
    """Creates an executive corporate title block."""
    p_comp = doc.add_paragraph()
    r_comp = p_comp.add_run("HWB CLEANING SERVICES LLC")
    r_comp.font.name = "Arial"
    r_comp.font.size = Pt(10)
    r_comp.font.bold = True
    r_comp.font.color.rgb = BLUE
    p_comp.paragraph_format.space_after = Pt(2)

    p_title = doc.add_paragraph()
    r_title = p_title.add_run(title)
    r_title.font.name = "Arial"
    r_title.font.size = Pt(20)
    r_title.font.bold = True
    r_title.font.color.rgb = NAVY
    p_title.paragraph_format.space_after = Pt(4)

    p_sub = doc.add_paragraph()
    r_sub = p_sub.add_run(subtitle)
    r_sub.font.name = "Arial"
    r_sub.font.size = Pt(11)
    r_sub.font.color.rgb = SLATE
    p_sub.paragraph_format.space_after = Pt(12)

    # Metadata Control Table
    table = doc.add_table(rows=5, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    meta_rows = [
        ("Document ID", doc_id),
        ("Version & Status", "Version 1.0.0 | ● APPROVED"),
        ("Approval Authority", "Humberto Dominguez, CEO"),
        ("Date of Issuance", "September 21, 2026"),
        ("Regulatory & Standard Alignment", standard)
    ]

    for idx, (label, val) in enumerate(meta_rows):
        cell_lbl, cell_val = table.rows[idx].cells
        cell_lbl.width = Inches(2.2)
        cell_val.width = Inches(4.3)
        set_cell_shading(cell_lbl, "F1F5F9")
        set_cell_shading(cell_val, "FFFFFF")
        set_cell_margins(cell_lbl, 80, 80, 120, 120)
        set_cell_margins(cell_val, 80, 80, 120, 120)

        p_lbl = cell_lbl.paragraphs[0]
        r_l = p_lbl.add_run(label)
        r_l.font.name = "Arial"
        r_l.font.size = Pt(9.5)
        r_l.font.bold = True
        r_l.font.color.rgb = NAVY
        p_lbl.paragraph_format.space_after = Pt(0)

        p_v = cell_val.paragraphs[0]
        r_v = p_v.add_run(val)
        r_v.font.name = "Arial"
        r_v.font.size = Pt(9.5)
        r_v.font.color.rgb = DARK
        if "APPROVED" in val:
            r_v.font.bold = True
        p_v.paragraph_format.space_after = Pt(0)

    p_spacer = doc.add_paragraph()
    p_spacer.paragraph_format.space_after = Pt(14)

def add_heading_1(doc: Document, text: str):
    h = doc.add_paragraph()
    r = h.add_run(text)
    r.font.name = "Arial"
    r.font.size = Pt(14)
    r.font.bold = True
    r.font.color.rgb = NAVY
    h.paragraph_format.space_before = Pt(14)
    h.paragraph_format.space_after = Pt(4)
    return h

def add_heading_2(doc: Document, text: str):
    h = doc.add_paragraph()
    r = h.add_run(text)
    r.font.name = "Arial"
    r.font.size = Pt(11.5)
    r.font.bold = True
    r.font.color.rgb = BLUE
    h.paragraph_format.space_before = Pt(10)
    h.paragraph_format.space_after = Pt(3)
    return h

def add_body_p(doc: Document, text: str):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r.font.color.rgb = DARK
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.15
    return p

def add_bullet(doc: Document, bold_prefix: str, text: str):
    p = doc.add_paragraph(style='List Bullet')
    if bold_prefix:
        r_b = p.add_run(bold_prefix + " ")
        r_b.font.name = "Arial"
        r_b.font.size = Pt(10)
        r_b.font.bold = True
        r_b.font.color.rgb = DARK
    r_t = p.add_run(text)
    r_t.font.name = "Arial"
    r_t.font.size = Pt(10)
    r_t.font.color.rgb = DARK
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.15
    return p

def add_callout(doc: Document, title: str, text: str):
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    cell = table.rows[0].cells[0]
    cell.width = Inches(6.5)
    set_cell_shading(cell, "EFF6FF")
    set_cell_margins(cell, 120, 120, 150, 150)

    p = cell.paragraphs[0]
    r_title = p.add_run(title + "\n")
    r_title.font.name = "Arial"
    r_title.font.size = Pt(10)
    r_title.font.bold = True
    r_title.font.color.rgb = BLUE

    r_text = p.add_run(text)
    r_text.font.name = "Arial"
    r_text.font.size = Pt(9.5)
    r_text.font.color.rgb = DARK
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.15

    doc.add_paragraph().paragraph_format.space_after = Pt(6)


# ==============================================================================
# 1. BUILD MASTER EHS MANUAL (HWB-EHS-001)
# ==============================================================================
def build_master_manual(output_path: str):
    doc = Document()
    add_header_banner(
        doc,
        doc_id="HWB-EHS-001",
        title="Master Environmental Health and Safety (EHS) Manual",
        subtitle="Corporate Safety Governance, Hazard Communication & Regulatory Compliance",
        standard="ISO 45001:2018 | OSHA 29 CFR 1910 & 29 CFR 1926"
    )

    add_heading_1(doc, "1.0 Purpose & Executive Commitment")
    add_body_p(doc, "HWB Cleaning Services LLC is dedicated to providing an accident-free, healthy, and compliant work environment for all employees, subcontractors, clients, and facility occupants. Safety is an uncompromised core value that takes precedence over speed or operational convenience. This Master Manual establishes company-wide safety policies, management responsibilities, reporting chains, and regulatory compliance standards across all commercial, post-construction, and public authority operations.")

    add_heading_1(doc, "2.0 Scope & Modular Architecture")
    add_body_p(doc, "This procedure applies to all personnel performing work on behalf of HWB Cleaning Services LLC. To address the distinct operational requirements of construction job sites versus occupied public facilities, this Master Manual connects to two specialized operational safety modules:")
    add_bullet(doc, "Module A — HWB-EHS-002:", "Construction Site Safety and Silica Dust Control Plan (OSHA 29 CFR 1926 / Division 01 35 23 for General Contractors).")
    add_bullet(doc, "Module B — HWB-EHS-003:", "Institutional Facilities Health and Safety Plan (OSHA 29 CFR 1910 for Public Authorities, NTTA, and Higher Education Campuses).")

    add_heading_1(doc, "3.0 Safety Roles & Responsibilities")
    add_bullet(doc, "Chief Executive Officer (Humberto Dominguez):", "Holds ultimate authority for corporate safety policies, resource allocation, and annual safety audits. Reviews all major incident investigations and regulatory filings.")
    add_bullet(doc, "Safety Director & Project Managers:", "Enforce daily safety rules across all active customer accounts and jobsites. Review Job Hazard Analysis (JHA) forms before work begins and conduct routine jobsite audits.")
    add_bullet(doc, "Site Supervisors & Foremen:", "Perform daily visual safety inspections of equipment, power cords, and PPE. Lead weekly Safety Tool Box Talks and correct unsafe conditions on the spot.")
    add_bullet(doc, "Cleaning Technicians & Subcontractors:", "Inspect and wear mandatory PPE daily, follow machine safety instructions and chemical dilution ratios without deviation, and report all injuries or near-misses immediately.")

    add_heading_1(doc, "4.0 General Safety Rules & Rules of Conduct")
    add_bullet(doc, "Zero Tolerance for Horseplay:", "Running, practical jokes, fighting, or careless behavior are strictly banned on all company and customer premises.")
    add_bullet(doc, "Personal Protective Equipment (PPE):", "Mandatory PPE must be clean, inspected, and worn whenever performing tasks presenting eye, skin, head, foot, or breathing risks.")
    add_bullet(doc, "Housekeeping & Cord Safety:", "Work areas must remain clean and orderly. Hoses, power cords, and equipment must be positioned to prevent tripping hazards.")
    add_bullet(doc, "Machinery Guards:", "Never bypass safety guards, emergency shut-off switches, or ground pins on 3-prong electrical cords.")
    add_bullet(doc, "Ergonomic Lifting:", "Use leg muscles and keep the back straight when lifting items. Team lifting is mandatory for loads over 50 pounds.")

    add_heading_1(doc, "5.0 Hazard Communication Program (OSHA 29 CFR 1910.1200 / GHS)")
    add_body_p(doc, "In full accordance with federal OSHA Hazard Communication regulations and the Texas Hazard Communication Act (THCA), HWB Cleaning Services LLC guarantees all workers the right to understand the chemical hazards present in their work environment.")
    add_bullet(doc, "Safety Data Sheets (SDS):", "An up-to-date SDS binder is maintained in every primary janitorial closet, mobile service van, and digitally on the backoffice portal. Mixing different chemicals—especially bleach and ammonia-based products—is strictly forbidden.")
    add_bullet(doc, "Secondary Container Labeling:", "Every spray bottle or secondary bucket must carry a complete GHS label identifying the product name, manufacturer, and key hazard warning pictograms. Unlabeled bottles are confiscated immediately.")

    add_heading_1(doc, "6.0 Injury, Incident, and Near-Miss Reporting")
    add_body_p(doc, "Prompt reporting ensures timely medical care and prevents repeat accidents:")
    add_bullet(doc, "Immediate Reporting Window:", "All injuries, regardless of severity, must be reported to the Site Supervisor and Safety Director within one (1) hour.")
    add_bullet(doc, "First Report of Injury:", "The supervisor must complete the official HWB First Report of Injury Form within 24 hours of the incident.")
    add_bullet(doc, "Root-Cause Investigation:", "The Safety Director leads a formal investigation within 48 hours to identify preventative actions.")

    add_heading_1(doc, "7.0 Disciplinary Policy for Safety Violations")
    add_bullet(doc, "1st Offense:", "Documented Verbal Counseling and mandatory retraining on the relevant safety standard.")
    add_bullet(doc, "2nd Offense:", "Written Warning placed in permanent personnel file and safety review meeting.")
    add_bullet(doc, "3rd Offense:", "Final Written Warning and three-day unpaid suspension.")
    add_bullet(doc, "4th Offense:", "Immediate termination of employment.")

    add_callout(
        doc,
        "Critical Safety Violations",
        "Bypassing safety locks, working at heights without required fall protection, failure to report an injury, or arriving to work under the influence of drugs or alcohol results in immediate suspension and potential termination on the first offense."
    )

    add_heading_1(doc, "8.0 Drug, Alcohol, and Contraband Policy")
    add_body_p(doc, "HWB Cleaning Services LLC maintains a zero-tolerance drug- and alcohol-free workplace. The use, possession, sale, or being under the influence of illegal drugs, unauthorized narcotics, or alcohol during work hours or on customer property is strictly prohibited. Carrying firearms, concealed handguns, knives over 3 inches (excluding standard utility tools), or weapons onto customer premises is strictly forbidden.")

    add_heading_1(doc, "9.0 OSHA Regulatory Inspection Procedure")
    add_body_p(doc, "When an OSHA compliance officer or regulatory inspector arrives at an HWB jobsite:")
    add_bullet(doc, "Verification & Management Alert:", "Examine official agency credentials, be courteous, and immediately notify the Safety Director and CEO Humberto Dominguez.")
    add_bullet(doc, "Accompaniment Mandate:", "An authorized HWB supervisor must accompany the inspector throughout the entire walk-around. Never allow an inspector to walk the site unescorted.")
    add_bullet(doc, "Photographic Mirroring:", "If the inspector takes a photograph or notes a specific condition, the HWB supervisor must take corresponding photos from the same angles and document all details.")
    add_bullet(doc, "Immediate Correction:", "If an unsafe condition can be fixed immediately, correct it on the spot while notifying the inspector.")

    add_heading_1(doc, "10.0 Emergency Action Plans (EAP)")
    add_bullet(doc, "Fire & Building Evacuation:", "Know two exit routes. Cease work immediately upon alarm sounding, shut off machinery, and assemble at the outdoor muster area for roll-call.")
    add_bullet(doc, "Severe Weather & Tornado:", "Move quickly to designated interior rooms or windowless ground-floor restrooms until all-clear is announced.")
    add_bullet(doc, "Active Threat (Run, Hide, Fight):", "Run and evacuate if possible. If trapped, hide and barricade doors, silence phones. Fight as an absolute last resort when in imminent danger.")

    doc.save(output_path)
    print(f"[SUCCESS] Master EHS Manual generated at: {output_path}")


# ==============================================================================
# 2. BUILD CONSTRUCTION SITE SAFETY PLAN (HWB-EHS-002)
# ==============================================================================
def build_construction_plan(output_path: str):
    doc = Document()
    add_header_banner(
        doc,
        doc_id="HWB-EHS-002",
        title="Construction Site Safety & Silica Dust Plan (CSSP)",
        subtitle="Rough, Final & Touch-Up Post-Construction Cleaning Safety Program",
        standard="CSI MasterFormat Div 01 35 23 & 01 74 00 | OSHA 29 CFR 1926"
    )

    add_heading_1(doc, "1.0 Purpose & Construction Scope")
    add_body_p(doc, "This plan establishes mandatory safety protocols for HWB Cleaning Services LLC personnel performing rough, final, and touch-up post-construction cleaning on commercial construction sites. This document complies with General Contractor site safety requirements, owner specifications, and CSI MasterFormat Division 01 35 23 (Project Safety Requirements).")

    add_heading_1(doc, "2.0 Respirable Crystalline Silica Dust Control (OSHA 29 CFR 1926.1153)")
    add_body_p(doc, "Post-construction cleaning involves drywall compound, concrete residue, tile dust, and mortar debris containing respirable crystalline silica. Inhaling silica dust causes severe irreversible lung illness (silicosis). HWB enforces strict engineering controls:")
    add_bullet(doc, "Zero Dry Sweeping Mandate:", "Dry sweeping with brooms or using compressed air to clean drywall or concrete dust is strictly prohibited under any circumstances.")
    add_bullet(doc, "HEPA Vacuum Extraction:", "All surface dust collection must be performed using commercial vacuums equipped with verified HEPA filtration certified to 99.97% efficiency at 0.3 microns, with sealed filter housings.")
    add_bullet(doc, "Wet Cleaning Methods:", "Baseboards, door frames, and window sills must be cleaned using damp microfiber cloths or wet-wiping systems to suppress airborne particles.")
    add_bullet(doc, "Respiratory Protection:", "Technicians must wear NIOSH-approved N95 or half-face respirators whenever dust-generating tasks warrant protection.")

    add_heading_1(doc, "3.0 Mobile Elevating Work Platforms (MEWPs) & Scissor Lifts")
    add_body_p(doc, "All overhead dusting, conduit wipe-down, and elevated window washing utilizing scissor lifts or boom lifts must strictly adhere to ANSI/SAIA A92.20 and A92.22 standards, and OSHA 29 CFR 1926.453:")
    add_bullet(doc, "Certified Operators Only:", "Only technicians with an active, documented MEWP Operator Certification card issued or vetted by HWB management are authorized to operate aerial lifts.")
    add_bullet(doc, "Daily Pre-Operation Inspection:", "Operators must complete a physical walk-around checklist inspecting tire integrity, hydraulic fluid leaks, emergency lowering controls, horn, guardrails, and battery charge levels.")
    add_bullet(doc, "100% Fall Arrest Tie-Off:", "Operators in boom lifts must wear a full-body harness with an energy-absorbing lanyard attached to the manufacturer anchor point at all times. On scissor lifts, guardrails and entry chains/gates must be locked closed before ascending.")
    add_bullet(doc, "Barricades & Ground Spotters:", "A safety perimeter must be established using cones or caution tape below elevated work areas, and a designated spotter must monitor ground pedestrian traffic.")

    add_heading_1(doc, "4.0 Glass Scraping, Window Cleaning & Blade Safety")
    add_bullet(doc, "Cut-Resistant Gloves:", "Technicians must wear cut-resistant gloves rated at minimum ANSI Cut Level A4 on the non-dominant stabilizing hand during all glass scraping activities.")
    add_bullet(doc, "Retractable Safety Scrapers:", "Only scrapers equipped with retractable blade guards are permitted. Blades must be retracted whenever the tool is not in active contact with glass.")
    add_bullet(doc, "Puncture-Resistant Sharps Disposal:", "Used razor blades must never be placed loose into trash bags. Blades must be placed directly into a hard-plastic sharps disposal container.")
    add_bullet(doc, "Glass Surface Lubrication:", "Glass surfaces must be thoroughly wetted with soapy water solution before scraping, holding the blade at a 30-degree angle to prevent scratches on tempered glass.")

    add_heading_1(doc, "5.0 Industrial Ladder Safety (OSHA 29 CFR 1926.1053)")
    add_bullet(doc, "Duty Rating:", "Only heavy-duty fiberglass ladders rated Type IA (300 lb capacity) or Type IAA (375 lb capacity) are permitted on construction sites. Aluminum household ladders are forbidden.")
    add_bullet(doc, "Three-Point Contact:", "Technicians must maintain three points of contact at all times while climbing or descending ladders.")
    add_bullet(doc, "Top Step Prohibition:", "Never stand, sit, or climb on the top step or bucket shelf of a stepladder.")
    add_bullet(doc, "Inspection & Tagging:", "Damaged ladders must be immediately tagged 'OUT OF SERVICE' and removed from the job site.")

    add_heading_1(doc, "6.0 Mandatory Construction PPE Standards")
    add_bullet(doc, "Hard Hats:", "ANSI Z89.1 (Type 1, Class E or G) worn continuously within active construction zones.")
    add_bullet(doc, "Eye Protection:", "ANSI Z87.1+ high-impact safety glasses with side shields worn at all times.")
    add_bullet(doc, "Safety Footwear:", "ASTM F2413 steel or composite toe work boots with puncture-resistant soles.")
    add_bullet(doc, "High-Visibility Vests:", "ANSI/ISEA 107 Class 2 or Class 3 fluorescent vests with reflective striping.")
    add_bullet(doc, "Hand Protection:", "ANSI Cut Level A2 to A4 work gloves.")

    add_heading_1(doc, "7.0 Daily Safety Briefings & General Contractor Integration")
    add_body_p(doc, "The HWB Site Supervisor conducts a daily morning Job Hazard Analysis (JHA) covering active hazards (overhead trades, floor openings, scissor lift paths). The crew attends a 5-minute Tool Box Talk and signs the daily attendance log. The supervisor coordinates all work scopes directly with the General Contractor Superintendent.")

    doc.save(output_path)
    print(f"[SUCCESS] Construction Site Safety Plan generated at: {output_path}")


# ==============================================================================
# 3. BUILD INSTITUTIONAL FACILITY SAFETY PLAN (HWB-EHS-003)
# ==============================================================================
def build_institutional_plan(output_path: str):
    doc = Document()
    add_header_banner(
        doc,
        doc_id="HWB-EHS-003",
        title="Institutional Facilities Health & Safety Plan (IFSP)",
        subtitle="Public Sector, Multi-Facility & Occupied Campus Custodial Safety Program",
        standard="OSHA 29 CFR 1910 (General Industry) | NTTA & Higher Ed Compliance"
    )

    add_heading_1(doc, "1.0 Purpose & Institutional Scope")
    add_body_p(doc, "This plan establishes safety, health, and security standards for HWB Cleaning Services LLC personnel operating inside occupied public authority facilities, transportation centers, higher education campuses, and municipal complexes. It addresses unique environmental risks including student and pedestrian traffic, biological fluid hazards, secure facility controls, and chemical dilution management across multi-facility portfolios (such as NTTA Ancillary Facilities and Collin College).")

    add_heading_1(doc, "2.0 Bloodborne Pathogens Exposure Control (OSHA 29 CFR 1910.1030)")
    add_body_p(doc, "Restroom sanitation, trash handling, and public area cleaning present potential risks of contact with blood or other potentially infectious materials (OPIM). HWB enforces universal precautions:")
    add_bullet(doc, "Universal Precautions:", "All human blood and bodily fluids are treated as if known to be infectious for HIV, Hepatitis B (HBV), and other pathogens.")
    add_bullet(doc, "Mandatory Restroom PPE:", "Technicians must wear disposable nitrile gloves for general restroom cleaning, and heavy-duty utility gloves when servicing toilets and urinals.")
    add_bullet(doc, "Biohazard Spill Kits:", "Every facility closet contains an OSHA-compliant Body Fluid Clean-up Spill Kit with absorbent powder, scoop, disinfectant wipes, and red biohazard disposal bags.")
    add_bullet(doc, "Sharps Awareness:", "Never push trash down with hands or feet. If a discarded syringe is found, use a mechanical grabber to place it into an approved sharps container. Never touch needles directly.")
    add_bullet(doc, "Hepatitis B Vaccination:", "Offered free of charge to all technicians with occupational exposure. Declinations must be signed on the official OSHA form.")

    add_heading_1(doc, "3.0 Public Pedestrian Safety & Slip, Trip, and Fall Prevention")
    add_bullet(doc, "Bilingual Wet Floor Cones:", "High-visibility bilingual (English/Spanish) 'Caution Wet Floor' cones must be placed at all entry points before mopping begins and left until floors are completely dry.")
    add_bullet(doc, "Half-Hallway Mopping:", "In corridors and lobbies, technicians must mop only one half of the corridor width at a time, leaving the other half dry and unobstructed for public egress.")
    add_bullet(doc, "Cord Management:", "Power cords for backpack vacuums and burnishers must never cross open doorways without heavy-duty yellow rubber cable ramps.")
    add_bullet(doc, "Rain & Freeze Walk-Off Mats:", "Entrance mats must be monitored hourly during wet weather, and standing water extracted immediately.")

    add_heading_1(doc, "4.0 Chemical Dilution Systems & GHS Secondary Labeling (OSHA 1910.1200)")
    add_bullet(doc, "Closed-Loop Dilution Dispensers:", "Concentrated chemicals must be mixed using wall-mounted dilution stations that meter exact water ratios, eliminating manual pouring hazards.")
    add_bullet(doc, "Secondary Container Labeling:", "Every spray bottle must carry a factory-printed GHS label showing the chemical name, manufacturer, and hazard pictograms.")
    add_bullet(doc, "Janitorial Closets & Slop Sinks:", "Closets must remain locked when unattended. Slop sinks must be drained and cleaned after each shift. Chemicals must be stored off the floor.")
    add_bullet(doc, "Emergency Eye Wash:", "Eye wash stations must have unobstructed access and receive weekly visual inspections.")

    add_heading_1(doc, "5.0 Commercial Floor Care Machinery Protocols")
    add_bullet(doc, "Auto-Scrubbers (Walk-Behind & Ride-On):", "Operate at walking pace with headlights and amber beacons active. Slow down at corridor intersections.")
    add_bullet(doc, "Battery Charging Ventilation:", "Lead-acid batteries must be charged only in well-ventilated areas away from sparks to prevent hydrogen gas accumulation.")
    add_bullet(doc, "High-Speed Burnishers:", "Inspect pad centering locks and power cords prior to each operation. Never leave running machines unattended.")

    add_heading_1(doc, "6.0 Facility Security, Access Badging & Weapon-Free Policy")
    add_body_p(doc, "Public authority contracts (such as NTTA toll plazas and administrative centers) and educational campuses mandate strict security controls:")
    add_bullet(doc, "Photo ID Badges:", "HWB photo ID badges and agency-issued access badges must be displayed on outer garments above the waist at all times.")
    add_bullet(doc, "Exterior Door Custody:", "Exterior doors must NEVER be propped open with wedges or trash cans. Doors must latch securely upon entering or leaving.")
    add_bullet(doc, "Key & Fob Custody:", "Master keys and fobs must remain clipped to the supervisor's belt and returned to lockboxes at shift end. Duplicating keys is strictly prohibited.")
    add_bullet(doc, "Background Screening:", "All personnel must pass 7-year statewide criminal background checks (including CJIS and FERPA clearances).")
    add_bullet(doc, "Weapon-Free Workplace Covenant:", "Carrying firearms, concealed handguns, knives over 3 inches, or weapons onto NTTA or campus property is strictly forbidden by contract and results in immediate arrest, termination, and contract removal.")

    add_heading_1(doc, "7.0 Custodial Ergonomics & Zero-Injury Mechanics")
    add_bullet(doc, "Backpack Vacuum Adjustment:", "Tighten waist belt first so that 80% of weight rests on the hips, not shoulders. Maintain upright posture and arm sweeping motions.")
    add_bullet(doc, "Mop Bucket Mechanics:", "Never lift full 5-gallon mop buckets. Utilize bucket wheels and pour spouts, emptying frequently to keep lift weights under 25 pounds.")
    add_bullet(doc, "Trash Can Tipping:", "Use 2-person team lifts when emptying heavy 44-gallon trash barrels into exterior dumpsters.")

    add_heading_1(doc, "8.0 Emergency Action Plans in Occupied Facilities")
    add_bullet(doc, "Active Threat (Run / Hide / Fight):", "Know two exit routes from every zone. Evacuate immediately if safe, or shelter in locked utility closets with radios silenced.")
    add_bullet(doc, "Fire Alarms:", "Evacuate immediately upon alarm. Guide occupants toward exit signs and assemble at the facility muster area.")
    add_bullet(doc, "Agency Dispatch Notification:", "In an emergency, call 911 first, then contact NTTA Operations Center or Campus Police dispatch desk using official emergency lines.")

    doc.save(output_path)
    print(f"[SUCCESS] Institutional Facility Safety Plan generated at: {output_path}")


if __name__ == "__main__":
    out_dir = "/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-EHSQ"
    os.makedirs(out_dir, exist_ok=True)
    
    build_master_manual(os.path.join(out_dir, "HWB-EHS-001-Master-Safety-Manual.docx"))
    build_construction_plan(os.path.join(out_dir, "HWB-EHS-002-Construction-Site-Safety-Plan.docx"))
    build_institutional_plan(os.path.join(out_dir, "HWB-EHS-003-Institutional-Facility-Safety-Plan.docx"))
    print("\n--- ALL THREE SAFETY MANUALS SUCCESSFULLY GENERATED ---")
