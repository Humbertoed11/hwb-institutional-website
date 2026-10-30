"""
SigmaFidelity™ Inbound Data Sanitization & Enterprise Quality Gateway
Standard: HWB-QMS-7.6 Backend Architecture and Enterprise Standards SOP
Custodians: George (Systems Architect) & Silas Sync (VP of CRM)
"""

import re
from typing import Optional, Union

def clean_phone(raw_phone: Optional[Union[str, int]]) -> Optional[str]:
    """
    Normalizes any phone number string or integer into institutional standard:
    (###)-###-#### or (###)-###-#### ext. <digits>
    Rejects garbage values (e.g., '0', 'NO PHONE', fewer than 10 digits).
    """
    if not raw_phone:
        return None

    raw_str = str(raw_phone).strip()
    if not raw_str or raw_str in {"0", "0000000000", "None", "null"}:
        return None

    # Check for text garbage like 'NO PHONE CALLS'
    if re.search(r'(?i)(no\s*phone|calls\s*accepted|n/?a|none)', raw_str):
        return None

    # Check for extension
    ext_match = re.search(r'(?i)(?:ext|x|extension)[.\s:]*(\d+)', raw_str)
    extension = ext_match.group(1) if ext_match else None

    # Strip extension part from main number if present
    main_part = raw_str
    if ext_match:
        main_part = raw_str[:ext_match.start()]

    digits = re.sub(r'\D', '', main_part)

    # Strip leading US country code 1 if 11 digits
    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]

    # Valid 10-digit North American number
    if len(digits) == 10:
        formatted = f"({digits[:3]})-{digits[3:6]}-{digits[6:]}"
        if extension:
            formatted += f" ext. {extension}"
        return formatted

    # If already formatted or special, return cleaned string if reasonable
    if len(digits) >= 10:
        return f"({digits[:3]})-{digits[3:6]}-{digits[6:10]}"

    return None

def clean_currency(raw_val: Optional[Union[str, int, float]]) -> float:
    """
    Safely sanitizes currency strings ('$12,450.00', '12450') into a pure float.
    """
    if raw_val is None:
        return 0.0
    if isinstance(raw_val, (int, float)):
        return float(raw_val)
    val_str = str(raw_val).strip().replace('$', '').replace(',', '')
    try:
        return float(val_str)
    except (ValueError, TypeError):
        return 0.0

def clean_sqft(raw_val: Optional[Union[str, int, float]]) -> int:
    """
    Safely sanitizes square footage ('12,000 sq ft', '12000') into an integer.
    """
    if raw_val is None:
        return 0
    if isinstance(raw_val, int):
        return raw_val
    if isinstance(raw_val, float):
        return int(raw_val)
    digits = re.sub(r'\D', '', str(raw_val))
    return int(digits) if digits else 0

def clean_zip(raw_zip: Optional[Union[str, int]]) -> Optional[str]:
    """
    Standardizes a US zipcode to 5 digits or Zip+4.
    """
    if not raw_zip:
        return None
    digits = re.sub(r'\D', '', str(raw_zip))
    if len(digits) == 5:
        return digits
    elif len(digits) == 9:
        return f"{digits[:5]}-{digits[5:]}"
    elif len(digits) > 5:
        return digits[:5]
    return digits if digits else None

_PLACEHOLDER_EMAIL_LOCAL_PARTS = {
    'none', 'noemail', 'no-email', 'no_email', 'na', 'n/a', 'null', 'nil',
    'unknown', 'blank', 'empty', 'placeholder', 'dummy', 'fake', '0', '00', '000',
}
_PLACEHOLDER_EMAIL_DOMAINS = {
    'none.com', 'noemail.com', 'no-email.com', 'na.com', 'null.com',
    'unknown.com', 'oooo.com', 'oooo.org', 'oooo.net', '0000.com',
    'fake.com', 'invalid.com', 'placeholder.com', 'dummy.com',
}
_INTERNAL_COMPANY_EMAILS = {
    'hwbcleaning11@gmail.com',
}
_INTERNAL_COMPANY_DOMAINS = {
    'hwbcleaning.com', 'www.hwbcleaning.com',
}


