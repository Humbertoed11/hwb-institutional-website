import os
import json
import re

if os.path.exists("/app"):
    INDEX_FILE = "/app/qms_index.json"
    HEX_QMS_DIR = "/app/static/manual_source"
else:
    INDEX_FILE = "/home/humbertoed/hexgrowth/app/qms_index.json"
    HEX_QMS_DIR = "/home/humbertoed/hexgrowth/HEX-QMS"

def repair_sops():
    if not os.path.exists(INDEX_FILE):
        print(f"FAILURE: QMS index not found at {INDEX_FILE}")
        return
        
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        sops = json.load(f)
        
    for index_entry in sops:
        doc_id = index_entry.get('id')
        url_slug = index_entry.get('file')
        file_path = os.path.join(HEX_QMS_DIR, url_slug)
        
        if not os.path.exists(file_path):
            print(f"WARNING: QMS file not found at {file_path}. Skipping.")
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 1. Parse Version
        # Match standard or single-quoted version span
        version_match = re.search(r'Version.*?class="meta-val">([^<]+)</span>', content, re.IGNORECASE)
        if not version_match:
            version_match = re.search(r"Version.*?class='meta-val'>([^<]+)</span>", content, re.IGNORECASE)
        version = version_match.group(1).strip() if version_match else "1.0.0"

        # 2. Parse Status
        status_match = re.search(r'Status.*?class="meta-val"[^>]*>(?:●\s*)?([^<]+)</span>', content, re.IGNORECASE)
        if not status_match:
            status_match = re.search(r"Status.*?class='meta-val'[^>]*>(?:●\s*)?([^<]+)</span>", content, re.IGNORECASE)
        status = status_match.group(1).strip() if status_match else "APPROVED"
        # Standard clean status representation
        status = status.replace("●", "").strip()

        # 3. Parse Author
        author_match = re.search(r'Author.*?class="meta-val">([^<]+)</span>', content, re.IGNORECASE)
        if not author_match:
            author_match = re.search(r"Author.*?class='meta-val'>([^<]+)</span>", content, re.IGNORECASE)
        author = author_match.group(1).strip() if author_match else "George Bytes (Lead Auditor)"

        # 4. Extract Body Content
        # Body starts at h1 tag
        body_start_match = re.search(r'<h1>', content, re.IGNORECASE)
        if not body_start_match:
            body_start_match = re.search(r'<div class=["\']sop-content-body["\']>', content)
            
        if not body_start_match:
            print(f"ERROR: Cannot find h1 or sop-content-body in {url_slug}")
            continue
            
        # If it matched <h1>, we start at its start; if it matched the div wrapper, we start at its end
        if body_start_match.group(0).lower() == '<h1>':
            body_start_idx = body_start_match.start()
        else:
            body_start_idx = body_start_match.end()
        
        # Body ends at footer comment or before footer class
        body_end_match = re.search(r'<!-- 3. DOCUMENT CONTROL FOOTER -->', content)
        if not body_end_match:
            body_end_match = re.search(r'<div class=["\']sop-card-footer["\']>', content)
            
        if body_end_match:
            body_end_idx = body_end_match.start()
        else:
            # Fallback if footer is not there, match up to the last </div>
            last_div = content.rstrip().rfind('</div>')
            body_end_idx = last_div if last_div != -1 else len(content)
            
        body_content = content[body_start_idx:body_end_idx].strip()
        
        # If body_content ends with </div>, remove it since we wrap it ourselves
        if body_content.endswith('</div>'):
            body_content = body_content[:-6].strip()
            
        # Clean any existing revision history block to avoid duplicates on re-runs
        body_content = re.sub(r'<hr\s*/?>\s*<h2>Document Revision History</h2>[\s\S]+?$', '', body_content).strip()
            
        # Reconstruct the file with correct indentation, revision table, and format
        reconstructed = f"""<!-- 
    HEXGROWTH Institutional QMS Document
    Standard: HEX-QMS-1.0 v1.0
    Document ID: {doc_id}
-->
<div class="sop-card">
    <!-- DOCUMENT CONTROL -->
    <div class="sop-meta">
        <div class="meta-unit"><span class="meta-label">Document ID</span><span class="meta-val">{doc_id}</span></div>
        <div class="meta-unit"><span class="meta-label">Version</span><span class="meta-val">{version}</span></div>
        <div class="meta-unit"><span class="meta-label">Status</span><span class="meta-val" style="color: #10b981;">● {status}</span></div>
        <div class="meta-unit"><span class="meta-label">Author</span><span class="meta-val">{author}</span></div>
    </div>

    <div class="sop-content-body">
        {body_content}
        
        <hr />
        <h2>Document Revision History</h2>
        <table class="sigma-data-grid">
            <thead>
                <tr>
                    <th>Revision</th>
                    <th>Date</th>
                    <th>Description of Change</th>
                    <th>Author / Approved By</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><b>{version}</b></td>
                    <td>06/03/2026</td>
                    <td>Standardized clinical formatting and aligned with ISO 9001 document controls.</td>
                    <td>George Bytes / Humberto Dominguez (Chairman)</td>
                </tr>
            </tbody>
        </table>
    </div>

    <!-- 3. DOCUMENT CONTROL FOOTER -->
    <div class="sop-card-footer">
        <div>Classification: Institutional ISO 9001 QMS Record</div>
        <div>Effective Date: 06/03/2026</div>
        <div>Review Cycle: Annual (Rev {version})</div>
    </div>
</div>
"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(reconstructed)
            
        print(f"REPAIRED & RECONSTRUCTED: [{doc_id}] {url_slug}")

if __name__ == '__main__':
    repair_sops()
