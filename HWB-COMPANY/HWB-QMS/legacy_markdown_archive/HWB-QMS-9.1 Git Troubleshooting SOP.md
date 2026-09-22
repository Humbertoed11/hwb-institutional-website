| **Document Control** |                                  |
| :------------------- | :------------------------------- |
| **Document Title**   | **Git Troubleshooting SOP**      |
| **Document ID**      | HWB-QMS-9.1-GIT                  |
| **Version**          | 2.0.0                            |
| **Status**           | APPROVED                         |
| **Author**           | George (Architect)               |
| **Approved By**      | Humberto Dominguez, CEO          |
| **Date**             | 05/21/2026                       |
| **ISO 9001 Clause**  | 7.1.3 (Infrastructure)           |

---

# Standard Operating Procedure: **Git Troubleshooting**

## 1.0 Purpose
To define the procedure for resolving common Git-related failures within the SigmaFidelity™ workspace. This ensures 100% repository integrity and prevents unverified commits from entering the production branch.

## 2.0 Universal Mandates (2026 Baseline)
1. **Peter Sentinel:** Before any major Git reset, verify that a Peter Sentinel snapshot exists.
2. **Guidance First:** If a merge conflict involves core logic files (/core), ASK the CEO before resolving.
3. **Tier 6 Telemetry:** Every `git push` or `git reset --hard` must be logged in the tactical DB.

## 3.0 Common Procedures

### 3.1 Resolving Merge Conflicts
1.  Identify the affected files: `git status`.
2.  Open the file and locate the conflict markers `<<<< HEAD`.
3.  Manually align the code to the latest approved HWB architecture.
4.  Stage and commit the fix: `git add <file> && git commit -m "George: Merge Conflict Resolved"`.

### 3.2 The "Force Hardening" Reset
If the local workspace is corrupted beyond repair:
`git fetch origin && git reset --hard origin/master && git clean -fd`
> **CAUTION:** This permanently deletes any unpushed work. Ensure Peter Sentinel is active first.

## 4.0 Verification (Zero-Defect Check)
*   `git status` reports "Your branch is up to date with 'origin/master'".
*   Recent commits are visible on the HWB GitHub repository.

## 5.0 Revision History
| Version | Date | Author | Change Description |
| :--- | :--- | :--- | :--- |
| 2.0.0 | 05/21/2026 | George | TOTAL MODERNIZATION. Added Peter Sentinel and Tier 6 mandates. |
| 1.0 | 2026-03-02 | George | Initial Troubleshooting Guide. |
