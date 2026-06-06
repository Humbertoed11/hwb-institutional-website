import os
import re
import json
import hashlib
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get("DATABASE_URL", "postgresql://hexadmin:hexpassword@hex_postgis_db:5432/hex_dev_db")

# Path Resolution
if os.path.exists("/app"):
    HEX_QMS_DIR = "/app/static/manual_source"
else:
    HEX_QMS_DIR = "/home/humbertoed/hexgrowth/HEX-QMS"

def calculate_local_embedding(text):
    # Generates a deterministic mock 1536-dimension embedding based on text hash
    # In production, this can be swapped with OpenAI or local transformer models.
    embedding = [0.0] * 1536
    hasher = hashlib.sha256(text.encode('utf-8'))
    digest = hasher.digest()
    for i in range(1536):
        byte_index = (i * 7) % len(digest)
        # Scale to range [-1.0, 1.0]
        val = (digest[byte_index] / 127.5) - 1.0
        embedding[i] = round(val, 6)
    return embedding

def scan_and_ingest():
    print(f"--- George Bytes: Initializing Persistence Protocol Ingestion ---")
    print(f"Target Directory: {HEX_QMS_DIR}")
    
    if not os.path.exists(HEX_QMS_DIR):
        print(f"FAILURE: QMS Directory not found at {HEX_QMS_DIR}")
        return

    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()

    count_inserted = 0
    count_updated = 0

    for root, dirs, files in os.walk(HEX_QMS_DIR):
        for file in files:
            if not (file.endswith('.html') or file.endswith('.md')):
                continue

            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, HEX_QMS_DIR)
            category = os.path.dirname(rel_path) or "General"
            
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse Doc ID
            doc_id_match = re.search(r'(HEX-[A-Z0-9.-]+)', file)
            doc_id = doc_id_match.group(1) if doc_id_match else file.replace('.html', '').replace('.md', '')
            doc_id = doc_id.rstrip('.-')

            # Parse Title
            title_match = re.search(r'<h1>(.*?)</h1>', content, re.IGNORECASE)
            if not title_match:
                title_match = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE)
            title = title_match.group(1).strip() if title_match else doc_id.replace('-', ' ').title()
            title = re.sub(r'<[^>]*>', '', title)

            # Calculate deterministic embedding vector
            embedding = calculate_local_embedding(content)

            # Ingest to database
            try:
                # Check if document exists
                cursor.execute('SELECT doc_id, content FROM "HEX_KB_Library" WHERE doc_id = %s', (doc_id,))
                existing = cursor.fetchone()

                if not existing:
                    cursor.execute("""
                        INSERT INTO "HEX_KB_Library" (doc_id, title, category, content, url_slug, embedding)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (doc_id, title, category, content, rel_path, embedding))
                    count_inserted += 1
                    print(f"INGESTED (NEW): [{doc_id}] {title}")
                else:
                    if existing[1] != content:
                        cursor.execute("""
                            UPDATE "HEX_KB_Library"
                            SET title = %s, category = %s, content = %s, url_slug = %s, embedding = %s, last_updated = CURRENT_TIMESTAMP
                            WHERE doc_id = %s
                        """, (title, category, content, rel_path, embedding, doc_id))
                        count_updated += 1
                        print(f"UPDATED: [{doc_id}] {title}")

            except Exception as e:
                print(f"ERROR: Failed to ingest [{doc_id}]: {e}")
                conn.rollback()
                continue

    # Log action to Telemetry table
    try:
        telemetry_data = {
            "inserted": count_inserted,
            "updated": count_updated,
            "total_scanned": count_inserted + count_updated
        }
        cursor.execute("""
            INSERT INTO "HEX_Telemetry" (action_name, status, technical_data)
            VALUES (%s, %s, %s)
        """, ("KB_Library_Sync", "SUCCESS", json.dumps(telemetry_data)))
        conn.commit()
    except Exception as e:
        print(f"WARNING: Telemetry logging failed: {e}")
        conn.rollback()

    conn.close()
    print(f"SUCCESS: Ingestion finished. Inserted: {count_inserted}, Updated: {count_updated}.")

if __name__ == "__main__":
    scan_and_ingest()
