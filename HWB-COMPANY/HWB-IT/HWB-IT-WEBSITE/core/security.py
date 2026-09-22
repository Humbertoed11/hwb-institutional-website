"""
SigmaFidelity™ Enterprise RBAC Security Gateway
Standard: HWB-QMS-7.6 Zero-Hotfix Standard / SOC 2 / ISO 27001
Custodians: George (Systems Architect) & Humberto Dominguez (CEO)
"""

from functools import wraps
from flask import request, redirect, url_for, flash, abort, current_app
from flask_login import current_user
from core.services.database import get_db


def log_security_violation(user_id, username, role, path, method):
    """Institutional Security Telemetry (SOC 2 / ISO 27001): Logs access breaches to GlobalActivities."""
    conn = None
    try:
        db_url = current_app.config['DATABASE_URL']
        conn = get_db(db_url)
        with conn.cursor() as cur:
            desc = f"Role '{role}' ({username}) blocked from accessing {method} {path}"
            cur.execute('''
                INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                VALUES (%s, %s, %s, %s)
            ''', (user_id, "User", "SECURITY_VIOLATION", desc))
            conn.commit()
    except Exception as e:
        print(f"[SECURITY_LOG_ERROR] Could not log violation: {e}", flush=True)
    finally:
        if conn:
            conn.close()


def roles_required(*roles):
    """Declarative Role-Based Access Control Decorator (Enterprise Standard)."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login', next=request.url))
            if current_user.role not in roles:
                print(f"[SECURITY_AUDIT] Unauthorized access attempt by {current_user.username} ({current_user.role}) to {request.path}", flush=True)
                log_security_violation(current_user.id, current_user.username, current_user.role, request.path, request.method)
                if current_user.role == 'Sales':
                    flash("Access restricted. Outside Sales personnel are routed to the Field Sales Desk.")
                    return redirect(url_for('sales_desk'))
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# =========================================================================
# Enterprise Sensitive Data Protection & PII Vault (ISO 27001 / SOC 2)
# =========================================================================
import os
import re
import base64
import hashlib
from cryptography.fernet import Fernet


def get_pii_cipher():
    """Derives a deterministic Fernet key for AES-256 PII column encryption."""
    key = os.getenv("PII_ENCRYPTION_KEY")
    if not key:
        secret = os.getenv("SECRET_KEY", "hwb_default_fallback_secret_key_2026")
        derived = hashlib.sha256(secret.encode()).digest()
        key = base64.urlsafe_b64encode(derived).decode()
    return Fernet(key.encode())


def encrypt_pii(plaintext: str) -> str:
    """Encrypts plaintext string using AES-256 Fernet cipher."""
    if not plaintext:
        return None
    cipher = get_pii_cipher()
    return cipher.encrypt(str(plaintext).strip().encode()).decode()


def decrypt_pii(ciphertext: str) -> str:
    """Decrypts ciphertext string using AES-256 Fernet cipher."""
    if not ciphertext:
        return ""
    try:
        cipher = get_pii_cipher()
        return cipher.decrypt(ciphertext.encode()).decode()
    except Exception as e:
        print(f"[PII_DECRYPT_ERROR] Failed to decrypt sensitive data: {e}", flush=True)
        return ""


def mask_ssn(raw_ssn: str = None, last_four: str = None) -> str:
    """Standardizes SSN to institutional masked display: ***-**-1234."""
    if last_four and len(str(last_four).strip()) == 4:
        return f"***-**-{str(last_four).strip()}"
    if raw_ssn:
        digits = re.sub(r"\D", "", str(raw_ssn))
        if len(digits) >= 4:
            return f"***-**-{digits[-4:]}"
    return "***-**-****"


def mask_account(raw_acc: str = None, last_four: str = None) -> str:
    """Standardizes direct deposit account to institutional masked display: ••••••••1234."""
    if last_four and len(str(last_four).strip()) == 4:
        return f"••••••••{str(last_four).strip()}"
    if raw_acc:
        digits = re.sub(r"\s", "", str(raw_acc))
        if len(digits) >= 4:
            return f"••••••••{digits[-4:]}"
    return "••••••••"


def log_sensitive_access(user_id, username, employee_id, field_name, ip_address=None):
    """Institutional Audit Log: Records all unmasking / decryptions of sensitive PII."""
    conn = None
    try:
        db_url = current_app.config['DATABASE_URL']
        conn = get_db(db_url)
        with conn.cursor() as cur:
            desc = f"Admin {username} (ID #{user_id}) inspected decrypted {field_name} for Employee #{employee_id} from {ip_address or 'internal'}"
            cur.execute('''
                INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                VALUES (%s, %s, %s, %s)
            ''', (employee_id, "Employee", "SENSITIVE_DATA_ACCESS", desc))
            conn.commit()
            print(f"[SECURITY_PII_AUDIT] {desc}", flush=True)
    except Exception as e:
        print(f"[SECURITY_LOG_ERROR] Could not log PII access: {e}", flush=True)
    finally:
        if conn:
            conn.close()