def clean_email(raw_email: Optional[str], allow_internal: bool = False) -> Optional[str]:
    """
    Sanitizes and lowercases an email address while filtering out placeholder values
    (such as '000000000@oooo', 'none@none.com', 'na@na.com') and internal company addresses
    on prospect records unless allow_internal is True.
    """
    if not raw_email:
        return None
    cleaned = str(raw_email).strip().lower()
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', cleaned):
        return None
    local_part, domain_part = cleaned.split('@', 1)
    if local_part in _PLACEHOLDER_EMAIL_LOCAL_PARTS or domain_part in _PLACEHOLDER_EMAIL_DOMAINS:
        return None
    # Reject repeated identical digits/characters such as 000000000@..., 11111@..., aaaaa@...
    stripped_local = re.sub(r'[._+-]', '', local_part)
    if stripped_local and (
        re.match(r'^0+$', stripped_local)
        or (len(stripped_local) >= 4 and len(set(stripped_local)) == 1)
    ):
        return None
    domain_stem = domain_part.split('.', 1)[0]
    if domain_stem and (
        re.match(r'^0+$', domain_stem)
        or (len(domain_stem) >= 3 and len(set(domain_stem)) == 1)
    ):
        return None
    if not allow_internal:
        if cleaned in _INTERNAL_COMPANY_EMAILS or domain_part in _INTERNAL_COMPANY_DOMAINS:
            return None
    return cleaned

def clean_city(raw_city: Optional[str]) -> Optional[str]:
    """
    Poka-Yoke normalization for Texas and North American municipalities.
    Standardizes abbreviation drifts (e.g., 'Ft Worth', 'Ft. Worth' -> 'Fort Worth').
    """
    if not raw_city:
        return None

    city = str(raw_city).strip()
    if not city or city.lower() in {"none", "null", "n/a", "unknown"}:
        return None

    # Replace multiple spaces with a single space
    city = re.sub(r'\s+', ' ', city)

    # Strip trailing state suffix like ', TX' or ' TX' if accidentally typed in city box
    city = re.sub(r'[,\s]+tx\.?$', '', city, flags=re.IGNORECASE).strip()

    # Specific common metropolitan Texas abbreviation mappings
    city_lower = city.lower()
    known_mappings = {
        "ft worth": "Fort Worth",
        "ft. worth": "Fort Worth",
        "ft.worth": "Fort Worth",
        "ftworth": "Fort Worth",
        "arlignton": "Arlington",
        "arlington tx": "Arlington",
        "n richland hills": "North Richland Hills",
        "n. richland hills": "North Richland Hills",
        "n.richland hills": "North Richland Hills",
        "e dallas": "East Dallas",
        "w dallas": "West Dallas",
        "s dallas": "South Dallas",
        "n dallas": "North Dallas",
        "desoto": "DeSoto",
        "de soto": "DeSoto",
        "mcgregor": "McGregor",
        "mc gregor": "McGregor",
        "mccamey": "McCamey",
        "mc camey": "McCamey",
        "mcqueeney": "McQueeney",
        "mc queeney": "McQueeney",
        "mckinney": "McKinney",
        "mcallen": "McAllen",
        "la porte": "La Porte",
        "laporte": "La Porte",
    }

    if city_lower in known_mappings:
        return known_mappings[city_lower]

    # Prefix standardizations: 'Ft.' or 'Ft ' -> 'Fort '
    city = re.sub(r'^ft\.?\s+', 'Fort ', city, flags=re.IGNORECASE)
    city = re.sub(r'^st\.?\s+', 'Saint ', city, flags=re.IGNORECASE)
    city = re.sub(r'^n\.?\s+', 'North ', city, flags=re.IGNORECASE)
    city = re.sub(r'^s\.?\s+', 'South ', city, flags=re.IGNORECASE)
    city = re.sub(r'^e\.?\s+', 'East ', city, flags=re.IGNORECASE)
    city = re.sub(r'^w\.?\s+', 'West ', city, flags=re.IGNORECASE)

    # Standard Title Casing while preserving multi-word capitalization
    words = city.split()
    res = " ".join(w.capitalize() for w in words)
    res = re.sub(r'\bMc([a-z])', lambda m: 'Mc' + m.group(1).upper(), res)
    res = re.sub(r"\bO'([a-z])", lambda m: "O'" + m.group(1).upper(), res)
    res = re.sub(r'-([a-z])', lambda m: '-' + m.group(1).upper(), res)
    return res


