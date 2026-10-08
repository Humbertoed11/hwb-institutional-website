"""
SigmaFidelity™ Subcontractor Labor Market Analytics & Wage Intelligence Engine
Standard: HWB-QMS-7.6 (Workforce & Subcontractor Compliance Operations)
Author: George (Systems Architect & mbB)

Calculates real-world market labor rates from incoming 1099 subcontractor
applications, distinguishing between the baseline anchor ($22 - $28/hr)
and custom asking rates to monitor wage pressure against commercial bids.
"""

from typing import Dict, Any, List, Optional, Tuple
import re


BASELINE_MIN = 22.0
BASELINE_MAX = 28.0
BASELINE_MID = 25.0
BASELINE_LABEL = "$22 - $28/hr"
HWB_ESTIMATING_BENCHMARK = 25.00


def parse_rate_entry(raw_rate: Optional[str]) -> Dict[str, Any]:
    """
    Parse a raw rate string from a subcontractor record into structured data.
    Identifies whether the rate is the standard baseline or custom input.
    """
    if not raw_rate:
        return {
            'raw': '',
            'is_baseline': True,
            'min_rate': BASELINE_MIN,
            'max_rate': BASELINE_MAX,
            'mid_rate': BASELINE_MID,
            'display': BASELINE_LABEL
        }

    clean_str = raw_rate.strip()

    # Check for direct match with baseline anchor
    normalized = clean_str.replace(" ", "").lower()
    if normalized in ('$22-$28/hr', '22-28', '$22-$28', '22-28/hr', '$22-$28/hour'):
        return {
            'raw': clean_str,
            'is_baseline': True,
            'min_rate': BASELINE_MIN,
            'max_rate': BASELINE_MAX,
            'mid_rate': BASELINE_MID,
            'display': BASELINE_LABEL
        }

    # Extract numeric values
    numbers = [float(n) for n in re.findall(r'(\d+(?:\.\d+)?)', clean_str)]

    if not numbers:
        return {
            'raw': clean_str,
            'is_baseline': True,
            'min_rate': BASELINE_MIN,
            'max_rate': BASELINE_MAX,
            'mid_rate': BASELINE_MID,
            'display': BASELINE_LABEL
        }

    if len(numbers) >= 2:
        val1, val2 = numbers[0], numbers[1]
        low = min(val1, val2)
        high = max(val1, val2)
        # Verify if it was just typing 22 and 28
        if low == 22.0 and high == 28.0:
            return {
                'raw': clean_str,
                'is_baseline': True,
                'min_rate': 22.0,
                'max_rate': 28.0,
                'mid_rate': 25.0,
                'display': BASELINE_LABEL
            }
        return {
            'raw': clean_str,
            'is_baseline': False,
            'min_rate': low,
            'max_rate': high,
            'mid_rate': round((low + high) / 2.0, 2),
            'display': f"${low:.2f} - ${high:.2f}/hr"
        }

    # Single number (e.g., 29.5 or 15)
    single_val = numbers[0]
    return {
        'raw': clean_str,
        'is_baseline': False,
        'min_rate': single_val,
        'max_rate': single_val,
        'mid_rate': single_val,
        'display': f"${single_val:.2f}/hr"
    }


