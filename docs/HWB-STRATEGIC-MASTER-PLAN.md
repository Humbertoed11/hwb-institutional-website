# SigmaFidelity™ Strategic Master Plan & Architectural Roadmap

**Document ID:** HWB-PLN-2026-Q3  
**Custodian:** George (Systems Architect & mbB)  
**Executive Authority:** Humberto Dominguez (CEO)  
**Version:** 3.0.0 (Enterprise Hardened)  
**Status:** ACTIVE & PERSISTED  

---

## 1.0 Executive Vision & Objectives
The overarching objective of the SigmaFidelity™ architecture is the complete operational digitization and automation of commercial facility maintenance, janitorial operations, and post-construction takeoff bidding across Texas.

### Core Growth & Velocity KPIs:
- **MRR Expansion:** Scaling commercial accounts and institutional contracts to high-margin recurring retainers.
- **100% Automation Coverage:** Migrating rule-based administration to autonomous daemons and background agents.
- **Zero-Friction Operations:** Relentless elimination of manual data entry, duplicate logging, and human error through strict typing and Poka-Yoke workflows.

---

## 2.0 Roadmap & Strategic Phasing

```mermaid
flowchart TD
    subgraph Phase 1: Completed Foundations
        P1A["ARCH-006 Frontier 1: Scope Parser & Proposal Factory"]
        P1B["BUG-090: Dynamic Project Resolver & Telegram Context"]
        P1C["Operational Form Hardening: Umbrella & Delivery Model"]
        P1D["Calendar Daycare Walkthrough Sync (2024-2025)"]
    end

    subgraph Phase 2: Immediate Staged Objectives
        P2A["ARCH-006 Frontier 2: Automated Addenda & RFI Delta Tracker"]
        P2B["ARCH-006 Frontier 3: Prime Contractor Teaming Radar"]
        P2C["GC Vetting Automation & Domain Enrichment"]
        P2D["Texas Statewide Lead Sync Expansion (CCL & GIS)"]
    end

    subgraph Phase 3: Mobile & Field Execution
        P3A["Standalone Mobile App for Technicians (Offline-First)"]
        P3B["React Scope of Work Real-Time Workflow Engine"]
        P3C["QR-Code Inspection & Safety Sign-off Sync"]
    end

    Phase 1 --> Phase 2
    Phase 2 --> Phase 3
```

---

## 3.0 Detailed Phase Breakdown

### Phase 1: Institutional Core & Backoffice Hardening (COMPLETED)
- [x] **Proposal Factory (`ARCH-006 Frontier 1`):** PyMuPDF 1.28.2 parsing multi-building municipal cleanable footprints and generating 3-Tier Negotiation Triads (Dallas Living Wage floor $18.00/hr).
- [x] **Dynamic Context Resolver (`BUG-090`):** Decoupled static Collin College context from `telegram_listener.py`; session tracking via `UserBehavioralProfiles.active_project_context`.
- [x] **Calendar Walkthrough Mining:** Extracted and linked CEO Humberto Dominguez's 2024–2025 daycare walkthrough visits to CRM records.
- [x] **Form Parity & Corporate Umbrella:** Added Corporate Umbrella, M&A Acquisition Tier, and Cleaning Delivery Model across Lead Edit, Add Lead, and Add Account forms. Unified 20 Fractal Education Group centers with zero missing fields.
- [x] **Peter's Recovery Shield:** Shadow snapshot automation (`peter_sentinel.py`), Ghost Checkpoint branch tracking, and daily incremental backups.

---

### Phase 2: Procurement Expansion & GC Intelligence (NEXT PRIORITY)

#### 2.1 ARCH-006 Frontier 2: Automated Addenda & RFI Delta Tracker
- **Objective:** Continuously monitor harvested municipal bids for addenda, wage rate updates, scope alterations, and schedule changes.
- **Implementation:**
  - Automated diffing between original specification PDFs and published addenda files.
  - Recalculation triggers in `core/services/estimator.py` if square footages or shift hours change.
  - High-priority alert generation in Backoffice Operations when proposal deadlines shift.

#### 2.2 ARCH-006 Frontier 3: Prime Contractor Teaming Radar
- **Objective:** Identify and track general contractors and joint venture primes bidding on institutional solicitations.
- **Implementation:**
  - Ingest pre-bid conference attendee rosters and planholder lists.
  - Cross-reference attendees with verified Texas commercial subcontractors and M/WBE compliance quotas.
  - Stage customized subcontract teaming proposals in `HWB-COMPANY/PendingOutbox/` under official letterhead (`HWB-COM-001`).

#### 2.3 Texas Statewide Lead Sync Daemon Expansion [2026-07-22 Mandate]
- **Objective:** Expand `scripts/daycare_registry_sync.py` and GIS spatial hunter from North Texas focus to statewide ingestion across all Texas metropolitan zones (Austin, San Antonio, Houston, El Paso, Rio Grande Valley).
- **Implementation:**
  - Update API endpoints to ingest all Texas CCL licenses without county bounding restrictions.
  - Implement automated duplicate deduplication and brand umbrella clustering (`autonomous_umbrella_engine.py`).

---

### Phase 3: Field Operations & Standalone Mobile App [2026-03-21 Mandate]

#### 3.1 Architecture & Stack
- **Framework:** Flutter / Compose Multiplatform (Offline-First architecture).
- **Core Engine:** Port of the React "Scope of Work" execution engine.
- **Data Layer:** Local SQLite / WatermelonDB synced bi-directionally with PostgreSQL `hwb_dev_db` / Azure Production via REST endpoints.

#### 3.2 Feature Deliverables
1. **Offline Workflow Execution:** Technicians can complete facility checklists, room inspections, and floor care sign-offs without cellular connectivity.
2. **GPS & Geofencing:** Auto-verification of technician presence on campus during scheduled shift windows.
3. **Poka-Yoke Visual Evidence:** Photo capture requirements for high-touch APPA Level 2 audit areas before shift completion.
4. **Supply & Chemical Tracker:** Field requisition of consumables and equipment maintenance logging.

---

## 4.0 Governance, Safety & Compliance Baseline

| Area | Governing Standard | Current Status |
| :--- | :--- | :--- |
| **QMS / Quality** | ISO 9001:2015 (10-Clause Manual) | 100% Inspection-Ready |
| **Safety / EHSQ** | HWB-EHS-001, 002, 003 | 0.00 TRIR (Zero incidents) |
| **Living Chronicles** | Act V: The Living Chronicles | Entries 001–010 Synchronized |
| **Data Integrity** | Empirical Data Integrity Mandate | Zero Synthetic Data; Empirical Heuristic Tags Active |
| **Recovery** | Peter Sentinel Shadow Snapshots | Active (`shadow_snapshots/`) |
| **Outbound Freeze** | CEO Humberto Dominguez Approval Rule | 100% Frozen; Stage in `PendingOutbox/` only |

---

*End of Strategic Master Plan — Persisted for Instant Session Handover*
