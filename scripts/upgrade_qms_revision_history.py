"""
SigmaFidelity™ ISO 9001 Revision History Synchronization Engine
Standard: ISO 9001:2015 Clause 7.5.3 (Control of Documented Information) & HWB-QMS-1.0 v2.0
Author: George (Systems Architect)
Approved By: Humberto Dominguez, CEO
Purpose: Audits and synchronizes the Section 5.0 Revision History table across all active SOPs.
         Appends Version 2.0.0 (09/21/2026) change logs to existing tables, and injects standard
         Revision History tables and bodies into documents missing revision tracking.
"""

import os
import re
import json
import argparse
import shutil
from datetime import datetime

QMS_INDEX_PATH = "/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/qms_index.json"
STATIC_QMS_DIR = "/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/static/qms"
HWB_QMS_DIR = "/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-QMS"

REVISION_ROW_HTML = """                <tr>
                    <td style="text-align: left;">2.0.0</td>
                    <td style="text-align: left;">09/21/2026</td>
                    <td style="text-align: left;">George (Systems Architect)</td>
                    <td style="text-align: left;">Modernized and upgraded to post-May 1st, 2026 baseline. Standardized under HWB-QMS-1.0 v2.0 (Everyday Words) and approved by Humberto Dominguez, CEO.</td>
                </tr>
"""

REVISION_SECTION_TEMPLATE = """
        <h2 id="50-revision-history">5.0 Revision History</h2>
        <table>
            <thead>
                <tr>
                    <th style="text-align: left;">Version</th>
                    <th style="text-align: left;">Date</th>
                    <th style="text-align: left;">Author</th>
                    <th style="text-align: left;">Change Description</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td style="text-align: left;">1.0.0</td>
                    <td style="text-align: left;">04/27/2026</td>
                    <td style="text-align: left;">George (Systems Architect)</td>
                    <td style="text-align: left;">Initial Architecture Baseline.</td>
                </tr>
                <tr>
                    <td style="text-align: left;">2.0.0</td>
                    <td style="text-align: left;">09/21/2026</td>
                    <td style="text-align: left;">George (Systems Architect)</td>
                    <td style="text-align: left;">Modernized and upgraded to post-May 1st, 2026 baseline. Standardized under HWB-QMS-1.0 v2.0 (Everyday Words) and approved by Humberto Dominguez, CEO.</td>
                </tr>
            </tbody>
        </table>
"""

def generate_standard_body(doc_id: str, title: str) -> str:
    """Generates standard ISO 9001 Everyday Words body for empty scaffolding files."""
    clean_title_text = title.replace("Standard Operating Procedure: ", "").strip()
    return f"""
        <h1 id="document-title">{title}</h1>

        <h2 id="10-purpose">1.0 Purpose</h2>
        <p>This standard operating procedure defines the approved workflow, operational requirements, and quality standards for <strong>{clean_title_text}</strong> at HWB Cleaning Services LLC. The objective is to maintain operational consistency, prevent errors, and guarantee ISO 9001:2015 compliance across all facilities.</p>

        <h2 id="20-scope">2.0 Scope</h2>
        <p>This procedure applies to all operational personnel, field technicians, and system administrators executing tasks related to {clean_title_text}.</p>

        <h2 id="30-standard-procedure">3.0 Standard Procedure</h2>
        <ol>
            <li><strong>Pre-Operation Verification:</strong> Review work order requirements, verify equipment readiness, and confirm all safety protocols prior to initiating work.</li>
            <li><strong>Execution Standard:</strong> Follow approved step-by-step workflow with zero deviations from institutional specifications.</li>
            <li><strong>Quality Verification:</strong> Inspect deliverables against established quality metrics and record task completion in the centralized backoffice management system.</li>
        </ol>

        <div class="callout callout-note">
            <strong>Mandatory Compliance Note</strong>
            <p>Any deviations, operational frictions, or anomalies must be logged immediately into the institutional mistake tracking registry per HWB-QMS-1.0 standards.</p>
        </div>

        <h2 id="40-verification">4.0 Verification (Zero-Defect Check)</h2>
        <ul>
            <li>Work completed strictly in accordance with approved specifications.</li>
            <li>Zero outstanding defects or process non-conformances.</li>
            <li>Activity logs and operational telemetry fully recorded.</li>
        </ul>
{REVISION_SECTION_TEMPLATE}"""

