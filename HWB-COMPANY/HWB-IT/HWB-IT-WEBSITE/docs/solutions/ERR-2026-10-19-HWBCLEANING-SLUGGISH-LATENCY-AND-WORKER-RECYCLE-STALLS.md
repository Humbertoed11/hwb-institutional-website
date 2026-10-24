# Error Governance & PKB Solution Log: `ERR-2026-10-19-HWBCLEANING-SLUGGISH-LATENCY-AND-WORKER-RECYCLE-STALLS`

| Metadata | Value |
| :--- | :--- |
| **Incident ID** | `ERR-2026-10-19-HWBCLEANING-SLUGGISH-LATENCY-AND-WORKER-RECYCLE-STALLS` (`BUG-132` & `BUG-133`) |
| **Date** | `10/19/2026` |
| **System** | HWB Cleaning Institutional Website & Backoffice (`https://www.hwbcleaning.com/` / `/admin/operations`) |
| **Governing SOP** | `HWB-QMS-11.14 v1.1.0` (Release `v5.4.4`) |
| **Mission Orders** | `MO-HWB-2026-10-19-PERF-014` (`BUG-132`) & `MO-HWB-2026-10-19-PERF-015` (`BUG-133`) |
| **Custodians** | Super George (Commander of Special Ops) & George Bytes (HWB Tactical Builder) |
| **Approved By** | Humberto Dominguez (CEO) |

---

## 1.0 Symptom Description
1. **Part I (`BUG-132` — Public Website Latency & Cold-Starts):** Executive inspection reported that `https://www.hwbcleaning.com/` felt sluggish on initial page loads, periodic navigation transitions, and visual rendering despite running on an Azure App Service (`P0v3` / `B1` Linux container) fronted by Cloudflare CDN.
2. **Part II (`BUG-133` — Post-Login Backoffice Tab-Switching Stalls):** After logging into `/admin/operations`, switching between **Leads**, **Accounts**, **Construction Bids**, **Marketing**, **Workforce**, and **IT Command Hub** required `2.44 seconds` to `9.05 seconds` per click and downloaded `2.6 MB` to `3.3 MB` of HTML on every tab switch.

---

## 2.0 Part I (`BUG-132`): Public Website Root Causes & Resolutions (`v5.4.3`)

### Root Cause 1: Azure App Service Cold-Start Unloading (`AlwaysOn=false`)
- **Finding:** Azure App Service `hwb-institutional-website` had `alwaysOn: false`, `use32BitWorkerProcess: true`, and `healthCheckPath: null`.
- **Resolution:** Hardened live Azure App Service configuration to `alwaysOn=true`, `use32BitWorkerProcess=false`, and `healthCheckPath="/heartbeat"`.

### Root Cause 2: Un-Preloaded Gunicorn Workers Re-Running Boot Migrations & Seeders on Every Worker Recycle
- **Finding:** `Dockerfile` ran 3 Gunicorn workers without `--preload` and with `--max-requests 1000`. Meanwhile, `main_app.py` unconditionally spawned `run_async_infrastructure_boot()` and `run_autonomous_deal_sync_daemon()` inside every worker.
- **Resolution:** Added `--preload --workers 2 --threads 8 --max-requests 10000 --keep-alive 65` to `Dockerfile` and guarded the startup boot block in `main_app.py` with an atomic non-blocking POSIX file lock (`fcntl.flock(LOCK_EX | LOCK_NB)`).

### Root Cause 3: Per-Checkout `SET TIME ZONE` & `SELECT 1` Network Round-Trip in `core/services/database.py`
- **Finding:** `get_db()` executed network queries on every connection checkout and ran 4 RBAC permission queries on anonymous public routes.
- **Resolution:** Configured `ThreadedConnectionPool` with `options="-c timezone=America/Chicago"`, added a 60-second socket trust window (`_CONN_LAST_USED`), and bypassed RBAC permission queries on anonymous public routes.

### Root Cause 4: Per-Request Synchronous Disk Read in `core/services/version_service.py`
- **Resolution:** Added `@functools.lru_cache(maxsize=1)` to `get_version_info()`.

