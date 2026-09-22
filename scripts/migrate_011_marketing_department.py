"""
Migration 011: SigmaFidelity™ Marketing Department & Autonomous Campaign Management Engine
Standard: HWB-QMS-7.6 Database Hardening & Schema Versioning SOP
Authority: Humberto Dominguez (CEO)
Architect: George (Systems Architect & mbB)
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db")

def run_migration(db_url: str):
    print("[MIGRATION] Applying 011_marketing_department...")
    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            # 1. Provision Table: MarketingCampaigns
            cur.execute('''
                CREATE TABLE IF NOT EXISTS "MarketingCampaigns" (
                    id SERIAL PRIMARY KEY,
                    campaign_code VARCHAR(64) UNIQUE NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    target_sector VARCHAR(100) NOT NULL,
                    target_geo VARCHAR(255) DEFAULT 'Collin, Dallas, Denton, Tarrant',
                    cadence_type VARCHAR(50) DEFAULT '3-Step Compliance',
                    template_id VARCHAR(100) DEFAULT 'TMPL_CHILDCARE_HEALTH_V1',
                    sender_persona VARCHAR(100) DEFAULT 'Humberto Dominguez (Owner & Operator)',
                    status VARCHAR(50) DEFAULT 'Draft',
                    total_targets INTEGER DEFAULT 0,
                    staged_count INTEGER DEFAULT 0,
                    sent_count INTEGER DEFAULT 0,
                    opened_count INTEGER DEFAULT 0,
                    walkthroughs_booked INTEGER DEFAULT 0,
                    total_mrr_won NUMERIC(12,2) DEFAULT 0.00,
                    daily_throttle_limit INTEGER DEFAULT 50,
                    created_by VARCHAR(100) DEFAULT 'George (Systems Architect)',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS "idx_mkt_campaigns_code" ON "MarketingCampaigns" (campaign_code);
                CREATE INDEX IF NOT EXISTS "idx_mkt_campaigns_status" ON "MarketingCampaigns" (status);
                CREATE INDEX IF NOT EXISTS "idx_mkt_campaigns_sector" ON "MarketingCampaigns" (target_sector);
            ''')
            print("  -> Table MarketingCampaigns and indexes provisioned.")

            # 2. Provision Table: CampaignRecipients
            cur.execute('''
                CREATE TABLE IF NOT EXISTS "CampaignRecipients" (
                    id SERIAL PRIMARY KEY,
                    campaign_id INTEGER REFERENCES "MarketingCampaigns"(id) ON DELETE CASCADE,
                    lead_id INTEGER REFERENCES "Leads"(id) ON DELETE SET NULL,
                    recipient_email VARCHAR(255) NOT NULL,
                    recipient_name VARCHAR(150),
                    facility_name VARCHAR(255),
                    city VARCHAR(100),
                    county VARCHAR(100),
                    capacity INTEGER,
                    sqf INTEGER,
                    current_step INTEGER DEFAULT 1,
                    status VARCHAR(50) DEFAULT 'STAGED',
                    outbox_id INTEGER REFERENCES "PendingOutbox"(id) ON DELETE SET NULL,
                    scheduled_send_at TIMESTAMP WITH TIME ZONE,
                    sent_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS "idx_camp_recip_campaign" ON "CampaignRecipients" (campaign_id);
                CREATE INDEX IF NOT EXISTS "idx_camp_recip_status" ON "CampaignRecipients" (status);
                CREATE INDEX IF NOT EXISTS "idx_camp_recip_email" ON "CampaignRecipients" (recipient_email);
            ''')
            print("  -> Table CampaignRecipients and indexes provisioned.")

            # 3. Seed Inaugural Campaign: CMP-2026-DAYCARE-CORE
            cur.execute('''
                INSERT INTO "MarketingCampaigns" (
                    campaign_code, name, target_sector, target_geo, cadence_type,
                    template_id, sender_persona, status, total_targets, staged_count,
                    daily_throttle_limit, created_by
                ) VALUES (
                    'CMP-2026-DAYCARE-CORE',
                    'North Texas Commercial Childcare Safety & Health Cadence',
                    'Licensed Childcare',
                    'Collin, Dallas, Denton, Tarrant Counties',
                    '3-Step Compliance',
                    'TMPL_CHILDCARE_HEALTH_V1',
                    'Humberto Dominguez (Owner & Operator)',
                    'Staged for Review',
                    100,
                    100,
                    50,
                    'George (Systems Architect)'
                )
                ON CONFLICT (campaign_code) DO UPDATE SET
                    name = EXCLUDED.name,
                    status = EXCLUDED.status,
                    total_targets = EXCLUDED.total_targets,
                    staged_count = EXCLUDED.staged_count,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id;
            ''')
            campaign_id = cur.fetchone()[0]
            print(f"  -> Seeded Campaign record CMP-2026-DAYCARE-CORE (ID: {campaign_id}).")

            # 4. Pull Top 100 Commercial Daycare Leads in Core North Texas Counties & Populate CampaignRecipients
            cur.execute('''
                SELECT id, center_name, director, email, city, county, capacity, sqf
                FROM "Leads"
                WHERE is_commercial = TRUE 
                  AND is_dnc = FALSE
                  AND is_converted = FALSE
                  AND email IS NOT NULL 
                  AND email LIKE '%@%'
                  AND county IN ('Collin', 'Dallas', 'Denton', 'Tarrant')
                  AND capacity >= 75
                ORDER BY capacity DESC NULLS LAST, id ASC
                LIMIT 100;
            ''')
            selected_leads = cur.fetchall()
            print(f"  -> Selected {len(selected_leads)} verified commercial targets for Campaign {campaign_id}.")

            recipients_inserted = 0
            for lead in selected_leads:
                lid, center, director, email, city, county, cap, sqf = lead
                director_name = director.strip() if director and director.strip() else "Facility Director"
                
                # Check if already staged in CampaignRecipients
                cur.execute('''
                    SELECT id FROM "CampaignRecipients"
                    WHERE campaign_id = %s AND (lead_id = %s OR recipient_email = %s);
                ''', (campaign_id, lid, email.strip()))
                existing_recip = cur.fetchone()

                if not existing_recip:
                    # Stage individual recipient
                    cur.execute('''
                        INSERT INTO "CampaignRecipients" (
                            campaign_id, lead_id, recipient_email, recipient_name,
                            facility_name, city, county, capacity, sqf, current_step, status
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1, 'STAGED')
                        RETURNING id;
                    ''', (campaign_id, lid, email.strip(), director_name, center, city, county, cap or 0, sqf or 0))
                    recipients_inserted += 1

            print(f"  -> Inserted {recipients_inserted} new targets into CampaignRecipients.")

            # Update actual total_targets count
            cur.execute('''
                UPDATE "MarketingCampaigns"
                SET total_targets = (SELECT COUNT(*) FROM "CampaignRecipients" WHERE campaign_id = %s),
                    staged_count = (SELECT COUNT(*) FROM "CampaignRecipients" WHERE campaign_id = %s AND status = 'STAGED'),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s;
            ''', (campaign_id, campaign_id, campaign_id))

            # 5. Stage a Master Representative Sample Email into PendingOutbox for CEO Review
            sample_subject = "Avoiding State Licensing & Bleach Hazards: Certified Childcare Sanitation Protocol"
            sample_body = f"""<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; font-size: 14px; color: #1e293b; line-height: 1.6;">
    <p>Dear Childcare Director & Educational Leadership,</p>
    
    <p>In operating a licensed childcare center in North Texas with high student enrollment, maintaining state chemical safety compliance under Texas Health and Human Services (HHS) and OSHA regulations is an ongoing priority. Traditional bleach solutions frequently present strong chemical odors, respiratory irritation among toddlers, and fabric degradation across classroom carpets.</p>
    
    <p><strong>HWB Cleaning Services LLC</strong> provides an ISO 9001:2015 compliant, hospital-grade green sanitization protocol engineered specifically for early educational environments. We replace harsh bleach mixtures with EPA List N hospital disinfectants that eliminate 99.99% of viral pathogens (RSV, Norovirus, Influenza) with zero toxic fumes and zero chemical residue.</p>
    
    <p>As the local Owner & Operator, I would be pleased to conduct a <strong>Complimentary 10-Point Sanitation Audit</strong> of your classrooms, nap rooms, and food prep areas at no charge.</p>
    
    <p>You can reserve a convenient 15-minute inspection slot directly on my calendar here:<br />
    <a href="https://outlook.office.com/bookwithme/user/hdominguez@hwbcleaning.com" style="display: inline-block; background: #2563eb; color: #ffffff; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: 700; margin-top: 10px;">Select a 15-Minute Slot on Humberto's Calendar</a></p>
    
    <p>Thank you for your dedicated service to our community's children.</p>
    
    <p>Sincerely,</p>
