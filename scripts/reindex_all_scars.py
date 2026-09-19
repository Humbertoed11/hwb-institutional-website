"""
SigmaFidelity™ Full Semantic Re-indexing Engine
Standard: HWB-QMS-11.3 Cognitive Architecture & Neural Growth
Upgrades all 145 scars in SigmaKnowledgeScars to 1536d Gemini Transformer Embeddings
Custodians: George (Systems Architect) & Humberto Dominguez (CEO)
"""

import os
import sys
import time
import psycopg2
from dotenv import load_dotenv

sys.path.insert(0, '/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE')
load_dotenv('/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/.env')

from core.services.embedding import get_embedding

def reindex_all_scars():
    print("================================================================================")
    print("  SigmaFidelity™ Enterprise Semantic Re-indexing (SigmaKnowledgeScars)")
    print("================================================================================")
    
    db_url = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db")
    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT id, description, category, root_cause, implemented_fix, preventative_rule FROM "SigmaKnowledgeScars" ORDER BY id;')
            rows = cur.fetchall()
            total = len(rows)
            print(f"[REINDEX] Found {total} scars to process.")
            
            start_time = time.time()
            updated_count = 0
            
            for idx, r in enumerate(rows, 1):
                scar_id, desc, cat, cause, fix, rule = r
                full_text = f"{desc} {cat or ''} {cause or ''} {fix or ''} {rule or ''}"
                
                try:
                    emb = get_embedding(full_text)
                    cur.execute('UPDATE "SigmaKnowledgeScars" SET embedding = %s WHERE id = %s;', (emb, scar_id))
                    updated_count += 1
                    if idx % 10 == 0 or idx == total:
                        elapsed = time.time() - start_time
                        print(f"  [{idx}/{total}] Processed scar ID {scar_id} ({updated_count}/{total} updated, {elapsed:.1f}s elapsed)")
                except Exception as e:
                    print(f"  [ERROR] Scar {scar_id} failed: {e}")
                
            conn.commit()
            total_elapsed = time.time() - start_time
            print("================================================================================")
            print(f"  ✓ SUCCESS: {updated_count}/{total} scars upgraded to true 1536d semantic embeddings.")
            print(f"  Total Duration: {total_elapsed:.2f}s (Average: {total_elapsed/total:.2f}s per scar)")
            print("================================================================================")
    finally:
        conn.close()

if __name__ == "__main__":
    reindex_all_scars()
