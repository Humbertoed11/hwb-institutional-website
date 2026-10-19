# Standard Operating Procedure: Enterprise Web Performance, Twelve-Factor Stateless Workers, Edge Caching & Post-Login CQRS Backoffice Standard

| Document Control | Value |
| :--- | :--- |
| **Document Title** | **Enterprise Web Performance, Twelve-Factor Stateless Workers, Edge Caching & Post-Login CQRS Backoffice Standard** |
| **Document ID** | `HWB-QMS-11.14` |
| **Version** | `1.1.0` (`v5.4.4`) |
| **Status** | `APPROVED` |
| **Author** | George (Systems Architect) & George Bytes (HWB Tactical Builder) |
| **Approved By** | Humberto Dominguez (Chief Executive Officer) |
| **Effective Date** | `10/19/2026` |
| **ISO 9001:2015 Clause** | `7.1.3` (Infrastructure), `8.5.1` (Control of Production and Service Provision), `9.1.1` (Monitoring, Measurement, Analysis and Evaluation) |

---

## 1.0 Purpose
This Standard Operating Procedure (SOP) establishes the mandatory Enterprise Web & Backoffice Performance Standard for the HWB Cleaning Services LLC institutional platform (`https://www.hwbcleaning.com/`).
- **Part I (`v1.0.0` / `v5.4.3`)** eliminates public surface cold-start stalls, Gunicorn worker recycle freezes, redundant database network round-trips, per-request disk reads, oversized static image payloads, and CDN cache bypasses.
- **Part II (`v1.1.0` / `v5.4.4`)** establishes the **5-Pillar Enterprise Backoffice & Post-Login Workspace Architecture (`<150ms` CQRS Standard)** for `/admin/operations`, eliminating synchronous external HTTP probes on the request thread, $O(N \times M)$ correlated SQL subqueries, multi-department SQL over-fetching, and `2.6 MB – 3.3 MB` hidden DOM rendering.

## 2.0 Scope
This procedure applies to all production and local container deployments of the HWB Web Platform (`/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE`), Microsoft Azure App Service (`hwb-institutional-website`), Azure Container Registry (`hwbprodacr`), PostgreSQL connection pools (`core/services/database.py`), telemetry services (`core/services/self_healing_engine.py`, `core/services/credential_sentinel.py`), backoffice controllers (`blueprints/operations.py`), and Jinja2 templates (`templates/backoffice_operations.html`).

---

## 3.0 Part I: The 5-Pillar Public Surface & Stateless Worker Standard (`v1.0.0`)

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
1. **Next-Gen WebP Assets:** All homepage and high-traffic service page hero/card images exceeding `500 KB` must be encoded in `.webp` (`quality=82`), achieving an empirical `92.7%` homepage visual payload reduction (`4,369.7 KB` PNG down to `319.5 KB` WebP) while preserving original `.png`/`.jpg` files on disk for backward compatibility. Below-the-fold `<img>` elements must include `loading="lazy" decoding="async"`.
2. **Split Cloudflare Edge Caching:**
   - **Anonymous Public Marketing `GET`/`HEAD` Routes:** When `not session.get('user_id') and not current_user.is_authenticated` on non-protected paths, `apply_application_security_headers(response)` in `main_app.py` must emit `Cache-Control: public, max-age=300, s-maxage=3600, stale-while-revalidate=86400`, strip `Cookie` from `Vary` (leaving `Vary: Accept-Encoding`), and delete any accidental `Set-Cookie` header via `_edge_safe_save_session` so Cloudflare edge nodes cache and serve public HTML in `<25ms`.
   - **Authenticated & Backoffice Routes (`/admin`, `/api`, `/auth`, `/sales-desk`, `/login`, `/logout`):** Must enforce `Cache-Control: no-cache, no-store, must-revalidate, private, max-age=0` and `Pragma: no-cache` to guarantee zero cross-user data leakage.

---

