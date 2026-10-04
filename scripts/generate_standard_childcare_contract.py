import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import shutil
import os

def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), fill_hex)
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def create_document():
    doc = docx.Document()
    
    # 1. Page Margins (0.75 in for professional density)
    for section in doc.sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    # Palette
    c_navy = RGBColor(15, 23, 42)      # Slate 900
    c_blue = RGBColor(2, 132, 199)     # Brand Blue 600
    c_slate = RGBColor(71, 85, 105)    # Slate 600
    c_dark = RGBColor(30, 41, 59)      # Slate 800
    c_gold = RGBColor(180, 83, 9)      # Amber 700

    # Header / Title Block
    p_pre = doc.add_paragraph()
    p_pre.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r_pre = p_pre.add_run("HWB-DOC-SAL-2026-CH01 | OPTION 1 TERM LOCK (ENFORCED)")
    r_pre.font.size = Pt(8)
    r_pre.font.bold = True
    r_pre.font.color.rgb = c_slate

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title1 = p_title.add_run("HWB CLEANING SERVICES LLC\n")
    r_title1.font.size = Pt(16)
    r_title1.font.bold = True
    r_title1.font.color.rgb = c_navy

    r_title2 = p_title.add_run("COMMERCIAL CHILDCARE & EDUCATIONAL FACILITY SERVICE AGREEMENT\n")
    r_title2.font.size = Pt(13)
    r_title2.font.bold = True
    r_title2.font.color.rgb = c_blue

    r_title3 = p_title.add_run("Master Scope of Work, Technical Hygiene Standards & Binding Commercial Contract")
    r_title3.font.size = Pt(10)
    r_title3.font.italic = True
    r_title3.font.color.rgb = c_slate

    doc.add_paragraph() # Spacer

    # Executive Cover Letter Box
    t_letter = doc.add_table(rows=1, cols=1)
    t_letter.alignment = WD_TABLE_ALIGNMENT.CENTER
    c_let = t_letter.cell(0, 0)
    set_cell_background(c_let, "F8FAFC")
    set_cell_margins(c_let, top=140, bottom=140, left=180, right=180)
    
    p_let = c_let.paragraphs[0]
    r_let_h = p_let.add_run("PROPOSAL & SERVICE COMMITMENT LETTER\n\n")
    r_let_h.font.bold = True
    r_let_h.font.size = Pt(11)
    r_let_h.font.color.rgb = c_navy

    p_let_b = c_let.add_paragraph()
    p_let_b.paragraph_format.line_spacing = 1.15
    r_body = p_let_b.add_run(
        "DATE: October 04, 2026 (or Target Proposal Date)\n"
        "PREPARED FOR: Center Director / Executive Facilities Management\n"
        "CLIENT / ENTITY: Educational Partner / Commercial Childcare Facility\n"
        "FACILITY ADDRESS: [Primary Facility Address / Center Name, City, TX]\n"
        "PREPARED BY: Humberto Dominguez, Chief Executive Officer\n"
        "OFFICE: HWB Cleaning Services LLC | 10925 Estate Ln., Suite 225, Dallas, TX 75238\n"
        "DIRECT LINE: 972-800-7808 | EMAIL: hdominguez@hwbcleaning.com | WEB: www.hwbcleaning.com\n\n"
        "Dear Center Director & Educational Leaders,\n\n"
        "Thank you for the opportunity to present this Comprehensive Facility Care & Disinfection Proposal for your school. "
        "At HWB Cleaning Services LLC ('HWB'), we recognize that maintaining an educational and licensed childcare facility "
        "is fundamentally different from cleaning a standard commercial office. Your facility demands strict adherence to "
        "Texas Child Care Regulation (TCCR) Chapter 746 Minimum Standards, child-safe hospital-grade pathogen containment, "
        "and verifiable indoor air quality that protects enrollment attendance and teacher retention.\n\n"
        "We assign dedicated, thoroughly vetted, background-checked, and badged custodial technicians trained exclusively in "
        "early childhood center hygiene. This proposal outlines our customized nightly maintenance program, our transparent "
        "Option 1 Fixed-Term Pricing Matrix with bundled floor maintenance, and our binding commercial agreement designed "
        "for uninterrupted operational excellence.\n\n"
        "Sincerely,\n\n"
        "Humberto Dominguez, CEO\n"
        "HWB Cleaning Services LLC"
    )
    r_body.font.size = Pt(9.5)
    r_body.font.color.rgb = c_dark

    doc.add_page_break()

    # SECTION 1: THE SIGMAFIDELITY™ CHILDCARE STANDARD
    p_s1 = doc.add_paragraph()
    r_s1 = p_s1.add_run("SECTION 1: THE SIGMAFIDELITY™ CHILDCARE HYGIENE STANDARD")
    r_s1.font.size = Pt(12)
    r_s1.font.bold = True
    r_s1.font.color.rgb = c_navy

    intro_p = doc.add_paragraph()
    intro_p.paragraph_format.line_spacing = 1.15
    intro_r = intro_p.add_run(
        "Commercial childcare centers face unique regulatory and operational pressures. Illness outbreaks directly decrease student "
        "attendance, generate parent complaints, and trigger state health inspection citations. HWB bridges this gap with an industrial-grade "
        "Poka-Yoke hygiene protocol built specifically for educational environments:"
    )
    intro_r.font.size = Pt(9.5)
    intro_r.font.color.rgb = c_dark

    # 4 Key Pillars Table
    t_pillars = doc.add_table(rows=5, cols=2)
    t_pillars.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers = ["Operational Pillar", "Technical Specification & Value to Center Director"]
    for i, h in enumerate(headers):
        cell = t_pillars.cell(0, i)
        set_cell_background(cell, "0F172A")
        set_cell_margins(cell, top=100, bottom=100, left=120, right=120)
        p = cell.paragraphs[0]
        r = p.add_run(h)
        r.font.bold = True
        r.font.size = Pt(9.5)
        r.font.color.rgb = RGBColor(255, 255, 255)

    pillars_data = [
        ("1. Texas Licensing Compliance (TCCR Chapter 746)", 
         "Strict 3-step sanitation process (clean, rinse, sanitize with EPA-registered quaternary solution) across all diaper changing stations, hand sinks, toddler toilets, and food contact tables to ensure 100% inspection-ready state standards every morning."),
        ("2. Color-Coded Cross-Contamination Elimination",
         "Strict 4-color microfiber system: RED (Toilet bowls, urinals, diaper disposal); YELLOW (Restroom sinks, dispensers); BLUE (Glass, mirrors, door windows); GREEN (Classroom desks, cots, high-touch points). Restroom pathogens are physically barred from classroom surfaces."),
        ("3. Indoor Air Quality & CRI Gold HEPA Filtration",
         "All carpeting and educational mats are vacuumed using commercial ProTeam HEPA backpack units capturing 99.97% of airborne particulate down to 0.3 microns (including dust mites, pollen, and chalk residue), significantly reducing respiratory irritants for children and staff."),
        ("4. 24-Hour Emergency Outbreak Response",
         "Immediate rapid dispatch of electrostatic disinfection crews upon confirmed school outbreaks (Norovirus, Flu, RSV, Hand-Foot-and-Mouth disease, Measles) at zero additional labor surcharge during the contract term.")
    ]

    for row_idx, (col0, col1) in enumerate(pillars_data, start=1):
        bg = "FFFFFF" if row_idx % 2 == 1 else "F8FAFC"
        c0 = t_pillars.cell(row_idx, 0)
        c1 = t_pillars.cell(row_idx, 1)
        set_cell_background(c0, bg)
        set_cell_background(c1, bg)
        set_cell_margins(c0, top=90, bottom=90, left=120, right=120)
        set_cell_margins(c1, top=90, bottom=90, left=120, right=120)

        p0 = c0.paragraphs[0]
        r0 = p0.add_run(col0)
        r0.font.bold = True
        r0.font.size = Pt(9)
        r0.font.color.rgb = c_navy

        p1 = c1.paragraphs[0]
        r1 = p1.add_run(col1)
        r1.font.size = Pt(8.8)
        r1.font.color.rgb = c_dark

    doc.add_paragraph() # Spacer

    # SECTION 2: UPDATED PRICING MATRIX & SERVICE COMMITMENT
    p_s2 = doc.add_paragraph()
    r_s2 = p_s2.add_run("SECTION 2: TRANSPARENT PRICING & SERVICE COMMITMENT (OPTION 1 TERM LOCK)")
    r_s2.font.size = Pt(12)
    r_s2.font.bold = True
    r_s2.font.color.rgb = c_navy

    p_pintro = doc.add_paragraph()
    r_pi = p_pintro.add_run(
        "Pricing is established on industry standard time-motion values (ISSA / BSCAI standards) allocating an average of "
        "2.5 to 3.0 labor hours daily to ensure unhurried, exhaustive sanitization. This agreement is executed under the "
        "Option 1 Fixed-Term Lock, guaranteeing complete price stability for the client while committing HWB's top-tier "
        "trained educational custodial team."
    )
    r_pi.font.size = Pt(9.5)
    r_pi.font.color.rgb = c_dark

    t_price = doc.add_table(rows=9, cols=2)
    t_price.alignment = WD_TABLE_ALIGNMENT.CENTER
    
    price_rows = [
        ("Facility Floor Area / Footprint", "10,000 Sq. Ft. (+/- Average Facility Floor Space)"),
        ("Service Frequency & Schedule", "5 Days Per Week (Monday through Friday, servicing window after 6:30 PM)"),
        ("Nightly Labor Allocation", "2.5 - 3.0 Production Hours Per Evening (Trained Academic Custodial Crew)"),
        ("Monthly Regular Janitorial Base Fee", "$2,500.00 / Month ($0.25 / Sq. Ft. | $115.38 / Daily Servicing Visit)"),
        ("Bundled Semi-Annual Floor Care (Amortized)", "INCLUDED ($0.00 / Mo) — 1 Comprehensive VCT Strip & Wax + 2 Deep Carpet Hot-Water Extractions Annually ($3,200.00 Annual Retail Value Included)"),
        ("Emergency Outbreak Electrostatic Disinfection", "INCLUDED ($0.00 / Mo) — Up to 2 Rapid Outbreak Containment Deployments Annually"),
        ("Texas State & Local Sales Tax (8.25%)", "$206.25 / Month (Mandatory Texas Sales Tax on Non-Residential Janitorial)"),
        ("TOTAL MONTHLY INVOICE (With Tax)", "$2,706.25 / Month ($32,475.00 / Year All-Inclusive Gross Invoice)"),
        ("Contract Commitment Structure", "OPTION 1 FIRM TERM LOCK: 12-Month or 24-Month Fixed Agreement (Protected Pricing)")
    ]

    for row_idx, (c0_text, c1_text) in enumerate(price_rows):
        bg = "EFF6FF" if row_idx == 7 else ("F8FAFC" if row_idx % 2 == 1 else "FFFFFF")
        c0 = t_price.cell(row_idx, 0)
        c1 = t_price.cell(row_idx, 1)
        set_cell_background(c0, bg)
        set_cell_background(c1, bg)
        set_cell_margins(c0, top=80, bottom=80, left=120, right=120)
        set_cell_margins(c1, top=80, bottom=80, left=120, right=120)

        p0 = c0.paragraphs[0]
        r0 = p0.add_run(c0_text)
        r0.font.bold = True
        r0.font.size = Pt(9.2)
        r0.font.color.rgb = c_navy if row_idx != 7 else c_blue

        p1 = c1.paragraphs[0]
        r1 = p1.add_run(c1_text)
        r1.font.bold = (row_idx in [3, 7, 8])
        r1.font.size = Pt(9)
        r1.font.color.rgb = c_navy if row_idx == 7 else c_dark

    doc.add_page_break()

    # SECTION 3: SCHEDULE A - CLEANING SPECIFICATIONS
    p_s3 = doc.add_paragraph()
    r_s3 = p_s3.add_run("SECTION 3: SCHEDULE A — CHILDCARE CLEANING & DISINFECTION SPECIFICATIONS")
    r_s3.font.size = Pt(12)
    r_s3.font.bold = True
    r_s3.font.color.rgb = c_navy

    specs = [
        ("A. CLASSROOMS, ACTIVITY ROOMS & COMMON HALLWAYS", [
            "Empty all waste receptacles; replace trash can liners daily; transport collected trash directly to on-site dumpsters.",
            "Disinfect all high-touch wall switch plates, door handles, push plates, and kick plates using hospital-grade EPA disinfectant.",
            "Damp wipe and sanitize child activity tables, shared desks, counter tops, and teacher podiums.",
            "Spot clean child cubbies, lockers, door frames, and classroom entrance vision panels to remove fingerprints, smudges, and adhesive residues.",
            "Remove cobwebs from room corners, vents, ceiling fixtures, and emergency lighting units.",
            "Vacuum all classroom educational carpets and entrance walk-off mats with CRI Gold HEPA backpack equipment.",
            "Damp mop all hard-surface classroom flooring (VCT, vinyl plank, linoleum) with neutral disinfectant floor cleaner."
        ]),
        ("B. INFANT & TODDLER CARE MODULES", [
            "Disinfect diaper changing station pads, surrounding side-guard rails, and adjacent wall surfaces using state-approved neutral sanitizer.",
            "Empty, disinfect, and re-line interior and exterior surfaces of diaper disposal pails and diaper trash containers.",
            "Wipe down and sanitize non-porous surfaces of toddler feeding chairs, high-chair trays, and wipeable crib frames.",
            "Disinfect hand-washing sinks, faucets, water-control levers, and surrounding splash tiles in toddler areas.",
            "Mop infant room floors with dedicated child-safe microfiber mops using dye-free and fragrance-free neutral cleaning solution."
        ]),
        ("C. RESTROOMS & SANITATION FIXTURES (RED / YELLOW PROTOCOL)", [
            "Clean, descale, and disinfect interior and exterior of all toilet bowls, urinals, and toddler-sized plumbing fixtures.",
            "Scrub and disinfect all wash basins, sinks, chrome faucets, and surrounding countertop surfaces.",
            "Clean and polish all restroom mirrors, soap dispenser levers, and paper towel dispenser touch points.",
            "Wipe down and sanitize stall partitions, grab bars, latching hardware, and restroom entry doors.",
            "Restock client-provided consumables: hand soap, toilet paper rolls, paper towels, and toilet seat liners.",
            "Sweep hard floor surfaces; damp mop and sanitize ceramic tile floors using odor-eliminating enzyme disinfectant."
        ]),
        ("D. ADMINISTRATIVE OFFICES, RECEPTION & LOBBY ENTRANCE", [
            "Clean both sides of main entrance glass entry doors, side lights, and aluminum framing.",
            "Dust and disinfect reception counter tops, sign-in kiosk stations, pens, and visitor sign-in surfaces.",
            "Vacuum lobby walk-off mats, runners, and administrative office carpeting edge-to-edge.",
            "Dust horizontal surfaces of office desks, file cabinets, and window sills (papers left on desks remain undisturbed).",
            "Empty executive waste containers, replace liners, and disinfect touch points."
        ]),
        ("E. KITCHENETTE, STAFF BREAK ROOM & CONSUMABLES", [
            "Wipe down and disinfect exterior of refrigerators, microwave ovens, ice makers, and coffee stations.",
            "Clean, sanitize, and polish kitchen sinks, faucet fixtures, and surrounding counter surfaces.",
            "Wipe clean break room dining tables and chairs.",
            "Replenish soap dispensers, paper towel holders, and kitchen trash can liners."
        ]),
        ("F. PERIODIC MAINTENANCE SERVICES (BUNDLED IN CONTRACT)", [
            "Semi-Annual VCT Floor Restoration: Machine scrubbing, stripping, and high-solid industrial wax recoating twice per contract year (or once annually depending on selected service schedule).",
            "Semi-Annual Carpet Deep Extraction: Hot-water steam extraction and pathogen disinfection of all educational classroom rugs and heavy-traffic hallway carpets twice per contract year.",
            "Quarterly Low & High Dusting: Deep dust removal from return air grilles, diffusers, ceiling vents, and door frames over 7 feet.",
            "Emergency Pathogen Disinfection: Electrostatic disinfection deployment within 24 hours of reported viral/bacterial outbreak."
        ])
    ]

    for title, items in specs:
        p_sub = doc.add_paragraph()
        r_sub = p_sub.add_run(title)
        r_sub.font.bold = True
        r_sub.font.size = Pt(10)
        r_sub.font.color.rgb = c_navy

        for item in items:
            p_item = doc.add_paragraph(style='List Bullet')
            p_item.paragraph_format.line_spacing = 1.1
            p_item.paragraph_format.space_after = Pt(2)
            r_item = p_item.add_run(item)
            r_item.font.size = Pt(8.8)
            r_item.font.color.rgb = c_dark

    doc.add_page_break()

    # SECTION 4: MASTER COMMERCIAL JANITORIAL SERVICE AGREEMENT
    p_s4 = doc.add_paragraph()
    r_s4 = p_s4.add_run("SECTION 4: MASTER COMMERCIAL JANITORIAL TERMS & CONDITIONS\n(OPTION 1 TERM LOCK ENFORCED)")
    r_s4.font.size = Pt(12)
    r_s4.font.bold = True
    r_s4.font.color.rgb = c_navy

    p_preamble = doc.add_paragraph()
    p_preamble.paragraph_format.line_spacing = 1.15
    r_preamble = p_preamble.add_run(
        "This Master Commercial Janitorial Service Agreement ('Agreement') is made and entered into as of the Effective Date "
        "written below, by and between HWB CLEANING SERVICES LLC, a Texas Limited Liability Company, having its primary corporate "
        "address at 10925 Estate Ln., Suite 225, Dallas, TX 75238 ('HWB' or 'Contractor'), and the client entity identified in the "
        "execution block below ('CLIENT'). In consideration of the mutual covenants, representations, and service obligations set forth "
        "herein, the parties agree as follows:"
    )
    r_preamble.font.size = Pt(9)
    r_preamble.font.color.rgb = c_dark

    terms = [
        ("1. SCOPE OF SERVICES & STANDARD OF PERFORMANCE",
         "HWB shall furnish all necessary labor, supervision, specialized equipment, and commercial cleaning chemicals required to "
         "perform the custodial maintenance services outlined in Schedule A ('Services') five (5) days per week (Monday through Friday, "
         "excluding recognized operational holidays). Services shall be executed in a professional, workmanlike manner adhering to "
         "Texas Child Care Regulation (TCCR) Chapter 746 hygiene standards and commercial best practices."),

        ("2. MATERIALS, EQUIPMENT & CONSUMABLES ALLOCATION",
         "HWB will provide all commercial machinery (including CRI Gold-rated HEPA vacuums, auto-scrubbers, floor machines), microfiber "
         "mopping systems, and hospital-grade EPA-registered disinfectants. CLIENT shall be solely responsible for furnishing, stocking, "
         "and providing on-site an adequate inventory of all consumable supplies, specifically: paper towels, toilet tissue, hand soap, "
         "and heavy-duty plastic trash liners. If CLIENT requests HWB to provide consumables, such supplies shall be billed separately "
         "at cost plus a standard fifteen percent (15%) procurement management fee."),

        ("3. TERM OF AGREEMENT & OPTION 1 TERM LOCK (NO TERMINATION FOR CONVENIENCE)",
         "This Agreement shall commence on the Effective Date and shall remain in full force and effect for an initial firm fixed term "
         "of twelve (12) calendar months (or twenty-four (24) months if selected in Schedule B) ('Initial Term'). The parties agree that "
         "under this Option 1 Term Lock structure, neither party possesses the right to terminate this Agreement for convenience. Upon "
         "expiration of the Initial Term, this Agreement shall automatically renew for successive twelve (12) month renewal periods unless "
         "either party delivers written notice of non-renewal at least sixty (60) days prior to the expiration of the then-current term."),

        ("4. TERMINATION FOR CAUSE & MANDATORY 30-DAY RIGHT TO CURE",
         "Either party may terminate this Agreement solely 'For Cause' if the other party materially defaults in the performance of its "
         "contractual obligations. In the event CLIENT identifies a material cleaning deficiency or service breach, CLIENT must provide "
         "HWB with immediate, detailed written notice specifying the exact non-conforming areas accompanied by photographic documentation. "
         "HWB shall be afforded a mandatory period of thirty (30) calendar days from receipt of said written notice ('Cure Period') to "
         "inspect, re-clean, and remediate the identified deficiency. If HWB cures the deficiency within the Cure Period, this Agreement "
         "shall continue in full force. Termination for Cause may only occur if HWB fails to remedy the material default within the Cure Period."),

        ("5. EARLY TERMINATION LIQUIDATED DAMAGES & FLOOR CARE RECOVERY",
         "If CLIENT cancels, terminates, breaches, or repudiates this Agreement prior to the expiration of the Initial Term without legal "
         "cause, or prevents HWB from performing Services by changing locks or codes, CLIENT acknowledges that HWB will incur substantial "
         "damages including unamortized equipment investment, labor scheduling loss, and overhead allocation. Therefore, CLIENT agrees to "
         "pay HWB as liquidated damages (and not as a penalty) an amount equal to: (a) two (2) full months of regular monthly service billing, "
         "PLUS (b) the full unamortized retail value ($1,500.00 per service) of any complimentary or bundled periodic floor restoration, "
         "tile stripping, or carpet steam extraction services executed by HWB during the preceding twelve (12) months. Said sums shall "
         "become immediately due and payable upon the issuance of the final invoice."),

        ("6. INVOICING, PAYMENT TERMS & FINANCE CHARGES",
         "Invoices are generated and electronically delivered on the first (1st) business day of each service month for that month's regular "
         "service. Payments are due Net thirty (30) days from the invoice date. Any account balance remaining unpaid past the thirtieth (30th) "
         "day shall be deemed delinquent. Delinquent accounts shall accrue a monthly finance charge of one and one-half percent (1.5%) per month "
         "(18% per annum) or the maximum legal rate permissible under Texas law, whichever is less, calculated daily from the due date until paid."),

        ("7. RIGHT TO SUSPEND SERVICES FOR NON-PAYMENT",
         "If any invoice remains unpaid fifteen (15) calendar days past the due date (i.e., 45 days from invoice issuance), HWB reserves the "
         "express right, without further notice and without liability for breach or facility condition, to immediately suspend all cleaning "
         "services until the account is paid in full. Suspension of services shall not relieve CLIENT of its ongoing payment obligations under "
         "the Initial Term."),

        ("8. FACILITY ACCESS, KEYS, ALARMS & LOCKOUT CHARGES",
         "CLIENT shall provide HWB technicians with reliable facility access including functional keys, electronic access fobs, and unique "
         "alarm arming/disarming codes prior to the service start date. CLIENT agrees to notify HWB in writing at least forty-eight (48) hours "
         "prior to any alarm code changes. If an HWB technician arrives at the scheduled facility during the agreed service window and is unable "
         "to gain entry due to deadbolted locks, deactivated fobs, invalid alarm codes, or unauthorized client personnel inside, the visit "
         "shall be billed at one hundred percent (100%) of the regular visit rate, and an additional seventy-five dollar ($75.00) return trip "
         "fee shall apply if re-dispatch is requested. CLIENT shall hold HWB harmless from any municipal false-alarm citations unless caused "
         "by documented gross negligence of HWB technicians."),

        ("9. SCOPE BOUNDARIES & EXCLUDED TASKS",
         "Services are strictly confined to standard commercial janitorial tasks outlined in Schedule A. Regular service expressly excludes: "
         "(a) washing cafeteria cooking utensils, pots, dishes, or kitchen food machinery; (b) staff or student personal laundry; (c) moving "
         "heavy furniture or equipment exceeding twenty-five (25) pounds; (d) exterior parking lot, playground, or landscaping groundskeeping; "
         "and (e) hazardous post-construction demolition cleanup. Biological hazards, human blood, sewage backup, and extensive viral bodily "
         "fluids require certified OSHA Bloodborne Pathogen containment and shall be quoted and billed separately as emergency decontamination."),

        ("10. UTILITIES & WORKING ENVIRONMENT",
         "CLIENT shall furnish continuous, uninterrupted access to running hot and cold water, electrical power outlets, exterior commercial "
         "dumpsters, and a secure locked custodial supply storage closet. CLIENT agrees to maintain safe, habitable indoor climate control "
         "within the facility during servicing hours (interior ambient temperature maintained between 68°F and 78°F). Technicians shall not "
         "be required to perform strenuous labor in unconditioned, extreme thermal environments."),

        ("11. PRE-EXISTING DEFECTS & NORMAL WEAR-AND-TEAR",
         "HWB's services provide routine hygiene and custodial maintenance, not structural restoration or resurfacing. HWB shall not be "
         "held liable for pre-existing carpet staining, permanent ink/dye bleed, chemical discoloration, worn subflooring, fractured vinyl tile, "
         "loose cove base, faded painted surfaces, or aged grout deterioration resulting from historical facility wear or client usage."),

        ("12. PERSONNEL NON-SOLICITATION & LIQUIDATED DAMAGES",
         "CLIENT acknowledges that HWB invests substantial financial resources in screening, FBI fingerprinting, background vetting, and "
         "training its custodial personnel. CLIENT agrees that during the term of this Agreement and for a period of one hundred eighty (180) "
         "days following termination, CLIENT shall not directly or indirectly hire, solicit, employ, or contract with any employee, technician, "
         "or subcontractor of HWB. In the event of a breach of this covenant, CLIENT agrees to pay HWB as agreed liquidated damages a placement "
         "and training recovery fee equal to five thousand dollars ($5,000.00) per individual within ten (10) days of hiring."),

        ("13. ANNUAL COST-OF-LIVING PRICE ESCALATION (COLA)",
         "To offset documented annual inflation in commercial cleaning supplies, fuel, insurance, and statutory minimum wage adjustments, "
         "the monthly base service fee shall automatically adjust upward by four percent (4.0%) upon each twelve (12) month anniversary "
         "of the Effective Date upon contract renewal."),

        ("14. RECOGNIZED OPERATIONAL HOLIDAYS",
         "HWB observes the following six (6) annual operational holidays during which facilities are not serviced: New Year's Day, Memorial Day, "
         "Independence Day (Fourth of July), Labor Day, Thanksgiving Day, and Christmas Day. Monthly billing remains fixed and is calculated "
         "based on a yearly fifty-two (52) week operational average."),

        ("15. LIMITATION OF LIABILITY & PROPERTY CLAIMS",
         "HWB maintains comprehensive General Liability, Property Damage, and Workers' Compensation insurance policies. In no event shall "
         "HWB's total aggregate liability arising out of or related to this Agreement exceed the total fees paid by CLIENT to HWB during the "
         "preceding three (3) calendar months, or the applicable limits of HWB's insurance coverage, whichever is greater. Under no circumstances "
         "shall either party be liable for indirect, special, incidental, punitive, or consequential damages (including lost tuition, student "
         "enrollment loss, or business interruption). Any claim for property damage or loss must be reported to HWB in writing with photographic "
         "evidence within forty-eight (48) hours of the alleged occurrence; failure to report within 48 hours constitutes an irrevocable waiver."),

        ("16. FORCE MAJEURE & WEATHER EMERGENCIES",
         "Neither party shall be deemed in breach of this Agreement for any failure or delay in performance resulting from acts of God, "
         "severe freezing weather, ice storms, tornado damage, electric power grid failure, flooding, pandemic quarantine orders, or "
         "mandatory emergency school closures declared by municipal, state, or federal authorities."),

        ("17. GOVERNING LAW, TEXAS VENUE & ATTORNEY'S FEES",
         "This Agreement shall be governed, interpreted, and enforced in accordance with the laws of the State of Texas, without regard to "
         "conflict of laws principles. The parties irrevocably agree that exclusive venue and jurisdiction for any legal action or proceeding "
         "arising out of this Agreement shall lie in the state district courts located in Dallas County, Texas (or Denton County, Texas, at "
         "HWB's election). In any action to enforce this Agreement or collect delinquent invoices, the prevailing party shall be entitled "
         "to recover all reasonable attorney's fees, expert witness fees, and court costs."),

        ("18. ENTIRE AGREEMENT, SEVERABILITY & EXECUTION",
         "This Agreement, together with Schedule A and Schedule B, constitutes the entire understanding between the parties and supersedes all "
         "prior verbal discussions, quotes, or proposals. If any provision is deemed invalid by a court of competent jurisdiction, the remaining "
         "provisions shall remain in full force. This Agreement may be executed in counterparts and via electronic signature (PDF / DocuSign), "
         "each of which shall be deemed an original binding document.")
    ]

    for title, text in terms:
        p_t = doc.add_paragraph()
        p_t.paragraph_format.line_spacing = 1.15
        p_t.paragraph_format.space_after = Pt(4)
        
        r_num = p_t.add_run(title + "\n")
        r_num.font.bold = True
        r_num.font.size = Pt(9.2)
        r_num.font.color.rgb = c_navy

        r_body = p_t.add_run(text)
        r_body.font.size = Pt(8.8)
        r_body.font.color.rgb = c_dark

    doc.add_page_break()

    # SECTION 5: AUTHORIZATION & SIGNATURE BLOCKS
    p_s5 = doc.add_paragraph()
    r_s5 = p_s5.add_run("SECTION 5: MUTUAL EXECUTION & BINDING AUTHORIZATION")
    r_s5.font.size = Pt(12)
    r_s5.font.bold = True
    r_s5.font.color.rgb = c_navy

    p_sig_intro = doc.add_paragraph()
    r_sigi = p_sig_intro.add_run(
        "IN WITNESS WHEREOF, the authorized representatives of HWB CLEANING SERVICES LLC and CLIENT have executed this "
        "Commercial Childcare Janitorial Service Agreement as of the Effective Date written below, agreeing to all terms, "
        "specifications, and the Option 1 Term Lock commitment."
    )
    r_sigi.font.size = Pt(9)
    r_sigi.font.color.rgb = c_dark

    doc.add_paragraph() # Spacer

    t_sig = doc.add_table(rows=6, cols=2)
    t_sig.alignment = WD_TABLE_ALIGNMENT.CENTER

    sig_headers = ["FOR CLIENT (EDUCATIONAL ENTITY)", "FOR HWB CLEANING SERVICES LLC"]
    for i, h in enumerate(sig_headers):
        cell = t_sig.cell(0, i)
        set_cell_background(cell, "0F172A")
        set_cell_margins(cell, top=100, bottom=100, left=120, right=120)
        p = cell.paragraphs[0]
        r = p.add_run(h)
        r.font.bold = True
        r.font.size = Pt(9.5)
        r.font.color.rgb = RGBColor(255, 255, 255)

    sig_rows = [
        ("Company / School: ____________________________", "Company: HWB Cleaning Services LLC"),
        ("Authorized Signature: ________________________", "Authorized Signature: ________________________"),
        ("Printed Name: _______________________________", "Printed Name: Humberto Dominguez"),
        ("Executive Title: ____________________________", "Executive Title: Chief Executive Officer"),
        ("Execution Date: _____________________________", "Execution Date: _____________________________")
    ]

    for row_idx, (c0_text, c1_text) in enumerate(sig_rows, start=1):
        bg = "FFFFFF" if row_idx % 2 == 1 else "F8FAFC"
        c0 = t_sig.cell(row_idx, 0)
        c1 = t_sig.cell(row_idx, 1)
        set_cell_background(c0, bg)
        set_cell_background(c1, bg)
        set_cell_margins(c0, top=110, bottom=110, left=120, right=120)
        set_cell_margins(c1, top=110, bottom=110, left=120, right=120)

        p0 = c0.paragraphs[0]
        r0 = p0.add_run(c0_text)
        r0.font.bold = (row_idx in [1, 2])
        r0.font.size = Pt(9.2)
        r0.font.color.rgb = c_navy

        p1 = c1.paragraphs[0]
        r1 = p1.add_run(c1_text)
        r1.font.bold = (row_idx in [1, 2])
        r1.font.size = Pt(9.2)
        r1.font.color.rgb = c_navy

    # Save to Target Locations
    out_dir = "/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-QUOTES/EDUCATIONAL-CHILDCARE"
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "HWB-STANDARD-CHILDCARE-CLEANING-CONTRACT-2026.docx")
    doc.save(out_file)
    print(f"Generated master contract at: {out_file}")

    # Mirror to HWB-LEGAL
    legal_dir = "/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-LEGAL"
    os.makedirs(legal_dir, exist_ok=True)
    legal_file = os.path.join(legal_dir, "HWB-STANDARD-CHILDCARE-SERVICE-AGREEMENT-2026.docx")
    shutil.copyfile(out_file, legal_file)
    print(f"Mirrored legal contract to: {legal_file}")

if __name__ == "__main__":
    create_document()
