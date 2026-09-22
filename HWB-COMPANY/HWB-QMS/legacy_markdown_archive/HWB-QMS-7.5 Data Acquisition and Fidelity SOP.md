| **Document Control** |                                              |
| :------------------- | :------------------------------------------- |
| **Document Title**   | **Data Acquisition and Fidelity SOP**        |
| **Document ID**      | HWB-QMS-7.5-DAF                              |
| **Version**          | 2.0.0                                        |
| **Status**           | APPROVED                                     |
| **Author**           | George (Architect)                           |
| **Approved By**      | Humberto Dominguez, CEO                      |
| **Date**             | 05/21/2026                                   |
| **ISO 9001 Clause**  | 8.1 (Operational Planning)                   |

---

# Standard Operating Procedure: **Data Acquisition and Fidelity**

## 1.0 Purpose
This SOP establishes strict protocols for the acquisition, validation, and injection of external datasets into the SigmaFidelity™ CRM. It ensures that only high-fidelity, verified, and non-synthetic data enters the institutional value chain.

## 2.0 Universal Mandates (2026 Baseline)
1. **The Operator Charter:** strictly industrial execution—zero synthetic data.
2. **Guidance First:** If a dataset fails the fidelity gate (sampling), ASK the CEO before attempting manual repair.
3. **Tier 6 Telemetry:** Every ETL (Extract, Transform, Load) cycle must be logged in the Tactical DB.

## 3.0 Procedure: The Fidelity Pipeline

### 3.1 Acquisition & Secure Transfer
1.  **Source Identification:** Datasets must originate from official government (.gov) or verified institutional portals.
2.  **Secure Landing:** Store raw files in `/HWB-DATA/HWB-RAW-DATA/`.
3.  **Integrity Check:** Execute MD5 checksum to ensure no corruption occurred during transfer.

### 3.2 Data Sampling (Fidelity Gate)
1.  **Sampling:** Extract a 10-record random sample.
2.  **Verification:** Physically verify that the 10 facilities exist at the listed addresses.
3.  **Gate:** If >1 record is unverified, the entire dataset is rejected.

### 3.3 Relational Injection
1.  **Deduplication:** Check for existing License Numbers in the Leads table.
2.  **Schema Alignment:** Map data to the standardized 10-field SigmaFidelity™ schema.
3.  **Archival:** Move raw files to the `/ARCHIVE` subfolder to maintain a "Zero-Muda" landing zone.

## 4.0 Verification (Zero-Defect Check)
*   Registry Audit confirms 100% match between archived files and CRM records.
*   Director names verified against LinkedIn decision-maker intelligence.

## 5.0 Revision History
| Version | Date | Author | Change Description |
| :--- | :--- | :--- | :--- |
| 2.0.0 | 05/21/2026 | George | TOTAL MODERNIZATION. Added 2026 mandates and Tier 6 lifecycle tracking. |
| 1.1 | 2026-03-05 | Nick Doria | Initial Data Acquisition protocol. |
| 1.0 | 2026-03-05 | George | Initial Release. |
