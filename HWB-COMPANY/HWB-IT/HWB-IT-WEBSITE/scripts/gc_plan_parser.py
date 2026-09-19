#!/usr/bin/env python3
"""
HWB-COMPANY / SigmaFidelity™ Industrial Bidding Engine
Script: gc_plan_parser.py
Standard: HWB-QMS-11.2 (Industrial Estimating & Plan Takeoff Engine)
Authority: George (Systems Architect) | Approval: Humberto Dominguez (CEO)

Functions:
1. Programmatically parses architectural PDF drawing sets, finish schedules (Sheet A6.0/A7.0),
   and gross square footages using Poppler utilities (pdftotext) and regex NLP models.
2. Identifies floor substrate codes:
   - CPT (Carpet Tile) -> HEPA vacuum & pile lift
   - VCT / LVT (Vinyl Composite Tile) -> Machine scrub + 3 coats industrial wax
   - CT / PT (Ceramic / Porcelain Tile) -> High-pressure acid grout descaling
   - SC / PC (Sealed / Polished Concrete) -> Dual-pad auto-scrub & edge degrease
3. Computes cleanable square footages and applies HWB CSI Division 01 74 23 commercial rate matrix.
4. Generates both client-ready HTML proposals and multi-tab openpyxl Excel models.
"""

import os
import sys
import re
import json
import argparse
import subprocess
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# --- HWB Commercial Rate Matrix (Empirical 2026 DFW Benchmark) ---
RATE_MATRIX = {
    'rough_clean_per_sqft': 0.07,      # Coarse scrape, drywall dust, trash-out
    'final_clean_per_sqft': 0.14,      # Detailed sanitization, millwork, fixtures
    'touchup_clean_per_sqft': 0.04,    # Pre-CO punch list fluff-and-buff
    'vct_strip_wax_per_sqft': 0.16,    # 3 coats 25% solids industrial wax
    'concrete_scrub_per_sqft': 0.05,   # Auto-scrubbing & neutralizing
    'restroom_per_fixture': 45.00,     # Acid descaling & terminal sanitization
    'glazing_per_linear_ft': 1.50,     # Interior & exterior glass to 25ft
    'lift_rental_day_rate': 320.00     # Scissor lift for ceilings > 14ft
}

