| **Document Control** | |
| :--- | :--- |
| **Document Title** | **AI Agents and Specialized Automation Scripts SOP** |
| **Document ID** | HWB-QMS-9.2 |
| **Version** | 4.5.0 |
| **Status** | APPROVED |
| **Author** | George (Systems Architect) |
| **Approved By** | Humberto Dominguez, CEO |
| **Date** | 11/12/2026 |

---

# Standard Operating Procedure: **AI Agents and Specialized Automation Scripts SOP**

## 1.0 Purpose
Defines execution standards, process supervision rules, polling cadences, and governance boundaries for all autonomous AI agents and background utilities operating in the HWB Cleaning Services LLC infrastructure.

## 2.0 Scope
Applies to all background daemons in `hwb_agent_worker`, `hwb_web_app`, Linux `cron` jobs (`scripts/hwb_hourly_backup.sh`), and CLI workspace hooks (`.agents/hooks.json`).

## 3.0 Core Daemon & Script Inventory
* **`worker_launcher.py` (`hwb_agent_worker`):** Master container supervisor launching and monitoring background agents with 60-second coalesced worker heartbeats (`BUG-174`).
* **`watchdog.py` (`hwb_agent_worker`):** 60-second health-check loop (`BUG-174`) querying the web container directly via Docker bridge container IP and monitoring logs for template or database lock faults.
* **`sigma_orchestrator.py` (`hwb_agent_worker`):** 6-hour analytics and procurement mining orchestrator writing directly to PostgreSQL 16.15 (`hwb_postgres_dev` / `sigmajan-server`).
* **`telegram_listener.py` (`hwb_agent_worker`):** Mobile command listener enforcing 5-tier RBAC, anti-narrowing context resolution (`ARCH-014`), and pre-change rollback staging (`BUG-163`).
* **`tessa_regression_suite.py` (`hwb_agent_worker`):** Continuous 1-hour 11-module platform regression suite.
* **`scripts/hwb_hourly_backup.sh` (`Linux cron :00`):** Hardened native `ext4` hourly snapshot script writing 24-hour rolling `pg_dump -Fc` binary backups locked to `chmod 600` with SHA-256 checksums (`hwb_dev_db.dump.sha256`) into `backups/hourly/` and `backups/latest/`. Replaces the retired `sigma-peter.service` 15m daemon and OneDrive `9P` sync (`BUG-173` / `SO-SCAR-023`).
* **`scripts/peter_sentinel.py` (`v2.0.0`):** Unified 3-command local recovery utility strictly scoped to `/home/humbertoed/gemini_projects`: `checkpoint --label <name>` (pins `chmod 600` PG16 dump, `.env`, and active code/QMS tar bundle in `backups/checkpoints/<name>/` with `SHA256SUMS.txt` and live `hwb_peter_verify_tmp` test-restore), `rollback --label <name> [--code-only | --full]` (`--full` restores via clean staging DB `hwb_restore_stage` before swapping `hwb_dev_db`), and `verify` (checks `<90m` freshness, `chmod 600`, and SHA-256, logging status to `"AIEmployeeHeartbeat"` and `"SecurityAuditLogs"`).
* **`core/ai_employee/seo_growth_engine.py` (Lauri Tells `#11`):** Search & Organic Growth AI Employee pairing internal 24h/7d conversion funnel monitoring (`"SEOMetricsSnapshots"`, `"SEOKeywordRadar"`) with a 900-second cached read-only Google Cloud Service Account connector (`GOOGLE_SERVICE_ACCOUNT_JSON`, `GA4_PROPERTY_ID`, `GSC_SITE_URL`) querying Google Analytics 4 Data API and Google Search Console Search Analytics API (`GRO-09` Striking-Distance positions `8.0–20.0`, zero synthetic numbers).
* **`sigma_sync.py`:** Synchronizes canonical QMS HTML procedures and resolved engineering lessons into PostgreSQL 16.15 (`sigma_kb` and `"SigmaKnowledgeScars"`).

## 4.0 Engineering & Runtime Governance Mandates
1. **Idempotency & Zero Synthetic Data:** All scripts must be 100% idempotent and operate strictly on verified transactional PostgreSQL 16.15 records.
2. **Outbox Gate:** Automated scripts stage outbound proposals exclusively in `PendingOutbox` (`HWB-COM-001`) for CEO approval.
3. **Proportional First-Pass Engineering (`GOV-04 Revised` / `SigmaKnowledgeScars #268` — `11/12/2026`):**
   * `fortune500-closed-loop-governor` (`scripts/agy_fortune500_gate_hook.py`) is set to `"enabled": false` in `.agents/hooks.json`.
   * Enforce **Smallest Proven Fix First**: never invent new tables, daemons, cron loops, or multi-layer wrappers when a configuration edit, SQL index, or dead-code removal solves the measured bottleneck.
   * Freeze all new meta-infrastructure unless required by an active customer or revenue campaign.
   * Pause and obtain explicit CEO Humberto Dominguez approval before modifying any host PC file (`/mnt/c/...`, `.wslconfig`, Docker Desktop, `crontab`, `systemd`, or `.bashrc`).

## 5.0 Verification
* `docker top hwb_agent_worker` confirms all 4 active supervised processes.
* `python3 scripts/peter_sentinel.py verify` confirms `<90m` freshness, `chmod 600` permissions, and SHA-256 checksum match on `backups/latest/hwb_dev_db.dump`.
* `scripts/test_web_performance_rack_14.py` and `scripts/check_soc2_data_leakage.py` pass at 100%.

## 6.0 Revision History
| Version | Date | Author | Change Description |
| :--- | :--- | :--- | :--- |
| 4.5.0 | 11/12/2026 | Lauri Tells & George (Systems Architect) | Added `core/ai_employee/seo_growth_engine.py` (Lauri Tells `#11`) read-only Google Analytics 4 Data API and Google Search Console Search Analytics API connector (`GRO-09` Striking-Distance `8.0–20.0`, 900s cache, zero synthetic data). Approved by Humberto Dominguez, CEO. |
| 4.4.0 | 11/12/2026 | Peter & George (Systems Architect) | Standardized `scripts/peter_sentinel.py v2.0.0` (`checkpoint`, `rollback [--code-only \| --full]`, `verify`) and hardened `scripts/hwb_hourly_backup.sh` (`chmod 600` + `.sha256`). Approved by Humberto Dominguez, CEO. |
| 4.3.0 | 11/12/2026 | George (Systems Architect) | Synchronized Markdown SOP with `v4.3.0` HTML baseline: codified `BUG-173` (`scripts/hwb_hourly_backup.sh` replacing `sigma-peter.service` & OneDrive `9P` sync), `BUG-174` (`watchdog.py` 60s Docker bridge IP loop & 60s worker heartbeats), and `GOV-04 Revised` / Scar `#268` (disabled forced chat hook, Smallest Proven Fix First, Host PC Approval Gate). Approved by Humberto Dominguez, CEO. |
| 4.2.0 | 10/29/2026 | George (Systems Architect) | Added 24/7 Enterprise AI Employee Engine (`BUG-163`). |
| 1.0.0 | 02/28/2026 | Gemini | Initial Release. |
