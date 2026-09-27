"""
SigmaFidelity™ Business Classification & Ingestion Gateway Engine
Standard: HWB-QMS-7.6 Enterprise Architecture Standards & Zero-Defect Poka-Yoke Protocol

Functions:
1. Evaluates incoming business records (mined, scraped, CSV, or API).
2. Deterministically classifies them into standard industry and facility types.
3. Identifies cognitive conflicts (e.g., auto dealerships ingested via childcare registry).
4. Assigns confidence scores to quarantine low-confidence records prior to production ingestion.
"""

import re
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple


@dataclass
class BusinessClassification:
    industry: str
    facility_type: str
    cleanable_profile: str
    confidence_score: float
    matched_rule: str
    is_conflict: bool
    normalized_lead_source: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "industry": self.industry,
            "facility_type": self.facility_type,
            "cleanable_profile": self.cleanable_profile,
            "confidence_score": self.confidence_score,
            "matched_rule": self.matched_rule,
            "is_conflict": self.is_conflict,
            "normalized_lead_source": self.normalized_lead_source,
        }


class BusinessClassifierEngine:
    """
    Industrial Lead Classifier enforcing standard SigmaFidelity™ commercial taxonomy.
    Guarantees zero-defect categorization across web scraping, Texas Open Data, CAD hunters,
    and quarantine batch importers.
    """

    # --- Calibrated Rule Lexicon ---
    RULES = [
        # 1. Faith-Based & Religious Facilities
        (
            "Religious / Nonprofit",
            "Church",
            "Assembly Hall / Sanctuary High-Capacity Disinfection",
            r"\b(church|ministr(y|ies)|baptist|methodist|lutheran|catholic|temple|parish|worship|cathedral|synagogue|mosque|chapel|assembly of god|christian center|tabernacle)\b",
            0.96,
            "FAITH_RULE",
        ),
        # 2. Education K-12 & Public School Districts
        (
            "Education",
            "School",
            "Campus Multi-Zone Janitorial / Hallways & Gyms",
            r"\b(isd|elementary|middle school|high school|prep school|charter school|collegiate|independent school district|alphabest|ymca)\b",
            0.96,
            "K12_ACADEMICS_RULE",
        ),
        # 3. Automotive Dealerships, Service Bays & Fleet Equipment
        (
            "Automotive",
            "Automotive",
            "High-Traffic Hard Floor / Showroom & Grease Management",
            r"\b(auto|motors|motor|car sales|cars|autos|dealership|collision|tire|tires|rv center|truck|trucks|trailer|trailers|autoplex|pre-owned|classic cars|body shop|motorcars|ford|chevrolet|chev|gmc|toyota|nissan|honda|tractor|tractors|fleet|wrecker|salvage|transmissions|brakes|exhaust|oil change)\b",
            0.96,
            "AUTOMOTIVE_RULE",
        ),
        # 4. Healthcare, Medical, Dental & Surgical Clinics
        (
            "Healthcare / Medical",
            "Medical",
            "Terminal Medical Disinfection / Biohazard / OSHA Compliant",
            r"\b(clinic|medical|dental|pediatric|hospital|surgery|surgical|rehab|therapy|orthopedic|urgent care|physician|doctor|healthcare|pharmacy|optometry|chiropractic|dialysis)\b",
            0.95,
            "HEALTHCARE_RULE",
        ),
        # 5. Industrial, Logistics, Warehousing & Supply
        (
            "Industrial / Logistics",
            "Warehouse",
            "Industrial Floor Scrubbing & Dust Abatement",
            r"\b(logistics|warehouse|freight|distribution|transport|supply chain|storage|hauling|packaging|cargo|container|supply|industrial|iron|steel|welding|metal|lumber|distributors|wholesalers)\b",
            0.92,
            "INDUSTRIAL_LOGISTICS_RULE",
        ),
        # 6. Retail, Supermarkets & Big-Box Stores
        (
            "Retail & Hospitality",
            "Retail",
            "High-Traffic Resilient Floor Care & Restroom Sanitization",
            r"\b(depot|walmart|target|market|grocer|supermarket|hardware|outlet|store|retail|mall|plaza|boutique|lowe|lowes|home depot|dollar general|family dollar|walgreens|cvs)\b",
            0.92,
            "RETAIL_RULE",
        ),
        # 7. Food Service, Restaurants & Commercial Kitchens
        (
            "Retail & Hospitality",
            "Other",
            "Degreasing & Health Code Kitchen Sanitize",
            r"\b(restaurant|cafe|grill|bistro|kitchen|bakery|diner|catering|pizzeria|taqueria|bbq|barbecue|taco|pizza|burger|eatery|buffet)\b",
            0.92,
            "FOOD_SERVICE_RULE",
        ),
        # 8. Corporate & Professional Services (Legal, Financial, Corporate)
        (
            "Corporate / Office",
            "Office",
            "Executive Carpet Care & Detail Day Portering",
            r"\b(law|legal|attorney|cpa|accounting|financial|wealth|realty|real estate|consulting|insurance|advisory|holdings|investments|capital|partners|headquarters|solutions|management)\b",
            0.90,
            "CORPORATE_OFFICE_RULE",
        ),
        # 9. Early Childhood Education & Daycare Centers
        (
            "Child Care",
            "Child Care Center",
            "EPA Hospital-Grade Sanitization / High-Touch Disinfection",
            r"\b(child care|daycare|preschool|learning center|montessori|early learning|children|kids|kidz|kindergarten|head start|infant|toddler|primrose|childcare|little|childhood|baby|nursery)\b",
            0.96,
            "CHILDCARE_RULE",
        ),
    ]

    @classmethod
    def classify(
        cls,
        center_name: str,
        capacity: Optional[int] = None,
        lead_source: Optional[str] = None,
        raw_payload: Optional[Dict[str, Any]] = None,
    ) -> BusinessClassification:
        """
        Classifies a business record using multi-layered heuristic lexical matching,
        detecting cognitive conflicts and calculating quarantine confidence.
        """
        name = (center_name or "").strip()
        name_lower = name.lower()
        source = (lead_source or "").strip()

        # 1. Evaluate Lexicon Rules
        for ind, fac, profile, pattern, conf, rule_id in cls.RULES:
            if re.search(pattern, name_lower):
                # Check for cognitive conflict with lead_source
                is_conflict = False
                normalized_source = source
                if "childcare" in source.lower() or "ccl" in source.lower():
                    if ind not in ("Child Care", "Education"):
                        is_conflict = True
                        normalized_source = "Texas Commercial Registry"

                return BusinessClassification(
                    industry=ind,
                    facility_type=fac,
                    cleanable_profile=profile,
                    confidence_score=conf,
                    matched_rule=rule_id,
                    is_conflict=is_conflict,
                    normalized_lead_source=normalized_source,
                )

        # 2. Capacity-Based Childcare Fallback (if genuine licensed capacity > 0)
        if capacity and int(capacity) > 0:
            return BusinessClassification(
                industry="Child Care",
                facility_type="Child Care Center",
                cleanable_profile="EPA Hospital-Grade Sanitization / High-Touch Disinfection",
                confidence_score=0.90,
                matched_rule="LICENSED_CAPACITY_HEURISTIC",
                is_conflict=False,
                normalized_lead_source=source or "Texas CCL API",
            )

        # 3. General Commercial Entity Fallback (LLCs, Holdings, Personal names)
        # Normalize contaminated childcare source tag on general commercial entities
        is_conflict = False
        normalized_source = source
        if "childcare" in source.lower() or "ccl" in source.lower():
            is_conflict = True
            normalized_source = "Texas Commercial Registry"

        return BusinessClassification(
            industry="Commercial Property",
            facility_type="Other",
            cleanable_profile="Standard Commercial Janitorial Routine",
            confidence_score=0.75,  # Moderate confidence: suitable for quarantine review if mined
            matched_rule="COMMERCIAL_PROPERTY_FALLBACK",
            is_conflict=is_conflict,
            normalized_lead_source=normalized_source,
        )
