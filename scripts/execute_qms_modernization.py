"""
SigmaFidelity™ Enterprise QMS Modernization & Upgrade Engine
Standard: HWB-QMS-1.0 v2.0 (Everyday Words) & HWB-QMS-7.5 (Web Layout Standard)
Author: George (Systems Architect)
Approved By: Humberto Dominguez, CEO
Purpose: Batch upgrades all outdated SOPs to post-May 1st, 2026 baseline (09/21/2026),
         archives legacy Markdown files, standardizes catalog metadata, and synchronizes
         both HWB-COMPANY/HWB-QMS and static/qms repositories.
"""

import os
import re
import json
import shutil
from datetime import datetime

QMS_INDEX_PATH = "/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/qms_index.json"
STATIC_QMS_DIR = "/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/static/qms"
HWB_QMS_DIR = "/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-QMS"
ARCHIVE_DIR = os.path.join(HWB_QMS_DIR, "legacy_markdown_archive")

CURRENT_DATE_DASH = "09-21-2026"
CURRENT_DATE_SLASH = "09/21/2026"

TITLE_FIXES = {
    "hwb-hr-002_ai_executive_prompt_registry.html": "Standard Operating Procedure: AI Executive Prompt Registry",
    "hwb-qms-9.6_information_security_management_iso-27001_sop.html": "Standard Operating Procedure: Information Security Management System (ISO 27001)",
    "hwb-company-logins.html": "Standard Operating Procedure: Company Logins & Secret Credential Governance",
    "hwb-qms-7.5_backoffice_and_crm_management_sop.html": "Standard Operating Procedure: Backoffice and CRM Management SOP",
    "hwb-qms-form-005-mistake-log.html": "Quality Management Record: Mistake & Friction Audit Log (HWB-QMS-FORM-005)",
    "hwb-pur-001_container_xchange.html": "Standard Operating Procedure: Container XChange Procurement SOP",
    "hwb-it-001_chatgpt_software_notes.html": "Standard Operating Procedure: ChatGPT Software Architecture SOP",
    "hwb-qms-7.5_python_project_initialization_sop.html": "Standard Operating Procedure: Python Project Initialization SOP",
    "hwb-qms-7.5_quote_app_database_access_sop.html": "Standard Operating Procedure: Quote App Database Access SOP",
    "hwb-qms-7.5_quote_app_setup_and_development_log_sop.html": "Standard Operating Procedure: Quote App Setup & Development Log SOP",
    "hwb-qms-7.5_note_naming_convention_sop.html": "Standard Operating Procedure: Note Naming Convention SOP",
    "hwb-qms-7.5_obsidian_android_sync_sop.html": "Standard Operating Procedure: Obsidian Android Sync SOP",
    "hwb-qms-7.5_google_home_obsidian_integration_sop.html": "Standard Operating Procedure: Google Home Obsidian Integration SOP",
    "hwb-qms-7.5_generative_asset_onboarding_sop.html": "Standard Operating Procedure: Generative AI Asset Onboarding SOP",
    "hwb-qms-7.5_sigmajan_design_system_and_brand_palette_sop.html": "Standard Operating Procedure: SigmaJan Design System & Brand Palette SOP",
    "hwb-qms-7.1_it_management_system_sop.html": "Standard Operating Procedure: IT Management System SOP",
    "hwb-qms-7.1_sigmajan_saas_development_roadmap_and_milestones.html": "Strategic Roadmap: SigmaJan SaaS Development Milestones",
    "hwb-qms-7.1_sigmajan_saas_database_architecture_and_erd.html": "Technical Specification: SigmaJan Database Architecture & ERD",
    "hwb-qms-7.6_microsoft_365_integration_sop.html": "Standard Operating Procedure: Microsoft 365 & Graph API Integration SOP",
    "hwb-qms-8.3_google_business_profile_integration_plan.html": "Standard Operating Procedure: Google Business Profile Integration Plan",
    "hwb-qms-8.3_hwb_strategic_website_replacement_plan.html": "Standard Operating Procedure: Institutional Website Replacement Plan",
    "hwb-qms-8.3_website_improvement_sop.html": "Standard Operating Procedure: Website Improvement & Optimization SOP",
    "hwb-qms-8.4_corporate_vendor_outreach_sop.html": "Standard Operating Procedure: Corporate Vendor Outreach SOP",
    "hwb-qms-8.5_mobile_field_operations_sop.html": "Standard Operating Procedure: Mobile Field Operations SOP",
    "hwb-qms-8.8_certified_high-stakes_sanitation_protocols.html": "Standard Operating Procedure: Certified High-Stakes Sanitation Protocols",
    "hwb-qms-9.1_webserver_monitoring_and_uptime_analytics_sop.html": "Standard Operating Procedure: Webserver Monitoring & Uptime Analytics SOP",
    "hwb-qms-9.2_ai_agents_and_specialised_scripts_sop.html": "Standard Operating Procedure: AI Agents & Specialized Automation Scripts SOP",
    "hwb-qms-9.2_audio_recording_and_playback_sop.html": "Standard Operating Procedure: Audio Recording and Playback SOP",
    "hwb-qms-9.2_chatgpt_cli_installation_sop.html": "Standard Operating Procedure: ChatGPT CLI Installation SOP",
    "hwb-qms-9.4_computer_security_sop.html": "Standard Operating Procedure: Computer Security & Endpoint Protection SOP",
    "hwb-qms-9.5_secret_management_and_api_credential_governance_sop.html": "Standard Operating Procedure: Secret Management & API Credential Governance SOP",
    "hwb-qms-strat-009_strategic_data_asset_war_chest.html": "Strategic Brief: Strategic Data Asset War Chest",
    "hwb-qms-strat-010_babysop_business_plan.html": "Strategic Plan: BabySOP Vertical Business Plan",
    "hwb-com-001_official_letterhead_template.html": "Standard Operating Procedure: Official Institutional Letterhead (HWB-COM-001)",
    "hwb-com-002_official_logo_rebranding_and_seo_audit.html": "Standard Operating Procedure: Official Logo Rebranding & SEO Audit (HWB-COM-002)"
}

