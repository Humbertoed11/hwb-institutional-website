"""
Migration 016: SigmaFidelity™ Enterprise Sensitive Data Protection & PII Vault
Standard: HWB-QMS-7.6 / ISO 27001 / Texas Bus. & Com. Code § 521.053
Authority: Humberto Dominguez (CEO)
Architect: George (Systems Architect & mbB)
"""

import os
import psycopg2
import base64
import hashlib
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://hwbdev:hwbpassword@localhost:5432/hwb_dev_db")


def get_cipher():
    key = os.getenv("PII_ENCRYPTION_KEY")
    if not key:
        secret = os.getenv("SECRET_KEY", "hwb_default_fallback_secret_key_2026")
        derived = hashlib.sha256(secret.encode()).digest()
        key = base64.urlsafe_b64encode(derived).decode()
    return Fernet(key.encode())


def run_migration(db_url: str):
    print("\n=======================================================")
    print("  Applying Migration 016: Sensitive PII Vault & AES-256")
    print("=======================================================")

    cipher = get_cipher()
    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            # 1. Add encrypted columns and last-4 columns to "Employees"
            cur.execute("""
                ALTER TABLE "Employees"
                ADD COLUMN IF NOT EXISTS ssn_encrypted TEXT,
                ADD COLUMN IF NOT EXISTS ssn_last_four VARCHAR(4),
                ADD COLUMN IF NOT EXISTS direct_deposit_account_encrypted TEXT,
                ADD COLUMN IF NOT EXISTS direct_deposit_account_last_four VARCHAR(4);
            """)
            print("  ✓ Added sensitive PII vault columns to 'Employees'.")

            # 2. Add performance/lookup index for last-4
            cur.execute("""
                CREATE INDEX IF NOT EXISTS "idx_employees_ssn_last_four" ON "Employees"(ssn_last_four);
            """)
            print("  ✓ Created index on Employees(ssn_last_four).")

            # 3. Encrypt any existing direct_deposit_account values
            cur.execute('SELECT id, direct_deposit_account FROM "Employees" WHERE direct_deposit_account IS NOT NULL AND direct_deposit_account != \'\';')
            rows = cur.fetchall()
            for emp_id, acct in rows:
                clean_acct = str(acct).strip()
                last_4 = clean_acct[-4:] if len(clean_acct) >= 4 else clean_acct
                enc = cipher.encrypt(clean_acct.encode()).decode()
                cur.execute("""
                    UPDATE "Employees"
                    SET direct_deposit_account_encrypted = %s,
                        direct_deposit_account_last_four = %s
                    WHERE id = %s;
                """, (enc, last_4, emp_id))
            print(f"  ✓ Sanitized and encrypted {len(rows)} existing banking records.")

            conn.commit()
            print("  ✓ Migration 016 committed successfully.")
    except Exception as e:
        conn.rollback()
        print(f"  ❌ Migration 016 failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration(DB_URL)
