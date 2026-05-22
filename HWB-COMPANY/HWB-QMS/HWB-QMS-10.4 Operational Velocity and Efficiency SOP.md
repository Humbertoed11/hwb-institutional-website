| **Document Control** |                                  |
| :------------------- | :------------------------------- |
| **Document Title**   | **Operational Velocity and Efficiency** |
| **Document ID**      | HWB-QMS-10.4                     |
| **Version**          | 1.0.0                            |
| **Status**           | APPROVED                         |
| **Author**           | George (Architect)               |
| **Approved By**      | Humberto Dominguez, CEO          |
| **Date**             | 05/21/2026                       |
| **ISO 9001 Clause**  | 7.1.3 (Infrastructure)           |

---

# Standard Operating Procedure: **Operational Velocity and Efficiency**

## 1.0 Purpose
To define the procedures for maximizing work speed and minimizing "token drag" (cost) during AI sessions. This SOP ensures the company gets the most value out of every interaction by moving from "File Searching" to "Database Knowing."

## 2.0 Universal Mandates (2026 Baseline)
1. **Database First:** AI team members must query the SQL databases (sigma_kb, SigmaVault, SigmaPrompts) before searching the filesystem.
2. **Task Bundling:** Multiple related tools must be used in a single turn to reduce back-and-forth messages.
3. **Simple Language:** All reports and code comments must use "Everyday Words" to keep memory space clear.
4. **State Loading:** Every session must start by loading the "Last Known Good State" from the **`SigmaState`** table.

## 3.0 Procedure

### 3.1 Efficient Work Cycle
1.  **Awake:** Load session state from `SigmaState`.
2.  **Intuition Check:** Scan `SigmaIntuition` for past lessons related to the task.
3.  **Knowledge Query:** Get rules directly from `sigma_kb` (SQL) instead of file searching.
4.  **Bundled Execution:** Read, write, and backup in one turn.
5.  **Log & Sleep:** Save state to `SigmaState` and log the win to Tier 6.

### 3.2 Vocabulary Standard
*   PhD Words (Forbidden): "Orchestration", "Ingestion", "Synchronicity", "Fidelity".
*   Everyday Words (Mandatory): "Teamwork", "Adding Info", "Matching", "Quality".

## 4.0 Verification (Zero-Defect Check)
*   Sessions complete in 50% fewer turns than legacy sessions.
*   Zero context "hallucinations" due to direct SQL data access.

## 5.0 Revision History
| Version | Date | Author | Change Description |
| :--- | :--- | :--- | :--- |
| 1.0.0 | 05/21/2026 | George | Initial Release. Formalized the 5-step Velocity Plan for token efficiency. |
