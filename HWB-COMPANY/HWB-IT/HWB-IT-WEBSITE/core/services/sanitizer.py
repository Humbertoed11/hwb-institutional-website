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

def clean_email(raw_email: Optional[str]) -> Optional[str]:
    """
    Sanitizes and lowercases email address.
    """
    if not raw_email:
        return None
    cleaned = str(raw_email).strip().lower()
    if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', cleaned):
        return cleaned
    return None

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

    # Specific common metropolitan Texas abbreviation mappings
    city_lower = city.lower()
    known_mappings = {
        "ft worth": "Fort Worth",
        "ft. worth": "Fort Worth",
        "ft.worth": "Fort Worth",
        "ftworth": "Fort Worth",
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

