"""
SigmaFidelity™ Advanced Query Engine
Standard: HWB-QMS-11.2 / BUG-065
Custodians: George (Systems Architect) & Silas Sync (VP of CRM)
Enterprise Boolean Logic: AND, OR, NOT, Parentheses, Quoted Phrases, Field Targeting, Numeric & Date Ranges
"""

import os
import re
import time
import threading
import psycopg2
from typing import List, Tuple, Any, Optional, Dict

_SEARCH_META_LOCK = threading.Lock()
_SEARCH_META_CACHE: Dict[str, Any] = {"users": None, "cities": None, "timestamp": 0.0}
_SEARCH_META_TTL = 120.0

# Known DFW / Texas phonetic & spelling variants mapped to canonical city names
TX_CITY_MISSPELLING_MAP: Dict[str, str] = {
    'wiley': 'Wylie',
    'wyley': 'Wylie',
    'carrolton': 'Carrollton',
    'carolton': 'Carrollton',
    'carrollten': 'Carrollton',
    'mckiney': 'McKinney',
    'mckinny': 'McKinney',
    'mac kinney': 'McKinney',
    'lewisvile': 'Lewisville',
    'flower mound': 'Flower Mound',
    'flowermound': 'Flower Mound',
    'ft worth': 'Fort Worth',
    'ft. worth': 'Fort Worth',
    'grand prarie': 'Grand Prairie',
    'grandprairie': 'Grand Prairie',
    'waxahachie': 'Waxahachie',
    'waxahatchie': 'Waxahachie',
    'weatherford': 'Weatherford',
    'burleson': 'Burleson',
    'grapevine': 'Grapevine',
    'southlake': 'Southlake',
    'westlake': 'Westlake',
    'rockwall': 'Rockwall',
    'forney': 'Forney',
    'sachse': 'Sachse',
    'rowlett': 'Rowlett',
    'mesquite': 'Mesquite',
    'desoto': 'DeSoto',
    'cedar hill': 'Cedar Hill',
    'duncanville': 'Duncanville',
    'lancaster': 'Lancaster',
    'coppell': 'Coppell',
    'colleyville': 'Colleyville',
    'euless': 'Euless',
    'bedford': 'Bedford',
    'hurst': 'Hurst',
    'keller': 'Keller',
    'mansfield': 'Mansfield',
    'midlothian': 'Midlothian',
    'prosper': 'Prosper',
    'celina': 'Celina',
    'anna': 'Anna',
    'melissa': 'Melissa',
    'little elm': 'Little Elm',
    'the colony': 'The Colony',
    'farmers branch': 'Farmers Branch',
    'highland park': 'Highland Park',
    'university park': 'University Park',
}


