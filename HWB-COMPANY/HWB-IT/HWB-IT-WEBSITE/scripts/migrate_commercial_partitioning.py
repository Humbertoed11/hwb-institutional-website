#!/usr/bin/env python3
"""
SigmaFidelity™ Commercial Partitioning & M&A Tiering Migration
HWB-QMS Standard: Industrial Data Integrity & Acquisition Radar
Author: George (Lead Systems Architect)
"""

import os
import sys
import psycopg2


def run_migration():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("[ERROR] DATABASE_URL is not set.")
        sys.exit(1)

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    print("================================================================================")
    print("🚀  Executing Commercial Partitioning & M&A Tiering Migration")
    print("================================================================================")

    # 1. Add Columns
    cur.execute("""
        ALTER TABLE "Leads" 
        ADD COLUMN IF NOT EXISTS is_commercial BOOLEAN DEFAULT TRUE,
        ADD COLUMN IF NOT EXISTS commercial_status VARCHAR(50) DEFAULT 'Commercial Hub',
        ADD COLUMN IF NOT EXISTS acquisition_tier VARCHAR(50) DEFAULT 'Unranked',
        ADD COLUMN IF NOT EXISTS ownership_type VARCHAR(50) DEFAULT 'Independent Commercial',
        ADD COLUMN IF NOT EXISTS owner_verification_status VARCHAR(50) DEFAULT 'PENDING_PROOF',
        ADD COLUMN IF NOT EXISTS owner_evidence_citation TEXT;

        CREATE INDEX IF NOT EXISTS idx_leads_is_commercial ON "Leads" (is_commercial);
        CREATE INDEX IF NOT EXISTS idx_leads_acquisition_tier ON "Leads" (acquisition_tier);
        CREATE INDEX IF NOT EXISTS idx_leads_ownership_type ON "Leads" (ownership_type);
        CREATE INDEX IF NOT EXISTS idx_leads_owner_verification ON "Leads" (owner_verification_status);
    """)
    conn.commit()
    print("[SCHEMA] Columns and indexes added successfully.")

    # 2. Partition Group A: Contaminated Historical / Non-Childcare Legacy (capacity = 0 or NULL)
    cur.execute("""
        UPDATE "Leads"
        SET is_commercial = FALSE,
            commercial_status = 'Non-Childcare Legacy',
            estimated_annual_value = 0.0,
            acquisition_tier = 'Disqualified',
            ownership_type = 'Non-Childcare Business',
            status = 'ARCHIVED'
        WHERE capacity = 0 OR capacity IS NULL;
    """)
    legacy_count = cur.rowcount
    conn.commit()
    print(f"[CLEANSE] Archived {legacy_count:,} non-childcare legacy records (zeroed phantom value).")

    # 3. Partition Group B: Micro / In-Home Daycares (capacity 1 to 29)
    cur.execute("""
        UPDATE "Leads"
        SET is_commercial = FALSE,
            commercial_status = 'Micro In-Home',
            estimated_annual_value = 0.0,
            acquisition_tier = 'Disqualified',
            ownership_type = 'Residential In-Home'
        WHERE capacity > 0 AND capacity < 30;
    """)
    in_home_count = cur.rowcount
    conn.commit()
    print(f"[CLEANSE] Partitioned {in_home_count:,} micro in-home daycares (capacity < 30).")

    # 4. Partition Group C: Small Commercial Centers (capacity 30 to 59)
    cur.execute("""
        UPDATE "Leads"
        SET is_commercial = TRUE,
            commercial_status = 'Small Commercial',
            acquisition_tier = 'Tier 3 - Tuck-in Target',
            ownership_type = CASE 
                WHEN umbrella_name IS NOT NULL AND umbrella_name != '' THEN 'Network Facility'
                ELSE 'Independent Commercial'
            END
        WHERE capacity >= 30 AND capacity < 60;
    """)
    small_comm_count = cur.rowcount
    conn.commit()
    print(f"[CLASSIFIED] Classified {small_comm_count:,} small commercial centers (capacity 30-59).")

    # 5. Partition Group D: Commercial Hubs (capacity >= 60)
    # Tier 1: Mega-Institutional (200+)
    cur.execute("""
        UPDATE "Leads"
        SET is_commercial = TRUE,
            commercial_status = 'Commercial Hub',
            acquisition_tier = CASE
                WHEN umbrella_name IS NOT NULL AND umbrella_name != '' THEN 'Corporate / Network (200+)'
                ELSE 'Tier 1 - Mega Institutional'
            END
        WHERE capacity >= 200;
    """)
    tier1_count = cur.rowcount

    # Tier 2: Regional Commercial (150-199)
    cur.execute("""
        UPDATE "Leads"
        SET is_commercial = TRUE,
            commercial_status = 'Commercial Hub',
            acquisition_tier = CASE
                WHEN umbrella_name IS NOT NULL AND umbrella_name != '' THEN 'Corporate / Network (150-199)'
                ELSE 'Tier 2 - Regional Commercial'
            END
        WHERE capacity >= 150 AND capacity < 200;
    """)
    tier2_count = cur.rowcount

    # Tier 3: Commercial Add-on (60-149)
    cur.execute("""
        UPDATE "Leads"
        SET is_commercial = TRUE,
            commercial_status = 'Commercial Hub',
            acquisition_tier = CASE
                WHEN umbrella_name IS NOT NULL AND umbrella_name != '' THEN 'Corporate / Network (60-149)'
                ELSE 'Tier 3 - Commercial Add-on'
            END
        WHERE capacity >= 60 AND capacity < 150;
    """)
    tier3_count = cur.rowcount
    conn.commit()
    print(f"[CLASSIFIED] Classified Commercial Hubs: Tier 1: {tier1_count:,} | Tier 2: {tier2_count:,} | Tier 3: {tier3_count:,}")

    # 6. Synchronize ownership_type from CorporateUmbrellas
    cur.execute("""
        UPDATE "Leads" l
        SET ownership_type = u.category
        FROM "CorporateUmbrellas" u
        WHERE l.umbrella_name = u.umbrella_name;
    """)
    corp_sync_count = cur.rowcount
    conn.commit()
    print(f"[OWNERSHIP] Linked ownership types for {corp_sync_count:,} corporate/network facilities.")

    # 7. Final Audit Summary
    cur.execute("""
        SELECT is_commercial, COUNT(*), SUM(capacity), SUM(estimated_annual_value)
        FROM "Leads"
        GROUP BY is_commercial
        ORDER BY is_commercial DESC;
    """)
    print("\n--------------------------------------------------------------------------------")
    print("LIVE PIPELINE PARTITIONING AUDIT:")
    print("--------------------------------------------------------------------------------")
    for r in cur.fetchall():
        status = "ACTIVE COMMERCIAL" if r[0] else "ARCHIVED / NON-COMMERCIAL"
        print(f"[{status:<26}]: {r[1]:>6,} records | Cap: {r[2] or 0:>9,} | Pipeline: ${r[3] or 0.0:>14,.2f}")

    cur.execute("""
        SELECT acquisition_tier, COUNT(*), SUM(capacity)
        FROM "Leads"
        WHERE is_commercial = TRUE AND acquisition_tier LIKE 'Tier%'
        GROUP BY acquisition_tier
        ORDER BY acquisition_tier;
    """)
    print("\n--------------------------------------------------------------------------------")
    print("INDEPENDENT M&A DEAL RADAR TIERS (FOR PRIVATE EQUITY ACQUIRERS):")
    print("--------------------------------------------------------------------------------")
    for r in cur.fetchall():
        print(f"  -> {r[0]:<35}: {r[1]:>5,} centers | Cap: {r[2] or 0:>8,}")

    print("================================================================================")
    cur.close()
    conn.close()


if __name__ == "__main__":
    run_migration()
