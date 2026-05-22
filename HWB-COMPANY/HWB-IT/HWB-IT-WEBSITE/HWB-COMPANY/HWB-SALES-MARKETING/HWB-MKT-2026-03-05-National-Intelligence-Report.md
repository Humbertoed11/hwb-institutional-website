| **Document Control** |                                              |
| :------------------- | :------------------------------------------- |
| **Document Title**   | **National Data Intelligence Report**        |
| **Document ID**      | HWB-MKT-NIR-001                              |
| **Version**          | 2.0.0                                        |
| **Status**           | APPROVED                                     |
| **Author**           | George (Architect)                           |
| **Approved By**      | Humberto Dominguez, CEO                      |
| **Date**             | 05/21/2026                                   |
| **ISO 9001 Clause**  | 8.1 (Operational Planning)                   |

---

# Standard Operating Procedure: **National Data Intelligence Report**

## 1.0 Purpose
To centralize and govern high-fidelity national data assets for market expansion. This ensures that HWB targets "Fidelity-Ready" facilities with verified empirical data.

## 2.0 Scope
Applies to all national datasets including EPA ECHO, CMS Healthcare Registry, and Logistics Hub maps.

## 3.0 Universal Mandates (2026 Baseline)
1. **Guidance First:** If a dataset's API changes, ASK the CEO before attempting an exhaustive fix.
2. **Tier 6 Telemetry:** Every data ingestion milestone must be logged.
3. **Physical Truth:** Reference absolute server paths for all bulk CSV/JSON downloads.

## 4.0 Core Data Assets
*   **EPA ECHO:** 1.5 Million+ active industrial facilities. Coverage for logistics and manufacturing.
*   **CMS National Registry:** Comprehensive hospital and clinic database for medical-grade cleaning.
*   **DFW Logistics Map:** Localized industrial targets for warehouse floor care.

## 5.0 Procedure
1.  **Harvesting:** Use the Lead Ingestor script to pull data from verified sources.
2.  **Verification:** Filter for NAICS code 561720 (Janitorial).
3.  **Persistence:** Store all raw data in `HWB-COMPANY/HWB-DATA/`.

## 6.0 Verification (Zero-Defect Check)
*   Data contains zero "synthetic" entries.
*   Addresses match verified US Postal Service standards.

## 7.0 Revision History
| Version | Date | Author | Change Description |
| :--- | :--- | : :--- | :--- |
| 2.0.0 | 05/21/2026 | George | TOTAL MODERNIZATION. Consolidated report into SOP format and added 2026 mandates. |
| 1.0 | 2026-03-05 | Lauri Tells | Initial Data Intelligence Sweep. |
