"""
Global Microsoft Office Suite Engine for HWB Ecosystem
Provides adaptive Word (.docx), Excel (.xlsx), and Template Merging across 4 Client Archetypes.
"""

from .archetypes import ClientArchetype
from .palette import ArchetypeStyle, get_style, STYLES
from .word_builder import WordBuilder
from .excel_builder import ExcelBuilder
from .template_merger import TemplateMerger

__all__ = [
    "ClientArchetype",
    "ArchetypeStyle",
    "get_style",
    "STYLES",
    "WordBuilder",
    "ExcelBuilder",
    "TemplateMerger"
]
