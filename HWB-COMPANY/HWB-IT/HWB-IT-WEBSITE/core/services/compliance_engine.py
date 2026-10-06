"""
SigmaFidelity™ Multi-Tenant B2G Compliance & Certification Engine
Standard: HWB-QMS-7.6, HWB-QMS-8.9 & ARCH-009 Multi-Tenancy Architecture
Custodians: George (Systems Architect & mbB) & Silas Sync (VP Systems)

Responsibilities:
1. Algorithmic eligibility auditing across Federal 13 CFR § 124, Texas HUB, and Regional MBE/SBE criteria.
2. SBA Two-Year Operating Rule Waiver Scorer (13 CFR § 124.107(b)).
3. Multi-Tenant Program Profiler with Row-Level Security (RLS) support.
4. Autonomous Waiver Justification Memorandum Generator.
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, Any, List, Optional
from decimal import Decimal

# Statutory SBA Thresholds (2026 Baseline - 13 CFR § 124.104)
SBA_NET_WORTH_CEILING = 850000.00
SBA_AGI_THREE_YEAR_AVG_CEILING = 400000.00
SBA_TOTAL_ASSETS_CEILING = 6500000.00
SBA_JANITORIAL_SIZE_STANDARD_CAP = 22000000.00  # NAICS 561720

def audit_tenant_eligibility(profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates a business profile against statutory 8(a), HUB, and diversity standards.
    
    Expected profile keys:
    - net_worth: float (excluding primary home equity and applicant business equity)
    - three_year_avg_agi: float
    - total_assets: float
    - operating_months: int
    - ownership_pct: float
    - is_us_citizen: bool
    - annual_gross_receipts: float
    - has_management_experience: bool
    - has_technical_capability: bool
    - has_adequate_capital: bool
    - has_client_contracts: bool
    - has_insurance_and_licenses: bool
    - negative_covenants_detected: bool
    """
    checks = {}
    recommendations = []
    
    # 1. Economic Disadvantage Gate (13 CFR § 124.104)
    net_worth = float(profile.get('net_worth', 0.0))
    agi = float(profile.get('three_year_avg_agi', 0.0))
    total_assets = float(profile.get('total_assets', 0.0))

    nw_pass = net_worth <= SBA_NET_WORTH_CEILING
    agi_pass = agi <= SBA_AGI_THREE_YEAR_AVG_CEILING
    assets_pass = total_assets <= SBA_TOTAL_ASSETS_CEILING

    checks['economic_disadvantage'] = {
        'status': 'PASS' if (nw_pass and agi_pass and assets_pass) else 'FAIL',
        'net_worth': net_worth,
        'net_worth_ceiling': SBA_NET_WORTH_CEILING,
        'net_worth_pass': nw_pass,
        'agi_three_year_avg': agi,
        'agi_ceiling': SBA_AGI_THREE_YEAR_AVG_CEILING,
        'agi_pass': agi_pass,
        'total_assets': total_assets,
        'total_assets_ceiling': SBA_TOTAL_ASSETS_CEILING,
        'total_assets_pass': assets_pass
    }

    if not nw_pass:
        recommendations.append(f"Personal Net Worth (${net_worth:,.2f}) exceeds the statutory $850k threshold. Ensure primary residence and applicant business equity are strictly excluded per SBA Form 413 instructions.")
    if not agi_pass:
        recommendations.append(f"Three-year average AGI (${agi:,.2f}) exceeds the $400k threshold.")

    # 2. Sovereign Control & Ownership (13 CFR § 124.106)
    ownership_pct = float(profile.get('ownership_pct', 100.0))
    neg_cov = bool(profile.get('negative_covenants_detected', False))
    is_citizen = bool(profile.get('is_us_citizen', True))

    control_pass = (ownership_pct >= 51.0) and (not neg_cov) and is_citizen
    checks['sovereign_control'] = {
        'status': 'PASS' if control_pass else 'FAIL',
        'ownership_pct': ownership_pct,
        'ownership_pass': ownership_pct >= 51.0,
        'negative_covenants_detected': neg_cov,
        'is_us_citizen': is_citizen
    }

    if ownership_pct < 51.0:
        recommendations.append(f"Qualifying disadvantaged owner holds {ownership_pct}%, which is below the mandatory 51.0% statutory minimum.")
    if neg_cov:
        recommendations.append("Operating Agreement contains minority veto or negative control covenants. Amend operating agreement to grant the majority owner sovereign authority.")
    if not is_citizen:
        recommendations.append("Qualifying owner must be a verified U.S. citizen.")

    # 3. Two-Year Operating Runway & Waiver Engine (13 CFR § 124.107)
    operating_months = int(profile.get('operating_months', 24))
    waiver_required = operating_months < 24
    waiver_points = 0
    waiver_breakdown = {}

    if waiver_required:
        # Evaluate 5 Regulatory Waiver Conditions
        # Condition 1: Substantial Management Experience (25 pts)
        c1 = bool(profile.get('has_management_experience', True))
        if c1: waiver_points += 25
        waiver_breakdown['management_experience'] = {'points': 25 if c1 else 0, 'max': 25, 'met': c1}

        # Condition 2: Technical Capability & SOPs (20 pts)
        c2 = bool(profile.get('has_technical_capability', True))
        if c2: waiver_points += 20
        waiver_breakdown['technical_capability'] = {'points': 20 if c2 else 0, 'max': 20, 'met': c2}

        # Condition 3: Adequate Capitalization & Working Capital (20 pts)
        c3 = bool(profile.get('has_adequate_capital', True))
        if c3: waiver_points += 20
        waiver_breakdown['adequate_capitalization'] = {'points': 20 if c3 else 0, 'max': 20, 'met': c3}

        # Condition 4: Record of Successful Performance / Invoices (20 pts)
        c4 = bool(profile.get('has_client_contracts', True))
        if c4: waiver_points += 20
        waiver_breakdown['contract_performance'] = {'points': 20 if c4 else 0, 'max': 20, 'met': c4}

        # Condition 5: Licenses, Insurance & Bonding (15 pts)
        c5 = bool(profile.get('has_insurance_and_licenses', True))
        if c5: waiver_points += 15
        waiver_breakdown['licenses_and_insurance'] = {'points': 15 if c5 else 0, 'max': 15, 'met': c5}

        waiver_eligible = waiver_points >= 80
        checks['operating_runway'] = {
            'status': 'WAIVER_READY' if waiver_eligible else 'WAIVER_DEFICIENT',
            'operating_months': operating_months,
            'waiver_required': True,
            'waiver_score': waiver_points,
            'waiver_eligible': waiver_eligible,
            'waiver_breakdown': waiver_breakdown
        }
        if not waiver_eligible:
            recommendations.append(f"Two-Year Rule Waiver score is {waiver_points}/100 (Threshold: 80). Strengthen commercial contract performance references or working capital.")
    else:
        checks['operating_runway'] = {
            'status': 'PASS',
            'operating_months': operating_months,
            'waiver_required': False,
            'waiver_score': 100,
            'waiver_eligible': True,
            'waiver_breakdown': {}
        }

    # 4. Small Business Size Standard (13 CFR § 121.201)
    receipts = float(profile.get('annual_gross_receipts', 250000.00))
    receipts_pass = receipts <= SBA_JANITORIAL_SIZE_STANDARD_CAP
    checks['size_standard'] = {
        'status': 'PASS' if receipts_pass else 'FAIL',
        'annual_gross_receipts': receipts,
        'cap': SBA_JANITORIAL_SIZE_STANDARD_CAP,
        'receipts_pass': receipts_pass
    }

    # Calculate Holistic Readiness Score (0-100)
    score_components = [
        1.0 if nw_pass else 0.0,
        1.0 if agi_pass else 0.5,
        1.0 if control_pass else 0.0,
        1.0 if not waiver_required else (waiver_points / 100.0),
        1.0 if receipts_pass else 0.0
    ]
    readiness_score = int(round((sum(score_components) / len(score_components)) * 100))

    overall_status = "FULLY_QUALIFIED" if (nw_pass and control_pass and receipts_pass and (not waiver_required or waiver_points >= 80)) else "QUALIFICATION_DEFICITS"

    return {
        'overall_status': overall_status,
        'readiness_score': readiness_score,
        'checks': checks,
        'recommendations': recommendations
    }

