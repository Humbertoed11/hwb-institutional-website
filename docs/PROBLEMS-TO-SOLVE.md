# SigmaFidelity™ Institutional Error Log (PROBLEMS-TO-SOLVE)
Standard: HWB-QMS-1.0 v2.0
Responsibility: George (Architect)

| Date | Issue ID | Description | Status | Impact |
| :--- | :--- | :--- | :--- | :--- |
| 06/01/2026 | BUG-033 | QMS Manual visibility failure (Ghost Volume glitch). | **RESOLVED** | HIGH |
| 06/01/2026 | MIG-001 | Antigravity CLI migration (Quota Exhaustion fallback active). | **IN PROGRESS** | CRITICAL |
| 06/23/2026 | MIG-002 | Session recovery file path mismatch inside container. | **RESOLVED** | MEDIUM |
| 06/23/2026 | SYS-001 | Postgres psql command hanging on interactive TTY pager. | **RESOLVED** | LOW |
| 06/23/2026 | BUG-034 | Operations page HTTP 500 / Gunicorn worker timeout. | **RESOLVED** | HIGH |
| 06/23/2026 | BUG-035 | Login redirection loop on local custom domains. | **RESOLVED** | HIGH |
| 06/23/2026 | BUG-036 | Invalid credentials on hdominguez login due to typo. | **RESOLVED** | HIGH |
| 06/23/2026 | BUG-037 | QMS manual document accessibility failure. | **RESOLVED** | HIGH |
| 06/23/2026 | BUG-038 | Recurrence of Ghost Volume Glitch on QMS templates. | **RESOLVED** | HIGH |
| 07/20/2026 | BUG-039 | Inconsistent and amateur visual weights in popup forms. | **RESOLVED** | MEDIUM |
| 07/20/2026 | BUG-040 | Modal delete stays on deleted record instead of sliding or closing. | **RESOLVED** | HIGH |
| 07/20/2026 | BUG-041 | Docker Desktop socket deletion and Telegram listener HTTP 409 collision. | **RESOLVED** | HIGH |




## BUG-033: Ghost Volume Glitch
**Detected:** 06/01/2026
**Symptoms:** `/manual` endpoint returns 200 OK but content zone is empty; Nginx logs show 404 for fragments.
**Root Cause:** `hwb_compliance_engine` starts before the Docker volume bind-mount from the host is fully synchronized.
**Solution:** Restarted the container.
**Preventative:** Add `sleep 5` or a volume check to `scripts/startup_master.sh`.

## MIG-002: Session Recovery Path Mismatch
**Detected:** 06/23/2026
**Symptoms:** Run of `sigma_sync.py` in container does not pick up latest host-level `HWB-SESSION-RECOVERY.md` updates.
**Root Cause:** The container only mounts the `HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE` subfolder. Root-level `HWB-SESSION-RECOVERY.md` is not visible inside the container.
**Solution:** Copied root recovery file to the container app directory before running the sync script.
**Preventative:** Modify `scripts/sigma_sync.py` to copy the file or use a shared bind mount.

## SYS-001: Psql Interactive TTY Hanging
**Detected:** 06/23/2026
**Symptoms:** `docker exec -t ... psql` query hangs indefinitely in background execution.
**Root Cause:** The interactive TTY allocation `-t` forces the output into a pager, pausing for keyboard input.
**Solution:** Removed `-t` and added `-A -t` parameters to `psql` to force clean non-interactive print.

## BUG-034: Operations Page Timeout / HTTP 500
**Detected:** 06/23/2026
**Symptoms:** `http://mop.test:5000/admin/operations` throws 500 error or connection times out.
**Root Cause:** Gunicorn worker failed to boot due to `ModuleNotFoundError` on container mismatch, and subsequently timed out due to database connection leaks in the `load_user` Flask-Login helper during unauthenticated request floods.
**Solution:** Initialized container suite via `startup_master.sh` to resolve boot path alignment, and verified connection leaks are blocked by `finally` blocks in `load_user` and other database operations.
**Preventative:** Strictly enforce `finally: conn.close()` on all database operations and run standard startup diagnostics.

## BUG-035: Login Redirection Loop / SameSite Cookie Mismatch
**Detected:** 06/23/2026
**Symptoms:** Logging in accepts correct username and password, but immediately redirects back to `/login` instead of showing `/admin/operations`.
**Root Cause:** The session cookie lacked an explicit `SameSite` attribute. Modern browsers reject or block cookies lacking explicit SameSite attributes on insecure local custom TLDs (like `mop.test:5000` over HTTP).
**Solution:** Explicitly configured `SESSION_COOKIE_SAMESITE = 'Lax'`, `SESSION_COOKIE_HTTPONLY = True`, and environment-specific `SESSION_COOKIE_SECURE` (`False` for local dev, `True` for production HTTPS) in `config.py` per QMS-9.7 specifications.
**Preventative:** Standardize explicit SameSite and Secure cookie inheritance for all corporate tenants and local sandbox portals.

