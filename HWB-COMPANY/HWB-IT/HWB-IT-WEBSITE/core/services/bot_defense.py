"""
SigmaFidelity™ Enterprise Bot Defense & Form Abuse Protection Engine
Standard: HWB-QMS-11.10 Spam Protection, Honey-pot Ingestion, and Bot Defense SOP
Standard: HWB-QMS-7.6 Enterprise Architecture Standards (SOC 2 / ISO 27001)
Custodians: George (Systems Architect) & Humberto Dominguez (CEO)
"""

import time
import re
from typing import Tuple, Dict, Any, Optional
from flask import current_app, Request
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from urllib.parse import urlparse

# Honeypot field names to inspect across all public forms and login gates
HONEYPOT_FIELDS = (
    'hp_organization_url',
    'hp_tax_id',
    'hp_website',
    'business_website_url',
    'hp_login_url',
)

# Suspicious URL protocols or top-level patterns in text fields
SPAM_URL_PATTERNS = (
    "http://",
    "https://",
    "graph.org",
    ".org/",
    ".net/",
    ".com/",
    ".xyz",
    ".top",
    ".ru",
    "t.me/"
)

# Financial scam, cryptocurrency, and wire transfer spam phrases
FINANCIAL_SPAM_PHRASES = (
    "us dollars",
    "usdc",
    "transfer of",
    "payment",
    "get the transfer",
    "balance",
    "transaction to you",
    "crypto",
    "bitcoin",
    "ethereum",
    "investment opportunity",
    "telegram bot",
    "seo ranking service"
)

# Minimum human interaction window (humans take at least 3 seconds to complete a form)
MIN_INTERACTION_SECONDS = 3.0

# Maximum token validity (24 hours = 86,400 seconds)
MAX_TOKEN_AGE_SECONDS = 86400

# Allowed hostnames for referrer and origin verification
ALLOWED_HOSTS = {
    'hwbcleaning.com',
    'www.hwbcleaning.com',
    'mop.test',
    'localhost',
    '127.0.0.1'
}


def get_serializer() -> URLSafeTimedSerializer:
    """Returns an itsdangerous serializer instance with the application secret key."""
    secret = current_app.config.get('SECRET_KEY', 'hwb-sigma-default-secret-key-2026')
    return URLSafeTimedSerializer(secret_key=secret, salt='hwb-bot-defense-salt-v1')


def generate_form_security_token(scope: str = "quote_form") -> str:
    """
    Generates an encrypted, signed timestamp token for embedding in web forms.
    Guarantees proof of form delivery and authenticates rendering time.
    """
    serializer = get_serializer()
    payload = {
        "rendered_at": time.time(),
        "scope": scope
    }
    return serializer.dumps(payload)


def validate_form_speed(token: Optional[str], min_seconds: float = MIN_INTERACTION_SECONDS) -> Tuple[bool, str]:
    """
    Validates form submission speed using the signed timestamp token.
    Rejects sub-second automated scripts and expired form submissions.
    """
    if not token or not str(token).strip():
        return False, "Missing security timestamp token"

    serializer = get_serializer()
    try:
        data = serializer.loads(token, max_age=MAX_TOKEN_AGE_SECONDS)
        rendered_at = data.get("rendered_at", 0)
        elapsed = time.time() - rendered_at
        
        if elapsed < min_seconds:
            return False, f"Sub-second automation detected ({elapsed:.2f}s < {min_seconds}s threshold)"
        
        return True, "Speed check passed"
    except SignatureExpired:
        return False, "Form security token expired (> 24 hours)"
    except BadSignature:
        return False, "Invalid or forged form security token signature"
    except Exception as e:
        return False, f"Token validation error: {str(e)}"


