"""
Office Engine: Palette & Styling Tokens
Provides precise RGB, HEX, and typographic tokens per Client Archetype.
"""

from docx.shared import RGBColor, Pt
from .archetypes import ClientArchetype

class ArchetypeStyle:
    def __init__(
        self,
        name: str,
        font_primary: str,
        font_heading: str,
        color_primary_hex: str,
        color_secondary_hex: str,
        color_accent_hex: str,
        color_bg_hex: str,
        color_border_hex: str,
        color_text_hex: str
    ):
        self.name = name
        self.font_primary = font_primary
        self.font_heading = font_heading
        self.color_primary_hex = color_primary_hex
        self.color_secondary_hex = color_secondary_hex
        self.color_accent_hex = color_accent_hex
        self.color_bg_hex = color_bg_hex
        self.color_border_hex = color_border_hex
        self.color_text_hex = color_text_hex

    def _hex_to_rgb(self, hex_code: str) -> RGBColor:
        h = hex_code.lstrip("#")
        return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

    @property
    def rgb_primary(self) -> RGBColor:
        return self._hex_to_rgb(self.color_primary_hex)

    @property
    def rgb_secondary(self) -> RGBColor:
        return self._hex_to_rgb(self.color_secondary_hex)

    @property
    def rgb_accent(self) -> RGBColor:
        return self._hex_to_rgb(self.color_accent_hex)

    @property
    def rgb_text(self) -> RGBColor:
        return self._hex_to_rgb(self.color_text_hex)

    @property
    def rgb_border(self) -> RGBColor:
        return self._hex_to_rgb(self.color_border_hex)


STYLES = {
    ClientArchetype.BOUTIQUE: ArchetypeStyle(
        name="Modern Boutique Commercial",
        font_primary="Segoe UI",
        font_heading="Segoe UI",
        color_primary_hex="1E3A8A",      # Deep Royal
        color_secondary_hex="0284C7",    # Sky Blue
        color_accent_hex="10B981",       # Emerald Green (Fresh/Approachable)
        color_bg_hex="F8FAFC",           # Soft Slate White
        color_border_hex="E2E8F0",       # Clean light gray
        color_text_hex="1E293B"          # Dark Slate
    ),
    ClientArchetype.REGIONAL: ArchetypeStyle(
        name="Regional Enterprise & Corporate",
        font_primary="Segoe UI",
        font_heading="Segoe UI",
        color_primary_hex="0F172A",      # Midnight Slate Navy
        color_secondary_hex="2563EB",    # Cobalt Enterprise
        color_accent_hex="D97706",       # Gold / Amber Accent
        color_bg_hex="F1F5F9",           # Neutral Light Tint
        color_border_hex="CBD5E1",       # Medium border
        color_text_hex="0F172A"          # Midnight Text
    ),
    ClientArchetype.INSTITUTIONAL: ArchetypeStyle(
        name="Public Sector & Institutional",
        font_primary="Arial",
        font_heading="Arial",
        color_primary_hex="0B192C",      # Federal Navy
        color_secondary_hex="334155",    # Steel Gray
        color_accent_hex="991B1B",       # Seal Crimson
        color_bg_hex="F8F9FA",           # Crisp White-Gray
        color_border_hex="94A3B8",       # Heavy Divider
        color_text_hex="020617"          # Formal Black-Slate
    ),
    ClientArchetype.CONSTRUCTION: ArchetypeStyle(
        name="Commercial Construction & Subcontract",
        font_primary="Segoe UI",
        font_heading="Segoe UI",
        color_primary_hex="18181B",      # Industrial Zinc
        color_secondary_hex="D97706",    # Safety Amber
        color_accent_hex="EA580C",       # Hardhat Orange
        color_bg_hex="FAFAFA",           # Crisp Planroom Gray
        color_border_hex="D4D4D8",       # Heavy Architectural Line
        color_text_hex="18181B"          # Zinc Black
    )
}

def get_style(archetype: ClientArchetype = ClientArchetype.REGIONAL) -> ArchetypeStyle:
    """Returns the style token collection for the specified archetype."""
    return STYLES.get(archetype, STYLES[ClientArchetype.REGIONAL])
