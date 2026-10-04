---
name: microsoft-office-architect
description: >-
  Standardizes and generates Fortune 500 & institutional-grade Microsoft Office Suite documents
  (Word .docx, Excel .xlsx, PowerPoint .pptx, and Outlook letterheads) across 4 Client Archetypes:
  Boutique Commercial, Regional Corporate, Institutional & Government, and Construction Subcontracting.
  Use whenever creating quotes, proposals, contracts, estimating spreadsheets, or financial reports.
---

# Microsoft Office Suite Architect: Global Document Standards

This skill governs the automated creation and formatting of all Microsoft Word (`.docx`), Microsoft Excel (`.xlsx`), and Microsoft PowerPoint (`.pptx`) documents across the HWB ecosystem.

The core principle: **Not all clients are institutions.**
The visual density, legal formality, and design layout must dynamically adapt to the target client archetype.

---

## 1. The 4 Client Archetypes

| Archetype | Target Audience | Length | Tone & Design Focus | Contract Strategy |
| :--- | :--- | :--- | :--- | :--- |
| **`ClientArchetype.BOUTIQUE`** | Local single daycares, dental clinics, boutique law offices, local retail | 2 – 3 Pages | Warm, clean, approachable, generous white space, soft slate text | Clean 1-Page Service Agreement (low friction, friendly terms) |
| **`ClientArchetype.REGIONAL`** | Multi-unit childcare, corporate regional offices, commercial buildings | 3 – 5 Pages | Executive, data-backed, technology and inspection app highlights | Option 1 Term Lock with 30-Day Right to Cure & Floor Care Amortization |
| **`ClientArchetype.INSTITUTIONAL`**| ISDs, colleges, municipal governments, state agencies, hospital systems | 6 – 12 Pages | Strict compliance, audit-ready, CAGE/NAICS codes, EMR safety, bonding | Formal 18-Clause Enforceable Agreement with Texas Venue & Statutory Shields |
| **`ClientArchetype.CONSTRUCTION`** | General Contractors (GCs), tenant finish-out, commercial ground-up | 2 – 4 Pages + Excel | CSI MasterFormat (Div 01 74 13 / 01 74 23), safety-hardened, phased | AIA billing schedule, lien waiver terms, phased rough/final/fluff takeoffs |

---

## 2. Using the Global `office_engine` Library

The engine is installed globally in the Python environment:
```python
from office_engine import ClientArchetype, WordBuilder, ExcelBuilder, TemplateMerger
```

### A. Creating a Master Word Document (.docx)
```python
from office_engine import ClientArchetype, WordBuilder

# 1. Initialize with appropriate archetype
builder = WordBuilder(
    doc_title="Commercial Janitorial Proposal",
    archetype=ClientArchetype.REGIONAL,
    margin_inches=0.75
)

# 2. Configure running headers & dynamic "Page X of Y" footers
builder.setup_header_footer(doc_ref_id="HWB-PROP-2026")

# 3. Add styled cover page
builder.add_cover_page(
    subtitle="Comprehensive Nightly Hygiene & Floor Care Agreement",
    client_name="Legacy Professional Pavilion",
    facility_address="5400 Legacy Dr., Plano, TX 75024",
    date_str="October 2026"
)

# 4. Add headings and body text
builder.add_heading("Section 1: Executive Hygiene Standard", level=1)
builder.add_paragraph("Our medical-grade sanitization system adheres strictly to TCCR Chapter 746 standards.")

# 5. Add callout cards (shaded with 4px left accent border)
builder.add_callout_box(
    title="Morning Readiness Guarantee",
    text="Our supervisors conduct digital photographic audits every evening. If any area fails inspection, our rapid-response crew corrects it within 2 hours.",
    badge="Service SLA"
)

# 6. Add enterprise tables (dark header, zebra rows, padded cells, auto-repeating headers)
headers = ["Service Scope", "Frequency", "Monthly Value"]
data = [
    ["Nightly Disinfection & Trash", "5 Days / Week", "$2,100.00"],
    ["Semi-Annual VCT Strip & Wax", "2x / Year", "INCLUDED ($0.00)"],
    ["Semi-Annual Carpet Extraction", "2x / Year", "INCLUDED ($0.00)"]
]
builder.add_table(headers, data, align_right_cols=[2])

# 7. Add double-column signature block
builder.add_signature_block(client_name="Legacy Professional Pavilion")

# 8. Save
builder.save("/path/to/output.docx")
```

### B. Creating an Executive Excel Spreadsheet (.xlsx)
```python
from office_engine import ClientArchetype, ExcelBuilder

# 1. Initialize
excel = ExcelBuilder(sheet_title="Commercial Estimate", archetype=ClientArchetype.REGIONAL)

# 2. Add title block
excel.add_title_block(
    title="Commercial Facility Estimate & Labor Takeoff",
    client_name="Xplor Childcare Center #1711",
    project_ref="HWB-EST-CORINTH"
)

# 3. Add structured data table with currency and sum formulas
headers = ["Cost Component", "Quantity / Sq. Ft.", "Unit Rate", "Monthly Cost", "Annual Total"]
data = [
    ["Direct Custodial Labor (2.5 hrs/day)", 54.25, 21.50, 1166.38, 13996.56],
    ["Chemicals & Consumable Equipment", 10000, 0.012, 120.00, 1440.00],
    ["Supervision & Digital QA Inspections", 1, 200.00, 200.00, 2400.00],
    ["Periodic Floor Care Amortization", 10000, 0.025, 250.00, 3000.00]
]

excel.add_table(
    headers=headers,
    data=data,
    currency_col_indices=[2, 3, 4],
    has_total_row=True,
    total_sum_col_indices=[3, 4]
)

# 4. Save
excel.save("/path/to/estimate.xlsx")
```

---

## 3. Formatting & Design Rules (Never Violate)

1. **No Harsh Gridlines:** Tables must never use heavy black border lines. Use subtle `#E2E8F0` or `#CBD5E1` horizontal dividers, with dark solid fills on the header row.
2. **Generous Internal Padding:** Always ensure table cells have at least 80–100 dxa (4–6pt) top and bottom padding, and 120–140 dxa (6–8pt) left and right padding.
3. **No Unformatted Numbers:** Financial columns must always be formatted as Currency (`$#,##0.00`) and aligned to the right.
4. **Repeat Table Headers:** Any multi-page table must have `w:tblHeader` enabled so readers never see detached data on page 2.
5. **No Broken Rows:** Every table row must have `w:cantSplit` enabled so rows do not break awkwardly across page breaks.
6. **Freeze Panes in Excel:** Every commercial spreadsheet must freeze panes below the header row so the column labels stay visible when scrolling down large datasets.