## 4.0 Part II: The 5-Pillar Enterprise Backoffice & Post-Login Workspace Architecture (`v1.1.0`)

### 4.1 Pillar 1: Asynchronous Background Telemetry Cache (Zero Synchronous Outbound HTTP Probes on Request Threads)
1. **Strict Prohibition of Synchronous External HTTP Calls on User Threads:** User-facing HTTP request threads in `/admin/operations` must NEVER block on outbound network requests to `api.cloudflare.com`, `api.telegram.org`, `api.github.com`, `hwbcleaning.com`, `hwb-institutional-website.azurewebsites.net`, or remote SSL handshakes.
2. **5-Minute (`300s` TTL) Thread-Safe Telemetry Cache:** `core/services/self_healing_engine.py` and `core/services/credential_sentinel.py` must maintain a process-level thread-safe cache (`_TELEMETRY_CACHE` with `TTL = 300s`) and non-blocking background refresh threads. All telemetry getters must accept `force_refresh: bool = False` for explicit diagnostic refreshes.
3. **Active-View Gate for IT Telemetry:** In `blueprints/operations.py`, the 11-Rack `it_telemetry` dictionary must ONLY be computed when `active_view in ('it_department', 'it_telemetry')`. On all other operational views (`leads`, `accounts`, `construction_bids`, `marketing`, `workforce`, etc.), `it_telemetry` must default to `{}` in `0ms`.

### 4.2 Pillar 2: Set-Based SQL Aggregation & Covering Composite Indexes (Zero Correlated Subqueries)
1. **Mandatory Composite Covering Indexes:** `database/schema_engine.py` and all PostgreSQL environments (`hwb_postgres_dev` and `sigmajan-server.postgres.database.azure.com`) must maintain:
   - `CREATE INDEX IF NOT EXISTS idx_global_activities_parent_lookup ON "GlobalActivities" (parent_type, parent_id, timestamp DESC);`
   - `CREATE INDEX IF NOT EXISTS idx_campaign_recipients_lead_lookup ON "CampaignRecipients" (lead_id, id DESC);`
2. **Elimination of Row-by-Row Correlated Subqueries:** Queries on `"Leads"`, `"Customers"` (`Accounts`), `"ConstructionBids"`, `"InstitutionalBids"`, and `"GeneralContractors"` in `blueprints/operations.py` must use single-pass set-based `LEFT JOIN` derived aggregations on `"GlobalActivities"` and `"CampaignRecipients"` rather than executing 2 to 4 correlated subqueries per row.

### 4.3 Pillar 3: Strict Active-View CQRS SQL Isolation & Cached Sidebar Badge Counts
1. **30-Second Cached Sidebar & KPI Counts:** `blueprints/operations.py` must compute lightweight department badge counts via a 30-second TTL cached helper (`_get_operations_sidebar_counts`) and cache active `"Users"` for 60 seconds (`_get_active_system_users`).
2. **Active-View Query Gating:** Each department's heavy data query (`leads`, `accounts`, `construction_bids`, `general_contractors`, `institutional_bids`, `programs`, `marketing`, `safety`, `workforce`, `monitor`, `scope`, `it_department`) must execute ONLY when `active_view` matches that department (or when `request.args.get('format') == 'json'` is requested). Inactive departments receive empty collections (`[]`) in `0ms`.

### 4.4 Pillar 4: Server-Side Jinja DOM Pruning & Externalized Static JS Bundle (`<250 KB` HTML Payload Cap)
1. **Server-Side Active View Rendering:** In `templates/backoffice_operations.html`, the inner HTML table/card trees of each `<div id="view-..." class="isc-view">` container and heavy department-specific modals must be wrapped in `{% if active_view == '...' %}` blocks so inactive departments are never serialized into the DOM.
2. **Externalized Static Operations Script:** The 382 KB backoffice JavaScript controller logic must be served from a browser-cacheable static asset (`/static/js/backoffice_operations_core.js`) while keeping dynamic Jinja configuration variables (`USER_MAP`, `IS_SALES_ROLE`, `CURRENT_CALLER_NAME`, `CURRENT_CALLER_EMAIL`, `BACKOFFICE_JOB_POSITIONS`) in a lightweight inline bootstrap `<script>`.
3. **Hard Payload Ceiling:** Every `/admin/operations?view=<dept>` HTML response must remain under `250 KB` uncompressed (down from `2,598 KB – 3,345 KB`).

