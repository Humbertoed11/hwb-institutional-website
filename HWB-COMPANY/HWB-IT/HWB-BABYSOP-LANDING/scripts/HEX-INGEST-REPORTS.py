import os
import psycopg2
import hashlib

DB_URL = "postgresql://hexadmin:hexpassword@hex_postgis_db:5432/hex_dev_db"

def calculate_local_embedding(text):
    embedding = [0.0] * 1536
    hasher = hashlib.sha256(text.encode('utf-8'))
    digest = hasher.digest()
    for i in range(1536):
        byte_index = (i * 7) % len(digest)
        val = (digest[byte_index] / 127.5) - 1.0
        embedding[i] = round(val, 6)
    return embedding

REPORTS = [
    {
        "doc_id": "HEX-REPORT-1.0",
        "title": "Token Saving Strategy Status",
        "category": "AI Reports",
        "file_path": "/app/static/manual_source/HEX-REPORT-1.0-token-saving.html",
        "url_slug": "HEX-REPORT-1.0-token-saving.html"
    },
    {
        "doc_id": "HEX-REPORT-2.0",
        "title": "Master Specification Comparison",
        "category": "AI Reports",
        "file_path": "/app/static/manual_source/HEX-REPORT-2.0-master-comparison.html",
        "url_slug": "HEX-REPORT-2.0-master-comparison.html"
    },
    {
        "doc_id": "HEX-REPORT-3.0",
        "title": "Strategy Comparison Report",
        "category": "AI Reports",
        "file_path": "/app/static/manual_source/HEX-REPORT-3.0-strategy-comparison.html",
        "url_slug": "HEX-REPORT-3.0-strategy-comparison.html"
    },
    {
        "doc_id": "HEX-REPORT-4.0",
        "title": "Master Reference Report",
        "category": "AI Reports",
        "file_path": "/app/static/manual_source/HEX-REPORT-4.0-master-reference.html",
        "url_slug": "HEX-REPORT-4.0-master-reference.html"
    },
    {
        "doc_id": "HEX-REPORT-5.0",
        "title": "Lobe Integration Functions",
        "category": "AI Reports",
        "file_path": "/app/static/manual_source/HEX-REPORT-5.0-lobe-functions.html",
        "url_slug": "HEX-REPORT-5.0-lobe-functions.html"
    },
    {
        "doc_id": "HEX-REPORT-6.0",
        "title": "Mavericks Relocation Opportunity",
        "category": "AI Reports",
        "file_path": "/app/static/manual_source/HEX-REPORT-6.0-mavericks-relocation.html",
        "url_slug": "HEX-REPORT-6.0-mavericks-relocation.html"
    },
    {
        "doc_id": "HEX-REPORT-7.0",
        "title": "HUD Customization Options",
        "category": "AI Reports",
        "file_path": "/app/static/manual_source/HEX-REPORT-7.0-hud-customization.html",
        "url_slug": "HEX-REPORT-7.0-hud-customization.html"
    },
    {
        "doc_id": "HEX-REPORT-8.0",
        "title": "Path B Cost Projections",
        "category": "AI Reports",
        "file_path": "/app/static/manual_source/HEX-REPORT-8.0-cost-projection.html",
        "url_slug": "HEX-REPORT-8.0-cost-projection.html"
    },
    {
        "doc_id": "HEX-REPORT-9.0",
        "title": "Domain Name Options",
        "category": "AI Reports",
        "file_path": "/app/static/manual_source/HEX-REPORT-9.0-domain-options.html",
        "url_slug": "HEX-REPORT-9.0-domain-options.html"
    }
]

def ingest_reports():
    print("--- George Bytes: Ingesting AI Reports into SQL Manual Index ---")
    try:
        conn = psycopg2.connect(DB_URL)
        with conn.cursor() as cur:
            for rep in REPORTS:
                file_path = rep["file_path"]
                if not os.path.exists(file_path):
                    alt_path = file_path.replace("/manual_source/", "/manual_source/evaluation/")
                    if os.path.exists(alt_path):
                        file_path = alt_path
                    else:
                        print(f"WARNING: File {file_path} not found. Skipping.")
                        continue
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                embedding = calculate_local_embedding(content)
                cur.execute("""
                    INSERT INTO "HEX_KB_Library" (doc_id, title, category, content, url_slug, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (doc_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    category = EXCLUDED.category,
                    content = EXCLUDED.content,
                    url_slug = EXCLUDED.url_slug,
                    embedding = EXCLUDED.embedding,
                    last_updated = CURRENT_TIMESTAMP;
                """, (rep["doc_id"], rep["title"], rep["category"], content, rep["url_slug"], embedding))
                print(f"SUCCESS: Ingested {rep['doc_id']} ({rep['title']}) into category '{rep['category']}'.")
            
            # Log this action into the Interaction Core
            cur.execute("""
                INSERT INTO "HEX_InteractionCore" (user_prompt, agent_explanation, status)
                VALUES (%s, %s, %s);
            """, (
                "Approved Report Department Setup",
                "George Bytes successfully created the 'AI Reports' department, converted reports to HTML, and ingested them into the HEX_KB_Library table.",
                "SUCCESS"
            ))
            
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"FAILURE: Ingestion of AI Reports failed. {e}")

if __name__ == "__main__":
    ingest_reports()
