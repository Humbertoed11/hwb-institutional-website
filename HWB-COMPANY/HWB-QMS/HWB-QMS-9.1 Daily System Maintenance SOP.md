| **Document Control** |                                  |
| :------------------- | :------------------------------- |
| **Document Title**   | **Daily System Maintenance SOP** |
| **Document ID**      | HWB-QMS-9.1-MAIN                 |
| **Version**          | 3.0.0                            |
| **Status**           | APPROVED                         |
| **Author**           | George (Architect)               |
| **Approved By**      | Humberto Dominguez, CEO          |
| **Date**             | 05/21/2026                       |
| **ISO 9001 Clause**  | 7.1.3 (Infrastructure)           |

---

# Standard Operating Procedure: **Daily System Maintenance**

## 1.0 Purpose
To define the mandatory procedures for daily system maintenance, self-healing, and autonomous agent verification. This ensures 100% uptime and data fidelity for the **SigmaFidelity™** ecosystem.

## 2.0 Universal Mandates (2026 Baseline)
1. **The Operator Charter:** No maintenance task is complete without a Peter Sentinel snapshot.
2. **Guidance First:** If a "Zombie Process" persists after self-healing, ASK the CEO before manual termination.
3. **Tier 6 Telemetry:** Every maintenance cycle completion and system-health check must be logged to the Tactical DB.

## 3.0 Procedure

### 3.1 Mandatory Startup and Self-Healing
Every operational session must begin with the following sequence:
1.  **Execute Startup Master:** `bash scripts/startup_master.sh`.
2.  **Verify Self-Healing:** Ensure output reports "--- SigmaFidelity: Initiating Self-Healing Sequence ---".

### 3.2 Autonomous Agent Verification
Verify that the autonomous suite is running stably:
1.  **George Pulse:** Check logs for "--- Sleeping for 6 hours (SigmaFidelity Standard Loop) ---".
2.  **Peter Sentinel:** Confirm 15-minute shadow snapshot rhythm is active.

### 3.3 Database & Logic Integrity
1.  **Production Diagnostics:** Run the diagnostic dashboard via the container:
    `docker exec hwb_web_app python diag_dashboard.py`
2.  **Telemetry Handshake:** Verify new interactions are appearing in the `SigmaInteractionLog`.

## 4.0 Verification (Zero-Defect Check)
*   Docker containers (`web`, `compliance`, `db`, `gateway`) all show status "Running".
*   Port 8000 (Gateway) is responding with 200 OK.
*   System is approximately 12% more efficient via automated indexing (Maria's Audit).

## 5.0 Revision History
| Version | Date | Author | Change Description |
| :--- | :--- | :--- | :--- |
| 3.0.0 | 05/21/2026 | George | TOTAL MODERNIZATION. Added 2026 mandates and Tier 6 lifecycle tracking. |
| 2.0 | 2026-04-27 | George | Integrated Self-Healing Protocol and Docker Orchestration. |
| 1.0 | 2025-11-05 | Gemini | Initial Release. |
