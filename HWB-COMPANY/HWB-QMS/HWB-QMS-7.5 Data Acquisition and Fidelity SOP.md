| **Document Control** |                                              |
| :------------------- | :------------------------------------------- |
| **Document Title**   | **Data Acquisition and Fidelity SOP**        |
| **Document ID**      | HWB-QMS-7.5-DAF                              |
| **Version**          | 1.0                                          |
| **Status**           | Active                                       |
| **Author**           | Nick Doria (VP Prompt Engineering)           |
| **Approved By**      | Humberto Dominguez (CEO)                     |
| **Date**             | 2026-03-05                                   |

---

# 1.0 Purpose
This SOP establishes strict protocols for the acquisition, validation, and injection of external datasets into the SigmaFidelity™ CRM. It ensures that only high-fidelity, verified, and non-synthetic data enters the institutional value chain.

# 2.0 Scope
Applies to all ETL (Extract, Transform, Load) operations performed by the Marketing, Sales, and IT divisions across all US state and federal datasets.

# 3.0 Procedure: The Fidelity Pipeline

## 3.1 Acquisition & Secure Transfer (Download)
1.  **Source Identification:** Datasets must originate from official government (.gov) or verified institutional portals.
2.  **Secure Landing:** All raw files must be stored in `HWB-COMPANY/HWB-SALES-MARKETING/HWB-RAW-DATA/`.
3.  **Integrity Check:** Execute `file [filename]` to verify the file format and MD5 checksum (where available) to ensure no corruption occurred during transfer.

## 3.2 Data Sampling (Fidelity Verification)
1.  **Random Sampling:** Extract a 10-record random sample from the raw file.
2.  **Physical Verification:** Use Google Maps or official agency lookups to verify that the 10 sampled facilities physically exist at the listed addresses.
3.  **Fidelity Gate:** If more than 1 record in the sample is unverified or synthetic, the entire dataset is rejected.

## 3.3 Data Criteria Selection (Transformation)
Before injection, data must be filtered based on the following **Institutional Tiers**:
*   **Tier 1 (High Yield):** Facilities with Capacity >= 99 OR Square Footage >= 15,000.
*   **Tier 2 (Growth):** Public institutional entities (Universities, School Districts, Municipal Hubs).
*   **NAICS Filtering (Mandatory):** For state and federal datasets (e.g., SAM.gov, TX Comptroller), only records matching the following codes are permitted for acquisition:
    *   **561720:** Janitorial Services (Core Operations)
    *   **561210:** Facilities Support Services (Strategic Expansion)
*   **Sector Tagging:** Industry tags must be assigned (e.g., "Child Care," "Higher Ed," "Logistics").

## 3.4 Relational Injection & Lifecycle Management (Loading)
1.  **Deduplication:** The Ingestion Engine must check for existing `center_name` or `License_Number` in `sigma_leads.db` to prevent redundancy.
2.  **Schema Alignment:** Data must be mapped to the standardized 10-field SigmaFidelity™ schema.
3.  **Execution:** Run the approved `Lead Ingestor.py` script.
4.  **Lifecycle Logging:** The engine automatically records the file, count, and timestamp in the `Data_Processing_Registry.csv`.
5.  **Archival:** The raw CSV file is automatically moved to the `HWB-RAW-DATA/ARCHIVE/` subfolder to maintain a "Zero-Muda" (clean) landing zone.
6.  **Telemetry:** Log the successful injection in the **Executive Pulse** activity feed.

# 4.0 Verification
*   **Audit Live:** All new injections must be visible in the Marketing Pipeline (The Hive).
*   **Registry Audit:** The Data Processing Registry must perfectly match the archived files.
*   **Director Verification:** Spot-check Director names against LinkedIn to ensure decision-maker accuracy.

# 5.0 Notes and Cautions
*   **Muda Reduction:** Avoid ingesting entire states unless the Tier 1 criteria are met. Focus on the "Growth Corridors."
*   **Absolute Pathing:** Never use relative paths in ingestion scripts to prevent data loss during system migrations.

---

## 6.0 Revision History
| Version | Date | Author | Change Description |
| :--- | :--- | :--- | :--- |
| 1.0 | 2026-03-05 | Nick Doria | Initial Data Acquisition & Fidelity protocol established. |
| 1.1 | 2026-03-05 | George | Integrated Institutional Data Lifecycle Management (Archiving). |

---\n*Standard Operating Procedure produced under the SigmaFidelity™ Quality Mandate.*
