| **Document Control** |                                              |
| :------------------- | :------------------------------------------- |
| **Document Title**   | **Texas Institutional Intelligence Report** |
| **Document ID**      | HWB-MKT-NIR-002                              |
| **Version**          | 2.0.0                                        |
| **Status**           | APPROVED                                     |
| **Author**           | George (Architect)                           |
| **Approved By**      | Humberto Dominguez, CEO                      |
| **Date**             | 05/21/2026                                   |
| **ISO 9001 Clause**  | 8.1 (Operational Planning)                   |

---

# Standard Operating Procedure: **Texas Institutional Intelligence Report**

## 1.0 Purpose
This report details high-fidelity, free public data assets for the Texas institutional market. We have identified specific portals for Universities, K-12 Districts, and Municipal structures that align with the SigmaFidelity™ market capture strategy.

## 2.0 Scope
Applies to all Texas-specific datasets including THECB, TEA/AskTED, and TxGIO DataHub.

## 3.0 Universal Mandates (2026 Baseline)
1. **Guidance First:** If a state agency's portal is locked, ASK the CEO before attempting to bypass.
2. **Tier 6 Telemetry:** Log all data extractions from Texas portals.
3. **Physical Truth:** Store all bulk CSV exports in the `/HWB-DATA/` directory.

## 4.0 Texas Data Assets
*   **Public Universities (THECB):** Master list of Higher Ed institutions for multi-building cleaning opportunities.
*   **K-12 Districts (TEA / AskTED):** 100% verified campus addresses for compliance-heavy cleaning.
*   **Municipal Structures (TxGIO):** Granular data for courthouses, police stations, and city halls.

## 5.0 Procedure
1.  **Extraction:** Pull data using the unified fields standard (Operation_Name, Address, Phone, Email, SQF).
2.  **Verification:** Cross-check against the Texas Comptroller Business API.
3.  **Injection:** Map data into the Lead Pipeline for Silas Sync.

## 6.0 Verification (Zero-Defect Check)
*   No duplicate records for DFW metroplex campuses.
*   Emails follow the professional administrative format.

## 7.0 Revision History
| Version | Date | Author | Change Description |
| :--- | :--- | :--- | :--- |
| 2.0.0 | 05/21/2026 | George | TOTAL MODERNIZATION. Consolidated report into SOP format and added 2026 mandates. |
| 1.0 | 2026-03-05 | Silas Sync | Initial Texas Intelligence Sweep. |
