| **Document Control** |                                  |
| :------------------- | :------------------------------- |
| **Document Title**   | **Operational Velocity and Efficiency** |
| **Document ID**      | HWB-QMS-10.4                     |
| **Version**          | 2.0.0                            |
| **Status**           | APPROVED                         |
| **Author**           | George (Architect)               |
| **Approved By**      | Humberto Dominguez, CEO          |
| **Date**             | 05/22/2026                       |
| **ISO 9001 Clause**  | 7.1.3 (Infrastructure)           |

---

# Standard Operating Procedure: **Operational Velocity and Efficiency**

## 1.0 Purpose
To define the procedures for maximizing work speed, eliminating repetitive manual work, and managing the AI system's "database brain." This standard ensures that all AI team members query our live PostgreSQL databases instead of slowly reading text files, keeping our memory organized, fast, and constantly growing.

## 2.0 Universal Mandates (2026 Database-Brain Baseline)
1. **Database-First Operations:** The AI team is strictly forbidden from using flat text files (like `HWB-SESSION-RECOVERY.md`) for session memory. All session starts and stops must run through our PostgreSQL memory databases.
2. **Zero Double-Entry Work:** The AI team must never manually record technical issues or bugs in multiple places. The database and the markdown files must sync automatically.
3. **Everyday Language Standard:** All text, reports, and code comments in this setup must use simple, clear words so the memory stays clean and fast.
4. **Secure Key Isolation:** All secure keys, passwords, and secrets must live inside our secure database table (`SigmaVault`) instead of plain-text configuration files.

## 3.0 Procedure (The 4-Step Brain Architecture)

### 3.1 Step 1: Active Knowledge Queries (`sigma_kb`)
*   Before starting any task, the AI system must run a quick semantic search against the 3,935 rows in `sigma_kb` to pull relevant company guidelines.
*   This removes the need to search through physical file folders, keeping system processing fast and accurate.

### 3.2 Step 2: Automated Session State (`SigmaState`)
*   On system startup, the AI must automatically query the `SigmaState` database table to load the "Last Known Good State."
*   On system shutdown, the AI must save our new progress and active tasks back to the database. This eliminates the need for manual recovery notes.

### 3.3 Step 3: Automated Bug Tracking (`SigmaProblems`)
*   `docs/PROBLEMS-TO-SOLVE.md` remains our single source of truth for tracking system friction.
*   We use a simple background script that automatically reads this markdown file and syncs it to the database table (`SigmaProblems`) during Git commits.

### 3.4 Step 4: Vault Protection (`SigmaVault`)
*   All passwords and API credentials must be stored securely inside `SigmaVault`.
*   The system loads these keys directly from the database at startup, keeping our environment files clean and safe from leaks.

## 4.0 Verification (Zero-Defect Check)
*   All session startups and shutdowns occur automatically without manual file writing.
*   Zero repetitive double-entry work recorded in our audits.
*   The system loads and runs 50% faster by using direct database queries instead of folder searches.

## 5.0 Revision History
| Version | Date | Author | Change Description |
| :--- | :--- | :--- | :--- |
| 1.0.0 | 05/21/2026 | George | Initial Release. Formalized the 5-step Velocity Plan for token efficiency. |
| 2.0.0 | 05/22/2026 | George | Updated to Database-Backed Brain architecture. Eliminated flat-file recovery and double-entry bug tracking. |
