import os
import json
import psycopg2

DB_URL = os.environ.get("DATABASE_URL", "postgresql://hexadmin:hexpassword@hex_postgis_db:5432/hex_dev_db")

def ingest_samsung_news():
    print("--- Pulse Brain Ingestion: Samsung HQ Relocation ---")
    conn = psycopg2.connect(DB_URL)
    with conn.cursor() as cur:
        # 1. Check if Samsung Profile exists, insert if not
        cur.execute("""
            INSERT INTO "HEX_DeveloperProfiles" (company_name, estimated_aum, target_asset_class, acquisition_criteria, contact_info)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (company_name) DO UPDATE
            SET estimated_aum = EXCLUDED.estimated_aum
            RETURNING id;
        """, (
            "Samsung Electronics America",
            3500000000.00,
            "Corporate HQ & Semiconductor Labs",
            json.dumps({"min_sqft": 400000, "region": "North Texas / Plano"}),
            json.dumps({"press_email": "press@sea.samsung.com", "hq_address": "Plano, TX"})
        ))
        company_id = cur.fetchone()[0]
        print(f"SUCCESS: Developer Profile indexed. ID: {company_id}")

        # 2. Ingest Developer Intent / Relocation Project
        cur.execute("""
            INSERT INTO "HEX_DeveloperIntent" (company_id, intent_type, target_parcel_id, description, estimated_value, source_url)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id;
        """, (
            company_id,
            "Planning",
            "8b62c4314ab2fff",
            "Samsung Electronics America relocates U.S. HQ from New Jersey to Plano campus, consolidating ~1,000 employees.",
            150000000.00,
            "https://qz.com/samsung-electronics-america-relocating-headquarters-plano-texas-1851518386"
        ))
        intent_id = cur.fetchone()[0]
        print(f"SUCCESS: Developer Intent registered. ID: {intent_id}")

        # 3. Ingest Social/News Sentiment Opportunity
        cur.execute("""
            INSERT INTO "HEX_PulseOpportunities" (h3_address, platform, post_url, post_content, sentiment_score)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (post_url) DO UPDATE
            SET sentiment_score = EXCLUDED.sentiment_score
            RETURNING id;
        """, (
            "8b62c4314ab2fff",
            "Commercial News / Quartz",
            "https://qz.com/samsung-electronics-america-relocating-headquarters-plano-texas-1851518386",
            "Samsung Electronics America officially consolidates mobile, network, and semiconductor divisions by relocating U.S. headquarters to Plano campus by end of 2026.",
            9.80
        ))
        pulse_id = cur.fetchone()[0]
        print(f"SUCCESS: Sentiment Opportunity logged. ID: {pulse_id}")

        conn.commit()
    conn.close()
    print("--- Ingestion Complete. Pulse Brain Core Updated ---")

if __name__ == '__main__':
    ingest_samsung_news()