## BUG-036: Invalid Credentials on hdominguez Login
**Detected:** 06/23/2026
**Symptoms:** Logging in as `hdominguez` with correct password `password11` fails with "invalid credentials".
**Root Cause:** The database user password hash was initialized using the typo string `assword11` from legacy scripts, causing standard logins with the correct spelling `password11` to fail hash verification.
**Recurrence (07/10/2026):** The login failure returned because a database restoration from `pre_consolidation_snapshot_05-22-2026_1405.sql` re-seeded the outdated/corrupted password hashes into the PostgreSQL database.
**Solution:** Re-ran python commands to generate and set fresh, cryptographically valid hashes for both `admin` (`HWB-Admin-2026!`) and `hdominguez` (`password11`) in both PostgreSQL and SQLite user tables.
**Preventative:** Standardize user seeding configurations and verify credentials against literal keys before committing password hashes.

## BUG-037: QMS Manual Document Accessibility Failure
**Detected:** 06/23/2026
**Symptoms:** Requesting specific QMS manual pages from `/manual/<filename>` returns "Document not found (404)".
**Root Cause:**
1. Four Obsidian-related HTML SOP files were located in the `trash/` directory instead of the active `static/qms/` directory.
2. The index file `qms_index.json` mapped `hwb-qms-9.1_gemini_master_setup_sop.html` as the target file, but on disk the file was named `hwb-qms-9.1_antigravity_master_setup_sop.html` (filename mismatch).
**Solution:**
1. Restored the 4 Obsidian HTML documents from `trash/` to `static/qms/`.
2. Updated the filename reference for the master setup document in `qms_index.json` to `hwb-qms-9.1_antigravity_master_setup_sop.html`.
**Preventative:** Perform automated file integrity checks on static resources during the database handshake sync.

## BUG-038: Recurrence of Ghost Volume Glitch on QMS Templates
**Detected:** 06/23/2026
**Symptoms:** Requests to `hwb-pur-001_container_xchange.html` and other QMS pages returned "Document not found (404)".
**Root Cause:** The bind mount mapping `/usr/share/nginx/html/qms` inside the `hwb_compliance_engine` container was empty, causing Nginx to serve 404 for all files even though they existed on the host.
**Solution:** Restarted the `compliance` container via `docker-compose restart compliance` to refresh the bind mounts.
**Preventative:** Check if `/usr/share/nginx/html/qms` inside the compliance container contains files during the master startup sequence, and auto-restart the container if it is empty.

## BUG-039: Inconsistent and amateur visual weights in popup forms
**Detected:** 07/20/2026
**Symptoms:** Details popup forms show oversized input boxes and loud, heavy `800`/`900` font weights for data values.
**Root Cause:**
1. CSS style class `.sigma-input` used `padding: 0.5rem 0.75rem` (40px height) and `font-weight: 600`.
2. Javascript dynamic template injected `font-weight: 800` and `font-size: 1.15rem` for read-only data values.
3. Overview cards used inside-card boundaries (`.isc-list-item`) which clashed with outer-label forms styling.
**Solution:**
1. Modified `.sigma-input` to use vertically compressed `0.4rem 0.65rem` padding (32-34px height) and medium `500` weight.
2. Standardized details values in Javascript template to `font-weight: 600` and `font-size: 0.9rem`.
3. Converted Overview tab cards to borderless `.sigma-read-field` with Title Case outer labels sitting above values.
4. Standardized split grid layouts across all tab screens to `300px 1fr` columns with a `2.5rem` gap.
**Preventative:** Strictly follow the *Outer Label and Grid Stability Standard* codified in version 5.0 of HWB-QMS-7.2.

## BUG-040: Modal delete stays on deleted record
**Detected:** 07/20/2026
**Symptoms:** Clicking "Delete Lead" (or "Delete Account") from inside the details modal successfully deletes the record, but leaves the modal open showing the deleted data.
**Root Cause:** The `deleteLead` and `deleteAccount` callbacks did not close the modal or switch to the adjacent records after the DELETE background query.
**Solution:** Updated callbacks to check if the modal is open. If so, they scan the table row elements to retrieve the adjacent record's ID and load it instantly. If no records remain on the page, the modal closes.
**Preventative:** Standardize in-modal deletions to use transition navigation handlers.

## BUG-041: Docker Desktop Socket Deletion and Telegram Listener Collision
**Detected:** 07/20/2026
**Symptoms:** `hwb_agent_worker` logs show repeated `[TELEGRAM] getUpdates error: HTTP 409` errors, blocking the containerized Telegram daemon from fetching updates. Additionally, Port 8000 returns a 502 routing error.
**Root Cause:**
1. A duplicate container stack was running under the legacy host `snap.docker.dockerd` service, running an older `telegram_listener.py` instance that collided with the new Docker Desktop stack.
2. The legacy snap container stack bound to Port 8000 on the host, preventing the new gateway from routing web traffic.
3. Stopping the snap service successfully deleted the duplicate containers, but also deleted the shared `/var/run/docker.sock` socket file.
**Solution:**
1. Disabled and stopped the `docker.dockerd` snap service permanently to prevent legacy container auto-restart.
2. Toggled the WSL integration in the Docker Desktop settings GUI to force the integration daemon to recreate the `/var/run/docker.sock` file and restart all containers cleanly.
**Preventative:** Ensure Docker Desktop is the sole active container runtime, and verify `/var/run/docker.sock` validity during the pre-flight check.







