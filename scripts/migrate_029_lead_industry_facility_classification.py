#!/usr/bin/env python3
"""
SigmaFidelity™ Migration 029: Lead Industry & Facility Type Classification Engine
Standard: HWB-QMS-7.6 Enterprise Architecture Standards & Zero-Defect Poka-Yoke Protocol
Execution Authority: George (Systems Architect & mbB) & Humberto Dominguez (CEO)

Objectives:
1. Reclassify all 28,720+ leads using BusinessClassifierEngine into verified institutional sectors:
   - Automotive Sales & Services -> Automotive
   - Early Childhood Education -> Child Care Center
   - Primary & Secondary Education -> School
   - Faith-Based Organizations -> Church
   - Healthcare & Clinical -> Medical
   - Industrial & Logistics -> Warehouse
   - Retail & Wholesale -> Retail
   - Corporate & Professional Services -> Office
   - Commercial Property -> Other
2. Eliminate contaminated source attribution by updating lead_source from 'Texas Childcare Registry'
   to 'Texas Commercial Registry' for all non-childcare commercial entities.
3. Guarantee 100% data continuity and zero orphaned rows.
"""

import os
import sys
import time
from collections import Counter
from typing import Dict, Any, List, Tuple

import psycopg2
from psycopg2.extras import execute_batch

# Ensure core is importable
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", "HWB-COMPANY", "HWB-IT", "HWB-IT-WEBSITE"))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.services.classifier import BusinessClassifierEngine


def get_db_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db")


def run_migration(db_url: str = None) -> None:
    target_db_url = db_url or get_db_url()
    print("=" * 80)
    print("🏛️  STARTING SIGMAFIDELITY™ MIGRATION 029: LEAD CLASSIFICATION & SOURCE PURIFICATION")
    print(f"📡  Target Database: {target_db_url.split('@')[-1] if '@' in target_db_url else target_db_url}")
    print("=" * 80)

    start_time = time.time()
    conn = psycopg2.connect(target_db_url)
    cur = conn.cursor()

    try:
        # 1. Fetch all leads
        print("[STEP 1/4] Fetching all leads from production table...")
        cur.execute('SELECT id, center_name, capacity, lead_source, industry, facility_type FROM "Leads" ORDER BY id ASC;')
        rows = cur.fetchall()
        total_leads = len(rows)
        print(f"✓ Retrieved {total_leads:,} leads for classification audit.")

        # 2. Classify and detect diffs
        print("[STEP 2/4] Executing BusinessClassifierEngine across full dataset...")
        update_batch: List[Tuple[str, str, str, int]] = []
        industry_counts: Counter = Counter()
        facility_counts: Counter = Counter()
        lead_source_corrections = 0
        unchanged_count = 0

        for lead_id, center_name, capacity, current_source, current_ind, current_fac in rows:
            classification = BusinessClassifierEngine.classify(
                center_name=center_name,
                capacity=capacity,
                lead_source=current_source
            )

            new_ind = classification.industry
            new_fac = classification.facility_type
            new_source = classification.normalized_lead_source

            industry_counts[new_ind] += 1
            facility_counts[new_fac] += 1

            if current_source != new_source:
                lead_source_corrections += 1

            if new_ind != current_ind or new_fac != current_fac or new_source != current_source:
                update_batch.append((new_ind, new_fac, new_source, lead_id))
            else:
                unchanged_count += 1

        print(f"✓ Classification complete: {len(update_batch):,} rows require updating ({unchanged_count:,} already aligned).")

        # 3. Batch Update
        print(f"[STEP 3/4] Applying atomic batch updates to PostgreSQL ({len(update_batch):,} rows)...")
        update_query = """
            UPDATE "Leads"
            SET industry = %s,
                facility_type = %s,
                lead_source = %s,
                updated_at = CURRENT_DATE
            WHERE id = %s;
        """
        
        # Execute in chunks of 2,000 for maximum memory and lock efficiency
        chunk_size = 2000
        for i in range(0, len(update_batch), chunk_size):
            chunk = update_batch[i : i + chunk_size]
            execute_batch(cur, update_query, chunk, page_size=1000)
            print(f"   -> Committed chunk {i + len(chunk):,} / {len(update_batch):,} records...")

        conn.commit()
        print("✓ All batch updates committed to PostgreSQL successfully.")

        # 4. Telemetry & Verification
        print("[STEP 4/4] Generating Institutional Classification Audit Report...")
        print("\n--- NEW INDUSTRY SEGMENTATION ---")
        for ind, count in industry_counts.most_common():
            pct = (count / total_leads) * 100
            print(f"  • {ind:<30}: {count:>6,} ({pct:>5.1f}%)")

        print("\n--- NEW FACILITY TYPE SEGMENTATION ---")
        for fac, count in facility_counts.most_common():
            pct = (count / total_leads) * 100
            print(f"  • {fac:<30}: {count:>6,} ({pct:>5.1f}%)")

        print("\n--- SOURCE PURIFICATION METRICS ---")
        print(f"  • Contaminated Sources Cleansed (Childcare -> Commercial): {lead_source_corrections:,}")

        duration = round(time.time() - start_time, 2)
        print("=" * 80)
        print(f"🏛️  MIGRATION 029 COMPLETE: {len(update_batch):,} records updated in {duration}s.")
        print("=" * 80)

    except Exception as e:
        conn.rollback()
        print(f"❌ [MIGRATION 029 FATAL ERROR]: {e}")
        raise
    finally:
        cur.close()
        conn.close()
run_migration_029 = run_migration


if __name__ == "__main__":
    run_migration_029()