### 4.5 Pillar 5: Instantaneous Tab Navigation & Automated Performance Regression Gate
1. **Sub-150ms Warm Tab Switching:** All 6 core post-login departments (`leads`, `accounts`, `construction_bids`, `marketing`, `workforce`, `it_department`) must render in `<150ms` warm locally and `<300ms` on Azure App Service.
2. **Automated Regression Gate:** `scripts/test_web_performance_rack_14.py` must enforce both Part I (public surface) and Part II (post-login backoffice CQRS, covering indexes, telemetry cache, and `<250 KB` HTML payload ceiling) prior to every production deployment.

---

## 5.0 Verification & Audit Matrix
| Metric | Pre-Hardening Baseline | Mandatory Target | Verification Method |
| :--- | :--- | :--- | :--- |
| Azure Cold Start Idle Eviction | `AlwaysOn=false` (15–35s stall) | `AlwaysOn=true` (`0s` stall) | `az webapp config show` |
| Worker Recycle Boot Overhead | 3 workers running migrations/seeders | Single-execution lock (`0ms` recycle) | `main_app.py` `/tmp/hwb_enterprise_boot.lock` |
| DB Checkout Network Round-Trips | 1 SQL query per `get_db()` checkout | `0` extra queries (`options="-c timezone=..."`) | `core/services/database.py` inspection |
| `version.json` Disk Reads | 1 disk `open()` per HTML page | `1` read per process (`@lru_cache`) | `core/services/version_service.py` inspection |
| Homepage Image Payload (5 visuals) | `4,369.7 KB` (`4.27 MB` PNG) | `< 450 KB` (`319.5 KB` WebP, `-92.7%`) | `ls -lh static/img/*.webp` & `templates/index.html` |
| Public HTML Edge Cache Headers | `Vary: Accept-Encoding, Cookie` (`DYNAMIC`) | `Vary: Accept-Encoding` + `s-maxage=3600` | `curl -sI https://www.hwbcleaning.com/` |
| `/admin/operations?view=leads` Latency & Size | `9,046 ms` / `2,598 KB` (`2.6 MB`) | `< 150 ms` warm / `< 250 KB` | `scripts/test_web_performance_rack_14.py` |
| `/admin/operations?view=accounts` Latency & Size | `2,584 ms` / `3,345 KB` (`3.3 MB`) | `< 150 ms` warm / `< 250 KB` | `scripts/test_web_performance_rack_14.py` |
| `/admin/operations?view=construction_bids` | `2,535 ms` / `3,345 KB` (`3.3 MB`) | `< 150 ms` warm / `< 250 KB` | `scripts/test_web_performance_rack_14.py` |
| `/admin/operations?view=marketing` | `2,520 ms` / `3,345 KB` (`3.3 MB`) | `< 150 ms` warm / `< 250 KB` | `scripts/test_web_performance_rack_14.py` |
| `/admin/operations?view=workforce` | `2,442 ms` / `3,345 KB` (`3.3 MB`) | `< 150 ms` warm / `< 250 KB` | `scripts/test_web_performance_rack_14.py` |
| `/admin/operations?view=it_department` | `3,572 ms` / `3,345 KB` (`3.3 MB`) | `< 150 ms` warm / `< 250 KB` | `scripts/test_web_performance_rack_14.py` |

---
*Approved by Humberto Dominguez, Chief Executive Officer — HWB Cleaning Services LLC*
