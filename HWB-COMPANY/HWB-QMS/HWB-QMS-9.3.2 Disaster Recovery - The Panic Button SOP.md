| **Document Control** | |
| :--- | :--- |
| **Document Title** | **Disaster Recovery: The Panic Button SOP** |
| **Document ID** | HWB-QMS-9.3.2-PANIC |
| **Version** | 1.0.0 |
| **Status** | ACTIVE |
| **Author** | George (Systems Architect) |
| **Approved By** | Humberto Dominguez, CEO |
| **Date** | 04/27/2026 |

---

# 1.0 Objective
To provide a definitive, high-velocity response protocol for catastrophic system failures, data corruption, or accidental deletions. This SOP acts as the "Panic Button," guiding the operator through the immediate restoration of SigmaFidelity™ infrastructure.

# 2.0 Roles and Responsibilities
- **George (Systems Architect):** Decision authority on rollback necessity and target timestamps.
- **Peter (Recovery Specialist):** Primary autonomous execution agent for all backup/restore logic.
- **CEO (Humberto Dominguez):** Final approval for total system rollbacks.

# 3.0 The Recovery Stack (Tactics)
The system is protected by five autonomous layers managed by the **Peter Sentinel**:
1.  **Disk Protection (15m):** Prevents crashes via log/disk monitoring.
2.  **Shadow Snapshots (15m):** Hard-linked file-level recovery for web development.
3.  **Binary DB Snapshots (1h):** PostgreSQL state recovery via `.sql` archives.
4.  **Vault Guardian (24h):** Full institutional archival of SOPs and secrets.
5.  **Ghost Checkpoints (Pre-Stop):** Captures uncommitted Git state.

# 4.0 Protocol: The "Panic Button" Sequence

## STEP 1: Damage Assessment
1. Locate and read the **Black Box** at `HWB-COMPANY/HWB-DATA/HWB-SESSION-RECOVERY.md`.
2. Identify the **Heat Zone Files** and the **Timestamp** of the last successful action.

## STEP 2: Choose Restoration Path
- **If Code is Broken:** Locate the nearest **Shadow Snapshot** in `backup/shadow_snapshots/` and execute:
  `cp -r backup/shadow_snapshots/web_dev_[TIMESTAMP]/* HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/`
- **If Data is Lost:** Locate the nearest **DB Snapshot** in `backup/` and execute:
  `python3 scripts/peter_sentinel.py --restore backup/hwb_db_snapshot_[TIMESTAMP].sql`
- **If System is Unstable:** Perform a **Ghost Rollback** using the latest `kit-ghost-` branch in Git.

## STEP 3: Verification
1. Run the Diagnostic Dashboard: `docker exec hwb_web_app python diag_dashboard.py`.
2. Verify log health: `journalctl -u sigma-peter -n 20`.

# 5.0 Emergency Summoning
In a state of total disorientation, the human operator may summon Peter directly for any specific recovery task using the CLI:
- `python3 scripts/peter_sentinel.py --help`

---
**Institutional Standard Active**
*This document is a mandate of the SigmaFidelity™ Quality Management System.*
