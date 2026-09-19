"""
Test Script: Verify Semantic Embedding Generation and Re-indexing of SigmaKnowledgeScars
Standard: HWB-QMS-11.3 / Fortune 500 Cognitive Parity
Author: Systems Architect George
"""

import sys
import os
import psycopg2
import time
from dotenv import load_dotenv

sys.path.insert(0, '/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE')
load_dotenv('/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/.env')

from core.services.embedding import get_embedding, get_embeddings_batch

def test_semantic_reindex():
    print("Testing semantic embedding generation...")
    t0 = time.time()
    test_vec = get_embedding("Testing database connection pooling and query latency")
    t1 = time.time()
    print(f"Generated 1536d embedding in {t1 - t0:.3f}s. Sample: {test_vec[:5]}")
    assert len(test_vec) == 1536, f"Expected 1536 dimensions, got {len(test_vec)}"

    db_url = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db")
    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT id, description, root_cause, implemented_fix, preventative_rule FROM "SigmaKnowledgeScars" ORDER BY id LIMIT 5;')
            rows = cur.fetchall()
            print(f"\nFetched {len(rows)} scars for sample semantic re-indexing:")
            for r in rows:
                scar_id, desc, cause, fix, rule = r
                full_text = f"{desc} {cause or ''} {fix or ''} {rule or ''}"
                emb = get_embedding(full_text)
                cur.execute('UPDATE "SigmaKnowledgeScars" SET embedding = %s WHERE id = %s;', (emb, scar_id))
                print(f"  [SCAR {scar_id}] Updated with 1536d semantic embedding.")
            conn.commit()
            print("\nSample semantic re-indexing completed successfully!")
    finally:
        conn.close()

if __name__ == "__main__":
    test_semantic_reindex()
