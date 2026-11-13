# PKB Solution: 4-Layer Fleet Polling, Container Watchdog & Index-Scan Optimization (`BUG-174` / `HWB-QMS-9.2`)

- **Date:** `11/11/2026`
- **Author:** Super George (Systems Architect) & George Bytes (HWB Tactical Builder)
- **Approved By:** Humberto Dominguez (CEO)
- **References:** `BUG-174`, `SO-SCAR-023`, `HWB-QMS-7.6`, `HWB-QMS-9.2`

---

## 1.0 Problem Statement
Telemetry audits across `hwb_agent_worker` and `hwb_postgres_dev` identified four steady-state polling inefficiencies:
1. **Legacy `/mnt/c` OneDrive `tail -F` Subprocess in `watchdog.py`:** `hwb_agent_worker` ran a legacy `watchdog.py` spawning `tail -F /mnt/c/Users/humbe/OneDrive - hwbcleaning.com/.../HWB-WEB Server.log` across the WSL2 9P bridge and probing `127.0.0.1:5000/admin/operations` instead of the internal Docker service.
2. **High-Frequency `AIEmployeeHeartbeat` SQL Writes:** `worker_launcher.py` wrote two `AIEmployeeHeartbeat` upserts every `10` seconds (`12` SQL write transactions/minute) alongside child process `poll()` checks.
3. **Missing Lookup Indexes on `"Users"` & Expression Indexes on `"EmailSuppressionList"`:** `"Users"` (`2,104` sequential scans) lacked B-Tree indexes on `(username)`, `(LOWER(username))`, and `(LOWER(email))`.
4. **Hidden Browser Tab Polling:** `templates/backoffice_base.html` (`updateHeartbeat`) and `static/js/sigma_breadcrumbs.js` (`setInterval` flush) continued firing background HTTP/DB requests when browser tabs were minimized.

## 2.0 4-Layer Enterprise Resolution
1. **Layer 1 — Online PostgreSQL B-Tree Indexes (`CREATE INDEX CONCURRENTLY IF NOT EXISTS`):**
   - Created `idx_users_username`, `idx_users_lower_username`, `idx_users_lower_email`, `idx_email_suppression_lower_expr`, and `idx_email_suppression_btrim_lower` online on `hwb_postgres_dev`, calibrated `random_page_cost = 1.1`, and persisted all index definitions in `database/schema_engine.py` for Azure parity.
2. **Layer 2 — Container-Native HTTP `watchdog.py` (Zero `/mnt/c` or `tail -F`):**
   - Replaced `watchdog.py` with a PEP 8 typed container-native probe checking `HWB_WATCHDOG_HEALTH_URL` (`http://hwb_web_app:5000/login`) every `60s` (`timeout=5s`) with a 3-strike consecutive-failure alert counter and clean `SIGTERM`/`SIGINT` handling.
3. **Layer 3 — Coalesced `worker_launcher.py` Heartbeat Writes (`85%` Write Reduction):**
   - Preserved `10s` `p.poll()` child process supervision while gating `AIEmployeeHeartbeat` SQL writes behind a `60.0s` `last_heartbeat_ts` window.
4. **Layer 4 — Browser Page-Visibility Guards (`document.hidden`):**
   - Added `if (document.hidden) return;` (plus `visibilitychange` resume sync) in `templates/backoffice_base.html` (`updateHeartbeat`) and `static/js/sigma_breadcrumbs.js` (`setInterval` flush while keeping `visibilitychange` and `pagehide` unload flushes intact).
