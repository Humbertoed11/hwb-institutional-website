"""
SigmaFidelity™ Advanced Query Engine
Standard: HWB-QMS-11.2 / BUG-065
Custodians: George (Systems Architect) & Silas Sync (VP of CRM)
"""

import re
from typing import List, Tuple, Any


def parse_advanced_search(search_q: str, view: str = 'leads') -> Tuple[List[str], List[Any]]:
    """
    Parses advanced search query strings into SQL WHERE clauses and parameters.
    Supports:
    - Field targeting: city:Plano, industry:Child, status:New, rep:Wiley
    - Numeric comparisons & ranges: sqf:>=10000, sqf:<20000, value:>50000
    - Negative exclusions: -Church, -"School District"
    - Exact phrases: "North Texas"
    - Wildcards: Pla*
    - American dates: 04/10/2026 -> 2026-04-10
    - General keywords across primary text columns
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
            'city': ('city', 'text'),
            'state': ('state', 'text'),
            'zip': ('zip', 'text'),
            'company': ('company_name', 'text'),
            'name': ('company_name', 'text'),
            'phone': ('phone', 'text'),
            'email': ('email', 'text'),
            'address': ('company_address', 'text'),
            'revenue': ('annual_revenue', 'num'),
            'value': ('annual_revenue', 'num'),
            'status': ('status', 'text'),
            'industry': ('facility_type', 'text'),
            'facility': ('facility_type', 'text'),
            'building': ('facility_type', 'text'),
            'contact': ('contact_person_name', 'text'),
            'umbrella': ('c.umbrella_name', 'text'),
            'rep': ('c.assigned_rep_id', 'user_ref'),
            'owner': ('c.assigned_rep_id', 'user_ref'),
            'id': ('customer_id', 'num'),
            'acc': ('customer_id', 'num'),
        }
        general_cols = [
            'company_name', 'company_address', 'city', 'state', 'zip',
            'phone', 'email', 'contact_person_name', 'facility_type', 'c.umbrella_name'
        ]
        user_table_fk = 'c.assigned_rep_id'

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
            'id': ('cb.id', 'num'),
            'bid': ('cb.id', 'num'),
        }
        general_cols = [
            'cb.project_name', 'cb.gc_name', 'cb.city', 'cb.project_address',
            'cb.platform', 'cb.estimator_name', 'cb.estimator_phone', 'cb.estimator_email', 'cb.scope_phase'
        ]
        user_table_fk = None

    pattern = r'(?P<field>[a-zA-Z_]+):(?P<op>>=|<=|>|<|=)?(?P<fval>\"[^\"]+\"|[^\s]+)|-(?P<neg>\"[^\"]+\"|[^\s]+)|\"(?P<exact>[^\"]+)\"|(?P<word>[^\s]+)'
    
    where_clauses: List[str] = []
    params: List[Any] = []

    for m in re.finditer(pattern, search_q):
        d = m.groupdict()
        if d['field']:
            f_key = d['field'].lower()
            op = d['op'] or '='
            val = d['fval'].strip('\"')
            
            if f_key in field_map:
                col, col_type = field_map[f_key]
                if col_type == 'num':
                    clean_val = re.sub(r'[^0-9.]', '', val)
                    if clean_val:
                        valid_op = op if op in ['>=', '<=', '>', '<', '='] else '='
                        where_clauses.append(f'{col} {valid_op} %s')
                        params.append(float(clean_val))
                elif col_type == 'date':
                    norm_date = normalize_date(val)
                    if '*' in norm_date:
                        where_clauses.append(f'{col}::text LIKE %s')
                        params.append(norm_date.replace('*', '%'))
                    else:
                        valid_op = op if op in ['>=', '<=', '>', '<', '='] else '='
                        where_clauses.append(f'{col}::date {valid_op} %s::date')
                        params.append(norm_date)
                elif col_type == 'user_ref' and user_table_fk:
                    if val.isdigit():
                        where_clauses.append(f'{user_table_fk} = %s')
                        params.append(int(val))
                    else:
                        pat = f'%{val}%'
                        where_clauses.append(f'{user_table_fk} IN (SELECT id FROM "Users" WHERE full_name ILIKE %s OR username ILIKE %s)')
                        params.extend([pat, pat])
                elif f_key in ('phone', 'estimator_phone'):
                    digits = re.sub(r'\D', '', val)
                    if len(digits) >= 4:
                        where_clauses.append(f"({col} ILIKE %s OR regexp_replace(COALESCE({col}, ''), '\\D', '', 'g') ILIKE %s)")
                        params.extend([f"%{val}%", f"%{digits}%"])
                    else:
                        pat = val.replace('*', '%') if '*' in val else f'%{val}%'
                        where_clauses.append(f'{col} ILIKE %s')
                        params.append(pat)
                else:
                    pat = val.replace('*', '%') if '*' in val else f'%{val}%'
                    where_clauses.append(f'{col} ILIKE %s')
                    params.append(pat)
            else:
                full_token = m.group(0)
                pat = full_token.replace('*', '%') if '*' in full_token else f'%{full_token}%'
                sub = ' OR '.join([f'{c} ILIKE %s' for c in general_cols])
                where_clauses.append(f'({sub})')
                params.extend([pat] * len(general_cols))
                
        elif d['neg']:
            neg_val = d['neg'].strip('\"')
            neg_pat = f'%{neg_val}%'
            sub = ' AND '.join([f'COALESCE({c}::text, \'\') NOT ILIKE %s' for c in general_cols])
            where_clauses.append(f'({sub})')
            params.extend([neg_pat] * len(general_cols))
            
        elif d['exact']:
            exact_val = d['exact']
            exact_pat = rf'\y{re.escape(exact_val)}\y'
            sub = ' OR '.join([f'{c} ~* %s' for c in general_cols])
            where_clauses.append(f'({sub})')
            params.extend([exact_pat] * len(general_cols))
            
        elif d['word']:
            w = d['word']
            norm_date = normalize_date(w)

            # Check for Entity Shorthand format: GC-#014, GC-14, IB-#001, ACC-#003, LD-#1842, #14, etc.
            id_prefix_match = re.match(r'^(?:(?:gc|ib|acc|ld|app|cand|wo|vet)[-#]*)(\d+)$', w, re.I)
            raw_hash_match = re.match(r'^#(\d+)$', w)
            target_id = None
            if id_prefix_match:
                target_id = int(id_prefix_match.group(1))
            elif raw_hash_match:
                target_id = int(raw_hash_match.group(1))

            if target_id is not None:
                if view in ('leads', 'sales_desk'):
                    where_clauses.append('id = %s')
                    params.append(target_id)
                elif view == 'accounts':
                    where_clauses.append('customer_id = %s')
                    params.append(target_id)
                elif view == 'construction_bids':
                    where_clauses.append('cb.id = %s')
                    params.append(target_id)
            elif norm_date != w:
                sub = ' OR '.join([f'{c}::text ILIKE %s' for c in general_cols])
                where_clauses.append(f'({sub})')
                params.extend([f'%{norm_date}%'] * len(general_cols))
            elif re.search(r'^\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$', w) or (w.isdigit() and len(w) >= 7):
                digits = re.sub(r'\D', '', w)
                phone_cols = [c for c in general_cols if 'phone' in c]
                sub_parts = [f'{c} ILIKE %s' for c in general_cols]
                if phone_cols:
                    sub_parts.extend([f"regexp_replace(COALESCE({c}, ''), '\\D', '', 'g') ILIKE %s" for c in phone_cols])
                    where_clauses.append(f"({' OR '.join(sub_parts)})")
                    params.extend([f'%{w}%'] * len(general_cols) + [f'%{digits}%'] * len(phone_cols))
                else:
                    where_clauses.append(f"({' OR '.join(sub_parts)})")
                    params.extend([f'%{w}%'] * len(general_cols))
            else:
                w_pat = w.replace('*', '%') if '*' in w else f'%{w}%'
                sub = ' OR '.join([f'{c} ILIKE %s' for c in general_cols])
                where_clauses.append(f'({sub})')
                params.extend([w_pat] * len(general_cols))

    return where_clauses, params
