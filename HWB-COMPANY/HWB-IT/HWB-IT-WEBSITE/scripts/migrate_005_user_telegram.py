"""
Migration 005: User Telegram Chat ID Integration
Standard: HWB-QMS-7.6 Database Hardening & Schema Versioning SOP
"""

import os
import sys
import psycopg2

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "HWB-COMPANY", "HWB-IT", "HWB-IT-WEBSITE"))
sys.path.insert(0, BASE_DIR)

def run_migration(db_url: str):
    print("[MIGRATION] Applying 005_user_telegram_chat_id...")
    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            # 1. Add telegram_chat_id column to Users table
            cur.execute('''
                ALTER TABLE "Users" 
                ADD COLUMN IF NOT EXISTS telegram_chat_id VARCHAR(50);

                CREATE INDEX IF NOT EXISTS "idx_users_telegram_chat_id" 
                ON "Users" (telegram_chat_id);
            ''')

            # 2. Seed Humberto Dominguez's primary Telegram Chat ID
            cur.execute('''
                UPDATE "Users" 
                SET telegram_chat_id = '8564340073' 
                WHERE username = 'hdominguez' OR id = 1;
            ''')

            # 3. Register in schema_migrations
            cur.execute('''
                INSERT INTO schema_migrations (version, applied_at, description)
                VALUES ('005_user_telegram_chat_id', CURRENT_TIMESTAMP, 'Added telegram_chat_id to Users table for multi-user Telegram dispatch')
                ON CONFLICT (version) DO NOTHING;
            ''')

            conn.commit()
            print("✓ [MIGRATION 005 SUCCESS] telegram_chat_id added to Users table and CEO linked.")
    finally:
        conn.close()

if __name__ == '__main__':
    db_url = os.getenv('DATABASE_URL', 'postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db')
    run_migration(db_url)