### Root Cause 5: `16.4 MB` of Uncompressed Public PNG/JPG Assets
- **Resolution:** Converted all 35 active public images to `.webp` (`16.4 MB` $\rightarrow$ `1.98 MB`, **`-87.9%` reduction**), updated templates to serve `.webp`, and added `loading="lazy" decoding="async"`.

### Root Cause 6: `Vary: Cookie` Forcing `cf-cache-status: DYNAMIC` on Public Marketing Pages
- **Resolution:** Updated `apply_application_security_headers(response)` in `main_app.py` to emit immutable 1-year `Cache-Control` on `/static/*` and `s-maxage=3600` without `Vary: Cookie` on anonymous public GET routes.

---

## 3.0 Part II (`BUG-133`): Post-Login Backoffice Root Causes & Resolutions (`v5.4.4`)

### Root Cause 7: The "22-Query God-Controller" Anti-Pattern in `blueprints/operations.py`
- **Finding:** Every click on `/admin/operations?view=<tab>` unconditionally executed all 22 SQL queries across all 11 departments (**Accounts**, **Leads**, **Construction Bids**, **General Contractors**, **Institutional Bids**, **Gov Programs**, **Marketing**, **Workforce**, **Shift Monitor**, **Scopes Matrix**, and **IT Command Hub**).
- **Resolution (Pillar 3 — Active-View CQRS SQL Isolation):** Refactored `blueprints/operations.py` so each request executes only the active department's SQL query plus a single 30-second cached sidebar badge query (`_get_operations_sidebar_counts`) and 60-second cached user directory (`_get_active_system_users`).

### Root Cause 8: Correlated Subqueries in Loops & Missing Composite Indexes
- **Finding:** `operations.py` executed per-row correlated subqueries on `"GlobalActivities"`, `"CampaignRecipients"`, `"ConstructionBids"`, and `"EmployeeDocuments"` without composite indexes on `(parent_type, parent_id)` or `(lead_id)`.
- **Resolution (Pillar 2 — Migration `043_backoffice_cqrs_covering_indexes`):** Added 4 covering composite indexes (`idx_global_activities_parent_lookup`, `idx_campaign_recipients_lead_lookup`, `idx_leads_assigned_rep_status`, `idx_employee_documents_employee_id`) and replaced all correlated subqueries with set-based `LEFT JOIN` / `WITH paged_leads` CTE aggregations.

### Root Cause 9: Uncached 11-Rack Self-Healing Telemetry & `.env` Disk Scans on Every Click
- **Finding:** `operations.py` synchronously executed all 11 Racks of `self_healing_engine.py` and `audit_all_credentials()` on every page load (`1.2s – 6.5s` of CPU, disk, and DNS socket blocking).
- **Resolution (Pillar 1 — 300s Async Background Telemetry Cache):** Added a thread-safe 300-second TTL cache (`_TELEMETRY_CACHE` and `_CREDENTIAL_CACHE`) with non-blocking daemon refresh threads (`force_refresh=True` supported for manual IT audits), and gated `it_telemetry` synthesis exclusively behind `active_view in ('it_department', 'it_telemetry')`.

### Root Cause 10: `3.3 MB` Monolithic DOM Payload & `391 KB` Inline JavaScript
- **Finding:** `templates/backoffice_operations.html` (`16,900` lines) rendered all 11 hidden department views, 28 modals, and `391 KB` of inline `<script>` on every click.
- **Resolution (Pillar 4 — Server-Side Jinja DOM Pruning & Static JS Extraction):** Extracted `static/js/backoffice_operations_core.js` (`391 KB`, browser-cached) and wrapped inactive `<div id="view-...">` inner blocks and department-specific modals in server-side `{% if active_view == '...' %}` guards.

