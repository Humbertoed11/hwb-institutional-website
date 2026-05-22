| **Document Control** |                                  |
| :------------------- | :------------------------------- |
| **Document Title**   | **Automated Problem Management** |
| **Document ID**      | HWB-QMS-10.3                     |
| **Version**          | 1.0.0                            |
| **Status**           | APPROVED                         |
| **Author**           | George (Lead Developer)          |
| **Approved By**      | Humberto Dominguez, CEO          |
| **Date**             | 05/21/2026                       |
| **ISO 9001 Clause**  | 10.2 (Nonconformity)             |

---

# Standard Operating Procedure: **Automated Problem Management**

## 1.0 Purpose
To define the procedure for identifying, tracking, and resolving systemic friction and bugs within the HWB ecosystem. This system replaces manual Markdown tracking (Obsidian) with a fully automated, AI-managed database.

## 2.0 Scope
Applies to all software bugs, visual drifts, and operational friction found by the team or the CEO.

## 3.0 Universal Mandates (2026 Baseline)
1. **AI-Managed List:** The CEO and team members simply tell the AI agent about a problem. The AI is responsible for logging and tracking.
2. **Database Integrity:** All problems must be stored in the **`SigmaProblems`** SQL table.
3. **No More Obsidian:** Manual text file tracking is officially retired for problem management.

## 4.0 Procedure

### 4.1 Adding a Problem
1. When a problem is found, tell the AI agent (George).
2. The AI will instantly log the **Description**, **Category**, and **Impact Level** into the database.
3. The AI will assign a "Pending" status.

### 4.2 Listing Problems
1. The CEO can ask for a list of "Pending" or "Resolved" problems at any time.
2. The AI will generate a high-quality HTML grid from the database.

### 4.3 Resolving a Problem
1. Once a fix is applied, the AI agent updates the status to "Resolved."
2. The AI logs the **Resolution Notes** and moves the key lesson to the **Intuition Engine (`SigmaIntuition`)**.

## 5.0 Verification (Zero-Defect Check)
*   The **`SigmaProblems`** table contains zero duplicate entries.
*   100% of resolved problems have associated lessons in the Intuition Engine.

## 6.0 Notes and Cautions
> **NOTE:** Using a database makes the AI team faster at seeing patterns between different bugs.
> **CAUTION:** Always give the AI a clear description of the problem to ensure high-fidelity logging.

## 7.0 Revision History
| Version | Date | Author | Change Description |
| :--- | :--- | :--- | :--- |
| 1.0.0 | 05/21/2026 | George | Initial Release. Retired Markdown tracking and launched the SQL-based Automated Problem Management system. |
