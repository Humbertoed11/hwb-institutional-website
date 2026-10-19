# Standard Operating Procedure: Enterprise Web Performance, Twelve-Factor Stateless Workers & Edge Caching Standard

| Document Control | Value |
| :--- | :--- |
| **Document Title** | **Enterprise Web Performance, Twelve-Factor Stateless Workers & Edge Caching Standard** |
| **Document ID** | `HWB-QMS-11.14` |
| **Version** | `1.0.0` (`v5.4.3`) |
| **Status** | `APPROVED` |
| **Author** | George (Systems Architect) & George Bytes (HWB Tactical Builder) |
| **Approved By** | Humberto Dominguez (Chief Executive Officer) |
| **Effective Date** | `10/19/2026` |
| **ISO 9001:2015 Clause** | `7.1.3` (Infrastructure), `8.5.1` (Control of Production and Service Provision), `9.1.1` (Monitoring, Measurement, Analysis and Evaluation) |

---

## 1.0 Purpose
This Standard Operating Procedure (SOP) establishes the mandatory 5-Pillar Enterprise Web Performance Standard for the HWB Cleaning Services LLC institutional web application (`https://www.hwbcleaning.com/`). It eliminates cold-start stalls, Gunicorn worker recycle freezes, redundant database network round-trips, per-request disk reads, oversized static image payloads, and CDN cache bypasses.

## 2.0 Scope
This procedure applies to all production and local container deployments of the HWB Web Platform (`/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE`), Microsoft Azure App Service (`hwb-institutional-website`), Azure Container Registry (`hwbprodacr`), PostgreSQL connection pools (`core/services/database.py`), and Cloudflare Edge CDN caching rules (`main_app.py`).

## 3.0 The 5-Pillar Enterprise Web Performance Standard

### 3.1 Pillar 1: Azure App Service Infrastructure Hardening
1. **Zero Cold-Start Eviction (`AlwaysOn=true`):** The Azure App Service (`hwb-institutional-website` in `HWB-Production-RG`) must maintain `alwaysOn=true` at all times so the Linux container is never unloaded after idle periods.
2. **64-Bit Worker Architecture (`Use32BitWorkerProcess=false`):** The Azure App Service platform configuration must enforce 64-bit worker execution (`use32BitWorkerProcess=false`).
3. **Automated Health Probe (`HealthCheckPath="/heartbeat"`):** Azure App Service health monitoring must probe `/heartbeat` to guarantee continuous container warmth and automatic unhealthy instance replacement.

### 3.2 Pillar 2: Twelve-Factor Stateless Web Workers & Single-Execution Boot Guard
1. **Preloaded Right-Sized Gunicorn Topology:** On a 1-vCore Linux host (Azure `B1` / `P0v3`), Gunicorn must launch with `--preload --workers 2 --threads 8 --worker-class gthread`. Preloading loads the application into master memory before forking worker processes, reducing RAM overhead and accelerating worker creation.
2. **Single-Execution Atomic File Lock (`/tmp/hwb_enterprise_boot.lock`):** Web workers must never execute database schema migrations, 4,400-row lead seeding, or duplicate background polling loops when recycling (`--max-requests 1000`). The startup boot block in `main_app.py` must acquire a non-blocking exclusive OS file lock (`fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)`) on `/tmp/hwb_enterprise_boot.lock` before spawning `run_async_infrastructure_boot` or `run_autonomous_deal_sync_daemon`. Any recycled or secondary worker that fails to acquire the lock must skip boot threads in `0ms`.

