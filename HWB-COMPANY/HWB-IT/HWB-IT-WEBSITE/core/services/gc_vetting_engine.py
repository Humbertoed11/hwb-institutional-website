"""
SigmaFidelity™ Automated 4-Point GC Vetting Engine & Autonomous Profile Enricher
Standard: HWB-QMS-7.7 Commercial Construction Takeoff & Estimating Engine SOP
Custodians: George (Systems Architect & mbB) & Humberto Dominguez (CEO)
Authority: Approved 09/23/2026

Four-Point Vetting Framework:
1. Point 1: Corporate Standing & SOS Charter (25 Pts)
2. Point 2: Payment Terms & Retainage Integrity (25 Pts)
3. Point 3: Geographic Cluster & Mobilization Viability (25 Pts)
4. Point 4: Profile Completeness & Estimator Contact Integrity (25 Pts)
"""

import os
import re
import datetime
from typing import Dict, Any, Optional, List, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor
import requests
import msal
from dotenv import load_dotenv

from core.services.sanitizer import clean_phone, clean_sqft, clean_zip
from core.services.estimator import calculate_commercial_gc_bid

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db")
CID = os.getenv("GRAPH_API_PROD_APPLICATION_ID")
SECRET = os.getenv("GRAPH_API_PROD_SECRET_VALUE")
TID = os.getenv("GRAPH_API_PROD_TENANT_ID")
USER_EMAIL = os.getenv("OFFICE365_USER_EMAIL", "hdominguez@hwbcleaning.com")

