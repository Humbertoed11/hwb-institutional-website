"""
SigmaFidelity™ EHSQ HTML Formatter & Standalone Envelope Hardener
Standard: HWB-QMS-1.0 & HWB-QMS-7.5
Author: George (Systems Architect)
Purpose: Converts raw SOP snippets into self-contained, publication-grade standalone HTML documents
         with embedded institutional styling, Inter typography, and print layouts.
"""

import os
import json
from datetime import datetime

STANDALONE_HEAD_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} | HWB Cleaning Services LLC</title>
    
    <!-- Institutional Typography & Icons -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">

    <style>
        :root {{
            --brand-navy: #0f294a;
            --brand-blue: #2563eb;
            --brand-emerald: #059669;
            --slate-50: #f8fafc;
            --slate-100: #f1f5f9;
            --slate-200: #e2e8f0;
            --slate-300: #cbd5e1;
            --slate-500: #64748b;
            --slate-600: #475569;
            --slate-700: #334155;
            --slate-800: #1e293b;
            --slate-900: #0f172a;
        }}

        * {{
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            padding: 2.5rem 1rem;
            background-color: var(--slate-50);
            background-image: radial-gradient(#cbd5e1 0.75px, transparent 0.75px);
            background-size: 24px 24px;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            color: var(--slate-700);
            line-height: 1.65;
            -webkit-font-smoothing: antialiased;
        }}

        /* Corporate Masthead Banner */
        .institutional-header {{
            max-width: 1040px;
            margin: 0 auto 1.5rem auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #ffffff;
            padding: 1rem 1.75rem;
            border-radius: 8px;
            border: 1px solid var(--slate-200);
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        }}

        .brand-logo-unit {{
            display: flex;
            align-items: center;
            gap: 0.85rem;
        }}

        .brand-logo-unit i {{
            font-size: 1.75rem;
            color: var(--brand-blue);
        }}

        .brand-name {{
            font-size: 1.05rem;
            font-weight: 900;
            color: var(--brand-navy);
            letter-spacing: -0.02em;
        }}

        .brand-sub {{
            font-size: 0.72rem;
            font-weight: 700;
            color: var(--slate-500);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        .header-actions {{
            display: flex;
            gap: 0.65rem;
            align-items: center;
        }}

        .btn-action {{
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            height: 32px;
            padding: 0 0.85rem;
            font-size: 0.75rem;
            font-weight: 700;
            border-radius: 6px;
            text-decoration: none;
            transition: all 0.15s ease;
            cursor: pointer;
            border: 1px solid var(--slate-300);
            background: #ffffff;
            color: var(--slate-700);
        }}

        .btn-action:hover {{
            background: var(--slate-100);
            border-color: var(--brand-blue);
            color: var(--brand-blue);
        }}

        .btn-primary {{
            background: var(--brand-navy);
            color: #ffffff;
            border-color: var(--brand-navy);
        }}

        .btn-primary:hover {{
            background: var(--brand-blue);
            border-color: var(--brand-blue);
            color: #ffffff;
        }}

        /* Document Card Container */
        .sop-card {{
            max-width: 1040px;
            margin: 0 auto;
            background: #ffffff;
            border-radius: 12px;
            border: 1px solid var(--slate-200);
            box-shadow: 0 10px 30px -5px rgba(15, 23, 42, 0.08), 0 4px 6px -2px rgba(15, 23, 42, 0.03);
            padding: 3.5rem 4rem;
        }}

        /* Metadata Header Grid */
        .sop-meta {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1rem;
            background: var(--slate-50);
            border: 1px solid var(--slate-200);
            border-radius: 8px;
            padding: 1rem 1.25rem;
            margin-bottom: 2.5rem;
        }}

        .meta-unit {{
            display: flex;
            flex-direction: column;
            gap: 0.2rem;
        }}

        .meta-label {{
            font-size: 0.68rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--slate-500);
        }}

        .meta-val {{
            font-size: 0.88rem;
            font-weight: 800;
            color: var(--slate-900);
        }}

        /* Typography */
        h1 {{
            font-size: 1.75rem;
            font-weight: 900;
            color: var(--brand-navy);
            margin: 1.5rem 0 1rem 0;
            border-bottom: 2px solid var(--slate-100);
            padding-bottom: 0.75rem;
            letter-spacing: -0.02em;
        }}

        h2 {{
            font-size: 1.25rem;
            font-weight: 800;
            color: var(--slate-900);
            margin: 2rem 0 0.85rem 0;
            border-bottom: 1px solid var(--slate-100);
            padding-bottom: 0.4rem;
        }}

        h3 {{
            font-size: 1.05rem;
            font-weight: 800;
            color: var(--brand-blue);
            margin: 1.35rem 0 0.5rem 0;
        }}

        p {{
            margin: 0 0 1rem 0;
            font-size: 0.92rem;
            color: var(--slate-700);
        }}

        ul, ol {{
            margin: 0.5rem 0 1.25rem 0;
            padding-left: 1.75rem;
        }}

        li {{
            margin-bottom: 0.45rem;
            font-size: 0.92rem;
            color: var(--slate-700);
        }}

        strong {{
            color: var(--slate-900);
            font-weight: 700;
        }}

        hr {{
            border: none;
            border-top: 1px solid var(--slate-200);
            margin: 2rem 0;
        }}

        /* Standardized High-Density Tables */
        table {{
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            margin: 1.5rem 0 2rem 0;
            border: 1px solid var(--slate-200);
            border-radius: 8px;
            overflow: hidden;
            font-size: 0.85rem;
        }}

        th {{
            background: var(--slate-100);
            color: var(--slate-800);
            font-weight: 800;
            text-align: left;
            padding: 0.75rem 1rem;
            border-bottom: 1px solid var(--slate-200);
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}

        td {{
            padding: 0.75rem 1rem;
            border-bottom: 1px solid var(--slate-100);
            color: var(--slate-700);
            vertical-align: top;
        }}

        tr:last-child td {{
            border-bottom: none;
        }}

        tr:hover td {{
            background: #fafcff;
        }}

        /* Industrial Callout Boxes */
        .callout {{
            border-left: 4px solid var(--brand-blue);
            background: #eff6ff;
            border-radius: 0 8px 8px 0;
            padding: 1rem 1.25rem;
            margin: 1.5rem 0;
        }}

        .callout strong {{
            display: block;
            color: var(--brand-blue);
            font-size: 0.85rem;
            margin-bottom: 0.35rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        .callout p {{
            margin: 0;
            font-size: 0.88rem;
            color: var(--slate-800);
        }}

        /* Footer */
        .sop-card-footer {{
            margin-top: 3.5rem;
            padding-top: 1.5rem;
            border-top: 1px solid var(--slate-200);
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.75rem;
            font-weight: 700;
            color: var(--slate-500);
        }}

        /* Print Optimization */
        @media print {{
            body {{
                background: none;
                padding: 0;
            }}
            .institutional-header {{
                display: none;
            }}
            .sop-card {{
                border: none;
                box-shadow: none;
                padding: 0;
                max-width: 100%;
            }}
        }}
    </style>
</head>
<body>

    <!-- Executive Quick Header -->
    <div class="institutional-header">
        <div class="brand-logo-unit">
            <i class="fas fa-shield-alt"></i>
            <div>
                <div class="brand-name">HWB CLEANING SERVICES LLC</div>
                <div class="brand-sub">Environmental Health &amp; Safety Division &bull; ISO 45001 Compliant</div>
            </div>
        </div>
        <div class="header-actions">
            <a href="{docx_url}" download class="btn-action btn-primary">
                <i class="fas fa-file-word"></i> Download Word (.docx)
            </a>
            <button onclick="window.print()" class="btn-action">
                <i class="fas fa-print"></i> Print / PDF
            </button>
            <a href="/admin/operations?view=safety" class="btn-action">
                <i class="fas fa-arrow-left"></i> Operations Hub
            </a>
        </div>
    </div>
"""

STANDALONE_TAIL_TEMPLATE = """
</body>
</html>
"""

def harden_file(src_path: str, dest_path: str, title: str, docx_url: str):
    with open(src_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # If it already contains <!DOCTYPE html>, strip it or use body
    if "<!DOCTYPE html>" in content:
        start_idx = content.find('<div class="sop-card">')
        if start_idx != -1:
            end_idx = content.rfind('</div>') + 6
            inner_content = content[start_idx:end_idx]
        else:
            inner_content = content
    else:
        inner_content = content

    header = STANDALONE_HEAD_TEMPLATE.format(title=title, docx_url=docx_url)
    full_html = header + "\n" + inner_content + "\n" + STANDALONE_TAIL_TEMPLATE

    with open(dest_path, 'w', encoding='utf-8') as f:
        f.write(full_html)

    print(f"[HARDENED] {dest_path} successfully written ({len(full_html)} bytes)")


def update_qms_catalog():
    """Adds EHSQ manuals to static/qms and updates qms_index.json."""
    qms_dir = "/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/static/qms"
    os.makedirs(qms_dir, exist_ok=True)

    index_path = "/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/qms_index.json"
    sops = []
    if os.path.exists(index_path):
        with open(index_path, 'r', encoding='utf-8') as f:
            try:
                sops = json.load(f)
            except Exception:
                sops = []

    today = datetime.now().strftime("%m-%d-%Y")

    new_entries = [
        {
            "title": "Standard Operating Procedure: Master Environmental Health & Safety (EHS) Manual",
            "id": "HWB-EHS-001",
            "dept": "EHSQ",
            "file": "hwb-ehs-001_master_safety_manual.html",
            "version": "3.0.0",
            "compliance": "UPDATED",
            "date": today
        },
        {
            "title": "Standard Operating Procedure: Construction Site Safety and Silica Dust Control Plan (CSSP)",
            "id": "HWB-EHS-002",
            "dept": "EHSQ",
            "file": "hwb-ehs-002_construction_safety_plan.html",
            "version": "1.0.0",
            "compliance": "UPDATED",
            "date": today
        },
        {
            "title": "Standard Operating Procedure: Institutional Facilities Health and Safety Plan (IFSP)",
            "id": "HWB-EHS-003",
            "dept": "EHSQ",
            "file": "hwb-ehs-003_institutional_facility_safety_plan.html",
            "version": "1.0.0",
            "compliance": "UPDATED",
            "date": today
        }
    ]

    # Copy clean inner snippets to static/qms
    ehsq_src = "/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-EHSQ"
    snippet_mappings = [
        ("HWB-EHS-001 Master Environmental Health and Safety Manual SOP.html", "hwb-ehs-001_master_safety_manual.html"),
        ("HWB-EHS-002 Construction Site Safety and Silica Dust Control Plan SOP.html", "hwb-ehs-002_construction_safety_plan.html"),
        ("HWB-EHS-003 Institutional Facilities Health and Safety Plan SOP.html", "hwb-ehs-003_institutional_facility_safety_plan.html"),
    ]

    for src_name, dst_name in snippet_mappings:
        src = os.path.join(ehsq_src, src_name)
        dst = os.path.join(qms_dir, dst_name)
        if os.path.exists(src):
            with open(src, 'r', encoding='utf-8') as f:
                content = f.read()
            with open(dst, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"[QMS SNIPPET] Staged {dst_name} in static/qms")

    # Update index
    existing_files = {s.get('file') for s in sops}
    for e in new_entries:
        if e['file'] not in existing_files:
            sops.append(e)
            print(f"[QMS INDEX] Added {e['id']} ({e['file']}) to qms_index.json")

    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(sops, f, indent=4)
    print("[SUCCESS] qms_index.json updated with EHSQ department entries.")


if __name__ == '__main__':
    base_src = "/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-EHSQ"
    static_dst = "/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/static/ehsq"
    os.makedirs(static_dst, exist_ok=True)

    # 1. Harden static standalone files
    harden_file(
        os.path.join(base_src, "HWB-EHS-001 Master Environmental Health and Safety Manual SOP.html"),
        os.path.join(static_dst, "HWB-EHS-001.html"),
        title="HWB-EHS-001 Master Environmental Health & Safety Manual",
        docx_url="/static/ehsq/HWB-EHS-001-Master-Safety-Manual.docx"
    )

    harden_file(
        os.path.join(base_src, "HWB-EHS-002 Construction Site Safety and Silica Dust Control Plan SOP.html"),
        os.path.join(static_dst, "HWB-EHS-002.html"),
        title="HWB-EHS-002 Construction Site Safety & Silica Dust Control Plan",
        docx_url="/static/ehsq/HWB-EHS-002-Construction-Site-Safety-Plan.docx"
    )

    harden_file(
        os.path.join(base_src, "HWB-EHS-003 Institutional Facilities Health and Safety Plan SOP.html"),
        os.path.join(static_dst, "HWB-EHS-003.html"),
        title="HWB-EHS-003 Institutional Facilities Health & Safety Plan",
        docx_url="/static/ehsq/HWB-EHS-003-Institutional-Facility-Safety-Plan.docx"
    )

    # 2. Update QMS catalog and static/qms snippets
    update_qms_catalog()
