| **Document Control** |                                              |
| :------------------- | :------------------------------------------- |
| **Document Title**   | **Backoffice and CRM Management SOP**        |
| **Document ID**      | HWB-QMS-7.5-BO-CRM                           |
| **Version**          | 1.0                                          |
| **Status**           | Active                                       |
| **Author**           | Silas Sync (VP of CRM Systems)               |
| **Approved By**      | Humberto Dominguez (CEO)                     |
| **Date**             | 2026-03-05                                   |

---

# 1.0 Purpose
This SOP defines the procedures for operating and maintaining the SigmaFidelity™ Backoffice Management Suite and the Relational CRM engine. It ensures data integrity, secure access, and efficient "Zero-Fog" synchronization between market intelligence and field operations.

# 2.0 Scope
Applies to all administrative personnel, AI Vice Presidents, and technical teams managing the HWB Cleaning Services LLC digital infrastructure.

# 3.0 Prerequisites
*   Valid executive or employee credentials.
*   Access to the SigmaFidelity™ local server (Port 5000).
*   Installed Python environment with `Flask-Login` and `sqlite3`.

# 4.0 Procedures

## 4.1 System Access (Security Gateway)
1.  Navigate to `/login`.
2.  Provide the centralized corporate credentials.
3.  Unauthorized access attempts are automatically redirected to the **Security Notice** page and logged for compliance auditing.

## 4.2 Navigating the Double-Sidebar Layout
The backoffice utilizes a dual-sidebar system for maximum operational speed:
*   **Primary Rail (Far Left):** Used for switching between high-level departments (Pulse, CRM, Assets, Lab).
*   **Control Rack (Inner Left):** Used for departmental sub-navigation and contextual action buttons (e.g., "Add Activity," "Management Tools").

## 4.3 Market Intelligence Ingestion (The Hive)
1.  **Harvesting:** AI VP Lauri Tells harvests leads and saves raw CSV files to `HWB-COMPANY/HWB-SALES-MARKETING/HWB-RAW-DATA/`.
2.  **Ingestion:** Execute `python3 scripts/HWB-WEB Lead Ingestor.py`.
3.  **Verification:** Confirm leads appear in the **Marketing Pipeline** section of the CRM Dashboard.

## 4.4 Automated Client Conversion
1.  Locate a prospect in the **Marketing Pipeline**.
2.  Click the **"Convert ⚡"** button.
3.  The system will automatically migrate the facility data to the `clients.db` and log a "Conversion" activity in the client's historical record.

## 4.5 Relational Activity Logging
1.  Select the client from the dropdown menu in the **Log Activity Engine**.
2.  Choose the Activity Type (Site Audit, Quote, Incident, etc.).
3.  Input detailed notes and click **"Register Activity."**
4.  The Global Activity Feed will update instantly, maintaining a 100% auditable history.

# 5.0 Verification
*   **Audit Trail:** Every activity and conversion must be visible in the Executive Pulse dashboard.
*   **Database Integrity:** Periodic manual audits of `sigma_leads.db` vs. `clients.db` to ensure zero data loss.

# 6.0 Notes and Cautions
*   **Synthetic Data Prohibition:** Never manually enter placeholder data into the Hive.
*   **Credential Rotation:** Rotate the administrative password every 90 days via the database CRUD tools.

---

## 7.0 Revision History
| Version | Date | Author | Change Description |
| :--- | :--- | :--- | :--- |
| 1.0 | 2026-03-05 | Silas Sync | Initial Release of Backoffice & CRM SOP. |

---\n*Standard Operating Procedure produced under the SigmaFidelity™ Quality Mandate.*