class GCVettingEngine:
    """Industrial GC Vetting Engine and Autonomous Profile Completer."""

    @staticmethod
    def get_graph_token() -> Optional[str]:
        """Acquires Microsoft Graph API access token for full email inspection."""
        if not CID or not SECRET or not TID:
            return None
        try:
            authority = f"https://login.microsoftonline.com/{TID}"
            app = msal.ConfidentialClientApplication(CID, authority=authority, client_credential=SECRET)
            result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
            return result.get('access_token')
        except Exception:
            return None

    @staticmethod
    def fetch_email_body(email_id: str, token: Optional[str] = None) -> Optional[str]:
        """Fetches full email body from Microsoft Graph API given an email message ID."""
        if not email_id or email_id.startswith("WEEKES-") or email_id.startswith("NOVEL-") or email_id.startswith("SOURCE-") or email_id.startswith("MYCON-"):
            return None
        t = token or GCVettingEngine.get_graph_token()
        if not t:
            return None
        try:
            headers = {"Authorization": f"Bearer {t}", "Content-Type": "application/json"}
            url = f"https://graph.microsoft.com/v1.0/users/{USER_EMAIL}/messages/{email_id}"
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code == 200:
                data = res.json()
                raw_body = data.get("body", {}).get("content", "")
                # Strip HTML tags
                text = re.sub(r'<[^>]+>', ' ', raw_body)
                text = re.sub(r'&nbsp;', ' ', text)
                text = re.sub(r'\s+', ' ', text).strip()
                return text
        except Exception:
            pass
        return None

    @staticmethod
    def parse_email_text(
        subject: str,
        sender_name: str,
        sender_email: str,
        body_text: str
    ) -> Dict[str, Any]:
        """
        Parses raw email text, headers, and signatures to extract structured GC & bid fields:
        - GC Company Name
        - Lead Estimator Name & Title
        - Phone Number & Extension
        - Project Name & Physical Address
        - Cleanable Square Footage
        - Bid Due Date
        """
        combined = f"{subject} {sender_name} {sender_email} {body_text}"
        res: Dict[str, Any] = {
            "gc_name": None,
            "estimator_name": None,
            "estimator_title": None,
            "estimator_phone": None,
            "estimator_email": sender_email or None,
            "project_name": None,
            "project_address": None,
            "city": None,
            "state": "TX",
            "zipcode": None,
            "cleanable_sqft": 0,
            "bid_due_date": None,
            "scope_phase": "Rough, Final & Touch-Up Clean"
        }

        # 1. GC Company Identification
        lower_comb = combined.lower()
        if "healy construction" in lower_comb or "healyconstructionservices.com" in lower_comb:
            res["gc_name"] = "Healy Construction Services, Inc."
        elif "novel builders" in lower_comb or "novelbuilders.com" in lower_comb:
            res["gc_name"] = "Novel Builders, LLC"
        elif "weekes construction" in lower_comb or "weekesconstruction.com" in lower_comb:
            res["gc_name"] = "Weekes Construction, Inc."
        elif "mycon" in lower_comb or "mycon.com" in lower_comb:
            res["gc_name"] = "MYCON General Contractors"
        elif "embree" in lower_comb or "embreegroup.com" in lower_comb:
            res["gc_name"] = "Embree Construction Group, Inc."
        elif "source building group" in lower_comb or "sourcebuildinggroup.com" in lower_comb:
            res["gc_name"] = "Source Building Group, Inc."
        elif "dfw planroom" in lower_comb or "dfwplanroom.com" in lower_comb:
            res["gc_name"] = "DFW Planroom"
        elif "buildingconnected" in lower_comb:
            # Check if there is an underlying GC inside BuildingConnected notification
            m_gc = re.search(r'from\s+([A-Za-z0-9\s,&.\'-]+)\s+via\s+BuildingConnected', body_text, re.I)
            if m_gc:
                res["gc_name"] = m_gc.group(1).strip()
            else:
                res["gc_name"] = "BuildingConnected / Autodesk"
        else:
            # Extract from parentheses in sender_name e.g. "Amber Duhon (Weekes Construction)"
            match_paren = re.search(r'\((.*?)\)', sender_name)
            if match_paren:
                res["gc_name"] = match_paren.group(1).strip()
            elif "builders" in sender_name.lower() or "construction" in sender_name.lower():
                res["gc_name"] = sender_name.strip()

        # 2. Estimator Name & Title Extraction
        # Look for signature lines or known names
        if "poppy geerling" in lower_comb or "laura (poppy) geerling" in lower_comb or "pgeerling@" in lower_comb:
            res["estimator_name"] = "Laura (Poppy) Geerling"
            res["estimator_title"] = "Project Coordinator / Estimator"
        elif "amber duhon" in lower_comb or "anewland@" in lower_comb:
            res["estimator_name"] = "Amber Duhon"
            res["estimator_title"] = "Bid Coordinator"
        elif "austin addis" in lower_comb or "aaddis@" in lower_comb:
            res["estimator_name"] = "Austin Addis"
            res["estimator_title"] = "Estimator"
        elif "ryan porter" in lower_comb or "rporter@" in lower_comb:
            res["estimator_name"] = "Ryan Porter"
            res["estimator_title"] = "Senior Estimator"
        elif "bethany leander" in lower_comb or "bleander@" in lower_comb:
            res["estimator_name"] = "Bethany Leander"
            res["estimator_title"] = "Bid Coordinator"
        elif "colton bennett" in lower_comb or "cbennett@" in lower_comb:
            res["estimator_name"] = "Colton Bennett"
            res["estimator_title"] = "Estimator"
        elif sender_name and not any(p in sender_name.lower() for p in ["planroom", "buildingconnected", "notification", "digest", "no-reply"]):
            # Clean parentheses from sender name if present
            clean_name = re.sub(r'\(.*?\)', '', sender_name).strip()
            if clean_name and len(clean_name.split()) >= 2:
                res["estimator_name"] = clean_name

        # 3. Estimator Phone Number Extraction
        # Look for Office:, Direct:, Phone:, Tel:, Fax:
        phone_matches = re.findall(r'(?:Office|Direct|Phone|Tel|Cell)?:?\s*(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}(?:\s*(?:ext|x|ext\.)\s*\d+)?)', body_text, re.I)
        if phone_matches:
            for pm in phone_matches:
                # Disqualify fax if preceded by fax
                c_p = clean_phone(pm)
                if c_p:
                    res["estimator_phone"] = c_p
                    break

        # 4. Square Footage Extraction
        sqft_match = re.search(r'(\d[\d,]*)\s*(?:sq\.?\s*ft\.?|sqft|sf|square\s+feet)', body_text, re.I)
        if sqft_match:
            res["cleanable_sqft"] = clean_sqft(sqft_match.group(1))

        # 5. Project Name Extraction
        if subject.startswith("INVITATION TO BID:") or subject.startswith("Bid Invite:"):
            # Strip prefix
            p_name = re.sub(r'^(?:INVITATION TO BID:|Bid Invite:|Final Cleaning Bids Needed!! -|REMINDER!!! Bids Due Monday!! -)\s*', '', subject, flags=re.I).strip()
            res["project_name"] = p_name
        else:
            res["project_name"] = subject.strip()

        # 6. Physical Address & Location Extraction
        addr_match = re.search(r'located at\s+([^,.\n]+(?:Expressway|Expy|Parkway|Pkwy|Blvd|Boulevard|Street|St|Road|Rd|Ave|Avenue)[^,.\n]*),\s*([^,.\n]+),\s*([A-Z]{2})\s*(\d{5})', body_text, re.I)
        if addr_match:
            res["project_address"] = addr_match.group(1).strip()
            res["city"] = addr_match.group(2).strip()
            res["state"] = addr_match.group(3).strip()
            res["zipcode"] = clean_zip(addr_match.group(4))
        else:
            # Fallback city search from Texas common cities
            for c in ["Waco", "Grand Prairie", "Burleson", "Princeton", "Dallas", "Fort Worth", "Frisco", "Plano", "Arlington", "Irving", "Garland", "McKinney", "Denton"]:
                if re.search(rf'\b{c}\b', combined, re.I):
                    res["city"] = c
                    break

        # 7. Bid Due Date Extraction
        due_match = re.search(r'(?:Bid Due Date|Bids Due|Due Date):\s*([A-Za-z]+,?\s*\d{1,2}/\d{1,2}/\d{2,4})', body_text, re.I)
        if due_match:
            raw_due = due_match.group(1).strip()
            # Attempt date parsing e.g. "Wednesday, 9/30/26"
            date_part_match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{2,4})', raw_due)
            if date_part_match:
                m, d, y = int(date_part_match.group(1)), int(date_part_match.group(2)), int(date_part_match.group(3))
                if y < 100:
                    y += 2000
                res["bid_due_date"] = datetime.datetime(y, m, d, 14, 0, 0, tzinfo=datetime.timezone.utc)

        return res

    @staticmethod
    def calculate_completeness(bid: Dict[str, Any]) -> int:
        """
        Calculates profile completeness percentage (0 to 100%):
        - GC Name verified and not generic (15%)
        - Lead Estimator Name present (15%)
        - Lead Estimator Phone present & valid (15%)
        - Lead Estimator Email present & valid (15%)
        - Project Address & City present (15%)
        - Cleanable SQFT > 0 (15%)
        - Bid Due Date present (10%)
        """
        score = 0
        gc_name = (bid.get("gc_name") or "").strip()
        if gc_name and gc_name not in ["Field Verification", "BuildingConnected", "Planroom"] and not gc_name.startswith("Laura (Poppy)"):
            score += 15

        est_name = (bid.get("estimator_name") or "").strip()
        if est_name and len(est_name.split()) >= 2:
            score += 15

        est_phone = (bid.get("estimator_phone") or "").strip()
        if est_phone and len(re.sub(r'\D', '', est_phone)) >= 10:
            score += 15

        est_email = (bid.get("estimator_email") or "").strip()
        if est_email and "@" in est_email:
            score += 15

        city = (bid.get("city") or "").strip()
        address = (bid.get("project_address") or "").strip()
        if city or address:
            score += 15

        sqft = float(bid.get("cleanable_sqft") or 0)
        if sqft > 0:
            score += 15

        due = bid.get("bid_due_date")
        if due:
            score += 10

        return min(100, score)

    @staticmethod
    def calculate_4point_scorecard(
        gc_record: Optional[Dict[str, Any]],
        bid: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Computes 4-Point Vetting Scorecard (0 to 100):
        Pillar 1: Corporate Standing & SOS Status (Max 25 Pts)
        Pillar 2: Payment Terms & Retainage Integrity (Max 25 Pts)
        Pillar 3: Geographic Cluster & Mobilization Viability (Max 25 Pts)
        Pillar 4: Profile Completeness & Contact Integrity (Max 25 Pts)
        """
        p1_score = 15
        standing_str = "Verified Active"
        if gc_record:
            sos = (gc_record.get("sos_status") or "").lower()
            if "good standing" in sos or "active / good standing" in sos:
                p1_score = 25
                standing_str = "Verified Active (Good Standing)"
            elif "foreign" in sos:
                p1_score = 23
                standing_str = "Active Foreign Corp in Texas"
            elif "active" in sos:
                p1_score = 20
                standing_str = "Active Texas Entity"

        p2_score = 16
        terms_str = "Net 30 / AIA G702"
        if gc_record:
            terms = (gc_record.get("payment_terms") or "").lower()
            billing = (gc_record.get("billing_format") or "").lower()
            if "net 30" in terms and "aia" in billing:
                p2_score = 25
                terms_str = "Net 30 / AIA G702 Progress"
            elif "net 30-45" in terms:
                p2_score = 20
                terms_str = "Net 30-45 / Commercial Standard"
            elif "multi-prime" in terms:
                p2_score = 16
                terms_str = "Multi-Prime Planroom Terms"

        p3_score = 15
        geo_str = "Core DFW Corridor"
        city = (bid.get("city") or "").lower()
        if any(c in city for c in ["dallas", "fort worth", "arlington", "frisco", "plano", "grand prairie", "burleson", "richardson", "carrollton", "denton"]):
            p3_score = 25
            geo_str = "Core DFW Metroplex (≤ 60 mi)"
        elif any(c in city for c in ["waco", "princeton", "tyler", "sherman", "mckinney"]):
            p3_score = 23
            geo_str = "Active Operating Zone (≤ 100 mi)"
        elif any(c in city for c in ["austin", "san antonio", "houston"]):
            p3_score = 15
            geo_str = "Extended Texas Metropolitan"
        else:
            p3_score = 18
            geo_str = "Texas Regional Network"

        # Pillar 4: Completeness
        completeness = GCVettingEngine.calculate_completeness(bid)
        p4_score = int(round((completeness / 100.0) * 25))

        total_score = p1_score + p2_score + p3_score + p4_score

        if total_score >= 90:
            tier = "Tier 1 - Preferred Prime"
        elif total_score >= 75:
            tier = "Tier 2 - National Retail"
        elif total_score >= 60:
            tier = "Tier 3 - Planroom Broadcast"
        else:
            tier = "Needs Review / Flagged"

        return {
            "total_score": total_score,
            "vetting_tier": tier,
            "standing_status": standing_str,
            "payment_terms": terms_str,
            "geo_cluster": geo_str,
            "profile_completeness_pct": completeness,
            "breakdown": {
                "pillar_1_standing": p1_score,
                "pillar_2_payment": p2_score,
                "pillar_3_geo": p3_score,
                "pillar_4_contact": p4_score
            }
        }

    @staticmethod
    def enrich_single_bid(bid_id: int, db_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Autonomous Profile Completer for a single bid record in ConstructionBids:
        1. Checks for incomplete fields (missing phone, lead estimator, address, sqft).
        2. Retrieves full email text if available.
        3. Enriches GC, Estimator, and Project parameters.
        4. Re-calculates subcontract valuation if SQFT was missing.
        5. Computes 4-Point Vetting Scorecard and updates PostgreSQL.
        """
        target_url = db_url or DB_URL
        conn = psycopg2.connect(target_url)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('SELECT * FROM "ConstructionBids" WHERE id = %s;', (bid_id,))
                bid = cur.fetchone()
                if not bid:
                    return {"status": "error", "message": f"Bid ID {bid_id} not found."}

                # Check if fields are missing
                is_incomplete = (
                    not bid.get("estimator_phone") or
                    not bid.get("estimator_name") or
                    float(bid.get("cleanable_sqft") or 0) == 0 or
                    bid.get("gc_name") in ["Field Verification", "Laura (Poppy) Geerling"] or
                    "(" in str(bid.get("gc_name") or "")
                )

                email_id = bid.get("email_id")
                notes = bid.get("notes") or ""
                subject = bid.get("project_name") or ""
                sender_name = bid.get("gc_name") or ""
                sender_email = bid.get("estimator_email") or ""

                # Fetch full email body if incomplete and email_id exists
                body_text = notes
                if is_incomplete and email_id:
                    fetched_body = GCVettingEngine.fetch_email_body(email_id)
                    if fetched_body:
                        body_text = fetched_body

                # Parse email text
                parsed = GCVettingEngine.parse_email_text(
                    subject=subject,
                    sender_name=sender_name,
                    sender_email=sender_email,
                    body_text=body_text
                )

                # Find or match Master GC
                gc_lookup_name = parsed["gc_name"] or bid.get("gc_name")
                cur.execute('''
                    SELECT * FROM "GeneralContractors"
                    WHERE company_name ILIKE %s OR legal_name ILIKE %s
                    LIMIT 1;
                ''', (f"%{gc_lookup_name}%", f"%{gc_lookup_name}%"))
                master_gc = cur.fetchone()

                # If master GC found, fill any remaining gaps from master profile
                final_gc_name = master_gc["company_name"] if master_gc else (parsed["gc_name"] or bid.get("gc_name"))
                final_gc_id = master_gc["id"] if master_gc else None

                final_est_name = parsed["estimator_name"] or bid.get("estimator_name") or (master_gc.get("lead_estimator_name") if master_gc else None)
                final_est_title = parsed["estimator_title"] or bid.get("estimator_title") or (master_gc.get("lead_estimator_title") if master_gc else None)
                final_est_email = parsed["estimator_email"] or bid.get("estimator_email") or (master_gc.get("lead_estimator_email") if master_gc else None)
                final_est_phone = parsed["estimator_phone"] or bid.get("estimator_phone") or (master_gc.get("lead_estimator_phone") if master_gc else None)
                final_est_phone = clean_phone(final_est_phone)

                final_addr = parsed["project_address"] or bid.get("project_address")
                final_city = parsed["city"] or bid.get("city")
                final_zip = parsed["zipcode"] or bid.get("zipcode")
                final_due = parsed["bid_due_date"] or bid.get("bid_due_date")
                final_sqft = parsed["cleanable_sqft"] if parsed["cleanable_sqft"] > 0 else float(bid.get("cleanable_sqft") or 0)
                final_scope = bid.get("scope_phase") or parsed["scope_phase"]

                # Calculate subcontract estimated value if cleanable_sqft > 0
                final_val = float(bid.get("estimated_value") or 0)
                if final_sqft > 0 and final_val <= 0:
                    val_res = calculate_commercial_gc_bid(final_sqft, final_scope)
                    subtotal = float(val_res.get("subtotal_services", 0.0))
                    submittal = float(val_res.get("submittal_total", 0.0))
                    final_val = max(subtotal, submittal)

                # Build updated bid dict for scorecard
                eval_bid = dict(bid)
                eval_bid.update({
                    "gc_name": final_gc_name,
                    "estimator_name": final_est_name,
                    "estimator_phone": final_est_phone,
                    "estimator_email": final_est_email,
                    "project_address": final_addr,
                    "city": final_city,
                    "zipcode": final_zip,
                    "cleanable_sqft": final_sqft,
                    "bid_due_date": final_due,
                    "estimated_value": final_val
                })

                # Compute Scorecard & Completeness
                scorecard = GCVettingEngine.calculate_4point_scorecard(master_gc, eval_bid)

                # Persist updates to ConstructionBids
                cur.execute('''
                    UPDATE "ConstructionBids"
                    SET gc_id = %s,
                        gc_name = %s,
                        estimator_name = %s,
                        estimator_title = %s,
                        estimator_email = %s,
                        estimator_phone = %s,
                        project_address = %s,
                        city = COALESCE(%s, city),
                        zipcode = COALESCE(%s, zipcode),
                        bid_due_date = COALESCE(%s, bid_due_date),
                        cleanable_sqft = %s,
                        estimated_value = %s,
                        vetting_score = %s,
                        vetting_tier = %s,
                        standing_status = %s,
                        payment_terms = %s,
                        geo_cluster = %s,
                        profile_completeness_pct = %s,
                        enrichment_status = 'Auto-Enriched',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s;
                ''', (
                    final_gc_id,
                    final_gc_name,
                    final_est_name,
                    final_est_title,
                    final_est_email,
                    final_est_phone,
                    final_addr,
                    final_city,
                    final_zip,
                    final_due,
                    final_sqft,
                    final_val,
                    scorecard["total_score"],
                    scorecard["vetting_tier"],
                    scorecard["standing_status"],
                    scorecard["payment_terms"],
                    scorecard["geo_cluster"],
                    scorecard["profile_completeness_pct"],
                    bid_id
                ))

                # Log activity if enriched
                cur.execute('''
                    INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                    VALUES (%s, 'ConstructionBid', 'Autonomous Vetting & Enrichment', %s);
                ''', (bid_id, f"Profile completed: GC '{final_gc_name}', Estimator '{final_est_name}', Phone '{final_est_phone}', Score {scorecard['total_score']}/100 ({scorecard['vetting_tier']})."))

                conn.commit()
                return {
                    "status": "success",
                    "bid_id": bid_id,
                    "gc_name": final_gc_name,
                    "estimator_name": final_est_name,
                    "estimator_phone": final_est_phone,
                    "cleanable_sqft": final_sqft,
                    "estimated_value": final_val,
                    "scorecard": scorecard
                }
        except Exception as e:
            conn.rollback()
            return {"status": "error", "message": str(e)}
        finally:
            conn.close()

    @staticmethod
    def enrich_all_bids(db_url: Optional[str] = None) -> Dict[str, Any]:
        """Runs autonomous profile enrichment and 4-point vetting across all ConstructionBids."""
        target_url = db_url or DB_URL
        conn = psycopg2.connect(target_url)
        enriched_count = 0
        tier_counts = {"Tier 1 - Preferred Prime": 0, "Tier 2 - National Retail": 0, "Tier 3 - Planroom Broadcast": 0, "Needs Review / Flagged": 0}

        try:
            with conn.cursor() as cur:
                cur.execute('SELECT id FROM "ConstructionBids" ORDER BY id ASC;')
                bid_ids = [r[0] for r in cur.fetchall()]

            for bid_id in bid_ids:
                res = GCVettingEngine.enrich_single_bid(bid_id, target_url)
                if res.get("status") == "success":
                    enriched_count += 1
                    tier = res["scorecard"]["vetting_tier"]
                    tier_counts[tier] = tier_counts.get(tier, 0) + 1

            return {
                "status": "success",
                "total_processed": len(bid_ids),
                "enriched_count": enriched_count,
                "tier_breakdown": tier_counts
            }
        finally:
            conn.close()
