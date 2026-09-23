"""
SigmaFidelity™ Unified Estimating & Bidding Engine (SigmaEstimator™)
Standard: HWB-QMS-7.7 Commercial Construction Takeoff & Estimating Engine SOP
Custodians: George (Systems Architect & mbB) & Silas Sync (VP Systems)

Three-Tier Calculation Architecture:
1. Tier 1: Commercial GC Subcontract Takeoffs (Unit Production Rates + Phase Multipliers)
2. Tier 2: Public / Municipal Institutional Bids (State Co-ops, TIPS, Burdened Labor + G&A)
3. Tier 3: Federal Solicitations (McNamara-O'Hara Service Contract Act - SCA Wage Determinations)
"""

from typing import Dict, Any, Optional
import os
import psycopg2
from decimal import Decimal, ROUND_HALF_UP

# Default statutory burden rate: FICA (7.65%), SUTA (2.70%), FUTA (0.60%), WC Code 9014 (4.85%), GL (4.20%)
DEFAULT_BURDEN_RATE = 0.2000

# Standard annual full-time productive hours
STANDARD_ANNUAL_HOURS = 2080.0

def _to_currency(val: float) -> float:
    return float(Decimal(str(val)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

def get_sca_wage_determination(
    county: str = "Collin",
    occupation: str = "Janitor / Custodian",
    db_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Queries ScaWageDeterminations in PostgreSQL to fetch binding DOL wage floors.
    Falls back to DFW Metro baseline (WD 2015-5231) if county match is not found.
    """
    target_url = db_url or os.getenv("DATABASE_URL")
    default_record = {
        "wd_number": "2015-5231",
        "revision_number": 25,
        "state": "TX",
        "counties": "Collin, Dallas, Denton, Tarrant",
        "occupation_code": "11150",
        "occupation_title": occupation,
        "base_hourly_wage": 16.54,
        "health_welfare_hourly": 4.98,
        "health_welfare_eo13706": 4.98,
        "health_welfare_standard": 5.36,
        "paid_holidays_count": 11,
        "vacation_rules": "2 weeks paid after 1 year",
        "source": "Default DFW Metro Baseline"
    }

    if not target_url:
        return default_record

    try:
        conn = psycopg2.connect(target_url)
        with conn.cursor() as cur:
            clean_county = county.strip().lower()
            cur.execute('''
                SELECT wd_number, revision_number, state, counties, occupation_code,
                       occupation_title, base_hourly_wage, health_welfare_hourly,
                       health_welfare_eo13706, health_welfare_standard,
                       paid_holidays_count, vacation_rules, notes
                FROM "ScaWageDeterminations"
                WHERE LOWER(counties) LIKE %s AND LOWER(occupation_title) LIKE %s
                LIMIT 1;
            ''', (f"%{clean_county}%", f"%{occupation.strip().lower()}%"))
            row = cur.fetchone()
            if not row:
                # Try occupation match alone
                cur.execute('''
                    SELECT wd_number, revision_number, state, counties, occupation_code,
                           occupation_title, base_hourly_wage, health_welfare_hourly,
                           health_welfare_eo13706, health_welfare_standard,
                           paid_holidays_count, vacation_rules, notes
                    FROM "ScaWageDeterminations"
                    WHERE LOWER(occupation_title) LIKE %s
                    LIMIT 1;
                ''', (f"%{occupation.strip().lower()}%",))
                row = cur.fetchone()

            if row:
                return {
                    "wd_number": row[0],
                    "revision_number": row[1],
                    "state": row[2],
                    "counties": row[3],
                    "occupation_code": row[4],
                    "occupation_title": row[5],
                    "base_hourly_wage": float(row[6]),
                    "health_welfare_hourly": float(row[7]),
                    "health_welfare_eo13706": float(row[8]),
                    "health_welfare_standard": float(row[9]),
                    "paid_holidays_count": int(row[10]),
                    "vacation_rules": row[11],
                    "notes": row[12],
                    "source": f"DOL WD {row[0]} Rev {row[1]}"
                }
        conn.close()
    except Exception:
        pass

    return default_record

COMMERCIAL_GC_SAFEGUARDS = {
    "trade_stacking_clause": "This proposal includes one (1) continuous cleaning pass per contracted phase. Any re-cleaning required due to dust, foot traffic, or work performed by subsequent construction trades, punch-list repairs, or HVAC commissioning shall be billed as an extra at HWB's contractual change-order rate of $38.50 per man-hour.",
    "dry_run_fee_clause": "If HWB mobilizes to the site as scheduled and the facility is not broom-clean and clear of conflicting trades, a $450.00 Trip / Failed Mobilization Fee applies.",
    "tempered_glass_waiver": "HWB utilizes micro-bevel stainless steel blades and specialized slip agents. HWB is not liable for existing scratches or microscopic fabricating debris fused onto heat-strengthened or tempered glass during manufacturing.",
    "site_utility_preconditions": "Bid assumes continuous 110V/20A electrical power within 50 feet of work areas, domestic hot and cold running water, adequate overhead lighting, and operational climate-controlled HVAC (68°F–78°F for proper floor finish curing) are provided continuously by the General Contractor at zero cost to subcontractor.",
    "dumpster_disposal_clause": "Bid includes transporting job debris to on-site dumpsters provided by the General Contractor located within 150 feet of the building entrance. Off-site hauling or dedicated dumpster rental, if required, shall be billed as an extra at $750.00 per 30-yard container.",
    "explicit_exclusions": [
        "No removal of paint, concrete, or mortar from anodized aluminum window mullions (risk of chemical etching).",
        "No exterior masonry efflorescence removal or chemical acid washing.",
        "No cleaning inside energized high-voltage electrical switchgear, server racks, or air duct interiors.",
        "No hazardous materials, asbestos, lead, or medical sharps disposal.",
        "No carpet stretching, floor moisture mitigation, or subfloor repairs."
    ]
}

STANDARD_BID_SAFEGUARDS = COMMERCIAL_GC_SAFEGUARDS

INSTITUTIONAL_SAFEGUARDS = {
    "texas_prevailing_wage_statute": "Compliant with Texas Government Code Chapter 2258. Prevailing wage rates verified against local public body schedule. Mandatory statutory notice: underpayment subject to statutory penalty of $60.00 per worker per calendar day pursuant to § 2258.023.",
    "texas_prompt_pay_statute": "Governed by Texas Government Code Chapter 2251 (Prompt Payment Act). Subcontractor payment mandated within 10 days of prime contractor receiving payment from political subdivision or university system.",
    "educator_badging_fast_pass": "Technicians assigned to K-12 or higher education facilities adhere to Texas Education Code § 22.0834 FAST fingerprint and statutory background checks through the Texas Department of Public Safety (DPS) FACT Clearinghouse.",
    "chemical_environmental_standards": "All daily cleaning products are certified Green Seal GS-37 / GS-40, EcoLogo, or EPA Safer Choice, compliant with LEED v4.1 Operations & Maintenance and Texas state environmental purchasing directives.",
    "osha_safety_compliance": "Full adherence to OSHA 29 CFR 1910 General Industry Standards, including Hazard Communication standard (29 CFR 1910.1200), Bloodborne Pathogens standard (29 CFR 1910.1030), and facility-specific safety orientation."
}

DALLAS_MUNICIPAL_BENCHMARKS = {
    "citywide_master_agreement": {
        "solicitation_number": "CSP-BYZ25-00028708",
        "council_file": "26-1944A",
        "prime_contractor": "Ambassador Services LLC",
        "council_approval_date": "2026-06-24",
        "total_valuation": 45780678.43,
        "base_five_year": 32046741.44,
        "renewal_options_two_year": 13733936.99,
        "monthly_pool": 763011.31,
        "proposer_count": 37,
        "mandatory_mwbe_pct": 0.2380,  # 23.8% BEH Mandate
        "mandatory_mwbe_pool_total": 10895801.47,
        "mandatory_mwbe_monthly_pool": 181596.69,
        "scoring_weights": {
            "cost": 25,
            "experience": 25,
            "qualifications": 25,
            "work_plan": 20,
            "local_preference": 5
        }
    },
    "frem_14_facilities_agreement": {
        "council_file": "25-0471",
        "council_item": 39,
        "prime_contractor": "Ambassador Services LLC",
        "council_approval_date": "2025-03-26",
        "term_months": 36,
        "facilities_count": 14,
        "total_valuation": 1928263.80,
        "annual_run_rate": 642754.60,
        "monthly_run_rate": 53562.88,
        "monthly_per_facility_avg": 3825.92
    },
    "dallas_living_wage_floor": 18.00,
    "fast_track_discretionary_threshold": 50000.00  # Texas Local Gov Code § 252.0215
}


FEDERAL_SCA_SAFEGUARDS = {
    "mcnamara_ohara_sca_clause": "Governed by 41 U.S.C. 6701 et seq. (Service Contract Act) and FAR 52.222-41. Base wages and mandatory fringe benefits strictly bound by the U.S. Department of Labor Wage Determination cited in CLIN 0001 schedule.",
    "cwhssa_overtime_clause": "Compliant with Contract Work Hours and Safety Standards Act (40 U.S.C. 3701 et seq.). Overtime compensated at 1.5x regular base rate for all hours in excess of 40 hours per workweek. Acknowledged statutory liquidated damages penalty of $31.00 per worker per day for non-compliance.",
    "executive_order_13706": "Adheres to Executive Order 13706 (Establishing Paid Sick Leave for Federal Contractors). Cleaners accrue 1 hour of paid sick leave for every 30 hours worked, up to 56 hours (7 days) annually, usable for personal illness or family care.",
    "executive_order_14026": "Certified compliance with Executive Order 14026 (Increasing the Minimum Wage for Federal Contractors) establishing minimum wage floor for covered federal contracts.",
    "copeland_anti_kickback": "Compliant with the Copeland Anti-Kickback Act (40 U.S.C. 3145 and 18 U.S.C. 874), prohibiting inducements to give up any part of rightful worker compensation.",
    "usda_biopreferred_mandate": "Custodial chemicals and paper products comply with Federal BioPreferred and EPA Comprehensive Procurement Guidelines (CPG) pursuant to FAR 52.223-1 and FAR 52.223-2.",
    "e_verify_homeland_security": "Mandatory E-Verify employment eligibility verification per FAR 52.222-54 for all contractor and subcontractor personnel performing on federal installation.",
    "davis_bacon_threshold_notice": "Routine custodial operations are SCA covered. If scope includes post-construction final cleaning on a federal construction project, work converts to Davis-Bacon Act (29 CFR 5.2(j)) craft wages requiring weekly Certified Payroll submittals (Form WH-347)."
}

def calculate_commercial_gc_bid(
    cleanable_sqft: float,
    scope_phase: str = "Rough, Final & Touch-Up Clean",
    num_floors: int = 1,
    has_high_glass: bool = False,
    lift_rental: float = 0.0,
    target_margin: float = 0.20,
    negotiation_buffer: float = 0.04,
    walkaway_margin: float = 0.16,
    urban_logistics: bool = False,
    retainage_float: bool = False,
    offsite_trash_hauling: bool = False
) -> Dict[str, Any]:
    """
    Tier 1: Commercial General Contractor Subcontract Proposal.
    Calculates unit rates, phase breakdown, equipment passes, target margins,
    negotiation buffers (buyout protection), and contractual safeguards.
    """
    cleanable_sqft = max(0.0, float(cleanable_sqft))
    
    # Base production rates per square foot
    rate_table = {
        "Final Only": 0.16,
        "Rough & Final Clean": 0.24,
        "Rough, Final & Touch-Up Clean": 0.30
    }
    base_unit_rate = rate_table.get(scope_phase, 0.30)
    
    # Multi-floor vertical logistics surcharge (above 2 floors)
    floor_factor = 1.0 + (max(0, num_floors - 2) * 0.03)
    adjusted_unit_rate = base_unit_rate * floor_factor

    # Phase Breakdown
    rough_clean_val = _to_currency(cleanable_sqft * 0.10) if "Rough" in scope_phase else 0.0
    final_clean_val = _to_currency(cleanable_sqft * 0.16)
    touchup_clean_val = _to_currency(cleanable_sqft * 0.04) if "Touch-Up" in scope_phase else 0.0
    high_glass_val = 450.00 if has_high_glass else 0.00

    subtotal_services = rough_clean_val + final_clean_val + touchup_clean_val + high_glass_val

    # Cost Build-up (COGS)
    estimated_hours = (cleanable_sqft / 1200.0) * (2.2 if "Rough" in scope_phase else 1.0)
    direct_labor_cost = _to_currency(estimated_hours * 18.50) # $18.50 burdened crew rate
    consumables_cost = _to_currency(cleanable_sqft * 0.015)
    equipment_cost = _to_currency(cleanable_sqft * 0.01) + lift_rental

    # Optional Urban Logistics & Trash Alternates
    estimated_days = max(1.0, round(estimated_hours / 32.0, 1))
    parking_logistics_cost = (estimated_days * 150.00) if urban_logistics else 0.00
    dumpster_haul_cost = 750.00 if offsite_trash_hauling else 0.00
    retainage_float_cost = _to_currency(subtotal_services * 0.015) if retainage_float else 0.00

    total_cogs = direct_labor_cost + consumables_cost + equipment_cost + parking_logistics_cost + dumpster_haul_cost + retainage_float_cost

    # Fixed G&A Overhead (4.5%)
    ga_overhead = _to_currency(total_cogs * 0.045)
    cost_basis = total_cogs + ga_overhead

    # Negotiation Triad Build-Up
    # 1. Published Submittal Price (Target Margin + Negotiation Buffer, e.g. 24%)
    published_submittal = _to_currency(cost_basis / (1.0 - (target_margin + negotiation_buffer)))
    # 2. Authorized Close Price (Standard Target Margin, e.g. 20%)
    authorized_close = _to_currency(cost_basis / (1.0 - target_margin))
    # 3. Walk-Away Floor (Absolute Red-Line Floor, e.g. 16%)
    walkaway_floor = _to_currency(cost_basis / (1.0 - walkaway_margin))

    gross_profit = _to_currency(published_submittal - total_cogs)
    actual_margin = (gross_profit / published_submittal) if published_submittal > 0 else 0.0

    return {
        "tier": "Commercial GC",
        "cleanable_sqft": cleanable_sqft,
        "scope_phase": scope_phase,
        "num_floors": num_floors,
        "base_unit_rate": round(base_unit_rate, 4),
        "effective_unit_rate": round(published_submittal / cleanable_sqft, 4) if cleanable_sqft > 0 else 0.0,
        "rough_clean_total": rough_clean_val,
        "final_clean_total": final_clean_val,
        "touchup_clean_total": touchup_clean_val,
        "high_glass_total": high_glass_val,
        "lift_rental": lift_rental,
        "submittal_total": published_submittal,
        "negotiation_triad": {
            "published_submittal_price": published_submittal,
            "published_margin_pct": round((target_margin + negotiation_buffer) * 100, 2),
            "authorized_field_close_price": authorized_close,
            "authorized_margin_pct": round(target_margin * 100, 2),
            "walkaway_floor_price": walkaway_floor,
            "walkaway_floor_margin_pct": round(walkaway_margin * 100, 2),
            "buyout_discount_cushion_dollars": _to_currency(published_submittal - authorized_close)
        },
        "cogs": {
            "estimated_labor_hours": round(estimated_hours, 1),
            "estimated_shift_days": estimated_days,
            "direct_labor_cost": direct_labor_cost,
            "consumables_cost": consumables_cost,
            "equipment_cost": equipment_cost,
            "urban_logistics_parking": parking_logistics_cost,
            "offsite_trash_hauling": dumpster_haul_cost,
            "retainage_float_cost": retainage_float_cost,
            "ga_overhead": ga_overhead,
            "total_direct_cogs": total_cogs
        },
        "gross_profit": gross_profit,
        "margin_percentage": round(actual_margin * 100, 2),
        "safeguards": STANDARD_BID_SAFEGUARDS
    }

def calculate_institutional_bid(
    cleanable_sqft: float,
    mandated_weekly_hours: float = 40.0,
    term_months: int = 24,
    day_porters: int = 1,
    night_custodians: int = 2,
    base_hourly_rate: float = 16.00,
    sup_hourly_rate: float = 18.50,
    supply_monthly: float = 500.0,
    equipment_monthly: float = 350.0,
    target_margin: float = 0.18,
    negotiation_buffer: float = 0.03,
    walkaway_margin: float = 0.14
) -> Dict[str, Any]:
    """
    Tier 2: Public / Municipal Institutional Subcontract Proposal.
    Calculates multi-building campus labor, statutory burden, G&A overhead,
    negotiation triads for institutional procurement, and net EBITDA.
    """
    cleanable_sqft = max(0.0, float(cleanable_sqft))
    mandated_weekly_hours = max(1.0, float(mandated_weekly_hours))
    monthly_hours = (mandated_weekly_hours * 52.0) / 12.0
    annual_hours = mandated_weekly_hours * 52.0

    # Blended wage rate based on staffing mix
    total_staff = max(1, day_porters + night_custodians)
    cleaner_hours_share = (total_staff - 0.5) / total_staff
    blended_base_wage = (base_hourly_rate * cleaner_hours_share) + (sup_hourly_rate * (1.0 - cleaner_hours_share))

    # Monthly Base Wages
    monthly_base_labor = _to_currency(monthly_hours * blended_base_wage)
    # Payroll Burden (20.0%: FICA 7.65%, SUTA 2.7%, FUTA 0.6%, WC 4.85%, GL 4.2%)
    monthly_labor_burden = _to_currency(monthly_base_labor * DEFAULT_BURDEN_RATE)
    total_monthly_labor = monthly_base_labor + monthly_labor_burden

    # Direct Monthly COGS
    monthly_cogs = total_monthly_labor + supply_monthly + equipment_monthly

    # Fixed G&A Overhead Allocations (QMS management, HR recruiting, bonding, software)
    monthly_ga_overhead = _to_currency(monthly_cogs * 0.055)
    cost_basis = monthly_cogs + monthly_ga_overhead

    # Negotiation Triad Build-Up
    published_monthly = _to_currency(cost_basis / (1.0 - (target_margin + negotiation_buffer)))
    authorized_monthly = _to_currency(cost_basis / (1.0 - target_margin))
    walkaway_monthly = _to_currency(cost_basis / (1.0 - walkaway_margin))

    monthly_subcontract_submittal = published_monthly
    annual_subcontract_submittal = _to_currency(monthly_subcontract_submittal * 12.0)
    contract_total = _to_currency(monthly_subcontract_submittal * term_months)

    monthly_gross_profit = _to_currency(monthly_subcontract_submittal - monthly_cogs)
    monthly_net_profit = _to_currency(monthly_gross_profit - monthly_ga_overhead)
    actual_margin = (monthly_net_profit / monthly_subcontract_submittal) if monthly_subcontract_submittal > 0 else 0.0

    return {
        "tier": "Institutional Public Sector",
        "cleanable_sqft": cleanable_sqft,
        "contract_term_months": term_months,
        "mandated_weekly_hours": mandated_weekly_hours,
        "monthly_hours": round(monthly_hours, 1),
        "annual_hours": round(annual_hours, 1),
        "blended_hourly_wage": round(blended_base_wage, 2),
        "hourly_billing_rate": round(monthly_subcontract_submittal / monthly_hours, 2) if monthly_hours > 0 else 0.0,
        "negotiation_triad": {
            "published_submittal_monthly": published_monthly,
            "published_submittal_annual": _to_currency(published_monthly * 12.0),
            "published_contract_total": _to_currency(published_monthly * term_months),
            "published_margin_pct": round((target_margin + negotiation_buffer) * 100, 2),
            "authorized_field_close_monthly": authorized_monthly,
            "authorized_close_annual": _to_currency(authorized_monthly * 12.0),
            "authorized_contract_total": _to_currency(authorized_monthly * term_months),
            "authorized_margin_pct": round(target_margin * 100, 2),
            "walkaway_floor_monthly": walkaway_monthly,
            "walkaway_floor_annual": _to_currency(walkaway_monthly * 12.0),
            "walkaway_contract_total": _to_currency(walkaway_monthly * term_months),
            "walkaway_floor_margin_pct": round(walkaway_margin * 100, 2),
            "monthly_discount_cushion": _to_currency(published_monthly - authorized_monthly),
            "contract_discount_cushion": _to_currency((published_monthly - authorized_monthly) * term_months)
        },
        "monthly_breakdown": {
            "base_labor": monthly_base_labor,
            "payroll_burden_20pct": monthly_labor_burden,
            "total_labor": total_monthly_labor,
            "consumable_supplies": supply_monthly,
            "equipment_amortization": equipment_monthly,
            "total_direct_cogs": monthly_cogs,
            "ga_overhead_allocation": monthly_ga_overhead,
            "subcontract_submittal": monthly_subcontract_submittal,
            "net_ebitda_profit": monthly_net_profit
        },
        "annual_submittal": annual_subcontract_submittal,
        "contract_total_value": contract_total,
        "net_margin_percentage": round(actual_margin * 100, 2),
        "safeguards": INSTITUTIONAL_SAFEGUARDS
    }

def calculate_municipal_cluster_bid(
    num_facilities: int = 14,
    cleanable_sqft_per_facility: float = 10000.0,
    days_per_week: int = 5,
    custodians_per_facility: float = 1.0,
    hours_per_day_per_custodian: float = 4.0,
    hourly_wage: float = 18.00,
    contract_term_months: int = 36,
    supply_per_facility_monthly: float = 150.0,
    equipment_per_facility_monthly: float = 100.0,
    target_margin: float = 0.18,
    negotiation_buffer: float = 0.03,
    walkaway_margin: float = 0.14,
    is_mwbe_subcontract: bool = True
) -> Dict[str, Any]:
    """
    Tier 2b: Municipal Multi-Facility Campus/Cluster Proposal.
    Calculates multi-facility municipal cluster pricing calibrated against
    City of Dallas empirical benchmarks (Council Files 26-1944A & 25-0471).
    Enforces the Dallas Living Wage floor ($18.00/hr) and models M/WBE carve-outs.
    """
    num_fac = max(1, int(num_facilities))
    sqft_per_fac = max(100.0, float(cleanable_sqft_per_facility))
    total_sqft = sqft_per_fac * num_fac
    wage = max(18.00, float(hourly_wage))

    # Weekly hours per facility = days * hours_per_day * custodians
    weekly_hours_per_fac = days_per_week * hours_per_day_per_custodian * custodians_per_facility
    total_weekly_hours = weekly_hours_per_fac * num_fac
    monthly_hours = (total_weekly_hours * 52.0) / 12.0
    annual_hours = total_weekly_hours * 52.0

    # Labor Costs
    monthly_base_labor = _to_currency(monthly_hours * wage)
    monthly_labor_burden = _to_currency(monthly_base_labor * DEFAULT_BURDEN_RATE)
    total_monthly_labor = monthly_base_labor + monthly_labor_burden

    # Supplies & Equipment Amortization across cluster
    monthly_supplies = _to_currency(supply_per_facility_monthly * num_fac)
    monthly_equipment = _to_currency(equipment_per_facility_monthly * num_fac)
    total_cogs = total_monthly_labor + monthly_supplies + monthly_equipment

    # G&A Overhead (5.5% for operations supervision, digital quality audits, bonding)
    monthly_ga = _to_currency(total_cogs * 0.055)
    cost_basis = total_cogs + monthly_ga

    # Negotiation Triads
    published_monthly = _to_currency(cost_basis / (1.0 - (target_margin + negotiation_buffer)))
    authorized_monthly = _to_currency(cost_basis / (1.0 - target_margin))
    walkaway_monthly = _to_currency(cost_basis / (1.0 - walkaway_margin))

    published_per_facility_mo = _to_currency(published_monthly / num_fac)
    authorized_per_facility_mo = _to_currency(authorized_monthly / num_fac)
    walkaway_per_facility_mo = _to_currency(walkaway_monthly / num_fac)

    contract_total = _to_currency(published_monthly * contract_term_months)
    annual_total = _to_currency(published_monthly * 12.0)
    monthly_net_profit = _to_currency(published_monthly - cost_basis)

    # Empirical Variance against City of Dallas FREM Benchmark ($3,825.92 / fac / mo)
    empirical_dal_fac_benchmark = DALLAS_MUNICIPAL_BENCHMARKS["frem_14_facilities_agreement"]["monthly_per_facility_avg"]
    fac_rate_variance = _to_currency(authorized_per_facility_mo - empirical_dal_fac_benchmark)
    fac_rate_variance_pct = round(((authorized_per_facility_mo - empirical_dal_fac_benchmark) / empirical_dal_fac_benchmark) * 100.0, 2)

    # Ambassador Master Agreement M/WBE Pool Share (23.8% = $181,596.69 / mo)
    mwbe_monthly_pool = DALLAS_MUNICIPAL_BENCHMARKS["citywide_master_agreement"]["mandatory_mwbe_monthly_pool"]
    mwbe_pool_consumption_pct = round((authorized_monthly / mwbe_monthly_pool) * 100.0, 2)

    return {
        "tier": "Municipal Cluster (Empirical Calibration)",
        "cluster_summary": {
            "facilities_count": num_fac,
            "cleanable_sqft_per_facility": sqft_per_fac,
            "total_cleanable_sqft": total_sqft,
            "days_per_week": days_per_week,
            "total_monthly_hours": round(monthly_hours, 1),
            "effective_sqft_monthly_rate": round(published_monthly / total_sqft, 4) if total_sqft > 0 else 0.0,
            "contract_term_months": contract_term_months
        },
        "pricing_per_facility": {
            "published_monthly": published_per_facility_mo,
            "authorized_field_close_monthly": authorized_per_facility_mo,
            "walkaway_floor_monthly": walkaway_per_facility_mo
        },
        "pricing_cluster_totals": {
            "published_monthly": published_monthly,
            "published_annual": annual_total,
            "published_contract_total": contract_total,
            "authorized_monthly": authorized_monthly,
            "authorized_contract_total": _to_currency(authorized_monthly * contract_term_months),
            "walkaway_floor_monthly": walkaway_monthly,
            "walkaway_contract_total": _to_currency(walkaway_monthly * contract_term_months),
            "monthly_net_profit": monthly_net_profit,
            "net_margin_percentage": round((monthly_net_profit / published_monthly) * 100.0, 2)
        },
        "empirical_benchmarks_audit": {
            "dallas_frem_14_facility_benchmark_monthly": empirical_dal_fac_benchmark,
            "delta_vs_frem_benchmark_per_facility": fac_rate_variance,
            "delta_vs_frem_benchmark_pct": fac_rate_variance_pct,
            "dallas_mwbe_monthly_pool_total": mwbe_monthly_pool,
            "share_of_dallas_mwbe_subcontract_pool_pct": mwbe_pool_consumption_pct,
            "dallas_living_wage_floor_enforced": wage >= 18.00,
            "scoring_matrix_alignment": DALLAS_MUNICIPAL_BENCHMARKS["citywide_master_agreement"]["scoring_weights"]
        },
        "safeguards": INSTITUTIONAL_SAFEGUARDS
    }

def calculate_federal_sca_bid(
    county: str = "Collin",
    cleanable_sqft: float = 25000.0,
    weekly_labor_hours: float = 40.0,
    occupation: str = "Janitor / Custodian",
    use_eo13706: bool = True,
    vacation_weeks: int = 2,
    paid_holidays: int = 11,
    supplies_monthly: float = 300.0,
    equipment_monthly: float = 200.0,
    target_margin: float = 0.15,
    db_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Tier 3: Federal McNamara-O'Hara Service Contract Act (SCA) Proposal.
    Calculates exact DOL Wage Determination floor, mandatory Health & Welfare fringe,
    statutory holiday & vacation accrual reserves, payroll taxes, G&A, and profit.
    """
    wd_info = get_sca_wage_determination(county=county, occupation=occupation, db_url=db_url)
    base_hourly_wage = wd_info["base_hourly_wage"]
    
    # 1. Health & Welfare Fringe Rate per productive hour
    hw_hourly = wd_info["health_welfare_eo13706"] if use_eo13706 else wd_info["health_welfare_standard"]

    # 2. Statutory Paid Time Off (PTO) Accrual Factors
    # 11 Paid Federal Holidays = 88 hours / 2080 hours = 4.2308%
    holiday_accrual_factor = (paid_holidays * 8.0) / STANDARD_ANNUAL_HOURS
    # Vacation: 2 weeks = 80 hours / 2080 hours = 3.8462%
    vacation_accrual_factor = (vacation_weeks * 40.0) / STANDARD_ANNUAL_HOURS
    total_pto_factor = holiday_accrual_factor + vacation_accrual_factor

    # 3. Hourly Cash & Benefit Build-Up
    hourly_holiday_cash_reserve = base_hourly_wage * holiday_accrual_factor
    hourly_vacation_cash_reserve = base_hourly_wage * vacation_accrual_factor
    total_taxable_hourly_wage = base_hourly_wage + hourly_holiday_cash_reserve + hourly_vacation_cash_reserve

    # 4. Mandatory Payroll Taxes & Workers' Comp (Burden on Taxable Wages: 20.00%)
    hourly_payroll_burden = total_taxable_hourly_wage * DEFAULT_BURDEN_RATE

    # 5. Total Fully Loaded SCA Labor Cost per Hour
    # (Taxable Cash Wages + Statutory Taxes + Mandatory Non-Taxable Health & Welfare Cash/Fringe)
    fully_loaded_sca_labor_hourly = _to_currency(total_taxable_hourly_wage + hourly_payroll_burden + hw_hourly)

    # 6. Monthly & Annual Conversions
    weekly_hours = max(1.0, float(weekly_labor_hours))
    monthly_hours = (weekly_hours * 52.0) / 12.0
    annual_hours = weekly_hours * 52.0

    monthly_labor_cost = _to_currency(fully_loaded_sca_labor_hourly * monthly_hours)
    monthly_direct_cogs = _to_currency(monthly_labor_cost + supplies_monthly + equipment_monthly)

    # 7. G&A Overhead & Profit Markups
    monthly_ga_overhead = _to_currency(monthly_direct_cogs * 0.050) # 5.0% Fixed Gov SG&A
    
    # Target Profit Margin (typically 12% - 18% on firm-fixed-price federal janitorial)
    monthly_clin_submittal = _to_currency((monthly_direct_cogs + monthly_ga_overhead) / (1.0 - target_margin))
    annual_contract_value = _to_currency(monthly_clin_submittal * 12.0)
    five_year_ceiling_value = _to_currency(annual_contract_value * 5.0) # Base + 4 Option Years

    monthly_net_profit = _to_currency(monthly_clin_submittal - (monthly_direct_cogs + monthly_ga_overhead))
    effective_billing_rate = round(monthly_clin_submittal / monthly_hours, 2) if monthly_hours > 0 else 0.0

    return {
        "tier": "Federal McNamara-O'Hara SCA",
        "solicitation_county": county,
        "dol_wage_determination": {
            "wd_number": wd_info["wd_number"],
            "revision_number": wd_info["revision_number"],
            "occupation_title": wd_info["occupation_title"],
            "occupation_code": wd_info["occupation_code"],
            "source_citation": wd_info["source"]
        },
        "hourly_rate_buildup": {
            "dol_base_wage_floor": base_hourly_wage,
            "mandated_hw_fringe_rate": hw_hourly,
            "hw_governance": "Executive Order 13706 Applicable" if use_eo13706 else "Standard SCA Fringe",
            "holiday_reserve_hourly": round(hourly_holiday_cash_reserve, 4),
            "vacation_reserve_hourly": round(hourly_vacation_cash_reserve, 4),
            "taxable_hourly_wage": round(total_taxable_hourly_wage, 4),
            "payroll_burden_taxes_20pct": round(hourly_payroll_burden, 4),
            "fully_loaded_sca_hourly_cost": fully_loaded_sca_labor_hourly
        },
        "monthly_schedule": {
            "mandated_weekly_hours": weekly_hours,
            "monthly_hours": round(monthly_hours, 1),
            "monthly_labor_cost": monthly_labor_cost,
            "supplies_epa_biopreferred": supplies_monthly,
            "equipment_hepa_depreciation": equipment_monthly,
            "total_monthly_cogs": monthly_direct_cogs,
            "ga_overhead_5pct": monthly_ga_overhead,
            "clin_0001_monthly_submittal": monthly_clin_submittal,
            "monthly_net_profit": monthly_net_profit
        },
        "contract_commitments": {
            "clin_0001_base_year_annual": annual_contract_value,
            "five_year_idiq_ceiling_valuation": five_year_ceiling_value,
            "effective_hourly_billing_rate": effective_billing_rate,
            "net_operating_margin_pct": round((monthly_net_profit / monthly_clin_submittal) * 100, 2) if monthly_clin_submittal > 0 else 0.0
        },
        "safeguards": FEDERAL_SCA_SAFEGUARDS
    }


MULTI_FAMILY_VALET_SAFEGUARDS = {
    "doorstep_collection_protocol": "Service includes five (5) nights per week (Sunday through Thursday) collection of tied, bagged household waste placed in property-approved 13-gallon doorstep receptacles between 6:00 PM and 8:00 PM. Collection begins promptly at 8:00 PM.",
    "compactor_corral_maintenance": "Nightly sweep, litter policing, and deodorizing spray application across the central commercial compactor enclosure and dumpster pad following collection completion.",
    "hot_water_pressure_washing": "Quarterly high-pressure hot-water sanitization (3,500 PSI @ 200°F) of concrete compactor pads to eliminate grease, organic residue, bacteria, and leachate odors.",
    "pet_waste_station_service": "Weekly bag restocking, canister sanitization, and waste disposal across all designated community pet waste stations.",
    "bulk_junk_hauling_schedule": "Move-out bulk items (mattresses, couches, furniture) left in corrals or breezeways shall be hauled away on-demand at $125.00–$225.00 per item upon property manager dispatch.",
    "zero_leak_guarantee": "Technicians utilize leak-proof vinyl transport containers to prevent liquid leachate stains on breezeways, concrete sidewalks, and interior residential corridors."
}


def calculate_valet_waste_bid(
    num_units: int = 122,
    days_per_week: int = 5,
    pet_stations_count: int = 5,
    include_compactor_washing: bool = True,
    contract_term_months: int = 36,
    base_door_rate: float = 14.00,
    resident_fee_benchmark: float = 30.00,
    target_margin: float = 0.25,
    negotiation_buffer: float = 0.04,
    walkaway_margin: float = 0.18
) -> Dict[str, Any]:
    """
    Tier 4: Multi-Family & Built-to-Rent (BTR) Doorstep Valet Waste & Grounds Proposal.
    Calculates per-door recurring pricing, compactor pad sanitization, pet station management,
    direct labor build-up, and models Landlord Net Operating Income (NOI) expansion and
    property asset appreciation (6% Capitalization Rate).
    """
    num_units = max(10, int(num_units))
    days_per_week = max(3, min(7, int(days_per_week)))
    term_months = max(12, int(contract_term_months))
    base_door_rate = max(10.00, float(base_door_rate))

    # 1. Monthly Revenue Buildup
    monthly_valet_base = _to_currency(num_units * base_door_rate)
    monthly_pet_stations = _to_currency(pet_stations_count * 50.00)
    monthly_compactor_care = 150.00 if include_compactor_washing else 0.00
    
    published_monthly = _to_currency(monthly_valet_base + monthly_pet_stations + monthly_compactor_care)
    authorized_monthly = _to_currency((num_units * (base_door_rate - 1.00)) + monthly_pet_stations + monthly_compactor_care)
    walkaway_monthly = _to_currency((num_units * (base_door_rate - 2.00)) + monthly_pet_stations + monthly_compactor_care)

    annual_submittal = _to_currency(published_monthly * 12.0)
    contract_total = _to_currency(published_monthly * term_months)

    # 2. Labor & Operations COGS Buildup
    # Collection pacing: ~0.4 min/unit + 15 min compactor policing
    collection_hours_per_night = max(0.75, round(((num_units * 0.4) + 15.0) / 60.0, 2))
    weekly_labor_hours = collection_hours_per_night * days_per_week
    monthly_labor_hours = (weekly_labor_hours * 52.0) / 12.0

    tech_hourly_wage = 20.00  # Dallas Living Wage compliant technician rate
    monthly_base_labor = _to_currency(monthly_labor_hours * tech_hourly_wage)
    monthly_labor_burden = _to_currency(monthly_base_labor * DEFAULT_BURDEN_RATE)
    total_monthly_labor = monthly_base_labor + monthly_labor_burden

    monthly_supplies = _to_currency(50.00 + (pet_stations_count * 15.00))  # Can liners, pet bags, enzymes
    monthly_equipment = 45.00  # Collection cart depreciation & PPE
    total_cogs = total_monthly_labor + monthly_supplies + monthly_equipment

    # Fixed G&A Overhead (5.0%)
    monthly_ga_overhead = _to_currency(total_cogs * 0.050)
    cost_basis = total_cogs + monthly_ga_overhead

    monthly_net_profit = _to_currency(published_monthly - cost_basis)
    actual_margin = (monthly_net_profit / published_monthly) if published_monthly > 0 else 0.0

    # 3. Landlord Economic Modeling (Asset Manager Pitch Deck)
    landlord_gross_resident_mo = _to_currency(num_units * resident_fee_benchmark)
    landlord_net_noi_mo = _to_currency(landlord_gross_resident_mo - published_monthly)
    landlord_net_noi_annual = _to_currency(landlord_net_noi_mo * 12.0)
    
    # Capital Asset Appreciation @ 6% Market Cap Rate
    property_asset_value_gain = _to_currency(landlord_net_noi_annual / 0.06)

    return {
        "tier": "Multi-Family / BTR Doorstep Valet Waste",
        "community_profile": {
            "total_units": num_units,
            "collection_days_per_week": days_per_week,
            "pet_waste_stations": pet_stations_count,
            "compactor_pad_washing_included": include_compactor_washing,
            "contract_term_months": term_months
        },
        "pricing_structure": {
            "published_door_rate": base_door_rate,
            "published_monthly_total": published_monthly,
            "published_annual_total": annual_submittal,
            "published_contract_total": contract_total,
            "authorized_field_close_monthly": authorized_monthly,
            "authorized_contract_total": _to_currency(authorized_monthly * term_months),
            "walkaway_floor_monthly": walkaway_monthly,
            "walkaway_contract_total": _to_currency(walkaway_monthly * term_months)
        },
        "operations_cogs": {
            "estimated_shift_hours_nightly": collection_hours_per_night,
            "monthly_labor_hours": round(monthly_labor_hours, 1),
            "monthly_direct_labor": total_monthly_labor,
            "monthly_supplies_and_bags": monthly_supplies,
            "monthly_equipment": monthly_equipment,
            "total_monthly_cogs": total_cogs,
            "monthly_net_profit": monthly_net_profit,
            "net_operating_margin_pct": round(actual_margin * 100, 2)
        },
        "landlord_noi_expansion_model": {
            "resident_monthly_fee_benchmark": resident_fee_benchmark,
            "landlord_gross_resident_collections_monthly": landlord_gross_resident_mo,
            "landlord_net_monthly_profit": landlord_net_noi_mo,
            "landlord_annual_noi_increase": landlord_net_noi_annual,
            "property_capital_asset_appreciation_6pct_cap": property_asset_value_gain
        },
        "safeguards": MULTI_FAMILY_VALET_SAFEGUARDS
    }


COMMERCIAL_RECURRING_SAFEGUARDS = {
    "scope_demarcation": "Janitorial specifications cover all designated private offices, conference rooms, restrooms, kitchenettes/break areas, reception lobbies, and common circulation corridors. Exterior grounds and parking lots are excluded unless expressly added via Exhibit Rider.",
    "access_and_keycard_governance": "All security fobs, electronic access badges, and facility keys shall be cryptographically logged in the SigmaFidelity Chain-of-Custody register. Technicians are strictly prohibited from granting facility access to unvetted third parties.",
    "cross_contamination_prevention": "Mandatory color-coded microfiber protocol (Red = Restroom Sanitary/Toilets, Blue = General Office Surfaces/Desks, Green = Kitchen/Food Prep, Yellow = High-Touch Fixtures/Doorknobs) utilizing EPA-registered hospital-grade disinfectant.",
    "periodic_deep_maintenance_schedule": "Contract includes quarterly machine burnishing of VCT/hard surfaces and annual hot-water extraction of high-traffic carpet runners, coordinated 14 days in advance with facility management.",
    "price_escalation_clause": "Annual automatic rate adjustment indexed to the Bureau of Labor Statistics Consumer Price Index for All Urban Consumers (CPI-U DFW MSA) or 3.0%, whichever is greater, to protect labor wage floors against inflationary drift.",
    "cancellation_terms": "Mutual thirty (30) day written notice for cause, preceded by a formal ten (10) day cure period documented via the SigmaFidelity Digital Audit Portal."
}


def calculate_commercial_recurring_bid(
    cleanable_sqft: float,
    cleanings_per_week: int = 5,
    facility_type: str = "office",
    contract_term_months: int = 36,
    base_hourly_wage: Optional[float] = None,
    target_margin: float = 0.22,
    negotiation_buffer: float = 0.04,
    walkaway_margin: float = 0.16
) -> Dict[str, Any]:
    """
    Tier 5: Commercial Recurring Office & Facility Janitorial Proposal.
    Calculates recurring commercial cleaning pricing calibrated against ISSA 540
    production standards by facility archetype (Office, Legal, Medical, Surgical, Industrial Flex).
    Enforces the Dallas Living Wage floor ($18.00/hr) and models negotiation triads.
    """
    cleanable_sqft = max(500.0, float(cleanable_sqft))
    cleanings_per_week = max(1, min(7, int(cleanings_per_week)))
    term_months = max(12, int(contract_term_months))
    fac_type = facility_type.lower().strip()

    # Facility archetype calibration profiles
    # (Production rate sqft/hr, default wage, supply cost $/sqft/mo, monthly equipment depreciation)
    archetype_profiles = {
        "office": (3500.0, 18.50, 0.012, 75.00),
        "legal": (3000.0, 19.50, 0.015, 85.00),
        "financial": (3000.0, 19.50, 0.015, 85.00),
        "medical": (2400.0, 20.50, 0.022, 110.00),
        "surgical": (1800.0, 22.50, 0.030, 150.00),
        "industrial_flex": (5500.0, 19.00, 0.008, 225.00),
        "education": (3200.0, 18.50, 0.014, 85.00)
    }

    prod_rate, default_wage, supply_sqft_rate, equipment_cost = archetype_profiles.get(
        fac_type, (3500.0, 18.50, 0.012, 75.00)
    )

    wage = float(base_hourly_wage) if base_hourly_wage is not None else default_wage
    wage = max(18.00, wage)  # Dallas Living Wage floor enforcement

    # 1. Labor Hours Calculation (ISSA 540 Standard)
    hours_per_clean = max(1.0, round(cleanable_sqft / prod_rate, 2))
    weekly_hours = hours_per_clean * cleanings_per_week
    monthly_hours = (weekly_hours * 52.0) / 12.0
    annual_hours = weekly_hours * 52.0

    monthly_base_labor = _to_currency(monthly_hours * wage)
    monthly_labor_burden = _to_currency(monthly_base_labor * DEFAULT_BURDEN_RATE)
    total_monthly_labor = monthly_base_labor + monthly_labor_burden

    # 2. Consumables & Equipment Amortization
    monthly_supplies = _to_currency(max(65.00, cleanable_sqft * supply_sqft_rate))
    total_direct_cogs = total_monthly_labor + monthly_supplies + equipment_cost

    # 3. Fixed G&A Overhead (5.0%)
    monthly_ga = _to_currency(total_direct_cogs * 0.05)
    cost_basis = total_direct_cogs + monthly_ga

    # 4. Negotiation Triad Build-Up
    published_monthly = _to_currency(cost_basis / (1.0 - (target_margin + negotiation_buffer)))
    authorized_monthly = _to_currency(cost_basis / (1.0 - target_margin))
    walkaway_monthly = _to_currency(cost_basis / (1.0 - walkaway_margin))

    published_annual = _to_currency(published_monthly * 12.0)
    contract_total = _to_currency(published_monthly * term_months)
    monthly_net_profit = _to_currency(published_monthly - cost_basis)

    return {
        "tier": "Commercial Recurring Janitorial",
        "facility_profile": {
            "cleanable_sqft": cleanable_sqft,
            "facility_type": fac_type,
            "cleanings_per_week": cleanings_per_week,
            "contract_term_months": term_months,
            "issa_production_rate_sqft_hr": prod_rate,
            "hours_per_cleaning_shift": hours_per_clean
        },
        "pricing_structure": {
            "published_monthly_submittal": published_monthly,
            "published_annual_total": published_annual,
            "published_contract_total": contract_total,
            "effective_monthly_sqft_rate": round(published_monthly / cleanable_sqft, 4),
            "effective_annual_sqft_rate": round(published_annual / cleanable_sqft, 4),
            "authorized_field_close_monthly": authorized_monthly,
            "authorized_contract_total": _to_currency(authorized_monthly * term_months),
            "walkaway_floor_monthly": walkaway_monthly,
            "walkaway_contract_total": _to_currency(walkaway_monthly * term_months)
        },
        "operations_cogs": {
            "weekly_labor_hours": round(weekly_hours, 1),
            "monthly_labor_hours": round(monthly_hours, 1),
            "assigned_technician_wage": wage,
            "monthly_base_labor": monthly_base_labor,
            "monthly_labor_burden_20pct": monthly_labor_burden,
            "total_monthly_labor": total_monthly_labor,
            "monthly_supplies_and_disinfectant": monthly_supplies,
            "monthly_equipment_depreciation": equipment_cost,
            "total_monthly_cogs": total_direct_cogs,
            "monthly_ga_overhead_5pct": monthly_ga,
            "monthly_net_ebitda": monthly_net_profit,
            "net_operating_margin_pct": round((monthly_net_profit / published_monthly) * 100.0, 2) if published_monthly > 0 else 0.0
        },
        "safeguards": COMMERCIAL_RECURRING_SAFEGUARDS
    }