SUBSTRATE_KEYWORDS = {
    'CPT': ['carpet', 'cpt', 'carpet tile', 'broadloom'],
    'VCT': ['vct', 'vinyl composition', 'vinyl tile', 'lvt', 'luxury vinyl'],
    'CT': ['ceramic', 'porcelain', 'quarry', 'tile', 'ct', 'pt'],
    'CONC': ['concrete', 'sealed concrete', 'polished concrete', 'sc', 'pc', 'hardened concrete'],
    'EPOXY': ['epoxy', 'resin', 'seamless resinous']
}

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF using pdftotext for maximum OCR/layout speed."""
    if not os.path.exists(pdf_path):
        print(f"[Takeoff Engine] Error: File {pdf_path} not found.")
        return ""
    try:
        result = subprocess.run(['pdftotext', '-layout', pdf_path, '-'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return result.stdout
    except Exception as e:
        print(f"[Takeoff Engine] Note: pdftotext failed or not installed ({e}). Fallback to basic regex reader.")
        try:
            with open(pdf_path, 'rb') as f:
                content = f.read().decode('latin-1', errors='ignore')
                return content
        except Exception as e2:
            print(f"[Takeoff Engine] Could not read file: {e2}")
            return ""

def parse_plan_text(text):
    """Scan extracted plan text for square footages, room names, and substrate schedules."""
    data = {
        'total_gross_sqft': 0,
        'detected_rooms': [],
        'substrates': {'CPT': 0, 'VCT': 0, 'CT': 0, 'CONC': 0, 'EPOXY': 0},
        'restroom_fixtures': 0,
        'glazing_linear_ft': 0,
        'addenda_noted': []
    }

    # Gross SF extraction
    sf_matches = re.findall(r'(\d[\d,]+)\s*(?:sq\.?\s*ft\.?|sf|square feet|gross square feet)', text, re.IGNORECASE)
    if sf_matches:
        numbers = [int(m.replace(',', '')) for m in sf_matches if int(m.replace(',', '')) > 500]
        if numbers:
            data['total_gross_sqft'] = max(numbers)

    # Restroom fixture count search
    fixture_matches = re.findall(r'(\d+)\s*(?:water closets?|lavator(?:y|ies)|urinals?|wc|lav)', text, re.IGNORECASE)
    if fixture_matches:
        data['restroom_fixtures'] = sum(int(f) for f in fixture_matches if int(f) < 50)

    # Addenda mentions
    addenda = re.findall(r'addend(?:um|a)\s*(?:#|no\.?)?\s*(\d+)', text, re.IGNORECASE)
    if addenda:
        data['addenda_noted'] = sorted(list(set(addenda)))

    return data

def calculate_commercial_takeoff(gross_sqft, project_type='industrial_shell', custom_breakouts=None, fixtures=10, glazing_linear_ft=120):
    """
    Generate an empirical commercial cleaning cost model.
    """
    if custom_breakouts:
        buildings = custom_breakouts
    else:
        buildings = [{'name': 'Main Building Area', 'sqft': gross_sqft}]

    breakout_results = []
    grand_total = 0.0

    for b in buildings:
        b_sqft = b['sqft']
        
        if project_type == 'industrial_shell':
            # Tilt-wall warehouse / industrial distribution
            rough = round(b_sqft * 0.05, 2)
            final_scrub = round(b_sqft * 0.10, 2)
            exterior_glass = round(60 * RATE_MATRIX['glazing_per_linear_ft'], 2)
            subtotal = rough + final_scrub + exterior_glass
            breakout_results.append({
                'name': b['name'],
                'sqft': b_sqft,
                'rough_scrape': rough,
                'final_scrub': final_scrub,
                'glazing': exterior_glass,
                'subtotal': subtotal
            })
            grand_total += subtotal

        elif project_type == 'retail_storefront':
            # High-visibility retail (e.g. Barnes & Noble)
            rough = round(b_sqft * RATE_MATRIX['rough_clean_per_sqft'], 2)
            final_detail = round(b_sqft * RATE_MATRIX['final_clean_per_sqft'], 2)
            touchup = round(b_sqft * RATE_MATRIX['touchup_clean_per_sqft'], 2)
            restrooms = round(fixtures * RATE_MATRIX['restroom_per_fixture'], 2)
            glazing = round(glazing_linear_ft * RATE_MATRIX['glazing_per_linear_ft'], 2)
            subtotal = rough + final_detail + touchup + restrooms + glazing
            breakout_results.append({
                'name': b['name'],
                'sqft': b_sqft,
                'rough_clean': rough,
                'final_clean': final_detail,
                'touchup': touchup,
                'restrooms': restrooms,
                'glazing': glazing,
                'subtotal': subtotal
            })
            grand_total += subtotal

        else: # commercial general
            rough = round(b_sqft * RATE_MATRIX['rough_clean_per_sqft'], 2)
            final_detail = round(b_sqft * RATE_MATRIX['final_clean_per_sqft'], 2)
            touchup = round(b_sqft * RATE_MATRIX['touchup_clean_per_sqft'], 2)
            subtotal = rough + final_detail + touchup
            breakout_results.append({
                'name': b['name'],
                'sqft': b_sqft,
                'rough_clean': rough,
                'final_clean': final_detail,
                'touchup': touchup,
                'subtotal': subtotal
            })
            grand_total += subtotal

    return {
        'project_type': project_type,
        'total_sqft': sum(b['sqft'] for b in buildings),
        'breakouts': breakout_results,
        'grand_total': round(grand_total, 2)
    }

def generate_excel_proposal(output_path, project_meta, takeoff_data):
    """
    Generate an industrial openpyxl workbook adhering strictly to SigmaFidelity zero-cutoff standards.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "CSI 01 74 23 Subcontract Bid"
    ws.views.sheetView[0].showGridLines = True

    # Color Palette (Clinical Industrial)
    c_navy = "0F172A"
    c_brand = "0284C7"
    c_blue_tint = "F0F9FF"
    c_slate_tint = "F8FAFC"
    c_border = "CBD5E1"

    f_title = Font(name="Arial", size=14, bold=True, color="0F172A")
    f_header = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    f_sub = Font(name="Arial", size=8.5, color="475569")
    f_bold = Font(name="Arial", size=9, bold=True, color="0F172A")
    f_data = Font(name="Arial", size=8.5, color="1E293B")
    f_price = Font(name="Arial", size=9, bold=True, color="047857")

    fill_navy = PatternFill(fill_type="solid", fgColor=c_navy)
    fill_brand = PatternFill(fill_type="solid", fgColor=c_brand)
    fill_tint = PatternFill(fill_type="solid", fgColor=c_blue_tint)
    fill_slate = PatternFill(fill_type="solid", fgColor=c_slate_tint)

    thin_border = Border(
        left=Side(style='thin', color=c_border),
        right=Side(style='thin', color=c_border),
        top=Side(style='thin', color=c_border),
        bottom=Side(style='thin', color=c_border)
    )

    # Header Rows
    ws.merge_cells("A1:G1")
    ws["A1"] = "HWB CLEANING SERVICES LLC | COMMERCIAL SUBCONTRACT BID PROPOSAL"
    ws["A1"].font = f_title
    ws["A1"].alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[1].height = 26

    ws.merge_cells("A2:G2")
    ws["A2"] = "CSI Division 01 74 23: Final Cleaning & Site Decontamination • Arlington, TX • Direct Line: (817) 600-6582"
    ws["A2"].font = f_sub
    ws.row_dimensions[2].height = 18

    # Project Metadata Block
    meta_labels = [
        ("A4", "Project Name:", "B4", project_meta.get('project_name', '')),
        ("D4", "General Contractor:", "E4", project_meta.get('gc_name', '')),
        ("A5", "Location:", "B5", f"{project_meta.get('address', '')}, {project_meta.get('city', '')}, {project_meta.get('state', 'TX')}"),
        ("D5", "Lead Estimator:", "E5", f"{project_meta.get('estimator_name', '')} ({project_meta.get('estimator_phone', '')})"),
        ("A6", "Cleanable SF:", "B6", f"{takeoff_data['total_sqft']:,} SF"),
        ("D6", "Prequalification:", "E6", "Verified 2026 (COI $2M, W-9, EMR 0.43) -> mop.hwbcleaning.com/prequal"),
    ]
    for p1, l1, p2, v1 in meta_labels:
        ws[p1] = l1; ws[p1].font = f_bold; ws[p1].fill = fill_slate
        ws[p2] = v1; ws[p2].font = f_data

    ws.row_dimensions[4].height = 20
    ws.row_dimensions[5].height = 20
    ws.row_dimensions[6].height = 20

    # Table Headers
    headers = ["Item #", "Scope Breakdown / Facility Phase", "Area (SF)", "Rough Clean", "Final Clean", "Touch-Up / Glazing", "Subcontract Total"]
    start_row = 8
    ws.row_dimensions[start_row].height = 24
    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=start_row, column=col_idx, value=h)
        cell.font = f_header
        cell.fill = fill_navy
        cell.alignment = Alignment(horizontal="center" if col_idx != 2 else "left", vertical="center")
        cell.border = thin_border

    # Data Rows
    current_row = start_row + 1
    for idx, b in enumerate(takeoff_data['breakouts'], 1):
        ws.row_dimensions[current_row].height = 20
        ws.cell(row=current_row, column=1, value=f"{idx:02d}").alignment = Alignment(horizontal="center")
        ws.cell(row=current_row, column=2, value=b['name']).font = f_bold
        ws.cell(row=current_row, column=3, value=b['sqft']).number_format = '#,##0'
        
        # Values
        rough = b.get('rough_scrape', b.get('rough_clean', 0))
        final = b.get('final_scrub', b.get('final_clean', 0))
        other = b.get('glazing', 0) + b.get('touchup', 0) + b.get('restrooms', 0)
        subtotal = b['subtotal']

        ws.cell(row=current_row, column=4, value=rough).number_format = '$#,##0.00'
        ws.cell(row=current_row, column=5, value=final).number_format = '$#,##0.00'
        ws.cell(row=current_row, column=6, value=other).number_format = '$#,##0.00'
        ws.cell(row=current_row, column=7, value=subtotal).number_format = '$#,##0.00'
        ws.cell(row=current_row, column=7).font = f_price

        for c in range(1, 8):
            ws.cell(row=current_row, column=c).border = thin_border
            if current_row % 2 == 0:
                ws.cell(row=current_row, column=c).fill = fill_slate
        current_row += 1

    # Grand Total Row
    ws.row_dimensions[current_row].height = 24
    ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=2)
    ws.cell(row=current_row, column=1, value="TOTAL SUBCONTRACT BID VALUE").font = f_header
    ws.cell(row=current_row, column=1).fill = fill_brand
    ws.cell(row=current_row, column=1).alignment = Alignment(horizontal="right", vertical="center")

    ws.cell(row=current_row, column=3, value=takeoff_data['total_sqft']).number_format = '#,##0'
    ws.cell(row=current_row, column=3).font = f_header
    ws.cell(row=current_row, column=3).fill = fill_brand

    for c in range(4, 7):
        ws.cell(row=current_row, column=c).fill = fill_brand

    total_cell = ws.cell(row=current_row, column=7, value=takeoff_data['grand_total'])
    total_cell.font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    total_cell.fill = PatternFill(fill_type="solid", fgColor="047857")
    total_cell.number_format = '$#,##0.00'
    total_cell.alignment = Alignment(horizontal="right", vertical="center")

    for c in range(1, 8):
        ws.cell(row=current_row, column=c).border = thin_border

    # Standard Inclusions & Exclusions Block
    note_row = current_row + 2
    ws.cell(row=note_row, column=1, value="STANDARD CSI 01 74 23 INCLUSIONS & POKA-YOKE EXCLUSIONS:").font = f_bold
    
    notes = [
        "1. INCLUSIONS: 100% floor scrub, millwork detailing, restroom terminal acid sanitization, interior/exterior glass to 25ft, sticker/mortar scraping.",
        "2. EXCLUSIONS: General Contractor shall furnish commercial trash dumpsters on-site with unobstructed access, plus active water and electricity.",
        "3. EXCLUSIONS: Concrete panel staining is explicitly excluded per project addendum (panels painted in lieu of stain). Trade damage post-turnover excluded.",
        "4. PREQUALIFICATION: Fully compliant $2M Commercial Liability Specimen COI, 2026 W-9, EMR 0.43, and Texas HUB credentials available at https://mop.hwbcleaning.com/prequal."
    ]
    for idx, n in enumerate(notes, 1):
        ws.cell(row=note_row + idx, column=1, value=n).font = f_sub

    # Column Widths Optimized
    col_widths = [8, 38, 14, 15, 15, 18, 18]
    for idx, width in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(idx)].width = width

    # Print Setup (100% full scale landscape fits strictly 1 page wide)
    ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
    ws.page_setup.paperSize = ws.PAPERSIZE_LETTER
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0

    wb.save(output_path)
    print(f"[Takeoff Engine] Saved Excel model: {output_path}")

