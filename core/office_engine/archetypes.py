"""
Office Engine: Client Archetypes Module
Defines the visual, structural, and contractual profiles across commercial sectors.
"""

from enum import Enum

class ClientArchetype(str, Enum):
    """
    Client Archetype represents the market segment and expectations of the client.
    Ensures proposals and spreadsheets adapt to the appropriate formality and density.
    """
    BOUTIQUE = "BOUTIQUE"               # Local businesses, boutique legal/medical clinics, single daycares
    REGIONAL = "REGIONAL"               # Multi-unit commercial, corporate offices, educational networks
    INSTITUTIONAL = "INSTITUTIONAL"     # ISDs, municipal governments, colleges, state authorities
    CONSTRUCTION = "CONSTRUCTION"       # General contractors, commercial finish-out, ground-up subcontracting

    @property
    def label(self) -> str:
        labels = {
            self.BOUTIQUE: "Modern Boutique Commercial",
            self.REGIONAL: "Regional Enterprise & Corporate",
            self.INSTITUTIONAL: "Public Sector & Institutional",
            self.CONSTRUCTION: "Commercial Construction & Subcontract"
        }
        return labels.get(self, "Commercial")

    @property
    def target_page_count(self) -> str:
        counts = {
            self.BOUTIQUE: "2 - 3 Pages",
            self.REGIONAL: "3 - 5 Pages",
            self.INSTITUTIONAL: "6 - 12 Pages",
            self.CONSTRUCTION: "2 - 4 Pages + Excel Bid Sheet"
        }
        return counts.get(self, "3 - 5 Pages")

    @property
    def contract_strategy(self) -> str:
        strategies = {
            self.BOUTIQUE: "Clean 1-Page Service Agreement (Low friction, friendly terms)",
            self.REGIONAL: "Option 1 Term Lock with 30-Day Right to Cure & Floor Care Amortization",
            self.INSTITUTIONAL: "Full 18-Clause Enforceable Agreement with Texas Venue & Statutory Compliance",
            self.CONSTRUCTION: "AIA / CSI Division 01 MasterFormat with Phased Progress Payments"
        }
        return strategies.get(self, "Standard Agreement")
