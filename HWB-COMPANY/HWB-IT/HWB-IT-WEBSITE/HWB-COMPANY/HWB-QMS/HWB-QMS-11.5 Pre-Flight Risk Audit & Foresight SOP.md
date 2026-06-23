| **Document Control** | |
| :--- | :--- |
| **Document Title** | **Preflight Risk Audit and Foresight SOP** |
| **Document ID** | HWB QMS 11.5 |
| **Version** | 1.0 |
| **Status** | APPROVED |
| **Author** | George (Systems Architect) |
| **Approved By** | Humberto Dominguez, CEO |
| **Date** | 2026/06/06 |
| **ISO 9001 Clause** | 6.1 |

---

# Standard Operating Procedure: **Preflight Risk Audit and Foresight SOP**

## 1.0 Purpose
This document establishes the preflight audit and routing smoke testing procedures. These automated processes prevent syntax mismatches, template drift, and incorrect server path configurations from entering the live production environment.

## 2.0 Scope
This procedure applies to all HTML and Jinja templates, routing scripts, and configuration files within the development workspace and the production landing folder.

## 3.0 Universal Mandates
All code modifications and releases must pass the automated preflight audit suite without exception. No file package may be deployed if any safety check returns a failure status.

## 4.0 Prerequisites
* Python 3 runtime environment installed locally.
* Active docker container running the web application.
* Administrative privileges to execute docker commands.

## 5.0 Procedure

### 5.1 Static Tag Balance Audit
1. Execute the HTML tag validator.
2. The validator reads each template file and checks that all nested tags are balanced.
3. Any mismatched or unclosed tags are flagged with line numbers for immediate correction.

### 5.2 Template Parity Audit
1. Compare local templates with corresponding production templates.
2. The verification script alerts the operator of any file size or content mismatch.
3. Align the templates to ensure identical layouts across all environments.

### 5.3 Path Portability Audit
1. Scan all source code files for hardcoded paths.
2. Ensure all references utilize dynamic path resolvers relative to the application root.

### 5.4 Routing Smoke Tests
1. Execute the smoke test script inside the active docker container.
2. The script simulates an admin session and sends requests to critical routes.
3. Verify that all endpoints respond with a successful status and display expected DOM elements.

## 6.0 Verification (Zero Defect Check)
Run the master audit script from the root workspace directory:
`python3 scripts/HEX-PRE-FLIGHT-AUDIT.py`

Verify that the terminal output reports a successful status for all checks and returns a zero exit code.

## 7.0 Notes and Cautions
> **NOTE:** Run this preflight audit before committing changes or building deployment files.
> **CAUTION:** Do not deploy manual code updates without running the smoke test suite first.

## 8.0 Revision History
| Version | Date | Author | Change Description |
| :--- | :--- | :--- | :--- |
| 1.0 | 2026/06/06 | George | Initial release establishing automated preflight checks. |

## 9.0 Document Conventions
* **Storage:** Save as Markdown in `HWB-COMPANY/HWB-QMS/`.
* **Obsidian Mirroring:** Ensure the document is copied to the Obsidian vault directory.