def extract_phone_digits(raw_phone: Optional[Union[str, int]]) -> str:
    """
    Extracts canonical 10-digit North American phone digits for deduplication lookups.
    """
    if not raw_phone:
        return ""
    digits = re.sub(r'\D', '', str(raw_phone))
    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]
    return digits[:10] if len(digits) >= 10 else digits


def normalize_business_name(raw_name: Optional[str]) -> str:
    """
    Normalizes a business or entity name for deduplication by lowercasing,
    removing punctuation, and stripping trailing corporate entity suffixes.
    """
    if not raw_name:
        return ""
    cleaned = re.sub(r'[^\w\s]', ' ', str(raw_name).lower())
    cleaned = re.sub(
        r'\b(llc|l l c|inc|incorporated|corp|corporation|co|company|ltd|lp|llp)\b',
        ' ',
        cleaned
    )
    return re.sub(r'\s+', ' ', cleaned).strip()


def merge_comma_list(existing_csv: Optional[str], new_csv: Optional[str]) -> str:
    """
    Combines two comma-separated specialty or tag strings without duplicates,
    preserving the original item casing and order.
    """
    seen = set()
    merged = []
    for source in (existing_csv or "", new_csv or ""):
        for item in str(source).split(","):
            val = item.strip()
            if val and val.lower() not in seen:
                seen.add(val.lower())
                merged.append(val)
    return ", ".join(merged)


_INVALID_EIN_CAMPUS_PREFIXES = {
    "00", "07", "08", "09", "17", "18", "19", "28", "29", "49", "69", "70", "78", "79", "89",
}

_DUMMY_NINE_DIGIT_TINS = {
    "000000000",
    "111111111",
    "222222222",
    "333333333",
    "444444444",
    "555555555",
    "666666666",
    "777777777",
    "888888888",
    "999999999",
    "123456789",
    "987654321",
    "123451234",
}


def resolve_tax_id_mode(
    raw_tin: Optional[str],
    tax_classification: Optional[str] = "LLC",
    tax_id_mode: Optional[str] = None,
) -> str:
    """
    Determines whether a Federal Tax ID should be formatted and validated as
    'ssn' (XXX-XX-XXXX) or 'ein' (XX-XXXXXXX).
    Priority:
    1. Explicit tax_id_mode ('ssn' | 'ein')
    2. Explicit dash pattern in raw_tin (XXX-XX-XXXX / ***-**-XXXX vs XX-XXXXXXX / **-***XXXX)
    3. Tax classification ('Individual / Sole Proprietor' -> 'ssn', otherwise 'ein')
    """
    explicit = str(tax_id_mode or "").strip().lower()
    if explicit in ("ssn", "itin", "ssn_itin"):
        return "ssn"
    if explicit == "ein":
        return "ein"

    s = str(raw_tin or "").strip()
    if re.match(r"^[0-9*•]{3}-[0-9*•]{2}-", s):
        return "ssn"
    if re.match(r"^[0-9*•]{2}-[0-9*•]{3,7}$", s):
        return "ein"

    tc_low = str(tax_classification or "").lower()
    if "individual" in tc_low or "sole" in tc_low:
        return "ssn"
    return "ein"


def clean_ein_or_ssn(
    raw_tin: Optional[str],
    tax_classification: Optional[str] = "LLC",
    tax_id_mode: Optional[str] = None,
) -> Optional[str]:
    """
    Formats a 9-digit Federal Tax ID into canonical EIN (XX-XXXXXXX) or
    SSN (XXX-XX-XXXX) format based on explicit mode, dash pattern, or tax classification,
    while preserving server-masked values (**-***0455 / ***-**-9012).
    """
    if not raw_tin:
        return None
    s = str(raw_tin).strip()
    if not s:
        return None
    if "*" in s or "•" in s:
        return s
    digits = re.sub(r"\D", "", s)
    if not digits:
        return None
    digits = digits[:9]
    mode = resolve_tax_id_mode(s, tax_classification=tax_classification, tax_id_mode=tax_id_mode)
    if len(digits) == 9:
        if mode == "ssn":
            return f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"
        return f"{digits[:2]}-{digits[2:]}"
    return s