def get_search_entity_metadata() -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Returns cached active system users (id, username, full_name, role) and distinct Texas cities
    so parse_advanced_search can perform zero-latency entity recognition without extra DB round-trips.
    """
    now_ts = time.time()
    with _SEARCH_META_LOCK:
        if (
            _SEARCH_META_CACHE["users"] is not None
            and _SEARCH_META_CACHE["cities"] is not None
            and (now_ts - _SEARCH_META_CACHE["timestamp"]) < _SEARCH_META_TTL
        ):
            return _SEARCH_META_CACHE["users"], _SEARCH_META_CACHE["cities"]

    users: List[Dict[str, Any]] = []
    cities: List[str] = []
    db_url = None
    try:
        from flask import has_app_context, current_app
        if has_app_context():
            db_url = current_app.config.get("DATABASE_URL")
    except Exception:
        pass
    if not db_url:
        try:
            from config import sys_config
            db_url = getattr(sys_config, "DATABASE_URL", None)
        except Exception:
            pass
    if not db_url:
        db_url = os.environ.get("DATABASE_URL")
    if db_url:
        conn = None
        try:
            from core.services.database import get_db
            conn = get_db(db_url)
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT id, username, COALESCE(full_name, \'\') AS full_name, COALESCE(role, \'\') AS role '
                    'FROM "Users" WHERE COALESCE(status, \'Active\') = \'Active\' ORDER BY id ASC'
                )
                for row in cur.fetchall():
                    uid = row['id'] if isinstance(row, dict) else row[0]
                    uname = row['username'] if isinstance(row, dict) else row[1]
                    fname = row['full_name'] if isinstance(row, dict) else row[2]
                    urole = row['role'] if isinstance(row, dict) else row[3]
                    users.append({
                        "id": uid,
                        "username": (uname or "").strip(),
                        "full_name": (fname or "").strip(),
                        "role": (urole or "").strip(),
                    })
                cur.execute(
                    'SELECT DISTINCT city FROM "Leads" '
                    'WHERE city IS NOT NULL AND BTRIM(city) != \'\' '
                    'ORDER BY city ASC LIMIT 500'
                )
                for r in cur.fetchall():
                    c_val = r['city'] if isinstance(r, dict) else r[0]
                    if c_val and str(c_val).strip():
                        cities.append(str(c_val).strip())
        except Exception:
            pass
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    with _SEARCH_META_LOCK:
        if users:
            _SEARCH_META_CACHE["users"] = users
        if cities:
            _SEARCH_META_CACHE["cities"] = cities
        _SEARCH_META_CACHE["timestamp"] = now_ts
    return users or (_SEARCH_META_CACHE["users"] or []), cities or (_SEARCH_META_CACHE["cities"] or [])


def resolve_fuzzy_tx_city(raw_city: str, known_cities: Optional[List[str]] = None) -> Optional[str]:
    """
    Resolves common Texas city spelling variants (e.g. 'Wiley' -> 'Wylie', 'Carrolton' -> 'Carrollton')
    without false-positive collisions.
    """
    clean = (raw_city or "").strip().lower()
    if not clean:
        return None
    if clean in TX_CITY_MISSPELLING_MAP:
        return TX_CITY_MISSPELLING_MAP[clean]
    if known_cities:
        for kc in known_cities:
            if kc.lower() == clean:
                return kc
    return None


def parse_advanced_search(search_q: str, view: str = 'leads') -> Tuple[List[str], List[Any]]:
    """
    Parses advanced search query strings into SQL WHERE clauses and parameters with full enterprise boolean logic.
    Supports:
    - Boolean operators: AND, OR, NOT, &&, ||, ! (case-insensitive, e.g. 'plano and child care center', 'plano or frisco')
    - Grouped expressions: (plano OR frisco) AND "child care center"
    - Exact phrases: "Child Care Center", "North Texas"
    - Field targeting: city:Plano, industry:Child, status:New, rep:Wiley
    - Numeric comparisons & ranges: sqf:>=10000, sqf:<20000, value:>50000
    - Negative exclusions: -Church, -"School District", NOT Church
    - Wildcards: Pla*
    - American dates: 04/10/2026 -> 2026-04-10
    - Entity Shorthand format: GC-#014, GC-14, IB-#001, ACC-#003, LD-#1842, #14
    - Fault-tolerant parsing: unclosed quotes and unbalanced parentheses auto-balance safely without 500 errors
    """
    if not search_q or not search_q.strip():
        return [], []

    search_q = search_q.strip()

    def normalize_date(val: str) -> str:
        m = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{4})$', val)
        if m:
            month, day, year = m.groups()
            return f'{year}-{int(month):02d}-{int(day):02d}'
        return val

    # Configure field maps and general search columns by view
    if view in ('leads', 'sales_desk'):
        field_map = {
            'city': ('city', 'text'),
            'state': ('state', 'text'),
            'zip': ('zipcode', 'text'),
            'zipcode': ('zipcode', 'text'),
            'industry': ('industry', 'text'),
            'facility': ('facility_type', 'text'),
            'facility_type': ('facility_type', 'text'),
            'status': ('status', 'text'),
            'sqf': ('sqf', 'num'),
            'capacity': ('capacity', 'num'),
            'value': ('estimated_annual_value', 'num'),
            'revenue': ('estimated_annual_value', 'num'),
            'source': ('lead_source', 'text'),
            'contact': ('decision_maker', 'text'),
            'dm': ('decision_maker', 'text'),
            'director': ('director', 'text'),
            'company': ('center_name', 'text'),
            'name': ('center_name', 'text'),
            'phone': ('phone', 'text'),
            'email': ('email', 'text'),
            'address': ('address', 'text'),
            'umbrella': ('umbrella_name', 'text'),
            'tier': ('acquisition_tier', 'text'),
            'm_and_a': ('acquisition_tier', 'text'),
            'ownership': ('ownership_type', 'text'),
            'rep': ('owner_id', 'user_ref'),
            'owner': ('owner_id', 'user_ref'),
            'date': ('input_date', 'date'),
            'created': ('input_date', 'date'),
            'input_date': ('input_date', 'date'),
            'id': ('id', 'num'),
            'ld': ('id', 'num'),
        }
        general_cols = [
            'center_name', 'facility_type', 'city', 'state', 'zipcode', 
            'phone', 'email', 'address', 'lead_source', 'decision_maker', 
            'status', 'umbrella_name', 'acquisition_tier', 'ownership_type'
        ]
        user_table_fk = 'owner_id'

    elif view == 'accounts':
        field_map = {
            'city': ('c.city', 'text'),
            'state': ('c.state', 'text'),
            'zip': ('c.zip', 'text'),
            'company': ('c.company_name', 'text'),
            'name': ('c.company_name', 'text'),
            'phone': ('c.phone', 'text'),
            'email': ('c.email', 'text'),
            'address': ('c.company_address', 'text'),
            'revenue': ('c.annual_revenue', 'num'),
            'value': ('c.annual_revenue', 'num'),
            'status': ('c.status', 'text'),
            'sqf': ('c.sqf', 'num'),
            'contact': ('c.contact_person_name', 'text'),
            'umbrella': ('c.umbrella_name', 'text'),
            'notes': ('c.notes', 'text'),
            'rep': ('c.assigned_rep_id', 'user_ref'),
            'owner': ('c.assigned_rep_id', 'user_ref'),
            'id': ('c.customer_id', 'num'),
            'acc': ('c.customer_id', 'num'),
        }
        general_cols = [
            'c.company_name', 'c.company_address', 'c.city', 'c.state', 'c.zip',
            'c.phone', 'c.email', 'c.contact_person_name', 'c.umbrella_name', 'c.notes'
        ]
        user_table_fk = 'c.assigned_rep_id'

    elif view == 'institutional_bids':
        field_map = {
            'solicitation': ('ib.solicitation_number', 'text'),
            'number': ('ib.solicitation_number', 'text'),
            'title': ('ib.title', 'text'),
            'project': ('ib.title', 'text'),
            'name': ('ib.title', 'text'),
            'agency': ('ib.agency_name', 'text'),
            'officer': ('ib.procurement_officer', 'text'),
            'status': ('ib.status', 'text'),
            'value': ('ib.published_budget', 'num'),
            'budget': ('ib.published_budget', 'num'),
            'due': ('ib.bid_due_date', 'date'),
            'date': ('ib.bid_due_date', 'date'),
            'id': ('ib.id', 'num'),
            'ib': ('ib.id', 'num'),
        }
        general_cols = [
            'ib.solicitation_number', 'ib.title', 'ib.agency_name', 'ib.procurement_officer', 'ib.status'
        ]
        user_table_fk = None

    elif view == 'general_contractors':
        field_map = {
            'company': ('gc.company_name', 'text'),
            'name': ('gc.company_name', 'text'),
            'estimator': ('gc.lead_estimator_name', 'text'),
            'city': ('gc.city', 'text'),
            'state': ('gc.state', 'text'),
            'zip': ('gc.zipcode', 'text'),
            'market': ('gc.primary_market', 'text'),
            'phone': ('gc.lead_estimator_phone', 'text'),
            'email': ('gc.lead_estimator_email', 'text'),
            'status': ('gc.sos_status', 'text'),
            'tier': ('gc.vetting_tier', 'text'),
            'score': ('gc.vetting_score', 'num'),
            'id': ('gc.id', 'num'),
            'gc': ('gc.id', 'num'),
        }
        general_cols = [
            'gc.company_name', 'gc.city', 'gc.primary_market', 'gc.lead_estimator_name', 'gc.lead_estimator_email', 'gc.lead_estimator_phone'
        ]
        user_table_fk = None

    elif view == 'programs':
        field_map = {
            'code': ('program_code', 'text'),
            'name': ('program_name', 'text'),
            'program': ('program_name', 'text'),
            'agency': ('sponsoring_agency', 'text'),
            'jurisdiction': ('jurisdiction', 'text'),
            'status': ('status', 'text'),
            'naics': ('primary_naics', 'text'),
            'score': ('readiness_score', 'num'),
            'id': ('id', 'num'),
        }
        general_cols = [
            'program_code', 'program_name', 'sponsoring_agency', 'jurisdiction', 'status', 'primary_naics'
        ]
        user_table_fk = None

    else:  # construction_bids
        field_map = {
            'project': ('cb.project_name', 'text'),
            'name': ('cb.project_name', 'text'),
            'company': ('cb.project_name', 'text'),
            'gc': ('cb.gc_name', 'text'),
            'status': ('cb.status', 'text'),
            'sqf': ('cb.cleanable_sqft', 'num'),
            'value': ('cb.estimated_value', 'num'),
            'location': ('cb.city', 'text'),
            'city': ('cb.city', 'text'),
            'address': ('cb.project_address', 'text'),
            'platform': ('cb.platform', 'text'),
            'estimator': ('cb.estimator_name', 'text'),
            'phone': ('cb.estimator_phone', 'text'),
            'email': ('cb.estimator_email', 'text'),
            'scope': ('cb.scope_phase', 'text'),
            'date': ('cb.bid_due_date', 'date'),
            'due': ('cb.bid_due_date', 'date'),
            'rep': ('cb.assigned_rep_id', 'user_ref'),
            'owner': ('cb.assigned_rep_id', 'user_ref'),
            'id': ('cb.id', 'num'),
            'bid': ('cb.id', 'num'),
        }
        general_cols = [
            'cb.project_name', 'cb.gc_name', 'cb.city', 'cb.project_address',
            'cb.platform', 'cb.estimator_name', 'cb.estimator_phone', 'cb.estimator_email', 'cb.scope_phase'
        ]
        user_table_fk = 'cb.assigned_rep_id'

    known_users, known_cities = get_search_entity_metadata()

    # Pre-normalize search_q for exact user full-name recognition, unquoted rep:First Last, and Texas city spell-correction
    # 1. Convert unquoted `rep:First Last` or `owner:First Last` where First Last matches a known user's full_name into `rep:"First Last"`
    for u in known_users:
        fn = (u.get("full_name") or "").strip()
        un = (u.get("username") or "").strip()
        if fn and " " in fn:
            # Match explicit prefix `rep:Beabe Wiley` or `owner:Beabe Wiley`
            search_q = re.sub(
                rf'\b(rep|owner):{re.escape(fn)}\b',
                lambda m: f'{m.group(1)}:"{fn}"',
                search_q,
                flags=re.IGNORECASE,
            )
            # Match standalone multi-word full name `beabe wiley` -> `rep:"Beabe Wiley"` when user_table_fk is active
            if user_table_fk:
                search_q = re.sub(
                    rf'(?<![:"\w])\b{re.escape(fn)}\b(?![:"\w])',
                    f'rep:"{fn}"',
                    search_q,
                    flags=re.IGNORECASE,
                )
        if un and len(un) >= 4 and user_table_fk:
            # Match exact non-dictionary username (e.g. `bwiley`, `hdominguez`, `mrondinella`)
            if un.lower() not in ('admin', 'sales', 'custom', 'operator'):
                search_q = re.sub(
                    rf'(?<![:"\w])\b{re.escape(un)}\b(?![:"\w])',
                    f'rep:"{un}"',
                    search_q,
                    flags=re.IGNORECASE,
                )

    # 2. Normalize `<city_variant>, TX` or `<city_variant> TX` (e.g. `wiley tx` -> `city:Wylie state:TX`)
    def _replace_tx_city_pattern(match: re.Match) -> str:
        raw_c = match.group(1).strip().rstrip(',').strip()
        canonical_city = resolve_fuzzy_tx_city(raw_c, known_cities)
        if canonical_city:
            return f'city:"{canonical_city}" state:TX'
        return match.group(0)

    search_q = re.sub(
        r'(?<![:"\w])\b([a-zA-Z]+(?:\s+[a-zA-Z]+)?)\s*,?\s+\b(?:TX|Texas)\b',
        _replace_tx_city_pattern,
        search_q,
        flags=re.IGNORECASE,
    )

    def compile_leaf(token_str: str) -> Tuple[Optional[str], List[Any]]:
        # 1. Field Targeting (field:op?val)
        m_field = re.match(r'^([a-zA-Z_]+):(>=|<=|>|<|=)?(\"[^\"]*\"?|[^\s]+)$', token_str)
        if m_field:
            f_key = m_field.group(1).lower()
            op = m_field.group(2) or '='
            raw_val = m_field.group(3).strip('\"')
            if f_key in field_map:
                col, col_type = field_map[f_key]
                if col_type == 'num':
                    clean_val = re.sub(r'[^0-9.]', '', raw_val)
                    if clean_val:
                        valid_op = op if op in ['>=', '<=', '>', '<', '='] else '='
                        return f'{col} {valid_op} %s', [float(clean_val)]
                    return None, []
                elif col_type == 'date':
                    norm_date = normalize_date(raw_val)
                    if '*' in norm_date:
                        return f'{col}::text LIKE %s', [norm_date.replace('*', '%')]
                    valid_op = op if op in ['>=', '<=', '>', '<', '='] else '='
                    return f'{col}::date {valid_op} %s::date', [norm_date]
                elif col_type == 'user_ref' and user_table_fk:
                    if raw_val.lower() in ('unassigned', 'none', 'null', 'open'):
                        return f'{user_table_fk} IS NULL', []
                    if raw_val.isdigit():
                        return f'{user_table_fk} = %s', [int(raw_val)]
                    pat = f'%{raw_val}%'
                    return f'{user_table_fk} IN (SELECT id FROM "Users" WHERE full_name ILIKE %s OR username ILIKE %s)', [pat, pat]
                elif f_key in ('city', 'location'):
                    canonical_city = resolve_fuzzy_tx_city(raw_val, known_cities)
                    if canonical_city and canonical_city.lower() != raw_val.lower():
                        return f'({col} ILIKE %s OR {col} ILIKE %s)', [f'%{raw_val}%', f'%{canonical_city}%']
                    pat = raw_val.replace('*', '%') if '*' in raw_val else f'%{raw_val}%'
                    return f'{col} ILIKE %s', [pat]
                elif f_key in ('phone', 'estimator_phone'):
                    digits = re.sub(r'\D', '', raw_val)
                    if len(digits) >= 4:
                        return f"({col} ILIKE %s OR regexp_replace(COALESCE({col}, ''), '\\D', '', 'g') ILIKE %s)", [f"%{raw_val}%", f"%{digits}%"]
                    pat = raw_val.replace('*', '%') if '*' in raw_val else f'%{raw_val}%'
                    return f'{col} ILIKE %s', [pat]
                else:
                    pat = raw_val.replace('*', '%') if '*' in raw_val else f'%{raw_val}%'
                    return f'{col} ILIKE %s', [pat]
            else:
                pat = token_str.replace('*', '%') if '*' in token_str else f'%{token_str}%'
                sub = ' OR '.join([f'{c} ILIKE %s' for c in general_cols])
                return f'({sub})', [pat] * len(general_cols)

        # 2. Negation (-val or -"phrase")
        if token_str.startswith('-') and len(token_str) > 1:
            neg_val = token_str[1:].strip('\"')
            neg_pat = f'%{neg_val}%'
            sub = ' AND '.join([f'COALESCE({c}::text, \'\') NOT ILIKE %s' for c in general_cols])
            return f'({sub})', [neg_pat] * len(general_cols)

        # 3. Exact Quoted Phrase ("phrase")
        if token_str.startswith('\"'):
            exact_val = token_str.strip('\"')
            if exact_val:
                exact_pat = rf'\y{re.escape(exact_val)}\y'
                sub = ' OR '.join([f'{c} ~* %s' for c in general_cols])
                return f'({sub})', [exact_pat] * len(general_cols)
            return None, []

        # 4. Entity Shorthand ID (GC-#014, GC-14, IB-#001, ACC-#003, LD-#1842, #14)
        id_prefix_match = re.match(r'^(?:(?:gc|ib|acc|ld|app|cand|wo|vet)[-#]*)(\d+)$', token_str, re.I)
        raw_hash_match = re.match(r'^#(\d+)$', token_str)
        target_id = None
        if id_prefix_match:
            target_id = int(id_prefix_match.group(1))
        elif raw_hash_match:
            target_id = int(raw_hash_match.group(1))

        if target_id is not None:
            if view in ('leads', 'sales_desk'):
                return 'id = %s', [target_id]
            elif view == 'accounts':
                return 'customer_id = %s', [target_id]
            elif view == 'construction_bids':
                return 'cb.id = %s', [target_id]
            elif view == 'institutional_bids':
                return 'ib.id = %s', [target_id]
            elif view == 'general_contractors':
                return 'gc.id = %s', [target_id]
            elif view == 'programs':
                return 'id = %s', [target_id]

        # 5. Date formatted keyword (e.g. 04/10/2026)
        norm_date = normalize_date(token_str)
        if norm_date != token_str:
            sub = ' OR '.join([f'{c}::text ILIKE %s' for c in general_cols])
            return f'({sub})', [f'%{norm_date}%'] * len(general_cols)

        # 6. Phone pattern
        if re.search(r'^\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$', token_str) or (token_str.isdigit() and len(token_str) >= 7):
            digits = re.sub(r'\D', '', token_str)
            phone_cols = [c for c in general_cols if 'phone' in c]
            sub_parts = [f'{c} ILIKE %s' for c in general_cols]
            if phone_cols:
                sub_parts.extend([f"regexp_replace(COALESCE({c}, ''), '\\D', '', 'g') ILIKE %s" for c in phone_cols])
                return f"({' OR '.join(sub_parts)})", [f'%{token_str}%'] * len(general_cols) + [f'%{digits}%'] * len(phone_cols)
            return f"({' OR '.join(sub_parts)})", [f'%{token_str}%'] * len(general_cols)

        # 7. Standard keyword across general columns
        w_pat = token_str.replace('*', '%') if '*' in token_str else f'%{token_str}%'
        sub = ' OR '.join([f'{c} ILIKE %s' for c in general_cols])
        return f'({sub})', [w_pat] * len(general_cols)

    # Tokenize input string
    raw_pattern = r'(\(|\)|\"[^\"]*\"?|-[a-zA-Z0-9_\"]+|[a-zA-Z_]+:(?:>=|<=|>|<|=)?(?:\"[^\"]*\"?|[^\s()]+)|[^\s()]+)'
    raw_matches = re.finditer(raw_pattern, search_q)
    tokens = []
    for m in raw_matches:
        text = m.group(1).strip()
        if not text:
            continue
        upper = text.upper()
        if text == '(':
            tokens.append(('LPAREN', '('))
        elif text == ')':
            tokens.append(('RPAREN', ')'))
        elif upper in ('AND', '&&'):
            tokens.append(('AND', 'AND'))
        elif upper in ('OR', '||'):
            tokens.append(('OR', 'OR'))
        elif upper in ('NOT', '!') and not text.startswith('-'):
            tokens.append(('NOT', 'NOT'))
        else:
            tokens.append(('TERM', text))

    # Insert implicit AND between adjacent operands
    tokens_with_and = []
    for i, tok in enumerate(tokens):
        tokens_with_and.append(tok)
        if i + 1 < len(tokens):
            next_tok = tokens[i + 1]
            curr_can_end = tok[0] in ('TERM', 'RPAREN')
            next_can_start = next_tok[0] in ('TERM', 'LPAREN', 'NOT')
            if curr_can_end and next_can_start:
                tokens_with_and.append(('AND', 'AND'))

    # Recursive-Descent Parser
    class QueryParser:
        def __init__(self, tok_list):
            self.tokens = tok_list
            self.pos = 0

        def peek(self):
            if self.pos < len(self.tokens):
                return self.tokens[self.pos]
            return None

        def consume(self):
            tok = self.peek()
            if tok:
                self.pos += 1
            return tok

        def parse(self):
            if not self.tokens:
                return None
            return self.parse_or()

        def parse_or(self):
            left = self.parse_and()
            while True:
                tok = self.peek()
                if tok and tok[0] == 'OR':
                    self.consume()
                    right = self.parse_and()
                    if right and left:
                        left = ('OR', left, right)
                    elif right:
                        left = right
                else:
                    break
            return left

        def parse_and(self):
            left = self.parse_not()
            while True:
                tok = self.peek()
                if tok and tok[0] == 'AND':
                    self.consume()
                    right = self.parse_not()
                    if right and left:
                        left = ('AND', left, right)
                    elif right:
                        left = right
                else:
                    break
            return left

        def parse_not(self):
            tok = self.peek()
            if tok and tok[0] == 'NOT':
                self.consume()
                operand = self.parse_not()
                if operand:
                    return ('NOT', operand)
                return None
            return self.parse_primary()

        def parse_primary(self):
            tok = self.peek()
            if not tok:
                return None
            if tok[0] == 'LPAREN':
                self.consume()
                sub = self.parse_or()
                if self.peek() and self.peek()[0] == 'RPAREN':
                    self.consume()
                return sub
            elif tok[0] == 'TERM':
                self.consume()
                return ('TERM', tok[1])
            else:
                self.consume()
                return self.parse_primary()

    parser = QueryParser(tokens_with_and)
    root = parser.parse()
    if not root:
        return [], []

    def compile_node(node) -> Tuple[Optional[str], List[Any]]:
        if not node:
            return None, []
        ntype = node[0]
        if ntype == 'TERM':
            return compile_leaf(node[1])
        elif ntype == 'NOT':
            sql, params = compile_node(node[1])
            if sql:
                if 'NOT ILIKE' in sql and not sql.startswith('(NOT'):
                    return sql, params
                return f'(NOT ({sql}))', params
            return None, []
        elif ntype == 'AND':
            l_sql, l_p = compile_node(node[1])
            r_sql, r_p = compile_node(node[2])
            if l_sql and r_sql:
                return f'({l_sql} AND {r_sql})', l_p + r_p
            return l_sql or r_sql, l_p + r_p
        elif ntype == 'OR':
            l_sql, l_p = compile_node(node[1])
            r_sql, r_p = compile_node(node[2])
            if l_sql and r_sql:
                return f'({l_sql} OR {r_sql})', l_p + r_p
            return l_sql or r_sql, l_p + r_p
        return None, []

    sql, params = compile_node(root)
    if sql:
        return [sql], params
    return [], []
