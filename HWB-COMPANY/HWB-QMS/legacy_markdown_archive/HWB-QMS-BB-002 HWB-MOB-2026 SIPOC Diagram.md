| **Document Control** | |
| :--- | :--- |
| **Document Title** | **HWB-MOB-2026 SIPOC Diagram** |
| **Document ID** | HWB-QMS-BB-002 |
| **Version** | 1.0 |
| **Status** | Active / Define Phase |
| **Author** | George (Master Black Belt) |
| **Approved By** | Humberto Dominguez, CEO |
| **Date** | 2026-03-20 |

---

# SIPOC Diagram: **HWB-MOB-2026 Mobile Execution Engine**

The SIPOC (Supplier, Input, Process, Output, Customer) defines the boundaries of the project and ensures all stakeholders and resources are aligned prior to the Measure phase.

| **Supplier** | **Input** | **Process (High-Level)** | **Output** | **Customer** |
| :--- | :--- | :--- | :--- | :--- |
| **CEO / Ops** | Strategic Mandates & Budget | **1. Authentication:** GPS-verified Login/Clock-in. | **Verified Logs:** Audit-ready sanitation records. | **Facility Managers** |
| **IT Dept** | Azure Cloud & SQLite DBs | **2. Retrieval:** Fetch 'Scope of Work' for site. | **Efficiency Data:** Labor utilization vs. Budget. | **HWB Finance** |
| **Supervisors** | Site Schedules & SOPs | **3. Execution:** Sequence-locked task completion. | **Compliance Alerts:** Real-time exception reporting. | **Technicians** |
| **Facility Mgrs** | Site Access & Special Requests | **4. Evidence:** Photo/Timestamp capture of CTQs. | **Clean Environment:** Physical result of process. | **Building Occupants** |
| **Safety Dept** | SDS / Hazard Levels | **5. Sync:** Offline-first data push to CRM. | **Payroll Data:** Precise billable hours. | **CEO / Managing Dir** |

---

### 1.0 Boundary Definitions
*   **Start Point:** Technician arrives at the designated GPS geofence and initiates login.
*   **End Point:** Data successfully synchronizes with the `clients.db` and `sigma_leads.db` servers and the technician clocks out.

### 2.0 Critical-to-Quality (CTQ) Requirements
Based on initial VOC (Voice of Customer) analysis, the following are the primary "Must-Haves" for the process to be successful:
1.  **Reliability:** 99.9% app uptime (offline mode must work).
2.  **Integrity:** GPS coordinates must be within 50 meters of the site.
3.  **Compliance:** 100% of 'High-Stakes' sanitation items (disinfection) must have photo evidence.
4.  **Speed:** Sync must occur within 60 seconds of regaining connectivity.

### 3.0 Preliminary Value Stream Mapping (P-VSM)
The "Process" column above represents the **Core Value Stream**. During the Measure phase, we will calculate the **Value-Added (VA)** vs. **Non-Value-Added (NVA)** time for each step to identify where the "Payroll Mopping" waste occurs.

---

## 4.0 Approval & Sign-off
**CEO/Operations Director:** _________________________ **Date:** 2026-03-20

---

## 5.0 Revision History
| Version | Date | Author | Description |
| :--- | :--- | :--- | :--- |
| 1.0 | 2026-03-20 | George (MBB) | Initial SIPOC for Black Belt track. |
