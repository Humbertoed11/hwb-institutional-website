import os
import re
import markdown
import json
from datetime import datetime

# CONFIGURATION
SOURCE_ROOT = "HWB-COMPANY"
OUTPUT_DIR = "HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/static/qms"
INDEX_FILE = "HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/qms_index.json"
DEPARTMENTS = [
    "HWB-ACCOUNTING", "HWB-COMMUNICATION", "HWB-EHSQ", "HWB-HR", 
    "HWB-IT", "HWB-LEGAL", "HWB-OPERATIONS", "HWB-PURCHASING", 
    "HWB-QMS", "HWB-SALES-MARKETING"
]

# ISO 9001 Compliance Baseline
BASELINE_DATE = datetime(2026, 5, 1)

HTML_TEMPLATE = """
<div class="sop-card">
    <!-- 0.0 DOCUMENT CONTROL -->
    <div class="sop-meta">
        <div class="meta-unit"><span class="meta-label">Document ID</span><span class="meta-val">{doc_id}</span></div>
        <div class="meta-unit"><span class="meta-label">Version</span><span class="meta-val">{version}</span></div>
        <div class="meta-unit"><span class="meta-label">Status</span><span class="meta-val" style="color: #16a34a;">● {status}</span></div>
        <div class="meta-unit"><span class="meta-label">Clause</span><span class="meta-val">{clause}</span></div>
    </div>

    <div class="sop-content-body">
        {content_html}
    </div>
</div>
"""

def extract_metadata(content):
    meta = {
        "title": "Untitled SOP", 
        "doc_id": "TBD", 
        "version": "1.0.0", 
        "status": "DRAFT", 
        "clause": "7.5",
        "date": "2000-01-01"
    }
    h1_match = re.search(r'^#\s+(.*)', content, re.MULTILINE)
    if h1_match: meta["title"] = h1_match.group(1).strip()
    
    fields = {
        "doc_id": r'\|\s*\*\*Document ID\*\*\s*\|\s*([^|]*)\|',
        "version": r'\|\s*\*\*Version\*\*\s*\|\s*([^|]*)\|',
        "status": r'\|\s*\*\*Status\*\*\s*\|\s*([^|]*)\|',
        "clause": r'\|\s*\*\*ISO 9001 Clause\*\*\s*\|\s*([^|]*)\|',
        "date": r'\|\s*\*\*Date\*\*\s*\|\s*([^|]*)\|'
    }

    for key, pattern in fields.items():
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            meta[key] = match.group(1).strip()
    
    return meta

def process_callouts(md_text):
    """
    Converts blockquotes with labels into Industrial Callout HTML.
    """
    patterns = {
        r'>\s*\*\*NOTE:\*\*\s*(.*)': r'<div class="callout callout-note"><strong>Note</strong>\1</div>',
        r'>\s*\*\*CAUTION:\*\*\s*(.*)': r'<div class="callout callout-caution"><strong>Caution</strong>\1</div>',
        r'>\s*\*\*DANGER:\*\*\s*(.*)': r'<div class="callout callout-danger"><strong>Danger</strong>\1</div>',
        r'>\s*\*\*LOGIC:\*\*\s*(.*)': r'<div class="callout callout-logic"><strong>Technical Logic</strong>\1</div>'
    }
    
    for pattern, replacement in patterns.items():
        md_text = re.sub(pattern, replacement, md_text, flags=re.MULTILINE | re.IGNORECASE)
    
    # Fix Mermaid blocks to ensure they have the .mermaid class
    md_text = re.sub(r'```mermaid', r'<div class="mermaid">', md_text)
    md_text = re.sub(r'```(?=\s*\n|$)', r'</div>', md_text) # Only close div if it followed a mermaid start
    
    return md_text

def get_compliance_status(date_str):
    try:
        date_str = date_str.replace('/', '-')
        parts = date_str.split('-')
        if len(parts[0]) == 4:
            doc_date = datetime.strptime(date_str, "%Y-%m-%d")
        else:
            doc_date = datetime.strptime(date_str, "%m-%d-%Y")
        if doc_date >= BASELINE_DATE: return "UPDATED"
        return "OUTDATED"
    except: return "OUTDATED"

def migrate():
    print(f"--- SigmaFidelity: Initiating Industrial Hardening Migration ---")
    sops = []
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
    
    for dept in DEPARTMENTS:
        dept_path = os.path.join(SOURCE_ROOT, dept)
        if not os.path.exists(dept_path): continue
            
        print(f"[HARDENING] {dept}...")
        for filename in os.listdir(dept_path):
            if filename.endswith(".md"):
                file_path = os.path.join(dept_path, filename)
                with open(file_path, "r", encoding="utf-8") as f:
                    md_content = f.read()
                
                meta = extract_metadata(md_content)
                compliance = get_compliance_status(meta["date"])
                
                # Pre-process for Callouts and Mermaid
                hardened_md = process_callouts(md_content)
                
                # Convert to HTML with TOC and Table support
                content_html = markdown.markdown(hardened_md, extensions=['tables', 'fenced_code', 'toc'])
                
                final_html = HTML_TEMPLATE.format(
                    doc_id=meta["doc_id"],
                    version=meta["version"],
                    status=meta["status"],
                    clause=meta["clause"],
                    content_html=content_html
                )
                
                safe_name = filename.replace(".md", ".html").replace(" ", "_").lower()
                with open(os.path.join(OUTPUT_DIR, safe_name), "w", encoding="utf-8") as f:
                    f.write(final_html)
                
                sops.append({
                    "title": meta["title"], 
                    "id": meta["doc_id"], 
                    "dept": dept.replace("HWB-", ""), 
                    "file": f"{safe_name}", 
                    "version": meta["version"],
                    "compliance": compliance,
                    "date": meta["date"]
                })
    
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(sops, f, indent=4)
    print(f"--- SigmaFidelity: Hardening Complete. {len(sops)} Industrial Fragments Saved. ---")

if __name__ == "__main__":
    migrate()