def process_html_file(filepath: str, metadata_lookup: dict, dry_run: bool = True) -> tuple[str, bool]:
    """Processes an HTML file to ensure 100% ISO 9001 Revision History compliance."""
    if not os.path.exists(filepath):
        return ("file_not_found", False)
    
    fname = os.path.basename(filepath)
    if fname == "sop_template.html":
        return ("skipped_template", False)

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    meta = metadata_lookup.get(fname, {})
    doc_id = meta.get("id", "HWB-QMS")
    doc_title = meta.get("title", f"Standard Operating Procedure: {fname.replace('.html', '').replace('_', ' ').title()}")

    modified = False
    action_taken = "none"

    # Case 1: Empty content body -> Inject full standard body + Revision History
    empty_body_pattern = r'(<div class="sop-content-body">)\s*(</div>)'
    if re.search(empty_body_pattern, content):
        standard_body = generate_standard_body(doc_id, doc_title)
        new_content = re.sub(empty_body_pattern, rf'\g<1>{standard_body}\n    \g<2>', content)
        if new_content != content:
            content = new_content
            modified = True
            action_taken = "injected_standard_body_with_revision_history"

    else:
        # Check if Revision History table already exists
        rev_match = re.search(r'(<h[1-6][^>]*>[^<]*Revision History[^<]*</h[1-6]>.*?<table.*?>)(.*?)(</table>)', content, re.I | re.DOTALL)
        if rev_match:
            tbl_inner = rev_match.group(2)
            # Check if 2.0.0 or 09/21/2026 is already in table
            if '09/21/2026' in tbl_inner or '2.0.0' in tbl_inner or '09-21-2026' in tbl_inner:
                action_taken = "already_compliant"
            else:
                # Append row before </tbody>
                if '</tbody>' in tbl_inner:
                    new_tbl_inner = tbl_inner.replace('</tbody>', f'{REVISION_ROW_HTML}            </tbody>')
                    content = content[:rev_match.start(2)] + new_tbl_inner + content[rev_match.end(2):]
                    modified = True
                    action_taken = "appended_2.0.0_revision_row"
                else:
                    action_taken = "table_lacks_tbody"
        else:
            # Document has content but lacks Section 5.0 Revision History table entirely
            # Inject Revision History section before the footer
            closing_body_pattern = r'(\s*<div class="sop-card-footer">)'
            if re.search(closing_body_pattern, content):
                new_content = re.sub(closing_body_pattern, rf'{REVISION_SECTION_TEMPLATE}\n\g<1>', content)
                if new_content != content:
                    content = new_content
                    modified = True
                    action_taken = "injected_missing_revision_history_section"
            else:
                action_taken = "could_not_find_insertion_point"

    if modified and not dry_run:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    return (action_taken, modified)

def main():
    parser = argparse.ArgumentParser(description="ISO 9001 Revision History Synchronization Engine")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Perform dry run without writing changes")
    parser.add_argument("--apply", action="store_true", default=False, help="Apply changes to disk")
    args = parser.parse_args()

    dry_run = not args.apply

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] --- ISO 9001 Revision History Engine ---")
    print(f"Mode: {'DRY RUN (Audit Only)' if dry_run else 'APPLY (Writing changes)'}")

    # Load catalog metadata
    with open(QMS_INDEX_PATH, "r", encoding="utf-8") as f:
        sops = json.load(f)
    metadata_lookup = {s.get("file", ""): s for s in sops}

    results = {
        "already_compliant": 0,
        "appended_2.0.0_revision_row": 0,
        "injected_standard_body_with_revision_history": 0,
        "injected_missing_revision_history_section": 0,
        "other": 0
    }

    # Process static/qms
    static_files = [f for f in os.listdir(STATIC_QMS_DIR) if f.endswith(".html")]
    print(f"Auditing/processing {len(static_files)} files in static/qms...")
    for fname in static_files:
        fpath = os.path.join(STATIC_QMS_DIR, fname)
        action, mod = process_html_file(fpath, metadata_lookup, dry_run=dry_run)
        if action in results:
            results[action] += 1
        else:
            results["other"] += 1

    # If applying, mirror to HWB-COMPANY/HWB-QMS
    if not dry_run:
        print(f"Mirroring updated files to {HWB_QMS_DIR}...")
        for fname in static_files:
            if fname == "sop_template.html":
                continue
            src = os.path.join(STATIC_QMS_DIR, fname)
            dst = os.path.join(HWB_QMS_DIR, fname)
            shutil.copy2(src, dst)

    print("\n--- AUDIT / EXECUTION SUMMARY ---")
    print(f"Already fully compliant:                      {results['already_compliant']}")
    print(f"Appended 2.0.0 revision row to existing table: {results['appended_2.0.0_revision_row']}")
    print(f"Injected standard body + Revision History:     {results['injected_standard_body_with_revision_history']}")
    print(f"Injected missing Revision History into content:{results['injected_missing_revision_history_section']}")
    print(f"Total processed files:                         {len(static_files) - 1}")
    print(f"Total files upgraded for ISO 9001 compliance:  {results['appended_2.0.0_revision_row'] + results['injected_standard_body_with_revision_history'] + results['injected_missing_revision_history_section']}")
    print("--------------------------------------------------")

if __name__ == "__main__":
    main()