def validate_federal_tax_id(
    raw_tin: Optional[str],
    tax_id_mode: Optional[str] = None,
    tax_classification: Optional[str] = "LLC",
    allow_masked_existing: bool = True,
) -> tuple[bool, str, str]:
    """
    Validates a 9-digit Federal Tax ID (EIN or SSN/ITIN) against IRS Publication 1586 /
    CP2100 B-Notice and SSA formatting rules.
    Returns (is_valid, formatted_tin_or_error_message, resolved_mode).
    """
    s = str(raw_tin or "").strip()
    mode = resolve_tax_id_mode(s, tax_classification=tax_classification, tax_id_mode=tax_id_mode)

    if not s:
        return (
            False,
            "Please enter your 9-digit Federal Tax ID (EIN or SSN).",
            mode,
        )

    # Allow preserving an already-masked TIN on file when returning to update other fields
    if allow_masked_existing and ("*" in s or "•" in s):
        tail_digits = re.sub(r"\D", "", s)
        if len(tail_digits) == 4:
            return (True, s, mode)
        return (
            False,
            "Please click 'Change Tax ID' and enter all 9 digits of your EIN or SSN.",
            mode,
        )

    digits = re.sub(r"\D", "", s)
    if len(digits) != 9:
        expected_fmt = "XXX-XX-XXXX" if mode == "ssn" else "XX-XXXXXXX"
        return (
            False,
            f"Federal Tax ID must contain all 9 digits ({expected_fmt}). You entered {len(digits)} digit(s).",
            mode,
        )

    if digits in _DUMMY_NINE_DIGIT_TINS:
        return (
            False,
            "Please enter a valid IRS-issued 9-digit Tax ID (test or sequential numbers like 123-45-6789 are not permitted).",
            mode,
        )

    if mode == "ssn":
        area = digits[:3]
        group = digits[3:5]
        serial = digits[5:]
        if area in ("000", "666") or group == "00" or serial == "0000":
            return (
                False,
                "Invalid Social Security / ITIN number format. Area (first 3 digits) cannot be 000 or 666, and middle/last segments cannot be all zeros.",
                mode,
            )
        formatted = f"{area}-{group}-{serial}"
        return (True, formatted, "ssn")

    # EIN validation
    prefix = digits[:2]
    if prefix in _INVALID_EIN_CAMPUS_PREFIXES:
        return (
            False,
            f"Invalid IRS Employer Identification Number (EIN) prefix '{prefix}'. If you are entering a personal Social Security Number, click 'SSN / ITIN (XXX-XX-XXXX)' above.",
            mode,
        )
    if digits[2:] == "0000000":
        return (
            False,
            "Invalid Employer Identification Number (EIN). The last 7 digits cannot be all zeros.",
            mode,
        )
    formatted = f"{digits[:2]}-{digits[2:]}"
    return (True, formatted, "ein")


def clean_ssn(raw_ssn: Optional[str]) -> Optional[str]:
    """
    Formats a 9-digit Social Security Number into canonical XXX-XX-XXXX format
    while preserving server-masked values (***-**-XXXX).
    """
    return clean_ein_or_ssn(raw_ssn, tax_classification="Individual")


def clean_routing_number(raw_routing: Optional[Union[str, int]]) -> Optional[str]:
    """
    Standardizes a US bank ABA routing number to 9 numeric digits.
    """
    if not raw_routing:
        return None
    digits = re.sub(r"\D", "", str(raw_routing))
    return digits[:9] if digits else None


US_STATES_MAP: dict[str, str] = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "DC": "District of Columbia",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
}

STATE_ALIAS_MAP: dict[str, str] = {
    **{code.lower(): code for code in US_STATES_MAP},
    **{name.lower(): code for code, name in US_STATES_MAP.items()},
    "tejas": "TX",
    "tex": "TX",
    "tx.": "TX",
    "t.x.": "TX",
    "texas, usa": "TX",
    "tx - texas": "TX",
    "tx — texas": "TX",
    "okla": "OK",
    "ok.": "OK",
    "la.": "LA",
    "ark": "AR",
    "n.m.": "NM",
    "new mex": "NM",
    "calif": "CA",
    "fla": "FL",
    "wash": "WA",
    "d.c.": "DC",
    "washington dc": "DC",
    "washington d.c.": "DC",
}

CONSUMER_EMAIL_DOMAINS: set[str] = {
    "gmail.com",
    "yahoo.com",
    "outlook.com",
    "hotmail.com",
    "icloud.com",
    "aol.com",
    "msn.com",
    "live.com",
    "me.com",
    "sbcglobal.net",
    "att.net",
    "comcast.net",
    "verizon.net",
    "protonmail.com",
    "proton.me",
    "ymail.com",
    "mail.com",
    "zoho.com",
}


