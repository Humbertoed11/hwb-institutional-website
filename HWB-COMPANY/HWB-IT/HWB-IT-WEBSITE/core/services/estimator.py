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

def calculate_commercial_gc_bid(
    cleanable_sqft: float,
    scope_phase: str = "Rough, Final & Touch-Up Clean",
    num_floors: int = 1,
    has_high_glass: bool = False,
    lift_rental: float = 0.0,
    target_margin: float = 0.20
) -> Dict[str, Any]:
    """
    Tier 1: Commercial General Contractor Subcontract Proposal.
    Calculates unit rates, phase breakdown, equipment passes, and target margins.
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
    submittal_total = _to_currency(subtotal_services + lift_rental)

    # Cost Build-up (COGS)
    estimated_hours = (cleanable_sqft / 1200.0) * (2.2 if "Rough" in scope_phase else 1.0)
    direct_labor_cost = _to_currency(estimated_hours * 18.50) # $18.50 burdened crew rate
    consumables_cost = _to_currency(cleanable_sqft * 0.015)
    equipment_cost = _to_currency(cleanable_sqft * 0.01) + lift_rental
    total_cogs = direct_labor_cost + consumables_cost + equipment_cost

    gross_profit = _to_currency(submittal_total - total_cogs)
    actual_margin = (gross_profit / submittal_total) if submittal_total > 0 else 0.0

    return {
        "tier": "Commercial GC",
        "cleanable_sqft": cleanable_sqft,
        "scope_phase": scope_phase,
        "num_floors": num_floors,
        "base_unit_rate": round(base_unit_rate, 4),
        "effective_unit_rate": round(submittal_total / cleanable_sqft, 4) if cleanable_sqft > 0 else 0.0,
        "rough_clean_total": rough_clean_val,
        "final_clean_total": final_clean_val,
        "touchup_clean_total": touchup_clean_val,
        "high_glass_total": high_glass_val,
        "lift_rental": lift_rental,
        "submittal_total": submittal_total,
        "cogs": {
            "estimated_labor_hours": round(estimated_hours, 1),
            "direct_labor_cost": direct_labor_cost,
            "consumables_cost": consumables_cost,
            "equipment_cost": equipment_cost,
            "total_direct_cogs": total_cogs
        },
        "gross_profit": gross_profit,
        "margin_percentage": round(actual_margin * 100, 2),
        "target_margin_met": actual_margin >= target_margin
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
    target_margin: float = 0.18
) -> Dict[str, Any]:
    """
    Tier 2: Public / Municipal Institutional Subcontract Proposal.
    Calculates multi-building campus labor, statutory burden, G&A overhead, and net EBITDA.
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

    # Subcontract Required Billing to achieve target margin
    monthly_subcontract_submittal = _to_currency((monthly_cogs + monthly_ga_overhead) / (1.0 - target_margin))
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
        "net_margin_percentage": round(actual_margin * 100, 2)
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
        }
    }
