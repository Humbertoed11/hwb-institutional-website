import os
import json

if os.path.exists("/app"):
    INDEX_FILE = "/app/qms_index.json"
else:
    INDEX_FILE = "/home/humbertoed/hexgrowth/app/qms_index.json"

dept_mapping = {
    "HEX-SOP-0.1": "01 Executive Governance",
    "HEX-SOP-0.2": "01 Executive Governance",
    "HEX-SOP-1.0": "01 Executive Governance",
    "HEX-REPORT-12.0": "01 Executive Governance",
    "HEX-REPORT-13.0": "01 Executive Governance",
    "HEX-REPORT-2.0": "01 Executive Governance",
    "HEX-REPORT-3.0": "01 Executive Governance",
    
    "HEX-SOP-1.1": "02 HR (Human Resources)",
    
    "HEX-SOP-2.0": "03 Operations",
    "HEX-SOP-3.0": "03 Operations",
    "HEX-SOP-4.1": "03 Operations",
    "HEX-SOP-5.0": "03 Operations",
    "HEX-SOP-5.1": "03 Operations",
    "HEX-SOP-6.0": "03 Operations",
    "HEX-SOP-6.1": "03 Operations",
    "HEX-SOP-9.0": "03 Operations",
    "HEX-SOP-9.1": "03 Operations",
    "HEX-SOP-9.2": "03 Operations",
    "HEX-SOP-10.0": "03 Operations",
    "HEX-SOP-11.0": "03 Operations",
    "HEX-REPORT-5.0": "03 Operations",
    "HEX-REPORT-19.0": "03 Operations",
    "HEX-REPORT-21.0": "03 Operations",
    "HEX-LOBE-1.0": "03 Operations",
    "HEX-LOBE-2.0": "03 Operations",
    "HEX-LOBE-3.0": "03 Operations",
    "HEX-LOBE-4.0": "03 Operations",
    "HEX-LOBE-5.0": "03 Operations",
    "HEX-LOBE-6.0": "03 Operations",
    "HEX-LOBE-7.0": "03 Operations",
    
    "HEX-IP-8.0": "04 Purchasing",
    "HEX-IP-9.0": "04 Purchasing",
    
    "HEX-REPORT-4.0": "05 Marketing & Sales",
    "HEX-REPORT-6.0": "05 Marketing & Sales",
    "HEX-REPORT-7.0": "05 Marketing & Sales",
    "HEX-REPORT-9.0": "05 Marketing & Sales",
    
    "HEX-SOP-4.2": "06 IT (Information Technology)",
    "HEX-SOP-7.5": "06 IT (Information Technology)",
    "HEX-REPORT-1.0": "06 IT (Information Technology)",
    "HEX-REPORT-10.0": "06 IT (Information Technology)",
    "HEX-REPORT-14.0": "06 IT (Information Technology)",
    "HEX-REPORT-15.0": "06 IT (Information Technology)",
    "HEX-REPORT-16.0": "06 IT (Information Technology)",
    
    "HEX-REPORT-11.0": "07 Communications",
    
    "HEX-REPORT-8.0": "08 Accounting",
    
    "HEX-SOP-7.1": "09 Legal & Compliance",
    "HEX-IP-9.1": "09 Legal & Compliance"
}

def reindex_departments():
    if not os.path.exists(INDEX_FILE):
        print(f"FAILURE: QMS index not found at {INDEX_FILE}")
        return
        
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        sops = json.load(f)
        
    for item in sops:
        doc_id = item.get('id')
        if doc_id in dept_mapping:
            old_dept = item.get('department')
            new_dept = dept_mapping[doc_id]
            item['department'] = new_dept
            print(f"REINDEXED: [{doc_id}] {old_dept} -> {new_dept}")
        else:
            print(f"WARNING: No mapping found for {doc_id}")
            
    # Sort the index items based on their new department prefixes to ensure they sit sequentially in qms_index.json
    sops.sort(key=lambda x: (x.get('department', 'General'), x.get('id', '')))

    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        json.dump(sops, f, indent=4)
        
    print(f"SUCCESS: Reindexed QMS Master Index saved at {INDEX_FILE}")

if __name__ == '__main__':
    reindex_departments()
