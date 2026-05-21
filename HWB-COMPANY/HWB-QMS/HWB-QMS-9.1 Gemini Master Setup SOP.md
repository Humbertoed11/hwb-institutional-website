| **Document Control** |                                  |
| :------------------- | :------------------------------- |
| **Document Title**   | **Gemini Master Setup SOP**      |
| **Document ID**      | HWB-QMS-9.1-GEM                  |
| **Version**          | 2.0.0                            |
| **Status**           | APPROVED                         |
| **Author**           | George (Architect)               |
| **Approved By**      | Humberto Dominguez, CEO          |
| **Date**             | 05/21/2026                       |
| **ISO 9001 Clause**  | 7.1.3 (Infrastructure)           |

---

# Standard Operating Procedure: **Gemini Master Setup**

## 1.0 Purpose
To define the procedure for initializing and hardening the Gemini CLI agent environment. This ensures that every session starts with the correct SigmaFidelity™ context, mandates, and Tier 6 telemetry connection.

## 2.0 Universal Mandates (2026 Baseline)
1. **Startup Sequence:** Every session MUST begin with `bash scripts/startup_master.sh`.
2. **Guidance First:** If the master setup fails, ASK the CEO before attempting to manual-patch the `.venv`.
3. **Tier 6 Telemetry:** Successful setup must be logged instantly to the tactical DB.

## 3.0 Setup Procedure
1.  **Environment Activation:** Initialize the `.venv_agent` Python environment.
2.  **Secret Injection:** Load the `.env` file via `inject_production_secrets.py`.
3.  **Mandate Loading:** Verify that all `GEMINI.md` files (Global, Project, Local) are parsed.
4.  **Telemetry Handshake:** Execute a test log to `SigmaInteractionLog` to verify DB connectivity.

## 4.0 Verification (Zero-Defect Check)
*   Output of `startup_master.sh` shows "WATCHDOG ACTIVE".
*   Tier 6 log entry "Session Initialized" is visible in Postgres.

## 5.0 Revision History
| Version | Date | Author | Change Description |
| :--- | :--- | :--- | :--- |
| 2.0.0 | 05/21/2026 | George | TOTAL MODERNIZATION. Integrated the 2026 Startup Sequence and Telemetry Handshake. |
| 1.0 | 2026-03-02 | George | Initial Setup Guide. |
