"""
SigmaFidelity™ Quarantine Ingestion & Sanitization Engine
Standard: HWB-QMS-7.6 Enterprise Architecture Standards & SOC 2 PI1.2 (Processing Integrity)
Architect: George (Systems Architect & mbB) & Silas Sync (VP of CRM)
"""

import os
import re
import json
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
from difflib import SequenceMatcher

import psycopg2
from psycopg2.extras import RealDictCursor, Json
from core.services.database import get_db
from core.services.classifier import BusinessClassifierEngine

DB_URL = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@db:5432/hwb_dev_db")


def normalize_phone_proc002(raw_phone: Optional[str]) -> str:
    """
    Normalizes arbitrary phone strings into strict institutional PROC-002 format: (###) ###-####.
    Returns cleaned string or empty string if invalid.
    """
    if not raw_phone:
        return ""
    digits = re.sub(r"\D", "", str(raw_phone).strip())
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return str(raw_phone).strip()


def calculate_similarity(a: str, b: str) -> float:
    """Calculates text similarity ratio (0.0 to 100.0) using SequenceMatcher."""
    if not a or not b:
        return 0.0
    return round(SequenceMatcher(None, str(a).strip().lower(), str(b).strip().lower()).ratio() * 100.0, 2)


def stage_and_quarantine_records(
    records: List[Dict[str, Any]],
    tenant_id: int = 1,
    source_filename: str = "batch_upload.csv",
    record_type: str = "LEAD",
    db_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Poka-Yoke Ingestion Gateway:
    Ingests raw client records into 'crm_ingestion_quarantine', executes automated PROC-002
    cleansing, fuzzy duplicate scans, and defect isolation. Zero unverified records touch production.
    """
    target_url = db_url or DB_URL
    batch_id = f"BATCH-{datetime.now().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:8].upper()}"

    total_count = len(records)
    validated_count = 0
    conflict_count = 0
    defect_count = 0

    conn = get_db(target_url)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            staging_rows = []

            for raw in records:
                defects = []
                # 1. Extraction & Cleaning
                name = str(raw.get("center_name") or raw.get("name") or raw.get("company") or "").strip()
                phone_raw = raw.get("phone") or raw.get("telephone") or raw.get("contact_phone") or ""
                phone_clean = normalize_phone_proc002(phone_raw)
                email = str(raw.get("email") or raw.get("contact_email") or "").strip().lower()
                address = str(raw.get("address") or raw.get("street") or "").strip()
                city = str(raw.get("city") or "").strip()
                state = str(raw.get("state") or "TX").strip().upper()
                zipcode = str(raw.get("zip") or raw.get("zipcode") or "").strip()

                # Defect Check: Mandatory identification
                if not name:
                    defects.append("Missing mandatory company or contact name.")
                if not phone_clean and not email:
                    defects.append("Missing valid contact method (no valid phone or email).")
                if phone_clean and not re.match(r"^\(\d{3}\) \d{3}-\d{4}$", phone_clean):
                    defects.append(f"Phone '{phone_raw}' violates PROC-002 format.")

                # Duplicate / Conflict Check against existing records
                conflict_id = None
                max_similarity = 0.0

                candidate = None
                if phone_clean:
                    cur.execute('SELECT id, center_name, phone FROM "Leads" WHERE tenant_id = %s AND phone = %s LIMIT 1;', (tenant_id, phone_clean))
                    candidate = cur.fetchone()

                if not candidate and name:
                    cur.execute('SELECT id, center_name, phone FROM "Leads" WHERE tenant_id = %s AND lower(btrim(center_name)) = lower(btrim(%s)) LIMIT 1;', (tenant_id, name))
                    candidate = cur.fetchone()

                if candidate:
                    conflict_id = candidate["id"]
                    phone_match = phone_clean and phone_clean == candidate.get("phone")
                    sim = calculate_similarity(name, candidate.get("center_name", ""))
                    max_similarity = 100.0 if phone_match else sim
                    defects.append(f"Potential duplicate of existing Lead #{conflict_id} ('{candidate.get('center_name')}') - {max_similarity}% match.")

                # Business Classification & Cognitive Conflict Gate (Poka-Yoke)
                classification = BusinessClassifierEngine.classify(
                    center_name=name,
                    capacity=raw.get("capacity"),
                    lead_source=raw.get("lead_source") or source_filename,
                    raw_payload=raw
                )

                if classification.is_conflict:
                    defects.append(
                        f"Cognitive Conflict: Entity '{name}' ({classification.industry}) contradicts source registry '{source_filename}'."
                    )

                if classification.confidence_score < 0.85:
                    defects.append(
                        f"Low Classification Confidence ({classification.confidence_score}): Manual review required."
                    )

                # Status Classification
                if any("Potential duplicate" in d for d in defects):
                    status = "CONFLICT_DUPLICATE"
                    conflict_count += 1
                elif classification.is_conflict:
                    status = "CLASSIFICATION_CONFLICT"
                    defect_count += 1
                elif classification.confidence_score < 0.85:
                    status = "LOW_CONFIDENCE_REVIEW"
                    defect_count += 1
                elif defects:
                    status = "DEFECT_REJECTED"
                    defect_count += 1
                else:
                    status = "VALIDATED"
                    validated_count += 1

                normalized = {
                    "center_name": name,
                    "phone": phone_clean,
                    "email": email,
                    "address": address,
                    "city": city,
                    "state": state,
                    "zip": zipcode,
                    "industry": classification.industry,
                    "facility_type": classification.facility_type,
                    "cleanable_profile": classification.cleanable_profile,
                    "confidence_score": classification.confidence_score,
                    "matched_rule": classification.matched_rule,
                    "lead_source": classification.normalized_lead_source,
                    "notes": raw.get("notes", "")
                }

                cur.execute("""
                    INSERT INTO "crm_ingestion_quarantine" (
                        batch_id, tenant_id, source_filename, record_type,
                        raw_data, normalized_data, validation_status,
                        validation_errors, conflict_target_id, similarity_score
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                """, (
                    batch_id, tenant_id, source_filename, record_type,
                    Json(raw), Json(normalized), status,
                    Json(defects), conflict_id, max_similarity
                ))

            conn.commit()

        return {
            "status": "success",
            "batch_id": batch_id,
            "tenant_id": tenant_id,
            "total_records": total_count,
            "validated_clean": validated_count,
            "conflict_duplicates": conflict_count,
            "defects_quarantined": defect_count,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        conn.rollback()
        print(f"[QUARANTINE_ERROR] Ingestion staging failed: {e}", flush=True)
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()


def commit_quarantine_batch(batch_id: str, tenant_id: int = 1, db_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Commits all clean 'VALIDATED' records from a quarantine batch into production 'Leads'.
    Guarantees atomic transaction commit: zero partial contamination.
    """
    target_url = db_url or DB_URL
    conn = get_db(target_url)
    committed_count = 0

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, normalized_data 
                FROM "crm_ingestion_quarantine"
                WHERE batch_id = %s AND tenant_id = %s AND validation_status = 'VALIDATED';
            """, (batch_id, tenant_id))
            records = cur.fetchall()

            for r in records:
                norm = r["normalized_data"]
                cur.execute("""
                    INSERT INTO "Leads" (
                        center_name, phone, email, address, city, state, zipcode,
                        industry, facility_type, lead_source, status, tenant_id, input_date
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    RETURNING id;
                """, (
                    norm.get("center_name"),
                    norm.get("phone"),
                    norm.get("email"),
                    norm.get("address"),
                    norm.get("city"),
                    norm.get("state", "TX"),
                    norm.get("zip") or norm.get("zipcode"),
                    norm.get("industry", "Commercial Property"),
                    norm.get("facility_type", "Other"),
                    norm.get("lead_source", f"Quarantine Batch: {batch_id}"),
                    "NEW_OPPORTUNITY",
                    tenant_id
                ))
                new_lead_id = cur.fetchone()["id"]

                cur.execute("""
                    UPDATE "crm_ingestion_quarantine"
                    SET validation_status = 'COMMITTED',
                        processed_at = CURRENT_TIMESTAMP,
                        conflict_target_id = %s
                    WHERE id = %s;
                """, (new_lead_id, r["id"]))
                committed_count += 1

            conn.commit()

        return {
            "status": "success",
            "batch_id": batch_id,
            "records_committed": committed_count,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        conn.rollback()
        print(f"[QUARANTINE_COMMIT_ERROR] Commit failed: {e}", flush=True)
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()
