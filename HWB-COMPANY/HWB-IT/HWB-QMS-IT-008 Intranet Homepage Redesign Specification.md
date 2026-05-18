# HWB-QMS-IT-008 Intranet Homepage Redesign Specification

| **Document Control** |                                              |
| :------------------- | :------------------------------------------- |
| **Document Title**   | **Intranet Homepage Redesign Specification** |
| **Document ID**      | HWB-QMS-IT-008                               |
| **Version**          | 1.0                                          |
| **Status**           | Approved                                     |
| **Author**           | George (Systems Architect)                   |
| **Approved By**      | Humberto Dominguez (CEO)                     |
| **Date**             | 2026-03-13                                   |

---

## 1.0 Purpose
To define the technical and structural layout for the **HWB SigmaFidelity™ Portal** (Corporate Intranet) homepage. This specification ensures a high-fidelity user experience (UX) that eliminates "Process Fog" and provides instant access to institutional intelligence.

## 2.0 Page Architecture (Home.aspx)

### 2.1 Section 1: Institutional Hero (Full Width)
*   **Web Part:** Hero
*   **Aesthetic:** High-resolution image of a sanitized facility or the DFW skyline.
*   **Content:**
    -   **Title:** "Fidelity. Safety. Respect."
    -   **CTA:** "Access ISO 9001 SOPs" (Links to consolidated document library).

### 2.2 Section 2: Command & Control (Three Columns)
*   **Column 1: Department Hubs (Quick Links)**
    -   Link 1: **Executive Hub** (Restrictive Access).
    -   Link 2: **Finance & Warchest** (Maria Bolanos Reports).
    -   Link 3: **SaaS Ops (BabySOP.com)**.
*   **Column 2: HWB News Desk (News Web Part)**
    -   Source: Root site "Site News".
    -   Auto-provisioned updates from the `HWB-WEB News Queue`.
*   **Column 3: The Warchest (Quick Links)**
    -   Link 1: **Zip-Code Intelligence** (DFW Market Mapping).
    -   Link 2: **TX Comptroller Portal**.
    -   Link 3: **BabySOP Staging Zone**.

### 2.3 Section 3: Performance Telemetry (Two Columns)
*   **Column 1: Institutional Pulse (Text/HTML)**
    -   Display real-time metrics: "92% Contract Retention" | "1,785 DPMO".
*   **Column 2: Critical Expirations (List Web Part)**
    -   Source: `sigma_leads.db` Milestones (Drone FAA expirations, Insurance renewals).

## 3.0 Structural JSON (Reference for Automated Deployment)
```json
{
  "title": "HWB SigmaFidelity™ Portal",
  "layout": "Home",
  "canvasLayout": {
    "horizontalSections": [
      {
        "columns": [
          { "webparts": [{ "title": "SigmaFidelity Hero", "type": "Hero" }] }
        ]
      },
      {
        "columns": [
          { "webparts": [{ "title": "Department Hubs", "type": "QuickLinks" }] },
          { "webparts": [{ "title": "Institutional News", "type": "News" }] },
          { "webparts": [{ "title": "Operational SOPs", "type": "DocumentLibrary" }] }
        ]
      }
    ]
  }
}
```

## 4.0 Verification & Audit
*   **UX Audit:** Conducted weekly by the Systems Architect.
*   **Link Integrity:** All links must resolve to high-fidelity internal targets. No dead links permitted.

---
*Produced by George under the SigmaFidelity™ Institutional Standard.*
