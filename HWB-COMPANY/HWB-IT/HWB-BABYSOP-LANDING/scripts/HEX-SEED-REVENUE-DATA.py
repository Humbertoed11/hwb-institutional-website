import os
import json
import psycopg2
from datetime import datetime, date
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get("DATABASE_URL", "postgresql://hexadmin:hexpassword@hex_postgis_db:5432/hex_dev_db")

def seed_revenue_data():
    print("--- George Bytes: Seeding Revenue Core (Leads & Market Value) ---")
    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        
        # 1. Seed Leads
        leads = [
            ("US-75-PLANO-01", "Plano North Land JV", "contact@planolandjv.com", "Under Contract", "Municipal GIS Portal"),
            ("US-75-PLANO-02", "Legacy West Expansion Group", "deals@legacywesteg.com", "New", "ArcGIS REST Crawler"),
            ("DECATUR-DC-01", "Wise County Industrial LLC", "land@wisecountyind.com", "Negotiation", "County Appraisal District"),
            ("DECATUR-DC-02", "Texas Power Grid GridCorp", "grid@powergridcorp.com", "Feasibility", "Ranger Mobile Survey"),
            ("VALLEY-VIEW-01", "Dallas Midtown Developers", "development@dallasmidtown.com", "Active", "Deed Restrictions Scraper")
        ]
        
        for pid, owner, contact, status, source in leads:
            cursor.execute("""
                INSERT INTO "HEX_Leads" (parcel_id, owner_name, owner_contact, status, lead_source)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (parcel_id) DO UPDATE SET
                    owner_name = EXCLUDED.owner_name,
                    owner_contact = EXCLUDED.owner_contact,
                    status = EXCLUDED.status,
                    lead_source = EXCLUDED.lead_source;
            """, (pid, owner, contact, status, source))
            
        print("SUCCESS: 5 leads seeded in 'HEX_Leads'.")
        
        # 2. Seed Market Values (Underwritten vs Asking Price comps)
        # We store composition scores from L1-L7 to show how the lobes contributed to underwritten_value
        market_values = [
            # US-75-PLANO-01: Underwritten too high compared to asking (Error)
            ("US-75-PLANO-01", 12500000.00, 11800000.00, 13100000.00, {
                "L1_zoning": 9.0, "L2_transit": 8.5, "L3_power": 7.0, "L4_legal": 8.0, "L5_ranger": 9.0, "L6_pulse": 6.5, "L7_finance": 7.5
            }),
            # US-75-PLANO-02: Underwritten close to asking
            ("US-75-PLANO-02", 9500000.00, 9200000.00, 9400000.00, {
                "L1_zoning": 8.0, "L2_transit": 9.0, "L3_power": 6.5, "L4_legal": 7.5, "L5_ranger": 8.0, "L6_pulse": 7.0, "L7_finance": 8.0
            }),
            # DECATUR-DC-01: Underwritten too low
            ("DECATUR-DC-01", 18000000.00, 19500000.00, 17200000.00, {
                "L1_zoning": 6.5, "L2_transit": 5.0, "L3_power": 9.5, "L4_legal": 8.0, "L5_ranger": 7.5, "L6_pulse": 5.0, "L7_finance": 9.0
            }),
            # DECATUR-DC-02: Underwritten close to asking
            ("DECATUR-DC-02", 14000000.00, 14200000.00, 14100000.00, {
                "L1_zoning": 7.0, "L2_transit": 6.0, "L3_power": 9.0, "L4_legal": 8.5, "L5_ranger": 8.0, "L6_pulse": 5.5, "L7_finance": 8.5
            }),
            # VALLEY-VIEW-01: Underwritten too high
            ("VALLEY-VIEW-01", 22000000.00, 20000000.00, 23500000.00, {
                "L1_zoning": 9.5, "L2_transit": 9.5, "L3_power": 8.0, "L4_legal": 6.0, "L5_ranger": 8.5, "L6_pulse": 9.0, "L7_finance": 7.0
            })
        ]
        
        # Clear existing MarketValue to prevent foreign key duplicate constraints in runs
        cursor.execute('DELETE FROM "HEX_MarketValue";')
        
        for pid, est, ask, und, comps in market_values:
            cursor.execute("""
                INSERT INTO "HEX_MarketValue" (parcel_id, estimated_value, asking_price, underwritten_value, compositions, assessed_date)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (pid, est, ask, und, json.dumps(comps), date.today()))
            
        conn.commit()
        conn.close()
        print("SUCCESS: 5 comps seeded in 'HEX_MarketValue'.")
    except Exception as e:
        print(f"FAILURE: Failed to seed revenue data. {e}")

if __name__ == '__main__':
    seed_revenue_data()
