"""
SigmaFidelity™ Enterprise RBAC Security Gateway
Standard: HWB-QMS-7.6 Zero-Hotfix Standard / SOC 2 / ISO 27001
Custodians: George (Systems Architect) & Humberto Dominguez (CEO)
"""

import os
from functools import wraps
from flask import request, redirect, url_for, flash, abort, current_app, has_app_context
from flask_login import current_user
from core.services.database import get_db


def log_security_violation(user_id, username, role, path, method):
    """Institutional Security Telemetry (SOC 2 / ISO 27001): Logs access breaches to GlobalActivities."""
    conn = None
    try:
        db_url = (current_app.config.get('DATABASE_URL') if has_app_context() else None) or os.getenv('DATABASE_URL')
        conn = get_db(db_url)
        with conn.cursor() as cur:
            desc = f"Role '{role}' ({username}) blocked from accessing {method} {path}"
            cur.execute('''
                INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                VALUES (%s, %s, %s, %s)
            ''', (user_id, "User", "SECURITY_VIOLATION", desc))
            conn.commit()

        from core.services.security_logger import log_security_event
        log_security_event(
            event_category='RBAC',
            event_action='ROUTE_BLOCKED',
            severity='WARNING',
            user_id=user_id,
            username=username,
            user_role=role,
            endpoint=path,
            http_method=method,
            status_code=403,
            details={'blocked_role': role, 'path': path, 'method': method}
        )
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
from cryptography.fernet import Fernet, MultiFernet


def _derive_fernet_key(secret_material: str) -> bytes:
    """Derives a 32-byte URL-safe base64 Fernet key from raw secret material."""
    raw = (secret_material or "").strip()
    if len(raw) == 44 and raw.endswith("="):
        try:
            decoded = base64.urlsafe_b64decode(raw.encode("utf-8"))
            if len(decoded) == 32:
                return raw.encode("utf-8")
        except Exception:
            pass
    derived = hashlib.sha256(raw.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(derived)


def get_pii_cipher():
    """
    Returns an AES-256 MultiFernet cipher for PII and HR/1099 document encryption.
    Uses dedicated PII_ENCRYPTION_KEY as primary cipher while retaining seamless
    decryption compatibility with existing SECRET_KEY-derived ciphertexts.
    """
    fernets = []
    pii_key = (os.getenv("PII_ENCRYPTION_KEY") or "").strip()
    secret_key = (os.getenv("SECRET_KEY") or "").strip()

    if pii_key:
        fernets.append(Fernet(_derive_fernet_key(pii_key)))
    if secret_key:
        # Derive a domain-separated PII key from SECRET_KEY when PII_ENCRYPTION_KEY is not separately set
        if not pii_key:
            fernets.append(Fernet(_derive_fernet_key(f"hwb-pii-vault-v2::{secret_key}")))
        # Always include direct SHA-256(SECRET_KEY) in MultiFernet key ring for legacy ciphertext decryption
        fernets.append(Fernet(_derive_fernet_key(secret_key)))

    if not fernets:
        raise RuntimeError("Cryptographic configuration error: PII_ENCRYPTION_KEY or SECRET_KEY must be set.")

    return MultiFernet(fernets) if len(fernets) > 1 else fernets[0]


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
        db_url = (current_app.config.get('DATABASE_URL') if has_app_context() else None) or os.getenv('DATABASE_URL')
        conn = get_db(db_url)
        with conn.cursor() as cur:
            desc = f"Admin {username} (ID #{user_id}) inspected decrypted {field_name} for Employee #{employee_id} from {ip_address or 'internal'}"
            cur.execute('''
                INSERT INTO "GlobalActivities" (parent_id, parent_type, activity_type, description)
                VALUES (%s, %s, %s, %s)
            ''', (employee_id, "Employee", "SENSITIVE_DATA_ACCESS", desc))
            conn.commit()
            print(f"[SECURITY_PII_AUDIT] {desc}", flush=True)

        from core.services.security_logger import log_security_event
        log_security_event(
            event_category='PII_ACCESS',
            event_action='PII_REVEAL',
            severity='CRITICAL',
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            status_code=200,
            details={'employee_id': employee_id, 'field_name': field_name, 'action': '30s_timed_reveal'}
        )
    except Exception as e:
        print(f"[SECURITY_LOG_ERROR] Could not log PII access: {e}", flush=True)
    finally:
        if conn:
            conn.close()

