| **Document Control** |                                              |
| :------------------- | :------------------------------------------- |
| **Document Title**   | **Backoffice and CRM Management SOP**        |
| **Document ID**      | HWB-QMS-7.5-BO-CRM                           |
| **Version**          | 1.0                                          |
| **Status**           | Active                                       |
| **Author**           | CRM Specialist                               |
| **Approved By**      | Humberto Dominguez (CEO)                     |
| **Date**             | 2026-03-05                                   |

---

# 1.0 Purpose
This SOP defines the procedures for operating and maintaining the HWB Backoffice Management Suite and the client management system. It ensures accurate information, secure access, and clear updates between business information and field operations.

# 2.0 Scope
Applies to all administrative personnel, support team members, and technical teams managing the HWB Cleaning Services LLC digital tools.

# 3.0 Prerequisites
*   Valid executive or employee logins.
*   Access to the HWB local server (Port 5000).
*   Installed Python environment with `Flask-Login` and `sqlite3`.

# 4.0 Procedures

## 4.1 System Access (Security Gateway)
1.  Navigate to `/login`.
2.  Provide the corporate login details.
3.  Unauthorized login attempts are automatically sent to the **Security Notice** page and recorded for review.

## 4.2 Navigating the Double-Sidebar Layout
The backoffice uses two sidebars to make work faster:
*   **Primary Rail (Far Left):** Used for switching between main departments (Pulse, CRM, Assets, Lab).
*   **Control Rack (Inner Left):** Used for department sub-menus and action buttons (e.g., "Add Activity," "Management Tools").

## 4.3 Adding Business Information (The Data Center)
1.  **Harvesting:** The marketing team collects leads and saves raw CSV files to `HWB-COMPANY/HWB-SALES-MARKETING/HWB-RAW-DATA/`.
2.  **Uploading:** Execute `python3 scripts/HWB-WEB Lead Ingestor.py`.
3.  **Verification:** Confirm leads appear in the **Marketing Pipeline** section of the CRM Dashboard.

## 4.4 Automated Client Conversion
1.  Locate a prospect in the **Marketing Pipeline**.
2.  Click the **"Convert ⚡"** button.
3.  The system will automatically move the facility data to the `clients.db` and record a "Conversion" activity in the client's history.

## 4.5 Client Activity Logging
1.  Select the client from the list in the **Log Activity Engine**.
2.  Choose the Activity Type (Site Audit, Quote, Incident, etc.).
3.  Type in detailed notes and click **"Register Activity."**
4.  The Global Activity Feed will update immediately, keeping a complete history.

# 5.0 Verification
*   **Audit Trail:** Every activity and conversion must be visible in the Executive Pulse dashboard.
*   **Database Accuracy:** Regular checks of `sigma_leads.db` vs. `clients.db` to ensure no data is lost.

# 6.0 Notes and Cautions
*   **No Fake Data Allowed:** Never enter placeholder data into the system.
*   **Password Updates:** Change the admin password every 90 days using the database tools.

---

## 7.0 Revision History
| Version | Date | Author | Change Description |
| :--- | :--- | :--- | :--- |
| 1.0 | 2026-03-05 | CRM Specialist | Initial Release of Backoffice & CRM SOP. |

---\n*Standard Operating Procedure produced under the HWB Quality Mandate.*
