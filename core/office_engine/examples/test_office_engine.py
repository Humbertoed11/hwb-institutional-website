import os
from office_engine import ClientArchetype, WordBuilder, ExcelBuilder

def test_boutique_generation():
    print("Testing Boutique Commercial Word Generation...")
    builder = WordBuilder(
        doc_title="Dental Clinic Sanitization Proposal",
        archetype=ClientArchetype.BOUTIQUE
    )
    builder.setup_header_footer(doc_ref_id="HWB-PROP-DENTAL-01")
    builder.add_cover_page(
        subtitle="Medical-Grade Evening Hygiene & Operatory Care",
        client_name="Preston Hollow Family Dentistry",
        facility_address="8222 Douglas Ave., Suite 400, Dallas, TX 75225",
        date_str="October 2026"
    )
    builder.add_heading("Section 1: Boutique Medical Standard", level=1)
    builder.add_paragraph("We understand that a boutique dental practice requires spotless operatories, fresh air, and pristine patient waiting lounges.")
    builder.add_callout_box(
        title="Operatory Cross-Contamination Protocol",
        text="Dedicated microfiber cloths and hospital-grade EPA hospital disinfectants ensuring patient safety and zero chemical odor.",
        badge="Safety First"
    )
    headers = ["Service Scope", "Frequency", "Monthly Value"]
    data = [
        ["Nightly Operatory & Lobby Sanitization", "5 Nights / Week", "$1,450.00"],
        ["Quarterly Hard Floor Buff & Polish", "4x / Year", "INCLUDED ($0.00)"],
        ["Emergency Touch-Up Service", "On-Call", "INCLUDED ($0.00)"]
    ]
    builder.add_table(headers, data, align_right_cols=[2])
    builder.add_signature_block(client_name="Preston Hollow Family Dentistry")
    
    out_docx = "/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-QUOTES/test_boutique_proposal.docx"
    builder.save(out_docx)
    print(f"Boutique Word doc created: {out_docx} ({os.path.getsize(out_docx)} bytes)")

def test_excel_estimating_sheet():
    print("Testing Excel Estimating Sheet Generation...")
    excel = ExcelBuilder(sheet_title="Commercial Estimate", archetype=ClientArchetype.REGIONAL)
    excel.add_title_block(
        title="Commercial Facility Estimate & Labor Takeoff",
        client_name="Regional Educational Center #1711",
        project_ref="HWB-EST-CORINTH-2026"
    )
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
    out_xlsx = "/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-QUOTES/test_estimate_model.xlsx"
    excel.save(out_xlsx)
    print(f"Excel Sheet created: {out_xlsx} ({os.path.getsize(out_xlsx)} bytes)")

if __name__ == "__main__":
    test_boutique_generation()
    test_excel_estimating_sheet()
    print("ALL TESTS PASSED!")
