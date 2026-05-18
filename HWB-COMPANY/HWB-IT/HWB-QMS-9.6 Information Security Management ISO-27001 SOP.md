| **Document Control** |                                                               |
| :------------------- | :------------------------------------------------------------ |
| **Document Title**   | **Information Security Management System (ISMS) SOP**         |
| **Document ID**      | HWB-QMS-9.6                                                   |
| **Version**          | 1.0                                                           |
| **Status**           | Active                                                        |
| **Author**           | George (VP Systems Architecture)                              |
| **Approved By**      | Humberto Dominguez (CEO)                                      |
| **Date**             | 2026-03-08                                                    |

---

# 1.0 Purpose
This SOP aligns the IT and Operational security protocols of HWB Cleaning Services LLC with the **ISO/IEC 27001:2022** standard. It ensures that both digital data (CRM, AI pipelines) and physical client infrastructure (Data Centers, Corporate Offices) are protected against unauthorized access, espionage, and compromise.

# 2.0 Scope
Applies to the entire IT infrastructure, all AI Vice Presidents, and all physical cleaning personnel operating in high-security environments.

# 3.0 Procedure: Information Security

## 3.1 Physical Security (Cleaners in the Field)
1.  **Zero-Interaction Mandate:** Cleaning personnel are strictly prohibited from touching, reading, or moving any client documents, whiteboards, or unlocked computer terminals.
2.  **Access Control:** Employees must only enter zones explicitly authorized by the client's physical security team. Tailgating or holding secure doors open is a fireable offense.
3.  **Device Prohibition:** Personal mobile phones must not be used to photograph any client equipment, data centers, or sensitive areas.

## 3.2 Digital Security (The SigmaFidelity™ Suite)
1.  **Data Encryption:** All CRM databases (`sigma_leads.db`, `clients.db`) must be encrypted at rest.
2.  **Access Logs:** The `ActivityLog` must record all administrative actions, data exports, and AI API calls.
3.  **Secret Management:** Strict adherence to the `HWB-QMS-9.5 Secret Management SOP` is required for all API keys.

# 4.0 Verification
*   **Penetration Testing:** Annual digital vulnerability scans of the HWB Webserver.
*   **Personnel Vetting:** Background checks and Non-Disclosure Agreements (NDAs) must be completed for all staff before they are deployed to ISO 27001-certified client facilities.

# 5.0 Notes and Cautions
*   **The "Killer Advantage":** This ISMS certification protocol is a core marketing pillar for acquiring high-value tech and defense contracts. Any breach of this SOP compromises the institutional reputation.

---

## 6.0 Revision History
| Version | Date | Author | Change Description |
| :--- | :--- | :--- | :--- |
| 1.0 | 2026-03-08 | George | Initial ISMS framework established per ISO/IEC 27001:2022. |

---
*Standard Operating Procedure produced under the SigmaFidelity™ Quality Mandate.*