</div>"""

            cur.execute('''
                INSERT INTO "PendingOutbox" (recipient, subject, body, created_at, status)
                VALUES (
                    'hdominguez@hwbcleaning.com',
                    '[EXECUTIVE SAMPLE] Childcare Health & Safety Compliance Sequence (Campaign CMP-2026-DAYCARE-CORE)',
                    %s,
                    CURRENT_DATE,
                    'PENDING'
                );
            ''', (sample_body,))
            print("  -> Staged Executive Verification Email in PendingOutbox for CEO Humberto Dominguez.")

            # 6. Log in schema_migrations
            cur.execute('''
                INSERT INTO schema_migrations (version, description)
                VALUES ('011_marketing_department', 'Marketing Department schema, MarketingCampaigns, CampaignRecipients, and inaugural Daycare batch')
                ON CONFLICT (version) DO UPDATE SET
                    applied_at = CURRENT_TIMESTAMP,
                    description = EXCLUDED.description;
            ''')
            print("  -> Recorded 011_marketing_department in schema_migrations.")

        conn.commit()
        print("[MIGRATION] 011_marketing_department applied successfully.")
    except Exception as e:
        conn.rollback()
        print(f"[MIGRATION ERROR] Failed to apply 011_marketing_department: {e}")
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else DB_URL
    run_migration(url)
