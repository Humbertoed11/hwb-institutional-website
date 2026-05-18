| **Document Control** |                                  |
| :------------------- | :------------------------------- |
| **Document Title**   | **Daily System Maintenance SOP** |
| **Document ID**      | HWB-QMS-9.1                      |
| **Version**          | 2.0                              |
| **Status**           | Approved                         |
| **Author**           | George (Systems Architect)       |
| **Approved By**      | Humberto Dominguez, CEO          |
| **Date**             | 2026-04-27                       |

---

# Standard Operating Procedure: **Daily System Maintenance SOP**

## 1.0 Purpose
This SOP describes the mandatory procedures for daily system maintenance, self-healing, and autonomous agent verification to ensure 100% uptime and data fidelity for the SigmaFidelity™ ecosystem.

## 2.0 Scope
Applies to all Linux/WSL environments, Docker containers, and autonomous agents (George, Watchdog) within the HWB Cleaning Services LLC technical infrastructure.

## 3.0 Prerequisites
*   Access to a terminal with Docker Engine active.
*   The `scripts/` directory containing `hwb_self_healing.sh` and `startup_master.sh`.
*   Executive login credentials for the production database.

## 4.0 Procedure

### 4.1 Mandatory Startup and Self-Healing
Every operational session must begin with the following sequence:
1.  **Execute Startup Master:**
    ```bash
    bash scripts/startup_master.sh
    ```
2.  **Verify Self-Healing:** Ensure the output reports "--- SigmaFidelity: Initiating Self-Healing Sequence ---" and confirms the termination of zombie processes.

### 4.2 Autonomous Agent Verification (George & Watchdog)
Verify that the autonomous suite is running stably in persistent loops:
1.  **Check Container Logs:**
    ```bash
    docker logs hwb_agent_worker --tail 20
    ```
2.  **Confirm Pulse Status:** Look for the message "--- Sleeping for 6 hours (SigmaFidelity Standard Loop) ---" to verify George is active.
3.  **Watchdog Status:** Confirm "WATCHDOG ACTIVE" is logged to ensure institutional integrity monitoring.

### 4.3 Database and Logic Integrity
1.  **Production Diagnostics:** Run the internal diagnostic dashboard via the container:
    ```bash
    docker exec hwb_web_app python diag_dashboard.py
    ```
2.  **Verification:** Confirm that RTY (Rolled Throughput Yield) is ≥ 95% and all tables are present.

### 4.4 OS Level Maintenance (Legacy)
1.  Run the Ubuntu update script to ensure security patches are applied:
    ```bash
    bash scripts/update_ubuntu.sh
    ```

## 5.0 Verification
*   Docker containers `hwb_web_app`, `hwb_agent_worker`, `hwb_postgres_dev`, and `hwb_traffic_director` all show status "Running".
*   Port 8000 is active and responding with 200 OK.
*   The `Analytics` table in Postgres reflects the latest pulse data.

## 6.0 Notes and Cautions
*   **Zero-Synthetic Data:** All maintenance reports must be based on verified transactional records.
*   **Log Permission Warning:** If the system logs directory is root-owned and unwritable, the system will automatically fallback to root-level logging for the Traffic Director.

## 7.0 Revision History
| Version | Date | Author | Change Description |
| :--- | :--- | :--- | :--- |
| 1.0 | 2025-11-05 | Gemini | Initial Release (Legacy). |
| 2.0 | 2026-04-27 | George | Integrated Self-Healing Protocol, Persistent Agent Loops, and Docker Orchestration standards. |