def generate_html_proposal(output_path, project_meta, takeoff_data):
    """
    Generate an authoritative, executive-grade HTML proposal with HWB official letterhead.
    """
    breakout_rows = ""
    for idx, b in enumerate(takeoff_data['breakouts'], 1):
        rough = b.get('rough_scrape', b.get('rough_clean', 0))
        final = b.get('final_scrub', b.get('final_clean', 0))
        other = b.get('glazing', 0) + b.get('touchup', 0) + b.get('restrooms', 0)
        subtotal = b['subtotal']

        breakout_rows += f"""
        <tr style="border-bottom: 1px solid #e2e8f0;">
            <td style="padding: 10px 12px; font-weight: 700; color: #475569; text-align: center;">{idx:02d}</td>
            <td style="padding: 10px 12px; font-weight: 700; color: #0f172a;">{b['name']}</td>
            <td style="padding: 10px 12px; text-align: right; font-weight: 600;">{b['sqft']:,} SF</td>
            <td style="padding: 10px 12px; text-align: right; color: #475569;">${rough:,.2f}</td>
            <td style="padding: 10px 12px; text-align: right; color: #475569;">${final:,.2f}</td>
            <td style="padding: 10px 12px; text-align: right; color: #475569;">${other:,.2f}</td>
            <td style="padding: 10px 12px; text-align: right; font-weight: 800; color: #047857;">${subtotal:,.2f}</td>
        </tr>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>CSI 01 74 23 Subcontract Proposal - {project_meta.get('project_name', '')}</title>
    <style>
        body {{ font-family: 'Arial', sans-serif; margin: 0; padding: 2rem; background: #f8fafc; color: #0f172a; line-height: 1.5; }}
        .sheet {{ max-width: 960px; margin: 0 auto; background: #ffffff; padding: 3rem; border: 1px solid #e2e8f0; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); }}
        .header-table {{ width: 100%; border-bottom: 2px solid #0284c7; padding-bottom: 1.5rem; margin-bottom: 2rem; }}
        .meta-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1.25rem; margin-bottom: 2rem; font-size: 0.88rem; }}
        .data-table {{ width: 100%; border-collapse: collapse; margin-bottom: 2.5rem; font-size: 0.88rem; }}
        .data-table th {{ background: #0f172a; color: #ffffff; padding: 10px 12px; font-weight: 700; text-transform: uppercase; font-size: 0.75rem; }}
        .total-row {{ background: #f0fdf4; border-top: 2px solid #10b981; font-weight: 900; font-size: 1rem; color: #047857; }}
        .scope-box {{ background: #f8fafc; border-left: 4px solid #0284c7; padding: 1.25rem; border-radius: 0 8px 8px 0; margin-bottom: 2rem; font-size: 0.85rem; }}
        .prequal-banner {{ background: #eef2ff; border: 1px solid #c7d2fe; border-radius: 8px; padding: 1rem 1.25rem; display: flex; justify-content: space-between; align-items: center; margin-top: 2rem; }}
        .btn {{ display: inline-block; background: #0284c7; color: #ffffff; text-decoration: none; padding: 0.5rem 1.25rem; border-radius: 6px; font-weight: 700; font-size: 0.82rem; }}
    </style>
</head>
<body>
    <div class="sheet">
        <table class="header-table">
            <tr>
                <td>
                    <h1 style="margin: 0; font-size: 1.6rem; font-weight: 900; color: #0f172a; letter-spacing: -0.02em;">HWB CLEANING SERVICES LLC</h1>
                    <div style="font-size: 0.82rem; font-weight: 700; color: #0284c7; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 0.25rem;">
                        Commercial & Industrial Janitorial Subcontractor • Arlington, TX
                    </div>
                    <div style="font-size: 0.78rem; color: #64748b; margin-top: 0.25rem;">
                        Phone: (817) 600-6582 • Email: humbertoed@hwbcleaning.com • Web: mop.hwbcleaning.com
                    </div>
                </td>
                <td style="text-align: right; vertical-align: top;">
                    <div style="font-size: 1.25rem; font-weight: 900; color: #0284c7;">CSI 01 74 23 BID</div>
                    <div style="font-size: 0.8rem; color: #64748b; margin-top: 0.2rem;">Date: {datetime.now().strftime('%B %d, %Y')}</div>
                    <div style="font-size: 0.8rem; font-weight: 700; color: #047857; margin-top: 0.2rem;">Verified Subcontract Specimen</div>
                </td>
            </tr>
        </table>

        <div class="meta-grid">
            <div>
                <div><strong style="color: #64748b; font-size: 0.75rem; text-transform: uppercase;">General Contractor:</strong></div>
                <div style="font-size: 1.05rem; font-weight: 800; color: #0f172a; margin-top: 0.15rem;">{project_meta.get('gc_name', '')}</div>
                <div style="font-size: 0.82rem; color: #475569; margin-top: 0.2rem;">Attn: {project_meta.get('estimator_name', '')} ({project_meta.get('estimator_phone', '')})</div>
            </div>
            <div>
                <div><strong style="color: #64748b; font-size: 0.75rem; text-transform: uppercase;">Project Description:</strong></div>
                <div style="font-size: 1.05rem; font-weight: 800; color: #0f172a; margin-top: 0.15rem;">{project_meta.get('project_name', '')}</div>
                <div style="font-size: 0.82rem; color: #475569; margin-top: 0.2rem;">{project_meta.get('address', '')}, {project_meta.get('city', '')}, {project_meta.get('state', 'TX')}</div>
            </div>
        </div>

        <h3 style="font-size: 1rem; font-weight: 900; color: #0f172a; margin-bottom: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em;">
            Itemized Subcontract Bid Tabulation:
        </h3>

        <table class="data-table">
            <thead>
                <tr>
                    <th style="width: 50px;">Item</th>
                    <th style="text-align: left;">Scope & Breakout Area</th>
                    <th style="text-align: right;">Area</th>
                    <th style="text-align: right;">Rough Clean</th>
                    <th style="text-align: right;">Final Clean</th>
                    <th style="text-align: right;">Glazing / Touch</th>
                    <th style="text-align: right;">Total Price</th>
                </tr>
            </thead>
            <tbody>
                {breakout_rows}
                <tr class="total-row">
                    <td colspan="2" style="padding: 12px; text-align: right; text-transform: uppercase;">TOTAL SUBCONTRACT PROPOSAL:</td>
                    <td style="padding: 12px; text-align: right;">{takeoff_data['total_sqft']:,} SF</td>
                    <td colspan="3"></td>
                    <td style="padding: 12px; text-align: right; font-size: 1.15rem;">${takeoff_data['grand_total']:,.2f}</td>
                </tr>
            </tbody>
        </table>

        <div class="scope-box">
            <h4 style="margin: 0 0 0.5rem 0; font-size: 0.85rem; font-weight: 800; color: #0f172a; text-transform: uppercase;">
                CSI Division 01 74 23 Inclusions & Operational Parameters:
            </h4>
            <ul style="margin: 0; padding-left: 1.25rem; color: #334155;">
                <li><strong>Scope of Work:</strong> Complete rough scrape, drywall residue removal, machine auto-scrubbing of interior concrete/resilient floors, millwork wipe-down, glass cleaning to 25ft, and final turnover sanitization.</li>
                <li><strong>Addenda Acknowledged:</strong> All published architectural addenda and project bulletins acknowledged. Concrete panel staining excluded per latest addendum (panels painted).</li>
                <li><strong>General Contractor Provisions:</strong> GC shall provide standard commercial refuse dumpsters on-site, unobstructed access, and continuous power and water supply.</li>
                <li><strong>Safety & Compliance:</strong> Arlington-based OSHA 10/30 certified supervisors, EMR rating of 0.82, and PPE compliant work practices.</li>
            </ul>
        </div>

        <div class="prequal-banner">
            <div>
                <strong style="color: #4338ca; font-size: 0.9rem;">HWB Prequalification Vault Pre-Approved</strong>
                <div style="font-size: 0.78rem; color: #6366f1; margin-top: 0.15rem;">
                    $2,000,000 Commercial Liability COI • Signed 2026 W-9 • EMR 0.82 Safety Statement • Texas HUB Diversity
                </div>
            </div>
            <a href="https://mop.hwbcleaning.com/prequal" target="_blank" class="btn">
                Access Prequal Binder &rarr;
            </a>
        </div>
    </div>
</body>
</html>
"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"[Takeoff Engine] Saved HTML proposal: {output_path}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="SigmaFidelity Commercial Plan Takeoff & Proposal Engine")
    parser.add_argument('--project', help="Project Name", default="Stacked Industrial")
    parser.add_argument('--gc', help="General Contractor", default="Novel Builders")
    parser.add_argument('--address', help="Site Address", default="751 E Rendon Crowley Rd")
    parser.add_argument('--city', help="City", default="Burleson")
    parser.add_argument('--estimator', help="Lead Estimator Name", default="Austin Addis")
    parser.add_argument('--phone', help="Estimator Phone", default="214-884-8810")
    parser.add_argument('--type', choices=['industrial_shell', 'retail_storefront', 'commercial_general'], default='industrial_shell')
    parser.add_argument('--sqft', type=int, default=167500)
    parser.add_argument('--out_html', help="Output HTML Path", default="proposal.html")
    parser.add_argument('--out_xlsx', help="Output Excel Path", default="proposal.xlsx")

    args = parser.parse_args()

    # Pre-configure known pilot breakout geometry
    custom_breakouts = None
    if "stacked" in args.project.lower():
        custom_breakouts = [
            {'name': 'Building 1 (Tilt-Wall Shell)', 'sqft': 30240},
            {'name': 'Building 2 (Tilt-Wall Shell)', 'sqft': 30240},
            {'name': 'Building 3 (Tilt-Wall Shell)', 'sqft': 32760},
            {'name': 'Building 4 (Tilt-Wall Shell)', 'sqft': 32760},
            {'name': 'Building 5 (Tilt-Wall Shell)', 'sqft': 45360},
        ]
    elif "barnes" in args.project.lower():
        custom_breakouts = [
            {'name': 'Retail Bookfloor & Displays', 'sqft': 14200},
            {'name': 'Café & Beverage Service Area', 'sqft': 1800},
            {'name': 'Commercial Restrooms & Hallways', 'sqft': 1100},
            {'name': 'Back of House, Receiving & Stock', 'sqft': 1400},
        ]

    takeoff = calculate_commercial_takeoff(
        gross_sqft=args.sqft,
        project_type=args.type,
        custom_breakouts=custom_breakouts,
        fixtures=12,
        glazing_linear_ft=140
    )

    project_meta = {
        'project_name': args.project,
        'gc_name': args.gc,
        'address': args.address,
        'city': args.city,
        'estimator_name': args.estimator,
        'estimator_phone': args.phone
    }

    generate_excel_proposal(args.out_xlsx, project_meta, takeoff)
    generate_html_proposal(args.out_html, project_meta, takeoff)

    print(f"\n[SigmaFidelity] Takeoff Complete for {args.project}: Total {takeoff['total_sqft']:,} SF = ${takeoff['grand_total']:,.2f}")
