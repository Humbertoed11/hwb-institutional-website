| **Document Control** |                                              |
| :------------------- | :------------------------------------------- |
| **Document Title**   | **Digital Lead Capture Form**                |
| **Document ID**      | HWB-MKT-FORM-001                             |
| **Version**          | 1.0                                          |
| **Status**           | Approved                                     |
| **Author**           | Gemini (Senior ISO 9001 Auditor)             |
| **Approved By**      | SigmaFidelity™ Orchestrator                  |
| **Date**             | 2026-03-01                                   |

---

# Marketing Form: **Digital Lead Capture (Website)**

## 1.0 Purpose
This form defines the required data fields for the HWB Website "Request a Quote" interface. It ensures that all incoming leads provide the necessary empirical data for accurate SigmaFidelity™ analysis.

## 2.0 Form Structure (Web Interface)

| Field Name | Type | Mandatory? | Purpose |
| :--- | :--- | :--- | :--- |
| **Organization Name** | Text | Yes | Identify potential client. |
| **Contact Person** | Text | Yes | Direct point of communication. |
| **Email Address** | Email | Yes | Formal correspondence. |
| **Project Type** | Dropdown | Yes | Category (Construction, Medical, Commercial). |
| **Facility Square Footage**| Number | Yes | Required for empirical pricing. |
| **Project Location** | Text | Yes | Identify North Texas jurisdiction. |
| **Project Start Date** | Date | No | Scheduling and readiness tracking. |
| **Current Challenges** | Text Area | No | Identify pain points for tailoring. |

## 3.0 Backend Processing (AI Marketing Agent)
1.  **Capture:** Data is submitted via the Flask webserver and stored in `sigma_leads.db`.
2.  **Notification:** An immediate notification is sent to the Sales Department.
3.  **Initial Triage:** The AI Agent checks the lead against the "High-Priority GC List" (refer to `1 task list 2025/2026-03-01.md`).

## 4.0 Verification
*   Lead data successfully populates the `Leads` table in `sigma_leads.db`.
*   Zero synthetic test data present in production lead records.

## 5.0 Revision History
| Version | Date | Author | Change Description |
| :--- | :--- | :--- | :--- |
| 1.0 | 2026-03-01 | Gemini | Initial Release: Standardized lead capture. |
