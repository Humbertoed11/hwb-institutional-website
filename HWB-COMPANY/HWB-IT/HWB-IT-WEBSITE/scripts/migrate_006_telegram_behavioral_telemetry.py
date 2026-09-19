"""
Migration 006: Telegram Behavioral Telemetry & Event Stream Architecture
Standard: HWB-QMS-7.6 Database Hardening & Schema Versioning SOP
Author: George (Systems Architect)
Governance: Executive Directive 2026-09-19 (CEO Humberto Dominguez)
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "HWB-COMPANY", "HWB-IT", "HWB-IT-WEBSITE"))
load_dotenv(os.path.join(BASE_DIR, ".env"))

def run_migration(db_url: str):
    print("[MIGRATION] Applying 006_telegram_behavioral_telemetry...")
    if "@localhost" in db_url and os.path.exists("/.dockerenv"):
        db_url = db_url.replace("@localhost", "@db")
    elif "@localhost" in db_url:
        # Check if local or docker
        pass

    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            # 1. Create TelegramEventStream table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS "TelegramEventStream" (
                    id SERIAL PRIMARY KEY,
                    user_id INT REFERENCES "Users"(id) ON DELETE SET NULL,
                    chat_id BIGINT NOT NULL,
                    user_handle VARCHAR(100),
                    user_full_name VARCHAR(150),
                    user_role VARCHAR(50),
                    event_type VARCHAR(50) NOT NULL,
                    payload_summary TEXT,
                    detected_intent VARCHAR(100),
                    friction_flag BOOLEAN DEFAULT FALSE,
                    latency_ms INT DEFAULT 0,
                    mirrored_to_ceo BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS "idx_tg_events_user_id" 
                ON "TelegramEventStream" (user_id, created_at DESC);

                CREATE INDEX IF NOT EXISTS "idx_tg_events_chat_id" 
                ON "TelegramEventStream" (chat_id, created_at DESC);

                CREATE INDEX IF NOT EXISTS "idx_tg_events_type" 
                ON "TelegramEventStream" (event_type, created_at DESC);
            ''')

            # 2. Create UserBehavioralProfiles table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS "UserBehavioralProfiles" (
                    user_id INT PRIMARY KEY REFERENCES "Users"(id) ON DELETE CASCADE,
                    chat_id BIGINT UNIQUE NOT NULL,
                    username VARCHAR(100),
                    full_name VARCHAR(150),
                    user_role VARCHAR(50),
                    total_interactions INT DEFAULT 0,
                    interaction_habits JSONB DEFAULT '{}'::jsonb,
                    intent_distribution JSONB DEFAULT '{}'::jsonb,
                    top_actions JSONB DEFAULT '[]'::jsonb,
                    friction_log JSONB DEFAULT '[]'::jsonb,
                    adaptive_preferences JSONB DEFAULT '{}'::jsonb,
                    qualitative_summary TEXT,
                    last_active_at TIMESTAMP WITH TIME ZONE,
                    last_analyzed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS "idx_user_behavior_chat_id" 
                ON "UserBehavioralProfiles" (chat_id);
            ''')

            # 3. Seed initial profiles for existing users with Telegram Chat IDs
            cur.execute('''
                INSERT INTO "UserBehavioralProfiles" (
                    user_id, chat_id, username, full_name, user_role, total_interactions, 
                    adaptive_preferences, qualitative_summary, last_analyzed_at
                )
                SELECT DISTINCT ON (telegram_chat_id)
                    id, 
                    CAST(telegram_chat_id AS BIGINT), 
                    username, 
                    COALESCE(full_name, username), 
                    role, 
                    0, 
                    '{"layout": "executive_command", "verbosity": "high_fidelity_concise"}'::jsonb,
                    'Initial profile established. Standing by for interaction stream synthesis.',
                    CURRENT_TIMESTAMP
                FROM "Users"
                WHERE telegram_chat_id IS NOT NULL 
                  AND telegram_chat_id != ''
                  AND telegram_chat_id ~ '^[0-9]+$'
                ORDER BY telegram_chat_id, (CASE WHEN username = 'hdominguez' THEN 0 ELSE 1 END), id
                ON CONFLICT (user_id) DO UPDATE SET
                    chat_id = EXCLUDED.chat_id,
                    username = EXCLUDED.username,
                    full_name = EXCLUDED.full_name,
                    user_role = EXCLUDED.user_role;
            ''')

            # 4. Record migration in schema_migrations
            cur.execute('''
                INSERT INTO schema_migrations (version, applied_at, description)
                VALUES (
                    '006_telegram_behavioral_telemetry', 
                    CURRENT_TIMESTAMP, 
                    'Deployed TelegramEventStream and UserBehavioralProfiles for continuous behavioral learning and real-time CEO activity mirroring'
                )
                ON CONFLICT (version) DO NOTHING;
            ''')

            conn.commit()
            print("✓ [MIGRATION 006 SUCCESS] TelegramEventStream and UserBehavioralProfiles deployed and initialized.")
    finally:
        conn.close()

if __name__ == '__main__':
    default_url = os.getenv('DATABASE_URL', 'postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db')
    run_migration(default_url)
