# HWB-QMS-9.3.1 Disaster Recovery (Shadow Snapshots) SOP

## 1.0 Objective
To ensure zero data loss for active web development projects by maintaining a high-frequency (15-minute) rotation of hard-linked snapshots. This protocol allows for near-instant rollback to a specific point-in-time without the overhead of full backups.

## 2.0 Scope
This SOP applies to the `HWB-IT-WEBSITE` directory and related web development assets within the SigmaFidelity™ environment.

## 3.0 Responsibilities
- **Peter (Recovery Specialist):** Responsible for the autonomous execution and verification of the sentinel loop.
- **George (Systems Architect):** Responsible for summoning Peter during catastrophic events.

## 4.0 Procedure: Automated Sentinel
1.  The **Peter Sentinel** service executes a Shadow Snapshot every 15 minutes.
2.  Snapshots are stored in `backup/shadow_snapshots/web_dev_YYYY-MM-DD_HHMM/`.
3.  The system utilizes `rsync` with `--link-dest` to minimize disk usage (hard-links are used for unchanged files).
4.  A rolling retention policy of **48 snapshots** (12 hours) is enforced to prevent disk saturation.

## 5.0 Procedure: Emergency Rollback (Summoning Peter)
In the event of a catastrophic failure:
1.  Identify the target timestamp folder in `backup/shadow_snapshots/`.
2.  Execute the manual restoration command:
    ```bash
    cp -r backup/shadow_snapshots/web_dev_[TIMESTAMP]/* HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/
    ```
3.  Verify system integrity by running `diag_dashboard.py`.

## 6.0 Manual Summoning
To trigger an immediate snapshot outside the 15-minute schedule:
```bash
python3 scripts/peter_sentinel.py --shadow
```

---
**Status:** Institutional Standard Active
**Revision:** 1.0.0 (04-27-2026)
**Approval Authority:** Humberto Dominguez (CEO)