def analyze_subcontractor_rates(
    subcontractor_records: List[Any],
    estimating_benchmark: float = HWB_ESTIMATING_BENCHMARK
) -> Dict[str, Any]:
    """
    Perform enterprise calculation of subcontractor labor rates.
    Aggregates default acceptance vs explicit custom requests.
    """
    if not subcontractor_records:
        return {
            'total_partners': 0,
            'baseline_count': 0,
            'baseline_pct': 0.0,
            'custom_count': 0,
            'custom_pct': 0.0,
            'custom_avg_rate': 0.0,
            'custom_min_rate': 0.0,
            'custom_max_rate': 0.0,
            'market_min_rate': BASELINE_MIN,
            'market_max_rate': BASELINE_MAX,
            'spread_display': BASELINE_LABEL,
            'blended_market_avg': BASELINE_MID,
            'estimating_benchmark': estimating_benchmark,
            'margin_pressure_status': 'STABLE',
            'status_label': 'Stable / In Budget',
            'status_color': '#059669',
            'status_bg': '#ecfdf5',
            'city_breakdown': {},
            'recent_submissions': []
        }

    total = len(subcontractor_records)
    baseline_count = 0
    custom_records = []
    all_mid_rates = []
    city_map: Dict[str, List[float]] = {}
    parsed_submissions = []

    for r in subcontractor_records:
        # Support dict-like or obj-like access
        if isinstance(r, dict):
            raw_rate = r.get('hourly_rate_range')
            company = r.get('company_name', 'Unknown')
            contact = r.get('contact_name', '')
            city = (r.get('city') or 'DFW').strip()
            sub_id = r.get('id')
            created_at = r.get('created_at')
        else:
            raw_rate = getattr(r, 'hourly_rate_range', None)
            if raw_rate is None and hasattr(r, '__getitem__'):
                try:
                    raw_rate = r['hourly_rate_range']
                except Exception:
                    raw_rate = None
            company = getattr(r, 'company_name', 'Unknown')
            contact = getattr(r, 'contact_name', '')
            city = (getattr(r, 'city', 'DFW') or 'DFW').strip()
            sub_id = getattr(r, 'id', None)
            created_at = getattr(r, 'created_at', None)

        parsed = parse_rate_entry(raw_rate)
        all_mid_rates.append(parsed['mid_rate'])

        if city not in city_map:
            city_map[city] = []
        city_map[city].append(parsed['mid_rate'])

        parsed_submissions.append({
            'id': sub_id,
            'company': company,
            'contact': contact,
            'city': city,
            'raw_rate': raw_rate,
            'display_rate': parsed['display'],
            'is_baseline': parsed['is_baseline'],
            'mid_rate': parsed['mid_rate'],
            'created_at': str(created_at) if created_at else ''
        })

        if parsed['is_baseline']:
            baseline_count += 1
        else:
            custom_records.append(parsed)

    custom_count = len(custom_records)
    baseline_pct = round((baseline_count / total) * 100.0, 1) if total > 0 else 0.0
    custom_pct = round((custom_count / total) * 100.0, 1) if total > 0 else 0.0

    if custom_count > 0:
        custom_mids = [c['mid_rate'] for c in custom_records]
        custom_mins = [c['min_rate'] for c in custom_records]
        custom_maxs = [c['max_rate'] for c in custom_records]
        custom_avg = round(sum(custom_mids) / len(custom_mids), 2)
        custom_min = min(custom_mins)
        custom_max = max(custom_maxs)
    else:
        custom_avg = BASELINE_MID
        custom_min = BASELINE_MIN
        custom_max = BASELINE_MAX

    market_min = min(min([p['min_rate'] for p in [parse_rate_entry(getattr(r, 'hourly_rate_range', None) if not isinstance(r, dict) else r.get('hourly_rate_range')) for r in subcontractor_records]]), BASELINE_MIN)
    market_max = max(max([p['max_rate'] for p in [parse_rate_entry(getattr(r, 'hourly_rate_range', None) if not isinstance(r, dict) else r.get('hourly_rate_range')) for r in subcontractor_records]]), BASELINE_MAX)
    blended_avg = round(sum(all_mid_rates) / len(all_mid_rates), 2) if all_mid_rates else BASELINE_MID

    # Determine margin pressure against HWB project estimating target
    if custom_count > 0:
        rate_to_evaluate = custom_avg
    else:
        rate_to_evaluate = blended_avg

    if rate_to_evaluate <= estimating_benchmark:
        status_code = 'STABLE'
        status_label = 'Stable / In Budget'
        status_color = '#059669'
        status_bg = '#ecfdf5'
    elif rate_to_evaluate <= (estimating_benchmark + 3.00):
        status_code = 'WATCH'
        status_label = 'Notice: Moderate Wage Pressure'
        status_color = '#d97706'
        status_bg = '#fffbeb'
    else:
        status_code = 'ALERT'
        status_label = 'Alert: High Wage Pressure'
        status_color = '#dc2626'
        status_bg = '#fef2f2'

    # Build city breakdown averages
    city_summary = {}
    for c_name, c_rates in city_map.items():
        if c_rates:
            city_summary[c_name] = {
                'count': len(c_rates),
                'avg_rate': round(sum(c_rates) / len(c_rates), 2),
                'min_rate': min(c_rates),
                'max_rate': max(c_rates)
            }

    return {
        'total_partners': total,
        'baseline_count': baseline_count,
        'baseline_pct': baseline_pct,
        'custom_count': custom_count,
        'custom_pct': custom_pct,
        'custom_avg_rate': custom_avg,
        'custom_min_rate': custom_min,
        'custom_max_rate': custom_max,
        'market_min_rate': market_min,
        'market_max_rate': market_max,
        'spread_display': f"${market_min:.2f} — ${market_max:.2f}/hr" if market_min != market_max else f"${market_min:.2f}/hr",
        'blended_market_avg': blended_avg,
        'estimating_benchmark': estimating_benchmark,
        'margin_pressure_status': status_code,
        'status_label': status_label,
        'status_color': status_color,
        'status_bg': status_bg,
        'city_breakdown': city_summary,
        'recent_submissions': parsed_submissions[:10]
    }
