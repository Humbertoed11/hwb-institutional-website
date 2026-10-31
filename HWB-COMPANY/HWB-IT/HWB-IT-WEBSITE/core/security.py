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


# =========================================================================
# SEC-11 Binary File-Upload Magic-Byte Airlock & Active-Payload Scanner
# Standard: AICPA SOC 2 Criterion CC6.8 / BABYSOP-SOP-0.41 / Mandate 10
# =========================================================================
import zlib

FORBIDDEN_UPLOAD_EXTENSIONS = {
    ".php", ".phtml", ".php5", ".js", ".mjs", ".exe", ".dll", ".so",
    ".sh", ".bash", ".bat", ".cmd", ".ps1", ".vbs", ".py", ".rb",
    ".pl", ".cgi", ".jar", ".war", ".jsp", ".asp", ".aspx", ".html",
    ".htm", ".xhtml", ".svg", ".xml", ".hta", ".scr", ".msi", ".com",
}

MAGIC_BYTE_SIGNATURES = {
    ".pdf": (b"%PDF-",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".gif": (b"GIF87a", b"GIF89a"),
    ".webp": (b"RIFF",),
}

ACTIVE_PAYLOAD_SIGNATURES = (
    b"/javascript",
    b"/js",
    b"/launch",
    b"/openaction",
    b"/aa",
    b"/richmedia",
    b"/submitform",
    b"/importdata",
    b"<?php",
    b"<script",
    b"javascript:",
    b"vbscript:",
    b"onload=",
    b"onerror=",
)


def inspect_and_sanitize_file_upload(
    filename: str,
    raw_bytes: bytes,
    allowed_extensions: tuple = (".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".csv", ".txt"),
    max_bytes: int = 10 * 1024 * 1024,
    max_compression_ratio: float = 25.0,
) -> dict:
    """
    Fortune 500 Binary File-Upload Airlock (Cartridge SEC-11 / SOC 2 CC6.8):
    1. Rejects empty payloads and enforces deterministic byte-size ceiling (10 MB default).
    2. Blocks polyglot / double extensions (e.g. 'invoice.php.pdf') and executable extensions.
    3. Validates cryptographic magic-byte file headers against the declared extension.
    4. Scans raw bytes for embedded active payloads (/JavaScript, /Launch, <?php, <script).
    5. Enforces Zip-Bomb / FlateDecode decompression ratio ceiling (<= 25:1).
    """
    raw_name = (filename or "").strip()
    sha256_hash = hashlib.sha256(raw_bytes or b"").hexdigest()

    def _reject(reason: str) -> dict:
        try:
            from core.services.security_logger import log_security_event
            log_security_event(
                event_category="FILE_UPLOAD_AIRLOCK",
                event_action="BLOCKED_MALICIOUS_UPLOAD",
                severity="CRITICAL",
                status_code=400,
                details={
                    "filename": raw_name,
                    "size_bytes": len(raw_bytes or b""),
                    "sha256": sha256_hash,
                    "rejection_reason": reason,
                    "standard": "SEC-11 / SOC2-CC6.8",
                },
            )
        except Exception:
            pass
        return {
            "allowed": False,
            "rejection_reason": reason,
            "sha256": sha256_hash,
            "size_bytes": len(raw_bytes or b""),
        }

    if not raw_name or "\x00" in raw_name:
        return _reject("INVALID_OR_NULL_FILENAME")
    if not raw_bytes:
        return _reject("EMPTY_FILE_PAYLOAD")
    if len(raw_bytes) > max_bytes:
        return _reject(f"PAYLOAD_EXCEEDS_MAX_BYTES ({len(raw_bytes)} > {max_bytes})")

    clean_parts = [p.lower() for p in raw_name.replace("\\", "/").split("/")[-1].split(".") if p]
    if len(clean_parts) < 2:
        return _reject("MISSING_FILE_EXTENSION")

    for part in clean_parts[1:]:
        if f".{part}" in FORBIDDEN_UPLOAD_EXTENSIONS:
            return _reject(f"FORBIDDEN_OR_POLYGLOT_EXTENSION (.{part})")

    ext = f".{clean_parts[-1]}"
    allowed_norm = {e.lower() for e in allowed_extensions}
    if ext not in allowed_norm:
        return _reject(f"DISALLOWED_EXTENSION ({ext})")

    # Magic-byte header verification
    if ext in MAGIC_BYTE_SIGNATURES:
        valid_prefixes = MAGIC_BYTE_SIGNATURES[ext]
        if not any(raw_bytes.startswith(prefix) for prefix in valid_prefixes):
            return _reject(f"MAGIC_BYTE_HEADER_MISMATCH_FOR_{ext.upper().lstrip('.')}")
        if ext == ".webp" and raw_bytes[8:12] != b"WEBP":
            return _reject("MAGIC_BYTE_HEADER_MISMATCH_FOR_WEBP")
    elif ext in (".csv", ".txt"):
        # Reject binary executables or archives masquerading as CSV/TXT
        if raw_bytes.startswith((b"MZ", b"\x7fELF", b"PK\x03\x04", b"%PDF-")) or b"\x00" in raw_bytes[:4096]:
            return _reject("BINARY_PAYLOAD_DISGUISED_AS_TEXT")

    # Active-payload inspection (case-insensitive scan over raw bytes)
    lowered = raw_bytes.lower()
    for sig in ACTIVE_PAYLOAD_SIGNATURES:
        if sig in lowered:
            # For /js or /aa in PDFs, ensure it is a PDF name token followed by delimiter
            if sig in (b"/js", b"/aa"):
                if re.search(rb"/(?:js|aa)(?:[\s(<\[/]|$)", lowered):
                    return _reject(f"ACTIVE_PAYLOAD_DETECTED ({sig.decode('ascii', 'ignore')})")
            else:
                return _reject(f"ACTIVE_PAYLOAD_DETECTED ({sig.decode('ascii', 'ignore')})")

    # Zip-Bomb / PDF stream decompression ratio guard
    if ext == ".pdf":
        total_decompressed = 0
        for stream_m in re.finditer(rb"stream[\r\n]+(.*?)[\r\n]+endstream", raw_bytes, re.DOTALL):
            s_bytes = stream_m.group(1)
            if not s_bytes:
                continue
            for wbits in (zlib.MAX_WBITS, -zlib.MAX_WBITS):
                try:
                    d_obj = zlib.decompressobj(wbits)
                    decomp = d_obj.decompress(s_bytes, max_bytes + 1024)
                    if d_obj.unconsumed_tail:
                        return _reject("ZIP_BOMB_DECOMPRESSION_CEILING_EXCEEDED")
                    total_decompressed += len(decomp)
                    ratio = len(decomp) / max(1, len(s_bytes))
                    if ratio > max_compression_ratio and len(decomp) > 1024 * 1024:
                        return _reject(f"ZIP_BOMB_COMPRESSION_RATIO_EXCEEDED ({ratio:.1f}:1)")
                    break
                except Exception:
                    continue
            if total_decompressed > max_bytes * 2:
                return _reject("CUMULATIVE_PDF_STREAM_EXPANSION_EXCEEDED")

    safe_filename = re.sub(r"[^A-Za-z0-9_.\-]", "_", clean_parts[0])[:80] + ext
    return {
        "allowed": True,
        "verified_extension": ext,
        "sanitized_filename": safe_filename,
        "sha256": sha256_hash,
        "size_bytes": len(raw_bytes),
    }


def sanitize_csv_cell_value(val: str) -> str:
    """
    Neutralizes CSV Formula Injection (OWASP CSV Injection / CWE-1236) by stripping
    leading spreadsheet execution triggers (=, +, -, @, tab, CR) from text cells.
    """
    cleaned = str(val or "").strip()
    if cleaned and cleaned[0] in ("=", "+", "-", "@", "\t", "\r"):
        # Preserve negative numbers like -123.45 while stripping formulas like -cmd|...
        if cleaned[0] == "-" and re.match(r"^-\d+(?:\.\d+)?$", cleaned):
            return cleaned
        return cleaned.lstrip("=+-@\t\r").strip()
    return cleaned


