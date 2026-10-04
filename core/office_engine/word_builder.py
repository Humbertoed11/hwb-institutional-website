"""
Office Engine: Word Builder Module
Builds Fortune 500 & Enterprise-grade Microsoft Word (.docx) documents.
Supports all 4 Client Archetypes with dynamic headers, footers, zebra tables, and callout cards.
"""

import os
from typing import List, Dict, Any, Optional
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from .archetypes import ClientArchetype
from .palette import ArchetypeStyle, get_style
from .company import CompanyProfile, get_company

class WordBuilder:
    def __init__(
        self,
        doc_title: str,
        company: Any = "HWB",
        archetype: ClientArchetype = ClientArchetype.REGIONAL,
        margin_inches: float = 0.75
    ):
        self.doc_title = doc_title
        self.company: CompanyProfile = get_company(company)
        self.archetype = archetype
        self.style: ArchetypeStyle = get_style(archetype)
        self.doc = docx.Document()
        
        # Configure margins
        for sec in self.doc.sections:
            sec.top_margin = Inches(margin_inches)
            sec.bottom_margin = Inches(margin_inches)
            sec.left_margin = Inches(margin_inches)
            sec.right_margin = Inches(margin_inches)
            # Differentiate first page for cover page
            sec.different_first_page_header_footer = True

        self._configure_default_styles()

    def _configure_default_styles(self):
        """Sets default font and paragraph spacing."""
        normal_style = self.doc.styles['Normal']
        normal_style.font.name = self.style.font_primary
        normal_style.font.size = Pt(9.5)
        normal_style.font.color.rgb = self.style.rgb_text

    @staticmethod
    def _set_cell_background(cell, fill_hex: str):
        tcPr = cell._tc.get_or_add_tcPr()
        shd = OxmlElement('w:shd')
        shd.set(qn('w:val'), 'clear')
        shd.set(qn('w:color'), 'auto')
        shd.set(qn('w:fill'), fill_hex.lstrip('#'))
        tcPr.append(shd)

    @staticmethod
    def _set_cell_margins(cell, top=100, bottom=100, left=140, right=140):
        tcPr = cell._tc.get_or_add_tcPr()
        tcMar = OxmlElement('w:tcMar')
        for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
            node = OxmlElement(f'w:{m}')
            node.set(qn('w:w'), str(val))
            node.set(qn('w:type'), 'dxa')
            tcMar.append(node)
        tcPr.append(tcMar)

    @staticmethod
    def _set_callout_borders(cell, border_color_hex: str):
        """Creates a modern callout card border: thick left border, no top/right/bottom."""
        tcPr = cell._tc.get_or_add_tcPr()
        tcBorders = OxmlElement('w:tcBorders')
        
        # Thick left border
        left = OxmlElement('w:left')
        left.set(qn('w:val'), 'single')
        left.set(qn('w:sz'), '24') # 3pt width
        left.set(qn('w:space'), '0')
        left.set(qn('w:color'), border_color_hex.lstrip('#'))
        tcBorders.append(left)

        for b in ['top', 'bottom', 'right']:
            node = OxmlElement(f'w:{b}')
            node.set(qn('w:val'), 'none')
            tcBorders.append(node)
            
        tcPr.append(tcBorders)

    @staticmethod
    def _add_field(paragraph, field_name: str):
        """Adds a native Microsoft Word dynamic field code (PAGE, NUMPAGES)."""
        run = paragraph.add_run()
        fldChar1 = OxmlElement('w:fldChar')
        fldChar1.set(qn('w:fldCharType'), 'begin')
        instrText = OxmlElement('w:instrText')
        instrText.set(qn('xml:space'), 'preserve')
        instrText.text = field_name
        fldChar2 = OxmlElement('w:fldChar')
        fldChar2.set(qn('w:fldCharType'), 'separate')
        fldChar3 = OxmlElement('w:fldChar')
        fldChar3.set(qn('w:fldCharType'), 'end')
        
        run._r.append(fldChar1)
        run._r.append(instrText)
        run._r.append(fldChar2)
        run._r.append(fldChar3)

    def setup_header_footer(self, doc_ref_id: str = "PROPOSAL-2026", footer_company_text: Optional[str] = None):
        """Configures running headers and dynamic page-numbered footers for subsequent pages."""
        section = self.doc.sections[0]
        f_text = footer_company_text or self.company.footer_text
        
        # 1. Header
        header = section.header
        p_hdr = header.paragraphs[0]
        p_hdr.text = ""
        r_hdr_l = p_hdr.add_run(f"{self.company.name.upper()}  •  {self.doc_title.upper()}")
        r_hdr_l.font.size = Pt(8)
        r_hdr_l.font.bold = True
        r_hdr_l.font.color.rgb = self.style.rgb_primary

        r_hdr_space = p_hdr.add_run("   |   ")
        r_hdr_space.font.size = Pt(8)
        r_hdr_space.font.color.rgb = self.style.rgb_border

        r_hdr_r = p_hdr.add_run(f"REF: {doc_ref_id} • CONFIDENTIAL")
        r_hdr_r.font.size = Pt(8)
        r_hdr_r.font.color.rgb = RGBColor(100, 116, 139)

        # 2. Footer
        footer = section.footer
        p_ftr = footer.paragraphs[0]
        p_ftr.text = ""
        
        r_ftr_l = p_ftr.add_run(f"{f_text}   —   ")
        r_ftr_l.font.size = Pt(8)
        r_ftr_l.font.color.rgb = RGBColor(100, 116, 139)

        r_page_lbl = p_ftr.add_run("Page ")
        r_page_lbl.font.size = Pt(8)
        r_page_lbl.font.color.rgb = self.style.rgb_primary
        r_page_lbl.font.bold = True
        
        self._add_field(p_ftr, "PAGE")
        
        r_of = p_ftr.add_run(" of ")
        r_of.font.size = Pt(8)
        r_of.font.color.rgb = RGBColor(100, 116, 139)
        
        self._add_field(p_ftr, "NUMPAGES")

    def add_cover_page(
        self,
        subtitle: str,
        client_name: str,
        facility_address: str,
        date_str: str = "October 2026",
        author_name: Optional[str] = None,
        author_title: Optional[str] = None
    ):
        """Generates a styled executive cover page adapted to the client archetype."""
        name = author_name or f"{self.company.primary_officer}, {self.company.officer_title}"

        # Top Archetype Badge
        p_top = self.doc.add_paragraph()
        p_top.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r_badge = p_top.add_run(f"COMMERCIAL SPECIFICATION • {self.style.name.upper()}")
        r_badge.font.size = Pt(8)
        r_badge.font.bold = True
        r_badge.font.color.rgb = self.style.rgb_secondary

        # Main Title Block
        p_title = self.doc.add_paragraph()
        p_title.paragraph_format.space_before = Pt(36)
        p_title.paragraph_format.space_after = Pt(8)
        
        r_co = p_title.add_run(f"{self.company.legal_name.upper()}\n")
        r_co.font.size = Pt(16)
        r_co.font.bold = True
        r_co.font.color.rgb = self.style.rgb_primary

        r_main = p_title.add_run(f"{self.doc_title}\n")
        r_main.font.size = Pt(22)
        r_main.font.bold = True
        r_main.font.color.rgb = self.style.rgb_primary

        r_sub = p_title.add_run(subtitle)
        r_sub.font.size = Pt(12)
        r_sub.font.italic = True
        r_sub.font.color.rgb = self.style.rgb_secondary

        # Metadata Card (Box)
        self.doc.add_paragraph() # Spacer
        t_meta = self.doc.add_table(rows=1, cols=1)
        t_meta.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = t_meta.cell(0, 0)
        self._set_cell_background(cell, self.style.color_bg_hex)
        self._set_callout_borders(cell, self.style.color_secondary_hex)
        self._set_cell_margins(cell, top=140, bottom=140, left=180, right=180)

        p_m = cell.paragraphs[0]
        p_m.paragraph_format.line_spacing = 1.2
        
        r_mh = p_m.add_run("PROPOSAL & CONTRACT METADATA\n\n")
        r_mh.font.bold = True
        r_mh.font.size = Pt(10)
        r_mh.font.color.rgb = self.style.rgb_primary

        meta_lines = [
            ("PREPARED FOR:", client_name),
            ("FACILITY / PROJECT:", facility_address),
            ("DATE:", date_str),
            ("PREPARED BY:", name),
            ("ORGANIZATION:", f"{self.company.name} ({self.company.tagline})"),
            ("DIRECT CONTACT:", f"{self.company.phone} | {self.company.email} | {self.company.website}")
        ]

        for k, v in meta_lines:
            rk = p_m.add_run(f"{k} ")
            rk.font.bold = True
            rk.font.size = Pt(9)
            rk.font.color.rgb = self.style.rgb_primary

            rv = p_m.add_run(f"{v}\n")
            rv.font.size = Pt(9)
            rv.font.color.rgb = self.style.rgb_text

        self.doc.add_page_break()

    def add_heading(self, text: str, level: int = 1):
        """Adds a styled heading matching the archetype palette."""
        p = self.doc.add_paragraph()
        p.paragraph_format.keep_with_next = True
        
        if level == 1:
            p.paragraph_format.space_before = Pt(16)
            p.paragraph_format.space_after = Pt(6)
            r = p.add_run(text)
            r.font.size = Pt(13)
            r.font.bold = True
            r.font.color.rgb = self.style.rgb_primary
        elif level == 2:
            p.paragraph_format.space_before = Pt(12)
            p.paragraph_format.space_after = Pt(4)
            r = p.add_run(text)
            r.font.size = Pt(11)
            r.font.bold = True
            r.font.color.rgb = self.style.rgb_secondary
        else:
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(2)
            r = p.add_run(text)
            r.font.size = Pt(10)
            r.font.bold = True
            r.font.color.rgb = self.style.rgb_primary

    def add_paragraph(self, text: str, bold_prefix: str = "", italic: bool = False):
        """Adds standard body paragraph with 1.15 line spacing and 4pt after."""
        p = self.doc.add_paragraph()
        p.paragraph_format.line_spacing = 1.15
        p.paragraph_format.space_after = Pt(4)
        
        if bold_prefix:
            rb = p.add_run(bold_prefix + " ")
            rb.font.bold = True
            rb.font.size = Pt(9.5)
            rb.font.color.rgb = self.style.rgb_primary

        r = p.add_run(text)
        r.font.size = Pt(9.5)
        r.font.italic = italic
        r.font.color.rgb = self.style.rgb_text

    def add_bullet(self, text: str, bold_prefix: str = ""):
        """Adds clean list bullet point."""
        p = self.doc.add_paragraph(style='List Bullet')
        p.paragraph_format.line_spacing = 1.1
        p.paragraph_format.space_after = Pt(2)
        
        if bold_prefix:
            rb = p.add_run(bold_prefix + " ")
            rb.font.bold = True
            rb.font.size = Pt(9)
            rb.font.color.rgb = self.style.rgb_primary

        r = p.add_run(text)
        r.font.size = Pt(9)
        r.font.color.rgb = self.style.rgb_text

    def add_callout_box(self, title: str, text: str, badge: Optional[str] = None):
        """Adds a shaded highlight card with thick colored left border."""
        t = self.doc.add_table(rows=1, cols=1)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = t.cell(0, 0)
        self._set_cell_background(cell, self.style.color_bg_hex)
        self._set_callout_borders(cell, self.style.color_secondary_hex)
        self._set_cell_margins(cell, top=100, bottom=100, left=140, right=140)

        p = cell.paragraphs[0]
        p.paragraph_format.line_spacing = 1.15
        
        if badge:
            rb = p.add_run(f"[{badge.upper()}] ")
            rb.font.bold = True
            rb.font.size = Pt(8.5)
            rb.font.color.rgb = self.style.rgb_secondary

        rt = p.add_run(f"{title}\n")
        rt.font.bold = True
        rt.font.size = Pt(10)
        rt.font.color.rgb = self.style.rgb_primary

        rx = p.add_run(text)
        rx.font.size = Pt(9)
        rx.font.color.rgb = self.style.rgb_text

        self.doc.add_paragraph() # Spacer

    def add_table(
        self,
        headers: List[str],
        data: List[List[str]],
        col_widths: Optional[List[float]] = None,
        align_right_cols: Optional[List[int]] = None
    ):
        """
        Creates an enterprise-formatted table:
        - Primary color header row with white text
        - Repeating table headers across page breaks (w:tblHeader)
        - Non-splitting rows across page breaks (w:cantSplit)
        - Alternating row zebra striping
        - Custom cell padding
        """
        align_right = align_right_cols or []
        t = self.doc.add_table(rows=len(data) + 1, cols=len(headers))
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        
        # 1. Header Row
        hdr_row = t.rows[0]
        # Repeat header across page breaks
        trPr = hdr_row._tr.get_or_add_trPr()
        trPr.append(OxmlElement('w:tblHeader'))

        for col_idx, h_text in enumerate(headers):
            cell = hdr_row.cells[col_idx]
            self._set_cell_background(cell, self.style.color_primary_hex)
            self._set_cell_margins(cell, top=90, bottom=90, left=120, right=120)
            p = cell.paragraphs[0]
            if col_idx in align_right:
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            r = p.add_run(h_text)
            r.font.bold = True
            r.font.size = Pt(9)
            r.font.color.rgb = RGBColor(255, 255, 255)

        # 2. Data Rows
        for row_idx, row_values in enumerate(data, start=1):
            row = t.rows[row_idx]
            # Prevent row split across pages
            r_trPr = row._tr.get_or_add_trPr()
            r_trPr.append(OxmlElement('w:cantSplit'))

            bg_hex = "FFFFFF" if row_idx % 2 == 1 else self.style.color_bg_hex

            for col_idx, val in enumerate(row_values):
                cell = row.cells[col_idx]
                self._set_cell_background(cell, bg_hex)
                self._set_cell_margins(cell, top=80, bottom=80, left=120, right=120)
                p = cell.paragraphs[0]
                if col_idx in align_right:
                    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                r = p.add_run(str(val))
                r.font.size = Pt(8.8)
                r.font.color.rgb = self.style.rgb_text

        # 3. Column Widths
        if col_widths and len(col_widths) == len(headers):
            for row in t.rows:
                for col_idx, w in enumerate(col_widths):
                    row.cells[col_idx].width = Inches(w)

        self.doc.add_paragraph() # Spacer

    def add_signature_block(self, client_name: str, hwb_signer: Optional[str] = None):
        """Creates a clean double-column execution card."""
        signer = hwb_signer or f"{self.company.primary_officer}, {self.company.officer_title}"
        self.doc.add_paragraph() # Spacer
        t = self.doc.add_table(rows=6, cols=2)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER

        headers = [f"FOR {client_name.upper()}", f"FOR {self.company.legal_name.upper()}"]
        for i, h in enumerate(headers):
            cell = t.cell(0, i)
            self._set_cell_background(cell, self.style.color_primary_hex)
            self._set_cell_margins(cell, top=80, bottom=80, left=120, right=120)
            p = cell.paragraphs[0]
            r = p.add_run(h)
            r.font.bold = True
            r.font.size = Pt(9)
            r.font.color.rgb = RGBColor(255, 255, 255)

        sig_rows = [
            ("Company: ____________________________", f"Company: {self.company.legal_name}"),
            ("Signature: __________________________", "Signature: __________________________"),
            ("Printed Name: _______________________", f"Printed Name: {signer.split(',')[0]}"),
            ("Title: ______________________________", f"Title: {signer.split(',')[1].strip() if ',' in signer else self.company.officer_title}"),
            ("Date: _______________________________", "Date: _______________________________")
        ]

        for row_idx, (c0_text, c1_text) in enumerate(sig_rows, start=1):
            bg = "FFFFFF" if row_idx % 2 == 1 else self.style.color_bg_hex
            c0 = t.cell(row_idx, 0)
            c1 = t.cell(row_idx, 1)
            self._set_cell_background(c0, bg)
            self._set_cell_background(c1, bg)
            self._set_cell_margins(c0, top=90, bottom=90, left=120, right=120)
            self._set_cell_margins(c1, top=90, bottom=90, left=120, right=120)

            p0 = c0.paragraphs[0]
            r0 = p0.add_run(c0_text)
            r0.font.size = Pt(8.8)
            r0.font.color.rgb = self.style.rgb_primary

            p1 = c1.paragraphs[0]
            r1 = p1.add_run(c1_text)
            r1.font.size = Pt(8.8)
            r1.font.color.rgb = self.style.rgb_primary

    def save(self, filepath: str):
        """Saves the document, creating directories if needed."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        self.doc.save(filepath)
        return filepath
