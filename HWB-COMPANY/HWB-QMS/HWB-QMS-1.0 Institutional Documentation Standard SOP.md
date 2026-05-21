| **Document Control** |                                              |
| :------------------- | :------------------------------------------- |
| **Document Title**   | **Institutional Documentation Standard SOP** |
| **Document ID**      | HWB-QMS-1.0                                  |
| **Version**          | 1.0.0                                        |
| **Status**           | APPROVED                                     |
| **Author**           | George (Architect)                           |
| **Approved By**      | Humberto Dominguez, CEO                      |
| **Date**             | 05/21/2026                                   |
| **ISO 9001 Clause**  | 7.5.3 (Control of Documented Information)    |

---

# Standard Operating Procedure: **Institutional Documentation Standard SOP**

## 1.0 Purpose
To define the mandatory standard for creating, managing, and modernizing all HWB documented information. This ensures that every manual, guide, and technical blueprint follows the clinical "Industrial Authority" look and is fully audit-ready for ISO 9001.

## 2.0 Scope
Applies to all departments (HR, IT, Ops, Sales) and all AI agents. Covers both internal Markdown files and the public-facing HTML Compliance Engine.

## 3.0 Universal Mandates (Documentation Continuity)
1. **The May 1st Baseline:** Any document dated before May 1st, 2026, is designated as **OUTDATED**. It must be audited and modernized before it can be used as production logic.
2. **Guidance First Search:** Agents must never perform exhaustive searches for missing files without CEO guidance.
3. **No Synthetic Data:** Synthetic, placeholder, or "make-belief" data is strictly prohibited in all controlled documents.
4. **Surgical Continuity:** Large documents must be updated using the `replace` tool (Surgical Insertion) to prevent **Content Erosion**.

## 4.0 Prerequisites
* **Master Template:** `HWB-COMPANY/HWB-QMS/sop_template.md` must be used as the starting point for every new SOP.
* **Clinical Shell:** Access to `HWB-IT-WEBSITE/templates/sop_base.html` for HTML rendering.
* **Migration Script:** `scripts/migrate_sops.py` must be verified and healthy.

## 5.0 Procedure

### 5.1 Document Creation (Markdown)
1. Copy the `sop_template.md`.
2. Fill in the **0.0 Document Control** table with the accurate ID, Version, and Date (MM-DD-YYYY).
3. Draft content using simple "Everyday Words" at a 20-year-old reading level.
4. Use **Industrial Callout** blocks for high-impact notes or cautions.
5. Save the file in the appropriate `HWB-COMPANY/[DEPT]` folder.

### 5.2 HTML Migration & Tracker Sync
1. Run `python scripts/migrate_sops.py`.
2. The script will automatically parse metadata and assign the **UPDATED** or **OUTDATED** status badge.
3. The script will generate a memory-efficient HTML fragment in `static/qms/`.
4. The system will automatically update the **Master Manual Index** at `/manual`.

### 5.3 Audit Verification
1. Open `http://mop.test:5000/manual`.
2. Locate the new document and verify the **Status Badge** is Green (UPDATED).
3. Click the document and verify the **TOC (Table of Contents)** and **Syntax Highlighting** are active.
4. Perform a **Print-to-PDF** test to ensure 8.5" x 11" alignment.

## 6.0 Verification (Zero-Defect Check)
* Every document must have a unique ID: `HWB-[DEPT]-[NUMBER]`.
* Every document must reference at least one ISO 9001 Clause.
* No document may use the 2000-01-01 sentinel date in production.

## 7.0 Notes and Cautions
> **LOGIC:** The Compliance Engine uses Nginx for isolation. If the manual is not loading, check the `hwb_compliance_engine` container status.
> **CAUTION:** Documents are protected by Peter Sentinel snapshots. Reverting a document also reverts its status in the Compliance Tracker.

## 8.0 Revision History
| Version | Date | Author | Change Description |
| :--- | :--- | :--- | :--- |
| 1.0.0 | 05/21/2026 | George | Initial Release. Formalized the 2026 Documentation Standards and HTML Migration Engine. |

## 9.0 Document Conventions
* **Primary Font:** Inter (900 for Headers, 400 for Body).
* **Body Size:** 16px (1rem).
* **Line Height:** 1.8.
* **H1 Tracking:** -0.04em.
