"""
SigmaFidelity™ Telegram User Linking Utility
Standard: HWB-QMS-7.6 Multi-User Command Center SOP
"""

import os
import sys
import psycopg2

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "HWB-COMPANY", "HWB-IT", "HWB-IT-WEBSITE"))
sys.path.insert(0, BASE_DIR)

def link_telegram_user(identifier: str, chat_id: str, db_url: str):
    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT id, username, full_name, email, role, telegram_chat_id 
                FROM "Users" 
                WHERE username = %s OR LOWER(email) = LOWER(%s) OR id::text = %s;
            ''', (identifier, identifier, identifier))
            user = cur.fetchone()
            if not user:
                print(f"[ERROR] User '{identifier}' not found in Users table.")
                sys.exit(1)

            user_id, username, full_name, email, role, old_chat = user
            clean_chat_id = str(chat_id).strip()

            cur.execute('''
                UPDATE "Users"
                SET telegram_chat_id = %s
                WHERE id = %s;
            ''', (clean_chat_id, user_id))
            conn.commit()

            print(f"✓ [SUCCESS] User '{full_name or username}' ({email}, role: {role}) linked to Telegram Chat ID: {clean_chat_id}")
    finally:
        conn.close()

def list_telegram_users(db_url: str):
    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT id, username, full_name, email, role, status, telegram_chat_id 
                FROM "Users" 
                ORDER BY id ASC;
            ''')
            rows = cur.fetchall()
            print("\n=== Active HWB Users Telegram Registry ===")
            print(f"{'ID':<4} {'Username':<15} {'Name':<22} {'Role':<12} {'Telegram Chat ID':<18}")
            print("-" * 75)
            for r in rows:
                uid, uname, name, em, role, status, chat = r
                chat_str = chat if chat else "[NOT LINKED]"
                print(f"{uid:<4} {uname:<15} {(name or '--'):<22} {role:<12} {chat_str:<18}")
            print("=" * 75 + "\n")
    finally:
        conn.close()

if __name__ == '__main__':
    db_url = os.getenv('DATABASE_URL', 'postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db')
    if len(sys.argv) == 1:
        list_telegram_users(db_url)
    elif len(sys.argv) >= 3:
        identifier = sys.argv[1]
        chat_id = sys.argv[2]
        link_telegram_user(identifier, chat_id, db_url)
    else:
        print("Usage:")
        print("  python3 scripts/link_user_telegram.py                # List all users & telegram status")
        print("  python3 scripts/link_user_telegram.py <username/email> <chat_id>  # Link Telegram ID")