### 3.3 Pillar 3: Zero-Round-Trip Pooled Database Connections
1. **Connection-Init Timezone & TCP Keepalives:** Every PostgreSQL connection created by `ThreadedConnectionPool` in `core/services/database.py` must initialize with `options="-c timezone=America/Chicago"` and OS-level TCP keepalives (`keepalives=1`, `keepalives_idle=30`, `keepalives_interval=10`, `keepalives_count=5`).
2. **Zero-Round-Trip Checkout:** `get_db()` must return pooled connections directly in `0ms` without executing a redundant `SET TIME ZONE 'America/Chicago'` SQL round-trip across the network on every checkout.
3. **Right-Sized Pool Ceiling (`DB_POOL_MAX=10`):** Default `MAX_POOL_CONNECTIONS` per process is capped at `10` (with `MIN_POOL_CONNECTIONS=2`) to prevent connection exhaustion across multi-worker containers.

### 3.4 Pillar 4: In-Memory Version & Telemetry Cache
1. **Zero Per-Request Disk I/O:** `get_version_info()` in `core/services/version_service.py` must be decorated with `@functools.lru_cache(maxsize=1)` so `/app/version.json` is parsed once per process lifetime rather than read from disk on every HTML request via Flask `@app.context_processor`.
2. **Cache Invalidation Helper:** A `clear_version_cache()` function must be exposed for unit tests and administrative hot-reload routines.

### 3.5 Pillar 5: Next-Gen WebP Image Pipeline & Split Cloudflare Edge Caching
1. **Next-Gen WebP Assets:** All homepage and high-traffic service page hero/card images exceeding `500 KB` must be encoded in `.webp` (`quality=82`), achieving an empirical `91%` homepage visual payload reduction (`4,369.7 KB` PNG down to `389.0 KB` WebP) while preserving original `.png`/`.jpg` files on disk for backward compatibility. Below-the-fold `<img>` elements must include `loading="lazy" decoding="async"`.
2. **Split Cloudflare Edge Caching:**
   - **Anonymous Public Marketing `GET`/`HEAD` Routes:** When `not session.get('user_id') and not current_user.is_authenticated` on non-protected paths, `apply_application_security_headers(response)` in `main_app.py` must emit `Cache-Control: public, max-age=300, s-maxage=3600, stale-while-revalidate=86400`, strip `Cookie` from `Vary` (leaving `Vary: Accept-Encoding`), and delete any accidental `Set-Cookie` header so Cloudflare edge nodes cache and serve public HTML in `<25ms`.
   - **Authenticated & Backoffice Routes (`/admin`, `/api`, `/auth`, `/sales-desk`, `/login`, `/logout`):** Must enforce `Cache-Control: no-cache, no-store, must-revalidate, private, max-age=0` and `Pragma: no-cache` to guarantee zero cross-user data leakage.

---

## 4.0 Verification & Audit Matrix
| Metric | Pre-Hardening Baseline | Mandatory Target | Verification Method |
| :--- | :--- | :--- | :--- |
| Azure Cold Start Idle Eviction | `AlwaysOn=false` (15–35s stall) | `AlwaysOn=true` (`0s` stall) | `az webapp config show` |
| Worker Recycle Boot Overhead | 3 workers running migrations/seeders | Single-execution lock (`0ms` recycle) | `main_app.py` `/tmp/hwb_enterprise_boot.lock` |
| DB Checkout Network Round-Trips | 1 SQL query per `get_db()` checkout | `0` extra queries (`options="-c timezone=..."`) | `core/services/database.py` inspection |
| `version.json` Disk Reads | 1 disk `open()` per HTML page | `1` read per process (`@lru_cache`) | `core/services/version_service.py` inspection |
| Homepage Image Payload (5 visuals) | `4,369.7 KB` (`4.27 MB` PNG) | `< 450 KB` (`389.0 KB` WebP, `-91.1%`) | `ls -lh static/img/*.webp` & `templates/index.html` |
| Public HTML Edge Cache Headers | `Vary: Accept-Encoding, Cookie` (`DYNAMIC`) | `Vary: Accept-Encoding` + `s-maxage=3600` | `curl -sI https://www.hwbcleaning.com/` |

---
*Approved by Humberto Dominguez, Chief Executive Officer — HWB Cleaning Services LLC*