def check_honeypots(form_data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Checks if any hidden honeypot fields were filled by automated crawlers.
    Returns: (is_clean: bool, reason: str)
    """
    for field in HONEYPOT_FIELDS:
        val = form_data.get(field)
        if val is not None and str(val).strip():
            return False, f"Honeypot field '{field}' was filled with '{str(val)[:20]}'"
    return True, "Honeypot check passed"


def check_content_signatures(form_data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Scans text fields for web links and financial scam keywords.
    Returns: (is_clean: bool, reason: str)
    """
    fields_to_scan = [
        'company', 'company_name', 'name', 'contact_name', 'full_name',
        'city', 'notes', 'comments', 'message', 'facility_type',
    ]
    for f in fields_to_scan:
        text = form_data.get(f)
        if not text:
            continue
        text_str = str(text)
        text_lower = text_str.lower()

        # URL protocol or spam domain check
        if any(pat in text_str for pat in SPAM_URL_PATTERNS):
            return False, f"External URL pattern detected in field '{f}'"

        # Financial scam check
        if any(phrase in text_lower for phrase in FINANCIAL_SPAM_PHRASES):
            return False, f"Financial spam signature detected in field '{f}'"

    return True, "Content check passed"


def check_origin(req: Request) -> Tuple[bool, str]:
    """
    Validates the Origin or Referrer header against authorized company domains.
    Returns: (is_valid: bool, reason: str)
    """
    ref = req.referrer or req.headers.get('Origin')
    if not ref:
        # Reject raw direct requests (cURL, Postman, automated API scripts) that bypass page load
        return False, "Direct raw request without Referrer or Origin header"

    try:
        parsed = urlparse(ref)
        hostname = (parsed.hostname or '').lower()
        if not hostname:
            return False, "Empty hostname in Referrer/Origin header"
            
        is_allowed = hostname in ALLOWED_HOSTS or any(hostname.endswith('.' + h) for h in ALLOWED_HOSTS)
        if not is_allowed:
            return False, f"Unauthorized cross-site origin: {hostname}"
            
        return True, "Origin check passed"
    except Exception as e:
        return False, f"Malformed Referrer/Origin header: {str(e)}"


def extract_request_payload(req: Request) -> Dict[str, Any]:
    """Extracts unified dictionary payload from either HTML FormData or JSON body."""
    payload: Dict[str, Any] = {}
    if req.form:
        payload.update(req.form.to_dict())
    json_body = req.get_json(silent=True)
    if isinstance(json_body, dict):
        payload.update(json_body)
    return payload


def generate_lead_update_token(lead_id: int) -> str:
    """Generates a signed 2-hour token binding Step-2 quote enrichment to a specific lead_id."""
    serializer = get_serializer()
    return serializer.dumps({"lead_id": int(lead_id), "scope": "lead_update"})


def validate_lead_update_token(token: Optional[str], lead_id: int) -> Tuple[bool, str]:
    """Verifies a Step-2 quote enrichment token matches the target lead_id."""
    if not token or not str(token).strip():
        return False, "Missing Step-2 lead security token"
    serializer = get_serializer()
    try:
        data = serializer.loads(str(token).strip(), max_age=7200)
        if data.get("scope") != "lead_update" or int(data.get("lead_id", -1)) != int(lead_id):
            return False, "Step-2 lead security token mismatch"
        return True, "Valid Step-2 token"
    except SignatureExpired:
        return False, "Step-2 lead security token expired"
    except BadSignature:
        return False, "Invalid Step-2 lead security token signature"
    except Exception as exc:
        return False, f"Step-2 token validation error: {exc}"


SCANNER_PROBE_USERNAMES = {
    'wp-admin', 'root', 'administrator', 'phpmyadmin',
    'postgres', 'sa', 'testadmin', 'guest', 'user',
}


def evaluate_login_bot_attempt(
    req: Request,
    identifier: str = '',
    db_url: Optional[str] = None,
    client_ip: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Detects automated login or password-reset bot attacks while keeping ordinary
    single-attempt human password typos classified separately under LOGIN_FAIL.
    """
    payload = extract_request_payload(req)

    # Signal 1: Hidden Honeypot Field Filled
    clean_hp, hp_reason = check_honeypots(payload)
    if not clean_hp:
        return True, hp_reason

    # Signal 2: Automated Scanner Username Probe
    ident_clean = (identifier or '').strip().lower()
    if ident_clean in SCANNER_PROBE_USERNAMES:
        return True, f"Automated scanner username probe ('{ident_clean}')"

    enforce_strict = (
        not current_app.config.get('TESTING')
        or req.headers.get('X-Enforce-Bot-Defense') == '1'
    )

    # Signal 3: Direct Script POST Without Valid Origin/Referer Header
    if enforce_strict:
        valid_origin, origin_reason = check_origin(req)
        if not valid_origin:
            return True, origin_reason

    # Signal 4: Credential-Stuffing / Brute-Force IP Burst (3+ prior failures in 15m)
    ip_val = (client_ip or '').strip()
    if ip_val and (enforce_strict or ip_val not in ('127.0.0.1', '::1', 'localhost')):
        target_db = db_url or current_app.config.get('DATABASE_URL')
        if target_db:
            try:
                from core.services.database import get_db
                conn = get_db(target_db)
                try:
                    with conn.cursor() as cur:
                        cur.execute('''
                            SELECT COUNT(*) AS cnt
                            FROM "SecurityAuditLogs"
                            WHERE ip_address = %s
                              AND event_action IN ('LOGIN_FAIL', 'LOGIN_BOT_BLOCKED')
                              AND timestamp >= NOW() - INTERVAL '15 minutes';
                        ''', (ip_val,))
                        r = cur.fetchone()
                        fail_cnt = int(r['cnt'] if isinstance(r, dict) else r[0])
                        if fail_cnt >= 2:
                            return True, f"Repeated login failure burst from IP {ip_val} ({fail_cnt + 1} attempts in 15m)"
                finally:
                    conn.close()
            except Exception:
                pass

    return False, "Human login attempt"


def evaluate_bot_defense(req: Request) -> Tuple[bool, str]:
    """
    Evaluates comprehensive enterprise bot defense across all layers:
    1. Honeypot traps (HTML form or JSON body)
    2. Signed timestamp speed gate (sub-second block)
    3. Content signatures (URLs & wire fraud phrases)
    4. Origin & Referrer domain validation

    Returns: (is_bot: bool, reason: str)
    """
    form_data = extract_request_payload(req)

    # Layer 1: Honeypot Trap (Zero Tolerance)
    clean_hp, hp_reason = check_honeypots(form_data)
    if not clean_hp:
        return True, hp_reason

    # Layer 3: Content Signatures (Spam links, crypto, wire fraud)
    clean_content, content_reason = check_content_signatures(form_data)
    if not clean_content:
        return True, content_reason

    enforce_strict = (
        not current_app.config.get('TESTING')
        or 'form_security_token' in form_data
        or req.headers.get('X-Enforce-Bot-Defense') == '1'
    )

    if enforce_strict:
        # Layer 2: Signed Timestamp Timing Challenge (< 3.0s = Machine Script)
        token = form_data.get('form_security_token')
        valid_speed, speed_reason = validate_form_speed(token)
        if not valid_speed:
            return True, speed_reason

        # Layer 4: Origin & Referrer Domain Authorization
        valid_origin, origin_reason = check_origin(req)
        if not valid_origin:
            return True, origin_reason

    return False, "Human interaction verified"
