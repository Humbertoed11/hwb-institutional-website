# PKB Solution: Dual-OS Workstation Governor Post-Mortem & Non-Destructive Guardrails (`BUG-173` / `SO-SCAR-023` / `BABYSOP-SOP-0.15 v2.2.0`)

- **Date:** `11/11/2026`
- **Author:** Super George (Systems Architect) & George Bytes (HWB Tactical Builder)
- **Approved By:** Humberto Dominguez (CEO)
- **References:** `BUG-173`, `SO-SCAR-023`, `HEX-SCAR-100100`, `BABYSOP-SOP-0.15 v2.2.0`

---

## 1.0 Problem Statement
During the morning workstation maintenance execution on `11/11/2026`, five cross-boundary Dual-OS governor defects destabilized live operator sessions and container runtimes across Windows 11 and WSL2 Ubuntu:
1. **Windows 11 `$parentDead` Console Reaper:** Killing `conhost.exe` processes based on a missing `ParentProcessId` (`$parentDead`) terminated `60+` live Windows 11 terminal sessions whose short-lived launcher/wrapper processes had already exited normally.
2. **`.wslconfig` Deletion & Simultaneous Memory Squeeze:** Combining an aggressive `.wslconfig` `8GB` / `dropCache` change with simultaneous live WSL2 cgroup memory squeezes destabilized WSL2 and left `.wslconfig` deleted.
3. **500 MB Active CLI Folder Eviction:** Enforcing a `500 MB` size ceiling on the active CLI conversation directory swept `21` recent active sessions to cold archive prematurely.
4. **8-Second Hair-Trigger Docker Desktop Kill:** Enforcing an `8s` `docker info` timeout automatically force-killed a busy but healthy Docker Desktop daemon during heavy container I/O.
5. **Legacy OneDrive 9P `sigma-peter.service` Lock Contention:** A legacy systemd unit (`sigma-peter.service`) continuously polled `/mnt/c/.../OneDrive` across the WSL2 9P bridge and collided on `.git/index.lock`.

## 2.0 Root-Cause Resolution (`BABYSOP-SOP-0.15 v2.2.0`)
1. **Safe Console Hygiene (`heal_zombie_conhosts()`):**
   - Removed `$parentDead` parent-PID reaping logic so live Windows 11 console hosts whose parent launcher exited are never terminated.
2. **Deterministic WSL2 Memory Profile (`.wslconfig`):**
   - Restored `.wslconfig` with a stable `12GB` allocation, `autoMemoryReclaim=gradual`, and `instanceIdleTimeout=-1`.
3. **14-Day Age-Based Session Retention:**
   - Removed the `500 MB` active folder cap and restored the `11/10/2026` CLI sessions under a deterministic `14-day` age retention policy.
4. **Passive 60-Second Docker Readiness & Explicit Opt-In Restart:**
   - Replaced the `8s` automatic kill trigger with a `60s` passive Docker readiness probe, gating any destructive restart strictly behind the explicit operator flag `--force-restart-deadlocked-docker`.
5. **Permanent Decommissioning of Legacy OneDrive 9P Poller:**
   - Permanently disabled the legacy systemd `sigma-peter.service` unit to eliminate `/mnt/c` OneDrive 9P filesystem polling and `.git/index.lock` collisions.

## 3.0 Preventative Governance Rule
- **Hard Constraint (`SO-SCAR-023` / `BUG-173`):** Never kill Windows `conhost.exe` by missing parent PID (`$parentDead`), never wire destructive Win32 or Docker kills into automatic background loops or short timeouts, never enforce a `500 MB` active CLI folder cap, and always audit `systemctl` units to prevent `/mnt/c` OneDrive 9P polling loops.
