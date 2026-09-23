"""
SigmaFidelity™ Autonomous Playbook Assessment & Pattern Recognition Engine
Standard: HWB-QMS-7.7, HWB-QMS-8.9, HWB-QMS-11.2 & ARCH-006 Strategic Playbook Assimilation
Authority: George (Systems Architect & mbB) | Approved: Humberto Dominguez (CEO)

This engine evaluates commercial, municipal, multi-family, and industrial facility leads
against the 5 SigmaFidelity™ Assessment Pillars, matches them against active hunting playbooks,
and autonomously formulates new specialized playbooks for unclassified high-value niches.

The 5 Assessment Pillars:
1. Economic Arbitrage & Leverage (0-20): Quantifiable NOI gain, cost recovery, or budget capture.
2. Decision Velocity & Directness (0-20): Direct executive authority (CEO/Owner) vs committee lag.
3. Regulatory & Compliance Stickiness (0-20): Mandates from OSHA, TDLR, CDC, CMS, or Lease terms.
4. Operational Density & Route Physics (0-20): Proximity to DFW clusters (Plano, Frisco, McKinney, Dallas).
5. Lifetime Value (LTV) & EBITDA Margin Floor (0-20): Minimum 20% margin and >= 24-36 mo recurring term.
"""

import os
import sys
import json
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# Active Institutional Playbook Registry
PLAYBOOK_REGISTRY: Dict[str, Dict[str, Any]] = {
    "PLAYBOOK-VALET-WASTE": {
        "playbook_id": "PLAYBOOK-VALET-WASTE",
        "title": "Multi-Family & BTR Doorstep Valet Waste & Grounds Playbook",
        "archetype": "Residential Communities & Detached Built-to-Rent Neighborhoods (75–450 units)",
        "target_sectors": ["Multi-Family", "Built-to-Rent", "Apartments", "Condominiums"],
        "cad_state_codes": ["B1", "B2"],
        "economic_driver": "Landlord NOI Arbitrage (Spread between $30/mo resident fee and $14/mo vendor cost yields +$16/mo pure net profit per door, expanding asset valuation by +$300k+ @ 6% cap rate).",
        "decision_maker_title": "Regional Facilities Director / Community Manager / Asset Manager",
        "regulatory_governance": "Municipal Solid Waste Codes, Texas Environmental Quality Regulations",
        "service_frequency": "5 Nights / Week (Sunday - Thursday)",
        "estimator_tier": "Tier 4: Valet Waste",
        "min_margin_floor": 0.22,
        "default_contract_term_months": 36,
        "status": "ACTIVE_PRODUCTION"
    },
    "PLAYBOOK-OWNER-OCCUPANT": {
        "playbook_id": "PLAYBOOK-OWNER-OCCUPANT",
        "title": "Commercial Owner-Occupant Direct Authority Playbook",
        "archetype": "Privately-Owned Commercial Buildings (4,000–30,000 SQFT) where Physical Situs == Owner Mailing Address",
        "target_sectors": ["Boutique Legal", "Private Wealth", "Corporate HQ", "Engineering", "Consulting"],
        "cad_state_codes": ["F1"],
        "economic_driver": "Direct Peer-to-Peer Decision Velocity (Zero corporate committee red tape; 48-to-72 hour proposal turnaround directly to the deed holder / Managing Partner).",
        "decision_maker_title": "Managing Partner / Founder / President / CEO",
        "regulatory_governance": "Direct Commercial Lease & Facility Standards",
        "service_frequency": "3 to 5 Nights / Week",
        "estimator_tier": "Tier 5: Commercial Recurring",
        "min_margin_floor": 0.20,
        "default_contract_term_months": 36,
        "status": "ACTIVE_PRODUCTION"
    },
    "PLAYBOOK-HEALTHCARE-SURGICAL": {
        "playbook_id": "PLAYBOOK-HEALTHCARE-SURGICAL",
        "title": "Ambulatory Surgery Centers & High-Acuity Medical Playbook",
        "archetype": "Outpatient Surgery Centers, Specialty Clinics, Dialysis Units & Compounding Pharmacies (8,000–40,000 SQFT)",
        "target_sectors": ["Ambulatory Surgery", "Specialty Medical", "Dialysis", "Clinical Lab", "Oncology"],
        "cad_state_codes": ["F1", "Medical"],
        "economic_driver": "Zero-Defect Regulatory Compliance (Infection prevention failure risks medical licensing suspension or CMS non-compliance; premium rates floor $0.35–$0.55/SQFT).",
        "decision_maker_title": "Medical Director / Clinical Administrator / Infection Control Officer",
        "regulatory_governance": "OSHA 1910.1030 (Bloodborne Pathogen Standard), CMS Conditions of Coverage, AAAHC/Joint Commission",
        "service_frequency": "5 Nights / Week (Terminal Disinfection)",
        "estimator_tier": "Tier 5: Commercial Recurring (Surgical/Medical Profile)",
        "min_margin_floor": 0.25,
        "default_contract_term_months": 36,
        "status": "ACTIVE_PRODUCTION"
    },
    "PLAYBOOK-CORPORATE-FINISHOUT": {
        "playbook_id": "PLAYBOOK-CORPORATE-FINISHOUT",
        "title": "Class A Corporate Tenant Finish-Out & Move-In Radar Playbook",
        "archetype": "Commercial Tenant Finish-Outs & Office Renovations with TDLR TABS Project Cost > $50,000",
        "target_sectors": ["Corporate Relocations", "Law Firm Relocations", "Tech HQs", "Finance"],
        "cad_state_codes": ["F1", "Office"],
        "economic_driver": "Dual-Revenue Funnel (One-time post-construction final clean for General Contractor converts directly into 3-year recurring master janitorial contract before market competitors discover tenant).",
        "decision_maker_title": "General Contractor Project Manager + Inbound Corporate Facilities Manager",
        "regulatory_governance": "TDLR Elimination of Architectural Barriers, Commercial Lease Occupancy Requirements",
        "service_frequency": "Post-Construction Clean + 5 Nights / Week Janitorial",
        "estimator_tier": "Tier 1: Commercial GC + Tier 5: Commercial Recurring",
        "min_margin_floor": 0.22,
        "default_contract_term_months": 36,
        "status": "ACTIVE_PRODUCTION"
    },
    "PLAYBOOK-INDUSTRIAL-LOGISTICS": {
        "playbook_id": "PLAYBOOK-INDUSTRIAL-LOGISTICS",
        "title": "Industrial Logistics & Flex Distribution Centers Playbook",
        "archetype": "Large-Footprint Warehouses, R&D Facilities & Light Industrial Distribution Hubs (40,000–250,000 SQFT)",
        "target_sectors": ["Logistics", "Distribution", "Manufacturing", "E-Commerce", "Flex Industrial"],
        "cad_state_codes": ["F2"],
        "economic_driver": "Machine-Assisted Density Physics (High square footage serviced via automated ride-on scrubbers; direct labor costs < 35% vs 50% in standard office spaces, yielding high dollar gross margin).",
        "decision_maker_title": "Director of Supply Chain Logistics / Warehouse Operations Manager",
        "regulatory_governance": "OSHA General Industry Safety Standards (29 CFR 1910), Dust & Leachate Control",
        "service_frequency": "3 to 5 Days / Week",
        "estimator_tier": "Tier 5: Commercial Recurring (Industrial Flex Profile)",
        "min_margin_floor": 0.24,
        "default_contract_term_months": 36,
        "status": "ACTIVE_PRODUCTION"
    },
    "PLAYBOOK-DAYCARE-ACADEMY": {
        "playbook_id": "PLAYBOOK-DAYCARE-ACADEMY",
        "title": "Licensed Child Development & Private Academy Playbook",
        "archetype": "State-Licensed Childcare Centers, Montessori Schools & Private Academies (5,000–25,000 SQFT)",
        "target_sectors": ["Child Care", "Daycare", "Montessori", "Private School", "Early Learning"],
        "cad_state_codes": ["F1", "School"],
        "economic_driver": "Health Inspection Compliance & Parent Trust (Mandatory daily sanitization of toys, touchpoints, and restrooms with EPA Safer Choice non-toxic hospital-grade disinfectants).",
        "decision_maker_title": "Owner-Operator / Academy Director / Board of Trustees",
        "regulatory_governance": "Texas Health and Human Services Child-Care Licensing Minimum Standards",
        "service_frequency": "5 Nights / Week",
        "estimator_tier": "Tier 5: Commercial Recurring (Education Profile)",
        "min_margin_floor": 0.20,
        "default_contract_term_months": 24,
        "status": "ACTIVE_PRODUCTION"
    }
}


