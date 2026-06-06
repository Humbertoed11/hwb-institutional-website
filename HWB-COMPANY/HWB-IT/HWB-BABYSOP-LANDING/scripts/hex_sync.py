import os
import json
import re
import psycopg2
import hashlib
from dotenv import load_dotenv

def calculate_local_embedding(text):
    # Generates a deterministic mock 1536-dimension embedding based on text hash
    embedding = [0.0] * 1536
    hasher = hashlib.sha256(text.encode('utf-8'))
    digest = hasher.digest()
    for i in range(1536):
        byte_index = (i * 7) % len(digest)
        val = (digest[byte_index] / 127.5) - 1.0
        embedding[i] = round(val, 6)
    return embedding

# Load local environment variables
load_dotenv()

DB_URL = os.environ.get("DATABASE_URL", "postgresql://hexadmin:hexpassword@hex_postgis_db:5432/hex_dev_db")

# Dynamic Environment Path Resolution
if os.path.exists("/app"):
    print("--- George Bytes: Container Environment Detected ---")
    INDEX_FILE = "/app/qms_index.json"
    HEX_QMS_DIR = "/app/static/manual_source"
    RECOVERY_FILE = "/app/HEX-SESSION-RECOVERY.md"
else:
    print("--- George Bytes: Host Environment Detected ---")
    INDEX_FILE = "/home/humbertoed/hexgrowth/app/qms_index.json"
    HEX_QMS_DIR = "/home/humbertoed/hexgrowth/HEX-QMS"
    RECOVERY_FILE = "/home/humbertoed/hexgrowth/HEX-SESSION-RECOVERY.md"

def parse_session_recovery():
    print(f"--- George Bytes: Parsing {RECOVERY_FILE} ---")
    if not os.path.exists(RECOVERY_FILE):
        print(f"WARNING: Session recovery file not found at {RECOVERY_FILE}")
        return None, {}
    
    with open(RECOVERY_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract Session ID using regex
    session_id_match = re.search(r"\|\s*\*\*Session ID\*\*\s*\|\s*([^\s|]+)\s*\|", content)
    session_id = session_id_match.group(1) if session_id_match else "HEXGROWTH-DEFAULT-SESSION"
    
    # Parse markdown table rows
    state_data = {
        "raw_markdown": content,
        "parameters": {}
    }
    
    rows = re.findall(r"\|\s*\*\*([^*]+)\*\*\s*\|\s*([^|]+?)\s*\|", content)
    for row in rows:
        key, value = row[0].strip(), row[1].strip()
        if key != "Session ID":
            state_data["parameters"][key] = value
            
    print(f"SUCCESS: Parsed Session ID: {session_id}")
    return session_id, state_data

def sync_qms():
    print("--- George Bytes: Synchronizing HexGrowth QMS Manuals ---")
    if not os.path.exists(INDEX_FILE):
        print(f"FAILURE: Master QMS index not found at {INDEX_FILE}")
        return
        
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        sops = json.load(f)
        
    try:
        conn = psycopg2.connect(DB_URL)
        with conn.cursor() as cur:
            # 1. Prune QMS records that are no longer in the master index
            valid_doc_ids = [sop.get('id') for sop in sops if sop.get('id')]
            if valid_doc_ids:
                cur.execute('DELETE FROM "HEX_KB_Library" WHERE doc_id NOT IN %s', (tuple(valid_doc_ids),))
            
            # 2. Iterate and ingest QMS documents
            for sop in sops:
                doc_id = sop.get('id')
                title = sop.get('title')
                category = sop.get('department')
                url_slug = sop.get('file')
                
                # QMS document path (resolving subdirectories if specified in index)
                file_path = os.path.join(HEX_QMS_DIR, url_slug)
                
                if not os.path.exists(file_path):
                    print(f"WARNING: QMS file not found at {file_path}. Skipping.")
                    continue
                    
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                embedding = calculate_local_embedding(content)
                cur.execute("""
                    INSERT INTO "HEX_KB_Library" (doc_id, title, category, content, url_slug, embedding, last_updated)
                    VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (doc_id) DO UPDATE 
                    SET title = EXCLUDED.title,
                        category = EXCLUDED.category,
                        content = EXCLUDED.content,
                        url_slug = EXCLUDED.url_slug,
                        embedding = EXCLUDED.embedding,
                        last_updated = CASE 
                            WHEN "HEX_KB_Library".content IS DISTINCT FROM EXCLUDED.content 
                              OR "HEX_KB_Library".title IS DISTINCT FROM EXCLUDED.title
                            THEN CURRENT_TIMESTAMP 
                            ELSE "HEX_KB_Library".last_updated 
                        END;
                """, (doc_id, title, category, content, url_slug, embedding))
                print(f"INGESTED (UPSERT): [{doc_id}] {title} -> {url_slug}")
            
            # 3. Synchronize Session Recovery State
            session_id, state_data = parse_session_recovery()
            if session_id:
                # Ingest to new HEX_SystemState (Tier 6)
                cur.execute("""
                    INSERT INTO "HEX_SystemState" (session_id, state_data)
                    VALUES (%s, %s)
                    ON CONFLICT (session_id) DO UPDATE
                    SET state_data = EXCLUDED.state_data,
                        updated_at = CURRENT_TIMESTAMP;
                """, (session_id, json.dumps(state_data)))
                print(f"INGESTED: Session State [{session_id}] successfully indexed in SystemState.")
                
            conn.commit()
            print("SUCCESS: HexGrowth QMS Monolithic database synchronization complete.")
        conn.close()
    except Exception as e:
        print(f"FAILURE: Synchronization failed. {e}")

if __name__ == "__main__":
    sync_qms()
