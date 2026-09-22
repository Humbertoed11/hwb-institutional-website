"""
Migration 012: SigmaFidelity™ Marketing Tracking Telemetry & Campaign Builder Engine
Standard: HWB-QMS-7.6 Database Hardening & Schema Versioning SOP
Authority: Humberto Dominguez (CEO)
Architect: George (Systems Architect & mbB)
"""

import os
import sys
import uuid
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db")

def run_migration(db_url: str):
    print("[MIGRATION] Applying 012_marketing_tracking_and_builder...")
    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            # 1. Enhance CampaignRecipients for Open & Click Tracking
            cur.execute('''
                ALTER TABLE "CampaignRecipients"
                ADD COLUMN IF NOT EXISTS tracking_token VARCHAR(64) UNIQUE,
                ADD COLUMN IF NOT EXISTS opened_at TIMESTAMP WITH TIME ZONE,
                ADD COLUMN IF NOT EXISTS open_count INTEGER DEFAULT 0,
                ADD COLUMN IF NOT EXISTS clicked_at TIMESTAMP WITH TIME ZONE,
                ADD COLUMN IF NOT EXISTS click_count INTEGER DEFAULT 0;

                CREATE INDEX IF NOT EXISTS "idx_camp_recip_token" ON "CampaignRecipients" (tracking_token);
                CREATE INDEX IF NOT EXISTS "idx_camp_recip_open" ON "CampaignRecipients" (opened_at);
            ''')
            print("  -> Table CampaignRecipients enhanced with tracking telemetry columns.")

            # 2. Enhance MarketingCampaigns with customizable templates
            cur.execute('''
                ALTER TABLE "MarketingCampaigns"
                ADD COLUMN IF NOT EXISTS email_subject_template TEXT,
                ADD COLUMN IF NOT EXISTS email_body_template TEXT;
            ''')
            print("  -> Table MarketingCampaigns enhanced with email template fields.")

            # 3. Enhance PendingOutbox with campaign tracking metadata
            cur.execute('''
                ALTER TABLE "PendingOutbox"
                ADD COLUMN IF NOT EXISTS tracking_token VARCHAR(64),
                ADD COLUMN IF NOT EXISTS campaign_id INTEGER,
                ADD COLUMN IF NOT EXISTS recipient_id INTEGER;

                CREATE INDEX IF NOT EXISTS "idx_pending_outbox_token" ON "PendingOutbox" (tracking_token);
                CREATE INDEX IF NOT EXISTS "idx_pending_outbox_campaign" ON "PendingOutbox" (campaign_id);
            ''')
            print("  -> Table PendingOutbox enhanced with tracking metadata.")

            # 4. Generate unique tracking tokens for any existing CampaignRecipients lacking one
            cur.execute('''
                SELECT id FROM "CampaignRecipients" WHERE tracking_token IS NULL;
            ''')
            missing_tokens = cur.fetchall()
            for row in missing_tokens:
                token = uuid.uuid4().hex
                cur.execute('UPDATE "CampaignRecipients" SET tracking_token = %s WHERE id = %s', (token, row[0]))
            print(f"  -> Generated tracking tokens for {len(missing_tokens)} existing recipients.")

            # 5. Populate default templates on inaugural Daycare campaign if empty
            default_daycare_subject = "Avoiding State Licensing & Bleach Hazards: Certified Childcare Sanitation Protocol"
            default_daycare_body = """<p>Dear {director_name},</p>

<p>In operating a licensed childcare center in {city}, maintaining state chemical safety compliance under Texas Health and Human Services (HHS) and OSHA regulations is an ongoing priority. Traditional bleach solutions frequently present strong chemical odors, respiratory irritation among toddlers, and fabric degradation across classroom carpets.</p>

<p><strong>HWB Cleaning Services LLC</strong> provides an ISO 9001:2015 certified, hospital-grade green sanitization protocol engineered specifically for early educational environments. We replace harsh bleach mixtures with EPA List N hospital disinfectants that eliminate 99.99% of viral pathogens (RSV, Norovirus, Influenza) with zero toxic fumes and zero chemical residue.</p>

<p>As the local Owner & Operator, I would be pleased to conduct a <strong>Complimentary 10-Point Sanitation Audit</strong> of {facility_name} at no charge.</p>

<p>You can reserve a convenient 15-minute inspection slot directly on my calendar here:<br />
<a href="{booking_link}" style="display: inline-block; background: #2563eb; color: #ffffff; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: 700; margin-top: 10px;">Select a 15-Minute Slot on Humberto's Calendar</a></p>

<p>Thank you for your dedicated service to our community's children.</p>

<p>Sincerely,</p>"""

            cur.execute('''
                UPDATE "MarketingCampaigns"
                SET email_subject_template = COALESCE(email_subject_template, %s),
                    email_body_template = COALESCE(email_body_template, %s)
                WHERE campaign_code = 'CMP-2026-DAYCARE-CORE';
            ''', (default_daycare_subject, default_daycare_body))

            # 6. Record in schema_migrations
            cur.execute('''
                INSERT INTO schema_migrations (version, description)
                VALUES ('012_marketing_tracking_and_builder', 'Telemetry open tracking pixel, tokens, and campaign builder template support')
                ON CONFLICT (version) DO UPDATE SET
                    applied_at = CURRENT_TIMESTAMP,
                    description = EXCLUDED.description;
            ''')
            print("  -> Recorded 012_marketing_tracking_and_builder in schema_migrations.")

        conn.commit()
        print("[MIGRATION] 012_marketing_tracking_and_builder applied successfully.")
    except Exception as e:
        conn.rollback()
        print(f"[MIGRATION ERROR] Failed to apply 012_marketing_tracking_and_builder: {e}")
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else DB_URL
    run_migration(url)
