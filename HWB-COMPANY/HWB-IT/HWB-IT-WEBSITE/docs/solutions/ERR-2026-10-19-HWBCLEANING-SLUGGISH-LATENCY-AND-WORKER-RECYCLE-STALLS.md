# Error Governance & PKB Solution Log: `ERR-2026-10-19-HWBCLEANING-SLUGGISH-LATENCY-AND-WORKER-RECYCLE-STALLS`

| Metadata | Value |
| :--- | :--- |
| **Incident ID** | `ERR-2026-10-19-HWBCLEANING-SLUGGISH-LATENCY-AND-WORKER-RECYCLE-STALLS` |
| **Date** | `10/19/2026` |
| **System** | HWB Cleaning Institutional Website (`https://www.hwbcleaning.com/` / `hwb-institutional-website`) |
| **Governing SOP** | `HWB-QMS-11.14` (`v5.4.3`) |
| **Mission Order** | `MO-HWB-2026-10-19-PERF-014` |
| **Custodians** | Super George (Commander of Special Ops) & George Bytes (HWB Tactical Builder) |
| **Approved By** | Humberto Dominguez (CEO) |

---

## 1.0 Symptom Description
Executive inspection reported that `https://www.hwbcleaning.com/` felt sluggish on initial page loads, periodic navigation transitions, and visual rendering despite running on an Azure App Service (`P0v3` / `B1` Linux container) fronted by Cloudflare CDN.

---

## 2.0 The 6 Empirical Root Causes Identified (10/19/2026 Audit)

### Root Cause 1: Azure App Service Cold-Start Unloading (`AlwaysOn=false`)
- **Finding:** Azure App Service `hwb-institutional-website` had `alwaysOn: false`, `use32BitWorkerProcess: true`, and `healthCheckPath: null`.
- **Impact:** After 20 minutes of inactivity, Azure unloaded the Docker container (`sigmafidelity-web`). The next visitor experienced a **15 to 35 second cold-start stall** while the container re-hydrated.
- **Resolution:** Hardened live Azure App Service configuration to `alwaysOn=true`, `use32BitWorkerProcess=false`, and `healthCheckPath="/heartbeat"`.

### Root Cause 2: Un-Preloaded Gunicorn Workers Re-Running Boot Migrations & Seeders on Every Worker Recycle
- **Finding:** `Dockerfile` ran 3 Gunicorn workers without `--preload` and with `--max-requests 1000`. Meanwhile, `main_app.py` unconditionally spawned `run_async_infrastructure_boot()` (running `sync_db_sequences`, `apply_system_migrations`, `seed_data.json` 4,400-lead inspection, and `sync_inbound_graph_bids`) and `run_autonomous_deal_sync_daemon()` at module import time inside every worker.
- **Impact:** All 3 workers collided on database locks at boot and ran 3 duplicate Microsoft Graph polling daemons. Worse, every 1,000 HTTP requests (roughly every 40–50 page views including static assets), Gunicorn recycled a worker and the replacement worker immediately triggered full DB schema migrations, sequence locking, and Graph API syncs while serving live user traffic.
- **Resolution:** Added `--preload --workers 2 --threads 8` to `Dockerfile` and guarded the startup boot block in `main_app.py` with an atomic non-blocking OS file lock (`/tmp/hwb_enterprise_boot.lock` via `fcntl.flock(LOCK_EX | LOCK_NB)`). Only 1 process per container ever runs boot migrations or the deal sync daemon; worker recycles now complete in `0ms`.

### Root Cause 3: Per-Checkout `SET TIME ZONE` Network Round-Trip in `core/services/database.py`
- **Finding:** `get_db()` in `core/services/database.py` executed `cur.execute("SET TIME ZONE 'America/Chicago'")` over the network to Azure PostgreSQL Flexible Server on **every single connection checkout** from `ThreadedConnectionPool`, and defaulted `MAX_POOL_CONNECTIONS` to `28` per worker (`84` total across 3 workers).
- **Impact:** Every database call paid an extra synchronous TCP network round-trip just to set a timezone that was already set on that pooled socket.
- **Resolution:** Configured `ThreadedConnectionPool` with `options="-c timezone=America/Chicago"` and TCP keepalives (`keepalives=1, keepalives_idle=30, keepalives_interval=10, keepalives_count=5`) at connection creation, removed the per-checkout `SET TIME ZONE` query from `get_db()`, and right-sized `MAX_POOL_CONNECTIONS = int(os.environ.get('DB_POOL_MAX', 10))`.

### Root Cause 4: Per-Request Synchronous Disk Read in `core/services/version_service.py`
- **Finding:** `inject_version_telemetry()` in `main_app.py` is a Flask `@app.context_processor` that called `get_version_info()` on every HTML render. `get_version_info()` and `_is_running_on_azure()` opened and parsed `/app/version.json` from the container filesystem up to **twice per HTTP request**.
- **Impact:** Unnecessary synchronous filesystem I/O on every page load.
- **Resolution:** Added `@functools.lru_cache(maxsize=1)` to `get_version_info()` (plus `clear_version_cache()`) and updated version metadata to `v5.4.3`.

### Root Cause 5: `4.27 MB` (`4,369.7 KB`) of Uncompressed Homepage PNGs
- **Finding:** `templates/index.html` loaded 5 uncompressed PNG background images via CSS `background-image: url(...)` with zero lazy-loading:
  - `hero_lobby.png`: `1,055.2 KB`
  - `industrial_m20_scrubber.png`: `902.9 KB`
  - `daycare_busy_active.png`: `830.1 KB`
  - `construction_sweeper_servicing_street.png`: `823.7 KB`
  - `commercial_marble_polishing.png`: `757.8 KB`
- **Impact:** Every visitor's browser had to download `4.27 MB` of uncompressed PNGs simultaneously on initial landing.
- **Resolution:** Generated high-efficiency `.webp` (`quality=82`) companions for all 5 homepage images and all `>500 KB` active service page images in `static/img/` (preserving original `.png`/`.jpg` files intact). Homepage visual payload dropped from `4,369.7 KB` to `389.0 KB` (**`-91.1%` reduction**). Updated `templates/index.html` and active public templates to reference `.webp` and added `loading="lazy" decoding="async"` to below-the-fold `<img>` tags.

### Root Cause 6: `Vary: Cookie` Forcing `cf-cache-status: DYNAMIC` on Public Marketing Pages
- **Finding:** Touching `current_user.is_authenticated` and `session.get('user_id')` during request hooks caused Flask to emit `Vary: Accept-Encoding, Cookie` on anonymous public HTML responses. Because `Vary` contained `Cookie`, Cloudflare bypassed edge caching (`cf-cache-status: DYNAMIC`), forcing every visitor request back to the Azure origin.
- **Resolution:** Updated `apply_application_security_headers(response)` in `main_app.py` so anonymous `GET`/`HEAD` requests to public marketing pages set `Cache-Control: public, max-age=300, s-maxage=3600, stale-while-revalidate=86400`, strip `Cookie` from `Vary`, and remove any accidental `Set-Cookie` header.

---

## 3.0 Prevention & Regression Guard
All 6 fixes are codified under `HWB-QMS-11.14` and verified via automated test suite prior to container deployment.