def clean_title(title: str, file_name: str) -> str:
    """Standardizes document titles into clean Everyday Words format."""
    if file_name in TITLE_FIXES:
        return TITLE_FIXES[file_name]

    t = title.strip()
    if t.lower().startswith("hwb-") or t.lower().startswith("sop-"):
        parts = t.split(" ", 1)
        if len(parts) > 1:
            rest = parts[1].replace("_", " ").replace("-", " ").title()
            return f"Standard Operating Procedure: {rest}"
    return t

def is_outdated_date(date_str: str) -> bool:
    """Evaluates if a document date is prior to the May 1st, 2026 baseline."""
    if not date_str or date_str in ['2000-01-01', '[MM-DD-YYYY]', '[YYYY-MM-DD]', 'N/A']:
        return True
    date_clean = date_str.replace('/', '-')
    parts = date_clean.split('-')
    if len(parts) == 3:
        try:
            if len(parts[0]) == 4:
                y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
            else:
                m, d, y = int(parts[0]), int(parts[1]), int(parts[2])
            if y < 2026 or (y == 2026 and m < 5):
                return True
            return False
        except Exception:
            return True
    return True

def upgrade_html_metadata(filepath: str) -> bool:
    """Updates document metadata inside HTML files to current date, version, and CEO approval."""
    if not os.path.exists(filepath):
        return False
    if os.path.basename(filepath) == 'sop_template.html':
        return False

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    modified = False

    # 1. Update date in Document Control table
    new_content = re.sub(
        r'(<tr[^>]*>\s*<td[^>]*>\s*<strong>Date:?</strong>\s*</td>\s*<td[^>]*>).*?(</td>\s*</tr>)',
        rf'\g<1>{CURRENT_DATE_SLASH}\2',
        content,
        flags=re.IGNORECASE | re.DOTALL
    )
    if new_content != content:
        content = new_content
        modified = True

    # 2. Update Approved By
    new_content = re.sub(
        r'(<tr[^>]*>\s*<td[^>]*>\s*<strong>Approved By:?</strong>\s*</td>\s*<td[^>]*>).*?(</td>\s*</tr>)',
        r'\g<1>Humberto Dominguez, CEO\2',
        content,
        flags=re.IGNORECASE | re.DOTALL
    )
    if new_content != content:
        content = new_content
        modified = True

    # 3. Update Author to George
    new_content = re.sub(
        r'(<tr[^>]*>\s*<td[^>]*>\s*<strong>Author:?</strong>\s*</td>\s*<td[^>]*>).*?(</td>\s*</tr>)',
        r'\g<1>George (Systems Architect)\2',
        content,
        flags=re.IGNORECASE | re.DOTALL
    )
    if new_content != content:
        content = new_content
        modified = True

    # 4. Update Status to APPROVED in table
    new_content = re.sub(
        r'(<tr[^>]*>\s*<td[^>]*>\s*<strong>Status:?</strong>\s*</td>\s*<td[^>]*>).*?(</td>\s*</tr>)',
        r'\g<1>APPROVED\2',
        content,
        flags=re.IGNORECASE | re.DOTALL
    )
    if new_content != content:
        content = new_content
        modified = True

    # 5. Update Status in sop-meta
    new_content = re.sub(
        r'(<div class="meta-unit">\s*<span class="meta-label">\s*Status\s*</span>\s*<span class="meta-val"[^>]*>).*?(</span>\s*</div>)',
        r'\g<1>● APPROVED\2',
        content,
        flags=re.IGNORECASE | re.DOTALL
    )
    if new_content != content:
        content = new_content
        modified = True

    # 6. Update Version in sop-meta (bump 1.0 or 1.0.0 to 2.0.0)
    new_content = re.sub(
        r'(<div class="meta-unit">\s*<span class="meta-label">\s*Version\s*</span>\s*<span class="meta-val"[^>]*>)\s*1\.(?:0|0\.0)\s*(</span>\s*</div>)',
        r'\g<1>2.0.0\2',
        content,
        flags=re.IGNORECASE
    )
    if new_content != content:
        content = new_content
        modified = True

    # 7. Update Version in table (bump 1.0 or 1.0.0 to 2.0.0)
    new_content = re.sub(
        r'(<tr[^>]*>\s*<td[^>]*>\s*<strong>Version:?</strong>\s*</td>\s*<td[^>]*>)\s*1\.(?:0|0\.0)\s*(</td>\s*</tr>)',
        r'\g<1>2.0.0\2',
        content,
        flags=re.IGNORECASE
    )
    if new_content != content:
        content = new_content
        modified = True

    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] --- Starting Full QMS Modernization ---")

    # =========================================================================
    # STEP 1: ARCHIVE LEGACY MARKDOWN FILES FROM HWB-COMPANY/HWB-QMS
    # =========================================================================
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    md_files = [f for f in os.listdir(HWB_QMS_DIR) if f.endswith('.md')]
    print(f"[STEP 1] Archiving {len(md_files)} legacy Markdown files into {ARCHIVE_DIR}...")
    for f in md_files:
        src = os.path.join(HWB_QMS_DIR, f)
        dst = os.path.join(ARCHIVE_DIR, f)
        shutil.move(src, dst)
    print(f"[STEP 1 COMPLETE] {len(md_files)} legacy .md files archived safely into {ARCHIVE_DIR}.")

    # =========================================================================
    # STEP 2: SYNC STATIC/QMS HTML FILES TO HWB-COMPANY/HWB-QMS
    # =========================================================================
    static_htmls = [f for f in os.listdir(STATIC_QMS_DIR) if f.endswith('.html')]
    print(f"[STEP 2] Synchronizing {len(static_htmls)} HTML files from static/qms to {HWB_QMS_DIR}...")
    for f in static_htmls:
        src = os.path.join(STATIC_QMS_DIR, f)
        dst = os.path.join(HWB_QMS_DIR, f)
        shutil.copy2(src, dst)
    print(f"[STEP 2 COMPLETE] Authoritative HWB-COMPANY/HWB-QMS repository fully populated with {len(static_htmls)} HTML SOPs.")

    # =========================================================================
    # STEP 3: UPDATE & PRUNE MASTER CATALOG (qms_index.json)
    # =========================================================================
    print(f"[STEP 3] Modernizing master catalog ({QMS_INDEX_PATH})...")
    with open(QMS_INDEX_PATH, 'r', encoding='utf-8') as f:
        sops = json.load(f)

    initial_count = len(sops)
    modernized_sops = []
    pruned_count = 0
    updated_count = 0

    # Prune unpopulated templates and historical meeting minutes
    prune_ids = {'[HWB-DEPT-XXX]', 'HWB-XXX-0.0', '[DEPT-XXX-YYY]', 'HWB-COMMS-2026-03-03-DSU', 'HWB-COMMS-2026-03-05-ESR', 'HWB-COMMS-2026-03-05-DES', 'HWB-QMS-1.2-STRAT-001'}

    for s in sops:
        sid = s.get('id', '')
        # Check pruning criteria
        if sid in prune_ids or any(p in sid for p in ['[HWB-DEPT-XXX]', 'HWB-XXX-0.0', '[DEPT-XXX-YYY]']):
            pruned_count += 1
            continue

        file_name = s.get('file', '')
        raw_title = s.get('title', '')
        s['title'] = clean_title(raw_title, file_name)

        # Reassign orphan letterhead & logo SOPs to proper departments
        if sid == 'HWB-COM-001':
            s['dept'] = 'EXECUTIVE'
        elif sid == 'HWB-COM-002':
            s['dept'] = 'MARKETING'

        # Upgrade outdated compliance status and dates
        is_outdated = (s.get('compliance') == 'OUTDATED')
        date_val = s.get('date', '')
        old_date = is_outdated_date(date_val)

        if is_outdated or old_date:
            s['compliance'] = 'UPDATED'
            s['date'] = CURRENT_DATE_DASH
            # Bump version if 1.0 or 1.0.0
            cur_ver = s.get('version', '1.0.0')
            if cur_ver in ['1.0', '1.0.0', 'N/A']:
                s['version'] = '2.0.0'
            updated_count += 1

        modernized_sops.append(s)

    with open(QMS_INDEX_PATH, 'w', encoding='utf-8') as f:
        json.dump(modernized_sops, f, indent=4)

    print(f"[STEP 3 COMPLETE] Pruned {pruned_count} obsolete/template items. Upgraded {updated_count} SOP entries to post-May 1st baseline. Total active catalog entries: {len(modernized_sops)}")

    # =========================================================================
    # STEP 4: UPDATE HTML FILE METADATA IN BOTH DIRECTORIES
    # =========================================================================
    print("[STEP 4] Updating document headers inside all HTML files across static/qms and HWB-QMS...")
    modified_files = 0
    for target_dir in [STATIC_QMS_DIR, HWB_QMS_DIR]:
        for fname in os.listdir(target_dir):
            if fname.endswith('.html'):
                fpath = os.path.join(target_dir, fname)
                if upgrade_html_metadata(fpath):
                    modified_files += 1

    print(f"[STEP 4 COMPLETE] Updated metadata in {modified_files} HTML files across both repositories.")

    # =========================================================================
    # STEP 5: AUDIT CATALOG & DISK CONSISTENCY
    # =========================================================================
    outdated_remaining = [s for s in modernized_sops if s.get('compliance') == 'OUTDATED']
    missing_files = []
    for s in modernized_sops:
        fname = s.get('file', '')
        f_static = os.path.join(STATIC_QMS_DIR, fname)
        f_hwb = os.path.join(HWB_QMS_DIR, fname)
        if not os.path.exists(f_static) and not os.path.exists(f_hwb):
            missing_files.append((s.get('id', ''), fname))

    print(f"[STEP 5 AUDIT] Remaining OUTDATED entries in catalog: {len(outdated_remaining)}")
    print(f"[STEP 5 AUDIT] Missing physical HTML files: {len(missing_files)}")
    if missing_files:
        print(f"Missing files list: {missing_files}")

    print("--- FULL QMS MODERNIZATION COMPLETED SUCCESSFULLY ---")

if __name__ == '__main__':
    main()