def clean_state(raw_state: Optional[str], default: str = "TX") -> str:
    """
    Normalizes any US state input ('TX', 'tx', 'Texas', 'Tejas', 'TX.')
    into its canonical 2-letter uppercase USPS state code.
    """
    if not raw_state:
        return default
    s = str(raw_state).strip()
    if not s:
        return default
    # Handle 'TX — Texas' or 'TX - Texas'
    if "—" in s or " - " in s:
        prefix = re.split(r"\s*[—-]\s*", s)[0].strip().upper()
        if prefix in US_STATES_MAP:
            return prefix
    cleaned = re.sub(r"[^a-zA-Z\s.]", "", s).strip().lower()
    cleaned_no_dots = cleaned.replace(".", "").strip()
    if cleaned in STATE_ALIAS_MAP:
        return STATE_ALIAS_MAP[cleaned]
    if cleaned_no_dots in STATE_ALIAS_MAP:
        return STATE_ALIAS_MAP[cleaned_no_dots]
    upper = cleaned_no_dots.upper()
    if len(upper) == 2 and upper in US_STATES_MAP:
        return upper
    return default


def clean_website(
    raw_url: Optional[str],
    fallback_email: Optional[str] = None,
) -> Optional[str]:
    """
    Normalizes a corporate website URL into canonical https:// format, or
    infers the corporate website from a business email address when blank.
    """
    val = str(raw_url or "").strip()
    if val and val.lower() not in {"none", "null", "n/a", "na", "-"}:
        # Strip accidental mailto: or whitespace
        val = re.sub(r"^mailto:", "", val, flags=re.IGNORECASE).strip()
        val = val.split()[0]
        if not re.match(r"^https?://", val, flags=re.IGNORECASE):
            val = "https://" + val.lstrip("/")
        # Lowercase the scheme + host portion
        m = re.match(r"^(https?://)([^/]+)(/.*)?$", val, flags=re.IGNORECASE)
        if m:
            scheme = m.group(1).lower()
            host = m.group(2).lower()
            rest = m.group(3) or ""
            if "." in host and len(host) >= 4:
                return f"{scheme}{host}{rest}"
        return val

    # Attempt fallback inference from corporate email domain
    email_clean = clean_email(fallback_email)
    if email_clean and "@" in email_clean:
        domain = email_clean.split("@", 1)[1].strip().lower()
        if domain and domain not in CONSUMER_EMAIL_DOMAINS and "." in domain:
            if not domain.startswith("www."):
                return f"https://www.{domain}"
            return f"https://{domain}"
    return None


def split_address_lines(
    raw_addr: Optional[str],
    raw_line2: Optional[str] = None,
) -> tuple[str, Optional[str]]:
    """
    USPS Publication 28 secondary unit splitter.
    Extracts Suite / Ste / Bldg / Unit / Apt / Floor / Rm / # from Address Line 1
    into Address Line 2 when Address Line 2 is empty.
    Returns (street_line_1, address_line_2).
    """
    addr1 = re.sub(r"\s+", " ", str(raw_addr or "").strip())
    addr2 = re.sub(r"\s+", " ", str(raw_line2 or "").strip()) or None
    if not addr1:
        return ("", addr2)

    if not addr2:
        pattern = re.compile(
            r"^(.*?)(?:,|\s+)\b("
            r"(?:suite|ste\.?|bldg\.?|building|unit|apt\.?|apartment|fl\.?|floor|rm\.?|room|spc\.?|space)\s*[#a-zA-Z0-9-]+"
            r"|#\s*[a-zA-Z0-9-]+"
            r")\s*$",
            re.IGNORECASE,
        )
        match = pattern.match(addr1)
        if match and match.group(1).strip():
            addr1 = match.group(1).strip().rstrip(",")
            extracted = match.group(2).strip()
            # Normalize 'ste 200' -> 'Suite 200'
            extracted = re.sub(
                r"^ste\.?\s+",
                "Suite ",
                extracted,
                flags=re.IGNORECASE,
            )
            extracted = re.sub(
                r"^bldg\.?\s+",
                "Bldg ",
                extracted,
                flags=re.IGNORECASE,
            )
            addr2 = extracted
    return (addr1, addr2)