### Root Cause 11 (`BUG-134`): Unclosed `#view-monitor` Container (`display: none`) Trapping Downstream Modals
- **Finding:** In `templates/backoffice_operations.html` (line `4002`), `<div id="view-monitor" style="display: none;">` was opened outside `{% if active_view in ['monitor', 'dispatch'] %}`, while its matching closing `</div>` tag (line `4272`) was placed inside the conditional block. On non-Monitor tabs (`view=leads`, `view=accounts`, etc.), Jinja skipped the closing `</div>` tag, wrapping all downstream views (`#view-scope`, `#view-it-department`) and modals (`#modal-lead-command`, `#modal-account-command`, `#modal-commercial-takeoff`, etc.) inside `#view-monitor` (`display: none`).
- **Resolution:** Closed `{% if active_view in ['monitor', 'dispatch'] %}` inside `#view-monitor` before its closing `</div>` tag, wrapped `#modal-dispatch-create` and `#modal-dispatch-detail` in a balanced block outside `#view-monitor`, replaced `ARRAY_AGG` in `ConstructionBids` with `LEFT JOIN LATERAL` (`147ms -> 30ms`), and added `test_11_backoffice_modal_dom_isolation_and_lead_click` in `scripts/test_web_performance_rack_14.py` (`11/11` passed).

---

## 4.0 Empirical Before vs. After Benchmark (`v5.4.4`)

| Backoffice Department View | Pre-Fix Latency | Post-Fix Warm Latency (`v5.4.4`) | Speedup | Gzipped Payload |
| :--- | :--- | :--- | :--- | :--- |
| **Leads (`/admin/operations?view=leads`)** | `2,440 ms – 4,100 ms` | **`28.01 ms`** | **`98.9%` faster** | `63.0 KB` |
| **Accounts (`/admin/operations?view=accounts`)** | `2,510 ms` | **`6.53 ms`** | **`99.7%` faster** | `40.8 KB` |
| **Construction Bids (`?view=construction_bids`)** | `2,680 ms` | **`125.99 ms`** | **`95.3%` faster** | `69.8 KB` |
| **General Contractors (`?view=general_contractors`)** | `2,490 ms` | **`6.09 ms`** | **`99.8%` faster** | `43.2 KB` |
| **Institutional Bids (`?view=institutional_bids`)** | `2,520 ms` | **`7.81 ms`** | **`99.7%` faster** | `51.4 KB` |
| **Gov Programs (`?view=programs`)** | `2,460 ms` | **`4.38 ms`** | **`99.8%` faster** | `38.9 KB` |
| **Marketing (`?view=marketing`)** | `2,490 ms` | **`5.16 ms`** | **`99.8%` faster** | `39.4 KB` |
| **Safety (`?view=safety`)** | `2,450 ms` | **`4.99 ms`** | **`99.8%` faster** | `36.5 KB` |
| **Workforce (`?view=workforce`)** | `2,550 ms` | **`10.34 ms`** | **`99.6%` faster** | `59.1 KB` |
| **Shift Monitor (`?view=monitor`)** | `2,480 ms` | **`7.55 ms`** | **`99.7%` faster** | `41.2 KB` |
| **IT Command Hub (`?view=it_department`)** | `4,100 ms – 9,050 ms` | **`7.41 ms`** | **`99.8%` faster** | `42.0 KB` |

---

## 5.0 5-Table Error & Audit Database Synchronization Ledger (Migration `044`)
- **`"SigmaKnowledgeScars"`:** `BUG-132` (`id=224`), `BUG-133` (`id=225`), & `BUG-134` (`id=226`)
- **`"GlobalActivities"`:** `[AUTO-HEALED-PERFORMANCE-BUG-132]` (`activity_id=208726`), `[AUTO-HEALED-PERFORMANCE-BUG-133]` (`activity_id=208727`), & `[AUTO-HEALED-DOM-BUG-134]` (`activity_id=209008`)
- **`"Incidents"`:** `BUG-132` (`id=3`), `BUG-133` (`id=4`), & `BUG-134` (`id=5`)
- **`"RackTelemetryHistory"`:** `session_id='HWB-QMS-11.14-V5.4.4-AUDIT'` (`id=3455`)
- **`"SecurityAuditLogs"`:** `event_action='HWB_QMS_11_14_V5_4_4_BUG_132_133_REMEDIATED'` (`id=2646`)

