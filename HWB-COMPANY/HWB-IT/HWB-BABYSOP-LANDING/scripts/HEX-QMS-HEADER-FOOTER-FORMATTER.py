import os
import json
import re

if os.path.exists("/app"):
    INDEX_FILE = "/app/qms_index.json"
    HEX_QMS_DIR = "/app/static/manual_source"
else:
    INDEX_FILE = "/home/humbertoed/hexgrowth/app/qms_index.json"
    HEX_QMS_DIR = "/home/humbertoed/hexgrowth/HEX-QMS"

def format_all_sops():
    if not os.path.exists(INDEX_FILE):
        print(f"FAILURE: QMS index not found at {INDEX_FILE}")
        return
        
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        sops = json.load(f)
        
    for index_entry in sops:
        url_slug = index_entry.get('file')
        file_path = os.path.join(HEX_QMS_DIR, url_slug)
        
        if not os.path.exists(file_path):
            print(f"WARNING: QMS file not found at {file_path}. Skipping.")
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Standardize quotes to double quotes for key classes and properties
        content = content.replace("class='sop-card'", 'class="sop-card"')
        content = content.replace("class='sop-meta'", 'class="sop-meta"')
        content = content.replace("class='sop-content-body'", 'class="sop-content-body"')
        content = content.replace("class='meta-unit'", 'class="meta-unit"')
        content = content.replace("class='meta-label'", 'class="meta-label"')
        content = content.replace("class='meta-val'", 'class="meta-val"')
        content = content.replace("style='color: #16a34a;'", 'style="color: #10b981;"')
        content = content.replace("style='color: #10b981;'", 'style="color: #10b981;"')

        # 1. Parse Version
        version_match = re.search(r'<span class="meta-label">Version</span><span class="meta-val">([^<]+)</span>', content)
        version = version_match.group(1).strip() if version_match else "1.0.0"

        # 2. Enforce/Ensure Author in sop-meta
        # Check if Author is already inside the sop-meta block
        meta_block_match = re.search(r'<div class="sop-meta">([\s\S]+?)</div>', content)
        if meta_block_match:
            meta_content = meta_block_match.group(1)
            if 'Author' not in meta_content:
                # Add Author before the end of the meta block
                new_meta_content = meta_content.rstrip() + '\n        <div class="meta-unit"><span class="meta-label">Author</span><span class="meta-val">George Bytes (Lead Auditor)</span></div>\n    '
                content = content.replace(meta_content, new_meta_content)
        
        # 3. Standardize and/or Wrap body content inside sop-content-body if needed
        # (Usually already wrapped, let's verify or ensure)
        
        # 4. Clean existing footer to avoid duplicates
        content = re.sub(r'<div class="sop-card-footer">[\s\S]+?</div>\s*</div>\s*$', '</div>', content)
        content = re.sub(r'<div class="sop-card-footer">[\s\S]+?</div>\s*$', '', content)
        
        # Strip trailing whitespaces and closing tags to cleanly append footer
        content = content.strip()
        
        # If the file ends with </div>, remove the last one, append footer, and add it back
        if content.endswith('</div>'):
            content = content[:-6].strip()
            
        footer_html = f"""
    <!-- 3. DOCUMENT CONTROL FOOTER -->
    <div class="sop-card-footer">
        <div>Classification: Institutional ISO 9001 QMS Record</div>
        <div>Effective Date: 06/03/2026</div>
        <div>Review Cycle: Annual (Rev {version})</div>
    </div>
</div>"""
        
        content = content + footer_html
        
        # Write back to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print(f"FORMATTED & Hardened: [{index_entry['id']}] {url_slug}")

if __name__ == '__main__':
    format_all_sops()
