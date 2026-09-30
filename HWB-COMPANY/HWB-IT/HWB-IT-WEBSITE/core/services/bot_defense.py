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

# Honeypot field names to inspect across all public forms
HONEYPOT_FIELDS = (
    'hp_organization_url',
    'hp_tax_id',
    'hp_website',
    'business_website_url'
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
    fields_to_scan = ['company', 'name', 'notes', 'comments', 'message', 'facility_type']
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


def evaluate_bot_defense(req: Request) -> Tuple[bool, str]:
    """
    Evaluates comprehensive enterprise bot defense across all layers:
    1. Honeypot traps
    2. Signed timestamp speed gate (sub-second block)
    3. Content signatures (URLs & wire fraud phrases)
    4. Origin & Referrer domain validation

    Returns: (is_bot: bool, reason: str)
    """
    form_data = req.form.to_dict() if req.form else {}

    # Layer 1: Honeypot Trap (Zero Tolerance)
    clean_hp, hp_reason = check_honeypots(form_data)
    if not clean_hp:
        return True, hp_reason

    # Layer 2: Signed Timestamp Timing Challenge (< 3.0s = Machine Script)
    token = form_data.get('form_security_token')
    valid_speed, speed_reason = validate_form_speed(token)
    if not valid_speed:
        return True, speed_reason

    # Layer 3: Content Signatures (Spam links, crypto, wire fraud)
    clean_content, content_reason = check_content_signatures(form_data)
    if not clean_content:
        return True, content_reason

    # Layer 4: Origin & Referrer Domain Authorization
    valid_origin, origin_reason = check_origin(req)
    if not valid_origin:
        return True, origin_reason

    return False, "Human interaction verified"