def score_lead(lead: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates a prospect or CAD property record against the 5 SigmaFidelity™ Assessment Pillars.
    Returns composite score (0-100), qualification tier, matched playbook, and strategic rationale.
    """
    # 1. Pillar 1: Economic Arbitrage & Leverage (0-20)
    # Evaluates whether the play generates net new revenue, rent recovery, or high gross margin.
    sector = str(lead.get("sector", lead.get("sector_type", ""))).lower()
    units = int(lead.get("units", 0))
    sqft = float(lead.get("cleanable_sqft", lead.get("sqft", 0.0)))
    
    if units >= 75:  # Multi-family valet waste arbitrage
        p1_score = 20
        p1_rationale = f"Landlord NOI Arbitrage: {units} doors generate pure net asset profit."
    elif "surg" in sector or "medic" in sector:
        p1_score = 19
        p1_rationale = "High-ticket regulatory risk mitigation; zero pricing pushback for clinical safety."
    elif sqft >= 40000:
        p1_score = 18
        p1_rationale = f"High cleanable volume ({sqft:,.0f} SQFT); machine-assisted labor leverage."
    elif sqft >= 10000:
        p1_score = 16
        p1_rationale = f"Standard high-ticket commercial scope ({sqft:,.0f} SQFT)."
    else:
        p1_score = 12
        p1_rationale = "Standard commercial margin profile."

    # 2. Pillar 2: Decision Velocity & Directness (0-20)
    # Direct owner/CEO = 20, Property Manager = 17, Regional Director = 14, Committee = 10
    officer = str(lead.get("procurement_officer", lead.get("owner_ceo", ""))).lower()
    situs_match = lead.get("situs_matches_mailing", True)  # Owner-occupant marker
    
    if "managing partner" in officer or "ceo" in officer or "owner" in officer or "president" in officer:
        p2_score = 20
        p2_rationale = "Direct executive authority: Single decision-maker; 48-72 hr close velocity."
    elif "community manager" in officer or "property manager" in officer:
        p2_score = 17
        p2_rationale = "Onsite management authority with direct budgetary signoff."
    elif "facilities" in officer or "administrator" in officer:
        p2_score = 15
        p2_rationale = "Technical facility buyer with departmental purchase requisition authority."
    else:
        p2_score = 12
        p2_rationale = "Standard corporate management hierarchy."

    # 3. Pillar 3: Regulatory & Compliance Stickiness (0-20)
    # OSHA, TDLR, Health Dept, or Lease requirement = high stickiness & low churn
    if "surg" in sector or "medic" in sector:
        p3_score = 20
        p3_rationale = "Governed by OSHA 1910.1030 & CMS infection control. Non-discretionary."
    elif units >= 75:
        p3_score = 18
        p3_rationale = "Tied directly to resident amenity lease covenants and municipal solid waste rules."
    elif "child" in sector or "daycare" in sector:
        p3_score = 19
        p3_rationale = "Mandated by Texas HHS Child Care Licensing minimum sanitation standards."
    elif "legal" in sector or "wealth" in sector:
        p3_score = 16
        p3_rationale = "Client-facing professional standard; confidential data privacy protocols."
    else:
        p3_score = 14
        p3_rationale = "Standard commercial lease maintenance standard."

    # 4. Pillar 4: Operational Density & Route Physics (0-20)
    # Proximity to core DFW clusters (Plano, Frisco, McKinney, Richardson, North Dallas)
    city = str(lead.get("city", "Plano")).lower()
    prime_clusters = ["plano", "frisco", "mckinney", "richardson", "dallas", "denton", "allen"]
    if any(c in city for c in ["plano", "frisco", "mckinney"]):
        p4_score = 20
        p4_rationale = f"Epicenter of existing operational cluster ({city.title()}); 0-mile dispatch radius."
    elif any(c in city for c in prime_clusters):
        p4_score = 17
        p4_rationale = f"DFW primary submarket ({city.title()}); high route density."
    else:
        p4_score = 13
        p4_rationale = f"Secondary Texas submarket ({city.title()}); standalone route deployment."

    # 5. Pillar 5: Lifetime Value (LTV) & EBITDA Margin Floor (0-20)
    term_months = int(lead.get("contract_term_months", 36))
    if term_months >= 36:
        p5_score = 20
        p5_rationale = f"Multi-year institutional agreement ({term_months} months); high LTV retention."
    elif term_months >= 24:
        p5_score = 17
        p5_rationale = f"24-Month recurring agreement; predictable annualized cashflow."
    else:
        p5_score = 14
        p5_rationale = "12-Month standard term."

    total_score = p1_score + p2_score + p3_score + p4_score + p5_score

    # Determine Qualification Tier
    if total_score >= 88:
        tier_label = "PLATINUM (Priority Immediate Action)"
    elif total_score >= 75:
        tier_label = "GOLD (Standard High-Yield Pursuit)"
    elif total_score >= 60:
        tier_label = "SILVER (Opportunistic Secondary)"
    else:
        tier_label = "BRONZE (Hold / Disqualified)"

    # Determine Matching Playbook
    matched_playbook_id = "PLAYBOOK-OWNER-OCCUPANT"
    if units >= 50 or "valet" in sector or "multi-family" in sector or "btr" in sector:
        matched_playbook_id = "PLAYBOOK-VALET-WASTE"
    elif "surg" in sector or "medic" in sector or "clinic" in sector:
        matched_playbook_id = "PLAYBOOK-HEALTHCARE-SURGICAL"
    elif "finish" in sector or "construction" in sector or "move-in" in sector:
        matched_playbook_id = "PLAYBOOK-CORPORATE-FINISHOUT"
    elif sqft >= 40000 or "warehouse" in sector or "logistics" in sector:
        matched_playbook_id = "PLAYBOOK-INDUSTRIAL-LOGISTICS"
    elif "daycare" in sector or "school" in sector or "academy" in sector:
        matched_playbook_id = "PLAYBOOK-DAYCARE-ACADEMY"

    matched_pb = PLAYBOOK_REGISTRY.get(matched_playbook_id, PLAYBOOK_REGISTRY["PLAYBOOK-OWNER-OCCUPANT"])

    return {
        "assessment_timestamp": datetime.datetime.now().isoformat(),
        "lead_identifier": lead.get("lead_id", lead.get("solicitation_number", "UNKNOWN")),
        "lead_title": lead.get("title", lead.get("company_name", lead.get("property_name", ""))),
        "composite_score": total_score,
        "qualification_tier": tier_label,
        "matched_playbook": {
            "playbook_id": matched_pb["playbook_id"],
            "title": matched_pb["title"],
            "estimator_tier": matched_pb["estimator_tier"],
            "economic_driver": matched_pb["economic_driver"],
            "decision_maker_target": matched_pb["decision_maker_title"]
        },
        "pillar_breakdown": {
            "pillar_1_economic_arbitrage": {"score": p1_score, "max": 20, "rationale": p1_rationale},
            "pillar_2_decision_velocity": {"score": p2_score, "max": 20, "rationale": p2_rationale},
            "pillar_3_regulatory_compliance": {"score": p3_score, "max": 20, "rationale": p3_rationale},
            "pillar_4_operational_density": {"score": p4_score, "max": 20, "rationale": p4_rationale},
            "pillar_5_contract_ltv_margin": {"score": p5_score, "max": 20, "rationale": p5_rationale}
        },
        "recommended_action": (
            "Autonomous Proposal Generation & Outbox Letter Staging (Official Letterhead HWB-COM-001)"
            if total_score >= 75 else "Hold in Nurture Queue"
        )
    }


def register_custom_playbook(playbook_def: Dict[str, Any]) -> bool:
    """
    Autonomously adds a newly discovered or synthesized playbook to the registry.
    Enables dynamic playbook expansion as new property archetypes emerge across Texas.
    """
    pb_id = playbook_def.get("playbook_id")
    if not pb_id:
        raise ValueError("playbook_id is required")
    
    PLAYBOOK_REGISTRY[pb_id] = playbook_def
    print(f"📖  [PLAYBOOK ENGINE] Registered New Hunting Playbook: {playbook_def.get('title')} ({pb_id})")
    return True


def list_active_playbooks() -> List[Dict[str, Any]]:
    """Returns a list of all active hunting playbooks in the SigmaFidelity ecosystem."""
    return list(PLAYBOOK_REGISTRY.values())


if __name__ == "__main__":
    print("================================================================================")
    print("🧠  SigmaFidelity™ Autonomous Playbook Assessment & Pattern Recognition Engine")
    print(f"🕒  Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("================================================================================")
    
    # Test sample assessment
    sample_lead = {
        "lead_id": "TEST-BTR-HORIZON",
        "property_name": "Horizon at Premier",
        "units": 122,
        "city": "Plano",
        "sector": "Multi-Family BTR",
        "procurement_officer": "Community Manager / Regional Facilities Director",
        "contract_term_months": 36
    }
    
    result = score_lead(sample_lead)
    print(json.dumps(result, indent=2))
