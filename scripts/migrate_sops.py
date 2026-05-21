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

HTML_TEMPLATE = """
<div class="sop-card">
    <!-- 0.0 DOCUMENT CONTROL -->
    <div class="sop-meta">
        <div class="meta-unit"><span class="meta-label">Document ID</span><span class="meta-val">{doc_id}</span></div>
        <div class="meta-unit"><span class="meta-label">Version</span><span class="meta-val">{version}</span></div>
        <div class="meta-unit"><span class="meta-label">Status</span><span class="meta-val" style="color: #16a34a;">● {status}</span></div>
        <div class="meta-unit"><span class="meta-label">Clause</span><span class="meta-val">{clause}</span></div>
    </div>

    {content_html}
</div>
"""

def extract_metadata(content):
    meta = {"title": "Untitled SOP", "doc_id": "TBD", "version": "1.0.0", "status": "DRAFT", "clause": "7.5"}
    h1_match = re.search(r'^#\s+(.*)', content, re.MULTILINE)
    if h1_match: meta["title"] = h1_match.group(1).strip()
    
    table_match = re.search(r'\|\s*\*\*Document ID\*\*\s*\|\s*([^|]*)\|', content, re.IGNORECASE)
    if table_match: meta["doc_id"] = table_match.group(1).strip()
    
    table_match = re.search(r'\|\s*\*\*Version\*\*\s*\|\s*([^|]*)\|', content, re.IGNORECASE)
    if table_match: meta["version"] = table_match.group(1).strip()

    table_match = re.search(r'\|\s*\*\*Status\*\*\s*\|\s*([^|]*)\|', content, re.IGNORECASE)
    if table_match: meta["status"] = table_match.group(1).strip()

    table_match = re.search(r'\|\s*\*\*ISO 9001 Clause\*\*\s*\|\s*([^|]*)\|', content, re.IGNORECASE)
    if table_match: meta["clause"] = table_match.group(1).strip()
    return meta

def migrate():
    print(f"--- SigmaFidelity: Initiating Memory-Efficient Migration ---")
    sops = []
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
    
    for dept in DEPARTMENTS:
        dept_path = os.path.join(SOURCE_ROOT, dept)
        if not os.path.exists(dept_path): continue
            
        print(f"[PROCESSING] {dept}...")
        for filename in os.listdir(dept_path):
            if filename.endswith(".md"):
                file_path = os.path.join(dept_path, filename)
                with open(file_path, "r", encoding="utf-8") as f:
                    md_content = f.read()
                
                meta = extract_metadata(md_content)
                content_html = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])
                
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
                
                sops.append({"title": meta["title"], "id": meta["doc_id"], "dept": dept.replace("HWB-", ""), "file": f"{safe_name}", "version": meta["version"]})
    
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(sops, f, indent=4)
    print(f"--- SigmaFidelity: Migration Complete. {len(sops)} Fragments Saved. ---")

if __name__ == "__main__":
    migrate()
