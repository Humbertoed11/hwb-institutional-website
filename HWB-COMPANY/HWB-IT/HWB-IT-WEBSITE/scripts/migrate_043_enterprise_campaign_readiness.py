#!/usr/bin/env python3
"""
SigmaFidelity™ Migration 043: Enterprise Campaign Readiness, Global Suppression & DNS MX Sync
Standard: HWB-QMS-7.6 Enterprise Architecture Standards
Authority: Humberto Dominguez (CEO) - Approved 10/17/2026
"""

import os
import sys
import json
import gzip
import time
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor, execute_batch, execute_values

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent if CURRENT_DIR.name == "scripts" else CURRENT_DIR.parent.parent
WEBSITE_DIR = PROJECT_ROOT / "HWB-COMPANY" / "HWB-IT" / "HWB-IT-WEBSITE"


def run_migration(db_url: str = None) -> dict:
    target_url = db_url or os.environ.get("DATABASE_URL", "postgresql://hwbdev:hwbpassword@db:5432/hwb_dev_db")
    t_start = time.time()
    print("\n==================================================================", flush=True)
    print("  Applying Migration 043: Enterprise Campaign Readiness & DNS MX Sync", flush=True)
    print("==================================================================", flush=True)

    possible_paths = [
        Path("/app/database/seeds/campaign_readiness_sync_043.json.gz"),
        WEBSITE_DIR / "database" / "seeds" / "campaign_readiness_sync_043.json.gz",
        CURRENT_DIR.parent / "database" / "seeds" / "campaign_readiness_sync_043.json.gz",
    ]
    payload_file = next((p for p in possible_paths if p.exists()), None)
    if not payload_file:
        raise FileNotFoundError("campaign_readiness_sync_043.json.gz not found in search paths")

    with gzip.open(payload_file, "rt", encoding="utf-8") as f:
        payload = json.load(f)

    comm_leads = payload.get("commercial_leads", [])
    suppressions = payload.get("suppressions", [])
    domain_health = payload.get("domain_health", [])

    conn = psycopg2.connect(target_url)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. Create tables and columns
            cur.execute("""
                CREATE TABLE IF NOT EXISTS "EmailSuppressionList" (
                    id SERIAL PRIMARY KEY,
                    email_lower VARCHAR(255) UNIQUE NOT NULL,
                    reason VARCHAR(100) NOT NULL,
                    source VARCHAR(100) DEFAULT 'SYSTEM_AUDIT',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS "EmailDomainHealth" (
                    domain VARCHAR(255) PRIMARY KEY,
                    has_mx BOOLEAN NOT NULL DEFAULT TRUE,
                    mx_records TEXT,
                    checked_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                ALTER TABLE "Leads" ADD COLUMN IF NOT EXISTS campaign_ready BOOLEAN DEFAULT FALSE;
                ALTER TABLE "Leads" ADD COLUMN IF NOT EXISTS email_hygiene_status VARCHAR(50) DEFAULT 'PHONE_ONLY';
                ALTER TABLE "Leads" ADD COLUMN IF NOT EXISTS email_inbox_type VARCHAR(50) DEFAULT 'NONE';
                ALTER TABLE "Leads" ADD COLUMN IF NOT EXISTS email_mx_verified BOOLEAN DEFAULT FALSE;
                ALTER TABLE "Leads" ADD COLUMN IF NOT EXISTS last_campaigned_at TIMESTAMP WITH TIME ZONE;
                CREATE INDEX IF NOT EXISTS idx_leads_campaign_ready ON "Leads"(campaign_ready) WHERE campaign_ready = TRUE;
                CREATE INDEX IF NOT EXISTS idx_leads_email_hygiene ON "Leads"(email_hygiene_status);
            """)

            # 2. Upsert EmailSuppressionList and EmailDomainHealth
            if suppressions:
                execute_values(
                    cur,
                    """
                    INSERT INTO "EmailSuppressionList" (email_lower, reason, source)
                    VALUES %s
                    ON CONFLICT (email_lower) DO NOTHING;
                    """,
                    [(s["email_lower"], s["reason"], s.get("source") or "SYSTEM_AUDIT") for s in suppressions]
                )

            if domain_health:
                execute_values(
                    cur,
                    """
                    INSERT INTO "EmailDomainHealth" (domain, has_mx, mx_records, checked_at)
                    VALUES %s
                    ON CONFLICT (domain) DO UPDATE SET
                        has_mx = EXCLUDED.has_mx,
                        mx_records = EXCLUDED.mx_records,
                        checked_at = CURRENT_TIMESTAMP;
                    """,
                    [(d["domain"], bool(d["has_mx"]), d.get("mx_records") or "") for d in domain_health],
                    template="(%s, %s, %s, CURRENT_TIMESTAMP)"
                )

            # 3. Quarantine non-childcare Texas Commercial Registry rows (capacity=0 Automotive/Commercial Property)
            # and micro/residential in-home daycares (capacity < 30) on target database
            cur.execute("""
                UPDATE "Leads"
                SET is_commercial = FALSE,
                    acquisition_tier = 'Disqualified',
                    ownership_type = COALESCE(ownership_type, 'Non-Childcare Business'),
                    commercial_status = 'Disqualified'
                WHERE (
                    (COALESCE(lead_source, '') = 'Texas Commercial Registry' AND COALESCE(capacity, 0) = 0 AND COALESCE(industry, '') IN ('Automotive', 'Commercial Property', 'Corporate / Office', 'Industrial / Logistics', 'Retail & Hospitality'))
                    OR (COALESCE(capacity, 0) > 0 AND capacity < 30 AND COALESCE(industry, '') IN ('Child Care', 'Education'))
                );
            """)

            # 4. Reconcile & Enrich the 10,732 Verified Commercial Leads
            cur.execute("""
                SELECT id, process_id,
                       LOWER(TRIM(COALESCE(center_name, ''))) AS cname,
                       LOWER(TRIM(COALESCE(address, ''))) AS addr,
                       LOWER(TRIM(COALESCE(city, ''))) AS cty
                FROM "Leads";
            """)
            existing_rows = cur.fetchall()
            by_pid = {r["process_id"]: r["id"] for r in existing_rows if r.get("process_id")}
            by_loc = {(r["cname"], r["addr"], r["cty"]): r["id"] for r in existing_rows if r.get("cname")}

            updates = []
            inserts = []
            for l in comm_leads:
                pid = l.get("process_id")
                loc_key = (
                    (l.get("center_name") or "").strip().lower(),
                    (l.get("address") or "").strip().lower(),
                    (l.get("city") or "").strip().lower(),
                )
                matched_id = None
                if pid and pid in by_pid:
                    matched_id = by_pid[pid]
                elif loc_key in by_loc:
                    matched_id = by_loc[loc_key]

                if matched_id:
                    updates.append({
                        "target_id": matched_id,
                        "email": l.get("email"),
                        "phone": l.get("phone"),
                        "director": l.get("director"),
                        "decision_maker": l.get("decision_maker"),
                        "job_title": l.get("job_title"),
                        "capacity": l.get("capacity") or 0,
                        "sqf": l.get("sqf") or 0,
                        "estimated_annual_value": l.get("estimated_annual_value") or 0.0,
                        "industry": l.get("industry"),
                        "facility_type": l.get("facility_type"),
                        "lead_source": l.get("lead_source"),
                        "umbrella_name": l.get("umbrella_name"),
                        "acquisition_tier": l.get("acquisition_tier"),
                        "ownership_type": l.get("ownership_type"),
                        "commercial_status": l.get("commercial_status"),
                        "is_commercial": True,
                        "is_dnc": bool(l.get("is_dnc", False)),
                        "process_id": pid,
                        "county": (l.get("county") or "").strip().upper() or None,
                    })
                else:
                    inserts.append({
                        "center_name": l.get("center_name"),
                        "address": l.get("address"),
                        "city": l.get("city"),
                        "county": (l.get("county") or "").strip().upper() or None,
                        "state": l.get("state") or "TX",
                        "zipcode": l.get("zipcode"),
                        "phone": l.get("phone"),
                        "email": l.get("email"),
                        "director": l.get("director"),
                        "decision_maker": l.get("decision_maker"),
                        "job_title": l.get("job_title"),
                        "capacity": l.get("capacity") or 0,
                        "sqf": l.get("sqf") or 0,
                        "estimated_annual_value": l.get("estimated_annual_value") or 0.0,
                        "industry": l.get("industry") or "Child Care",
                        "facility_type": l.get("facility_type") or "Child Care Center",
                        "lead_source": l.get("lead_source") or "Texas Childcare Registry",
                        "umbrella_name": l.get("umbrella_name"),
                        "acquisition_tier": l.get("acquisition_tier"),
                        "ownership_type": l.get("ownership_type"),
                        "commercial_status": l.get("commercial_status") or "Commercial Hub",
                        "is_commercial": True,
                        "is_dnc": bool(l.get("is_dnc", False)),
                        "status": l.get("status") or "NEW",
                        "process_id": pid,
                    })

            if updates:
                upd_sql = """
                    UPDATE "Leads" SET
                        email = COALESCE(NULLIF(%(email)s, ''), email),
                        phone = COALESCE(NULLIF(%(phone)s, ''), phone),
                        director = COALESCE(NULLIF(%(director)s, ''), director),
                        decision_maker = %(decision_maker)s,
                        job_title = COALESCE(NULLIF(%(job_title)s, ''), job_title),
                        capacity = CASE WHEN %(capacity)s > 0 THEN %(capacity)s ELSE capacity END,
                        sqf = CASE WHEN %(sqf)s > 0 THEN %(sqf)s ELSE sqf END,
                        estimated_annual_value = CASE WHEN %(estimated_annual_value)s > 0 THEN %(estimated_annual_value)s ELSE estimated_annual_value END,
                        industry = COALESCE(NULLIF(%(industry)s, ''), industry),
                        facility_type = COALESCE(NULLIF(%(facility_type)s, ''), facility_type),
                        lead_source = COALESCE(NULLIF(%(lead_source)s, ''), lead_source),
                        umbrella_name = COALESCE(NULLIF(%(umbrella_name)s, ''), umbrella_name),
                        acquisition_tier = COALESCE(NULLIF(%(acquisition_tier)s, ''), acquisition_tier),
                        ownership_type = COALESCE(NULLIF(%(ownership_type)s, ''), ownership_type),
                        commercial_status = COALESCE(NULLIF(%(commercial_status)s, ''), commercial_status),
                        is_commercial = TRUE,
                        is_dnc = (COALESCE(is_dnc, FALSE) OR %(is_dnc)s),
                        process_id = COALESCE(process_id, %(process_id)s),
                        county = COALESCE(%(county)s, UPPER(TRIM(county)))
                    WHERE id = %(target_id)s;
                """
                execute_batch(cur, upd_sql, updates, page_size=250)

            if inserts:
                ins_sql = """
                    INSERT INTO "Leads" (
                        center_name, address, city, county, state, zipcode,
                        phone, email, director, decision_maker, job_title,
                        capacity, sqf, estimated_annual_value,
                        industry, facility_type, lead_source, umbrella_name,
                        acquisition_tier, ownership_type, commercial_status,
                        is_commercial, is_dnc, status, process_id, input_date
                    ) VALUES (
                        %(center_name)s, %(address)s, %(city)s, %(county)s, %(state)s, %(zipcode)s,
                        %(phone)s, %(email)s, %(director)s, %(decision_maker)s, %(job_title)s,
                        %(capacity)s, %(sqf)s, %(estimated_annual_value)s,
                        %(industry)s, %(facility_type)s, %(lead_source)s, %(umbrella_name)s,
                        %(acquisition_tier)s, %(ownership_type)s, %(commercial_status)s,
                        %(is_commercial)s, %(is_dnc)s, %(status)s, %(process_id)s, CURRENT_DATE
                    );
                """
                execute_batch(cur, ins_sql, inserts, page_size=250)

            # 5. Install PostgreSQL BEFORE INSERT OR UPDATE Trigger for Campaign Readiness
            cur.execute(r"""
                CREATE OR REPLACE FUNCTION fn_leads_compute_campaign_readiness()
                RETURNS TRIGGER AS $$
                DECLARE
                    v_digits TEXT;
                    v_domain TEXT;
                    v_suppressed BOOLEAN;
                    v_dead_mx BOOLEAN;
                BEGIN
                    -- 1. Sanitize Email
                    IF NEW.email IS NOT NULL THEN
                        NEW.email := LOWER(REGEXP_REPLACE(TRIM(NEW.email), '\.+$', ''));
                        IF NEW.email IN ('', 'none', 'n/a', 'unknown', 'null', 'no email', '--') THEN
                            NEW.email := NULL;
                        END IF;
                    END IF;

                    -- 2. Sanitize Phone to (###)-###-####
                    IF NEW.phone IS NOT NULL THEN
                        v_digits := REGEXP_REPLACE(NEW.phone, '\D', '', 'g');
                        IF LENGTH(v_digits) = 11 AND LEFT(v_digits, 1) = '1' THEN
                            v_digits := SUBSTRING(v_digits FROM 2 FOR 10);
                        END IF;
                        IF LENGTH(v_digits) = 10 THEN
                            NEW.phone := '(' || SUBSTRING(v_digits FROM 1 FOR 3) || ')-'
                                         || SUBSTRING(v_digits FROM 4 FOR 3) || '-'
                                         || SUBSTRING(v_digits FROM 7 FOR 4);
                        ELSIF LENGTH(v_digits) < 10 THEN
                            NEW.phone := NULL;
                        END IF;
                    END IF;

                    -- 3. Classify Inbox Type
                    IF NEW.email IS NULL THEN
                        NEW.email_inbox_type := 'NONE';
                    ELSIF NEW.email ~* '^(info|contact|office|admin|director|hello|inquiries|admissions|enroll|frontdesk|support|school|center|daycare|preschool)@' THEN
                        NEW.email_inbox_type := 'ROLE_INBOX';
                    ELSE
                        NEW.email_inbox_type := 'DIRECT_PERSONAL';
                    END IF;

                    -- 4. Evaluate 6-Gate Enterprise Campaign Readiness
                    IF COALESCE(NEW.is_commercial, TRUE) = FALSE OR COALESCE(NEW.status, '') = 'ARCHIVED' OR COALESCE(NEW.commercial_status, '') = 'Permanently Closed' THEN
                        NEW.campaign_ready := FALSE;
                        NEW.email_mx_verified := FALSE;
                        IF COALESCE(NEW.commercial_status, '') = 'Permanently Closed' THEN
                            NEW.email_hygiene_status := 'FACILITY_CLOSED';
                        ELSE
                            NEW.email_hygiene_status := 'NON_COMMERCIAL';
                        END IF;
                        RETURN NEW;
                    END IF;

                    IF COALESCE(NEW.is_dnc, FALSE) = TRUE
                       OR UPPER(TRIM(COALESCE(NEW.status, ''))) IN ('DNC', 'DO NOT CALL (DNC)', 'UNSUBSCRIBED', 'LOST', 'ACTIVE')
                       OR COALESCE(NEW.is_converted, FALSE) = TRUE THEN
                        NEW.campaign_ready := FALSE;
                        NEW.email_hygiene_status := 'DO_NOT_EMAIL';
                        RETURN NEW;
                    END IF;

                    IF COALESCE(NEW.is_duplicate, FALSE) = TRUE THEN
                        NEW.campaign_ready := FALSE;
                        NEW.email_hygiene_status := 'DUPLICATE_RECORD';
                        RETURN NEW;
                    END IF;

                    IF NEW.email IS NULL THEN
                        NEW.campaign_ready := FALSE;
                        NEW.email_mx_verified := FALSE;
                        NEW.email_hygiene_status := 'PHONE_ONLY';
                        RETURN NEW;
                    END IF;

                    IF NEW.email !~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
                       OR NEW.email ~* '(^background@|backgroundcheck|donotreply|no-reply|noreply|abuse|postmaster|example\.com|sentry\.io|wixpress\.com)'
                       OR NEW.email LIKE '%.ca'
                       OR NEW.email LIKE '%.ca.gov'
                       OR UPPER(TRIM(COALESCE(NEW.state, 'TX'))) IN ('CA', 'WA') THEN
                        NEW.campaign_ready := FALSE;
                        NEW.email_mx_verified := FALSE;
                        NEW.email_hygiene_status := 'INVALID_OR_SUPPRESSED';
                        RETURN NEW;
                    END IF;

                    SELECT EXISTS (SELECT 1 FROM "EmailSuppressionList" WHERE email_lower = NEW.email) INTO v_suppressed;
                    IF v_suppressed THEN
                        NEW.campaign_ready := FALSE;
                        NEW.email_hygiene_status := 'SUPPRESSED';
                        RETURN NEW;
                    END IF;

                    v_domain := SPLIT_PART(NEW.email, '@', 2);
                    SELECT EXISTS (SELECT 1 FROM "EmailDomainHealth" WHERE domain = v_domain AND has_mx = FALSE) INTO v_dead_mx;
                    IF v_dead_mx THEN
                        NEW.campaign_ready := FALSE;
                        NEW.email_mx_verified := FALSE;
                        NEW.email_hygiene_status := 'DEAD_DOMAIN_NO_MX';
                        RETURN NEW;
                    END IF;

                    NEW.campaign_ready := TRUE;
                    NEW.email_mx_verified := TRUE;
                    NEW.email_hygiene_status := 'CAMPAIGN_READY';
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;

                DROP TRIGGER IF EXISTS trg_leads_campaign_readiness ON "Leads";
                CREATE TRIGGER trg_leads_campaign_readiness
                BEFORE INSERT OR UPDATE ON "Leads"
                FOR EACH ROW
                EXECUTE FUNCTION fn_leads_compute_campaign_readiness();

                UPDATE "Leads" SET email = email;
            """)

            cur.execute('SELECT COUNT(*) AS c FROM "Leads" WHERE campaign_ready = TRUE;')
            ready_cnt = cur.fetchone()["c"]

        conn.commit()
        elapsed = round(time.time() - t_start, 2)
        print(f"[SUCCESS] Migration 043 completed in {elapsed}s: {len(updates):,} updated, {len(inserts):,} inserted, {ready_cnt:,} CAMPAIGN_READY leads.", flush=True)
        return {"status": "success", "ready_count": ready_cnt}
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Migration 043 failed: {e}", file=sys.stderr, flush=True)
        raise e
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration()