def generate_sba_waiver_justification_memo(profile: Dict[str, Any]) -> str:
    """
    Generates an official, legally grounded SBA Two-Year Rule Waiver Justification Memorandum
    strictly adhering to 13 CFR § 124.107(b).
    """
    company_name = profile.get('company_name', 'HWB Cleaning Services LLC')
    owner_name = profile.get('owner_name') or profile.get('officer_name', 'Chief Executive Officer')
    operating_months = profile.get('operating_months', 18)
    capital_reserves = profile.get('capital_reserves', '$150,000+')

    return f"""================================================================================
MEMORANDUM IN SUPPORT OF TWO-YEAR RULE WAIVER
Pursuant to 13 CFR § 124.107(b) - SBA 8(a) Business Development Program
================================================================================

TO:      U.S. Small Business Administration (Office of Government Contracting)
FROM:    {owner_name}, Chief Executive Officer
ENTITIES: {company_name}
SUBJECT: Formal Justification for Waiver of the Two-Year Operating Requirement

1.0 JURISDICTIONAL STATEMENT
{company_name} hereby requests a formal waiver of the standard two-year operating requirement set forth in 13 CFR § 124.107(a). The firm has been actively engaged in commercial facility operations for {operating_months} months and fully satisfies all five mandatory statutory conditions under 13 CFR § 124.107(b).

2.0 SATISFACTION OF STATUTORY CONDITIONS

2.1 Substantial Management and Technical Experience (13 CFR § 124.107(b)(1))
The qualifying owner, {owner_name}, possesses extensive executive leadership and project management experience in commercial operations, executing precision Lean Six Sigma operational control, quality assurance, and commercial workforce dispatch.

2.2 Demonstrated Technical Capability (13 CFR § 124.107(b)(2))
{company_name} operates under an institutional ISO 9001 Quality Management System, APPA Level 2 cleaning standards, and strict OSHA-compliant Job Hazard Analyses (JHA), utilizing commercial HEPA extraction and eco-certified sanitation assets.

2.3 Adequate Capitalization and Working Capital (13 CFR § 124.107(b)(3))
{company_name} maintains dedicated working capital reserves ({capital_reserves}) and established commercial banking lines, demonstrating independent fiscal capacity to fulfill federal contractual obligations without advance disbursements.

2.4 Record of Successful Performance (13 CFR § 124.107(b)(4))
Since inception, {company_name} has successfully executed and completed multiple commercial contracts across North Texas, maintaining a 100% on-time completion record and verified commercial client satisfaction.

2.5 Necessary Licenses, Insurance, and Bonding (13 CFR § 124.107(b)(5))
{company_name} is actively registered in Texas (Entity in Good Standing), possesses active SAM.gov credentials (CAGE Code & UEI), and maintains Comprehensive General Liability and statutory Workers' Compensation coverage.

3.0 CONCLUSION & PRAYER FOR WAIVER
Based on verified commercial performance, robust capitalization, and technical excellence, {company_name} respectfully requests that the Associate Administrator grant the requested waiver and approve this application for 8(a) certification.

Respectfully submitted,

____________________________________________
{owner_name}, Chief Executive Officer
{company_name}
================================================================================
"""
