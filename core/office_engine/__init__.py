"""
Global Microsoft Office Suite Engine for HWB, Hexgrowth, BabySOP & Multi-Enterprise Ecosystem
Provides adaptive Word (.docx), Excel (.xlsx), and Template Merging across 4 Client Archetypes
and dynamic company profiles.
"""

from .archetypes import ClientArchetype
from .palette import ArchetypeStyle, get_style, STYLES
from .company import CompanyProfile, get_company, COMPANIES
from .word_builder import WordBuilder
from .excel_builder import ExcelBuilder
from .template_merger import TemplateMerger

__all__ = [
    "ClientArchetype",
    "ArchetypeStyle",
    "get_style",
    "STYLES",
    "CompanyProfile",
    "get_company",
    "COMPANIES",
    "WordBuilder",
    "ExcelBuilder",
    "TemplateMerger"
]
