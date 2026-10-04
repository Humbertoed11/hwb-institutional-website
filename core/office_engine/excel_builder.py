"""
Office Engine: Excel Builder Module
Builds executive, bank-grade commercial spreadsheets (.xlsx).
Features automated currency formatting, formula sums, auto-fitted columns, freeze panes, and print-ready layouts.
"""

import os
from typing import List, Dict, Any, Optional
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from .archetypes import ClientArchetype
from .palette import ArchetypeStyle, get_style

from .company import CompanyProfile, get_company

class ExcelBuilder:
    def __init__(
        self,
        sheet_title: str = "Commercial Estimate",
        company: Any = "HWB",
        archetype: ClientArchetype = ClientArchetype.REGIONAL
    ):
        self.sheet_title = sheet_title
        self.company: CompanyProfile = get_company(company)
        self.archetype = archetype
        self.style: ArchetypeStyle = get_style(archetype)
        
        self.wb = openpyxl.Workbook()
        self.ws = self.wb.active
        self.ws.title = sheet_title[:31]  # Excel 31-char tab limit
        self.ws.views.sheetView[0].showGridLines = True

        self.current_row = 1

    def add_title_block(
        self,
        title: str,
        client_name: str,
        project_ref: str = "EST-2026",
        date_str: str = "October 2026"
    ):
        """Adds a branded 4-row header card at the top of the spreadsheet."""
        # Row 1: Company Name
        c_co = self.ws.cell(row=self.current_row, column=1, value=self.company.legal_name.upper())
        c_co.font = Font(name=self.style.font_primary, size=11, bold=True, color=self.style.color_primary_hex)
        self.current_row += 1

        # Row 2: Document Title
        c_title = self.ws.cell(row=self.current_row, column=1, value=title.upper())
        c_title.font = Font(name=self.style.font_primary, size=14, bold=True, color=self.style.color_primary_hex)
        self.current_row += 1

        # Row 3: Metadata
        meta_text = f"CLIENT: {client_name}   |   REF: {project_ref}   |   DATE: {date_str}   |   PROFILE: {self.style.name.upper()}"
        c_meta = self.ws.cell(row=self.current_row, column=1, value=meta_text)
        c_meta.font = Font(name=self.style.font_primary, size=9, italic=True, color="64748B")
        self.current_row += 2 # Extra blank row spacer

    def add_table(
        self,
        headers: List[str],
        data: List[List[Any]],
        currency_col_indices: Optional[List[int]] = None,
        percentage_col_indices: Optional[List[int]] = None,
        integer_col_indices: Optional[List[int]] = None,
        has_total_row: bool = True,
        total_sum_col_indices: Optional[List[int]] = None
    ):
        """
        Builds an enterprise data table:
        - Primary color header band with white bold text
        - Alternating row background shading
        - Formatted numbers (currency, percentage, integers)
        - Automated SUM formulas on total row
        - Auto-fitted column widths
        - Freeze panes below the header row
        """
        curr_cols = currency_col_indices or []
        pct_cols = percentage_col_indices or []
        int_cols = integer_col_indices or []
        sum_cols = total_sum_col_indices or []

        start_row = self.current_row
        start_col = 1
        num_cols = len(headers)

        # 1. Freeze Panes directly below header
        self.ws.freeze_panes = self.ws.cell(row=start_row + 1, column=1)

        # 2. Header Row
        hdr_fill = PatternFill(start_color=self.style.color_primary_hex, end_color=self.style.color_primary_hex, fill_type="solid")
        hdr_font = Font(name=self.style.font_primary, size=10, bold=True, color="FFFFFF")
        hdr_border = Border(
            top=Side(style='thin', color=self.style.color_primary_hex),
            bottom=Side(style='medium', color=self.style.color_secondary_hex)
        )

        for col_idx, h_text in enumerate(headers, start=start_col):
            cell = self.ws.cell(row=start_row, column=col_idx, value=h_text)
            cell.fill = hdr_fill
            cell.font = hdr_font
            cell.border = hdr_border
            # Align right if numeric column
            if col_idx - start_col in curr_cols or col_idx - start_col in pct_cols or col_idx - start_col in int_cols:
                cell.alignment = Alignment(horizontal="right", vertical="center", wrap_text=True)
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

        self.ws.row_dimensions[start_row].height = 24
        self.current_row += 1

        # 3. Data Rows
        zebra_fill = PatternFill(start_color=self.style.color_bg_hex, end_color=self.style.color_bg_hex, fill_type="solid")
        white_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
        thin_border = Border(
            bottom=Side(style='thin', color="E2E8F0"),
            left=Side(style='thin', color="F1F5F9"),
            right=Side(style='thin', color="F1F5F9")
        )
        data_font = Font(name=self.style.font_primary, size=9.5, color=self.style.color_text_hex)

        first_data_row = self.current_row
        for row_idx, row_values in enumerate(data):
            r = self.current_row
            fill = white_fill if row_idx % 2 == 0 else zebra_fill
            self.ws.row_dimensions[r].height = 20

            for col_offset, val in enumerate(row_values):
                c = self.ws.cell(row=r, column=start_col + col_offset, value=val)
                c.fill = fill
                c.font = data_font
                c.border = thin_border

                # Formats
                if col_offset in curr_cols:
                    c.number_format = '"$"#,##0.00'
                    c.alignment = Alignment(horizontal="right", vertical="center")
                elif col_offset in pct_cols:
                    c.number_format = '0.0%'
                    c.alignment = Alignment(horizontal="right", vertical="center")
                elif col_offset in int_cols:
                    c.number_format = '#,##0'
                    c.alignment = Alignment(horizontal="right", vertical="center")
                else:
                    c.alignment = Alignment(horizontal="left", vertical="center")

            self.current_row += 1

        last_data_row = self.current_row - 1

        # 4. Total Summary Row
        if has_total_row and len(data) > 0:
            r = self.current_row
            self.ws.row_dimensions[r].height = 22
            total_font = Font(name=self.style.font_primary, size=10, bold=True, color=self.style.color_primary_hex)
            total_border = Border(
                top=Side(style='thin', color=self.style.color_primary_hex),
                bottom=Side(style='double', color=self.style.color_primary_hex)
            )

            # Label in column 1
            c_lbl = self.ws.cell(row=r, column=start_col, value="TOTAL")
            c_lbl.font = total_font
            c_lbl.border = total_border

            # Fill intermediate blank cells with border
            for col_idx in range(start_col + 1, start_col + num_cols):
                cell = self.ws.cell(row=r, column=col_idx)
                cell.font = total_font
                cell.border = total_border

            # Injected Sum Formulas
            for col_offset in sum_cols:
                col_letter = get_column_letter(start_col + col_offset)
                c_sum = self.ws.cell(
                    row=r,
                    column=start_col + col_offset,
                    value=f"=SUM({col_letter}{first_data_row}:{col_letter}{last_data_row})"
                )
                c_sum.font = total_font
                c_sum.border = total_border
                c_sum.alignment = Alignment(horizontal="right", vertical="center")
                if col_offset in curr_cols:
                    c_sum.number_format = '"$"#,##0.00'
                elif col_offset in int_cols:
                    c_sum.number_format = '#,##0'

            self.current_row += 2 # Extra spacing after table

        # 5. Auto-fit column widths
        for col_idx in range(start_col, start_col + num_cols):
            col_letter = get_column_letter(col_idx)
            max_len = 0
            for r in range(start_row, self.current_row):
                val = self.ws.cell(row=r, column=col_idx).value
                if val:
                    # Treat formula strings as shorter
                    val_str = str(val)
                    if not val_str.startswith("="):
                        max_len = max(max_len, len(val_str))
            self.ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    def save(self, filepath: str):
        """Saves the workbook, creating directories if needed."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        self.wb.save(filepath)
        return filepath
