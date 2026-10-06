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
        P1E["Migration 026: 7-Rack SPC Telemetry Ledger"]
        P1F["ARCH-007: Telegram Operations Gateway & /cmd Shell"]
    end

    subgraph Phase 2: Immediate Staged Objectives
        P2A["Twilio WebRTC Voice Softphone & Cadence Automation (Tomorrow)"]
        P2B["ARCH-006 Frontier 2: Automated Addenda & RFI Delta Tracker"]
        P2C["ARCH-006 Frontier 3: Prime Contractor Teaming Radar"]
        P2D["GC Vetting Automation & Domain Enrichment"]
        P2E["Texas Statewide Lead Sync Expansion (CCL & GIS)"]
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
- [x] **Historical SPC Telemetry Ledger (`Migration 026`):** Provisioned `RackTelemetryHistory` in PostgreSQL and automated 7-rack capture during session finalization.
- [x] **Telegram Operations Gateway & Permissions Architecture (`ARCH-007`):** Embedded single-pane mobile user management inside `/admin/executive#users`. Enforced 5-Tier permission matrix, single-use token Magic Link onboarding (`https://t.me/Georgebytesbot?start=auth_<token>`), `/cmd <bash>` mobile Linux terminal shell gateway, episodic conversational memory, and live Google Search Grounding with Gemini 2.5 Flash.

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

#### 2.4 Twilio WebRTC In-Browser Calling & Telephony Automation Engine [Planning Target: Tomorrow 09/25/2026]
- **Objective:** Eliminate manual dialing and external application switching by embedding a native WebRTC softphone directly into the Calling Cadence Console (`modal-lead-cadence`) and Field Sales Desk (`/sales-desk`).
- **Financial Architecture:**
  - Client WebRTC connection leg: $0.0040 / minute.
  - Outbound US PSTN destination leg: $0.0140 / minute.
  - Total combined calling rate: $0.0180 / minute (~$2.25/day for 100 calls, ~$50.65/month per representative).
  - Dedicated local Texas caller ID number: $1.15 / month per salesperson.
- **Implementation Deliverables for Tomorrow:**
  1. **Twilio Voice Backend (`core/services/telephony.py`):**
     - JWT Capability Token endpoint (`/api/v1/voice/token`) with identity mapping to active CRM user.
     - TwiML Voice Webhook (`/api/v1/voice/call-connect`) bridging WebRTC browser audio to outbound prospect phone numbers with local Texas caller ID.
     - Telephony Webhook (`/api/v1/voice/call-status`) capturing empirical call duration and connection status.
  2. **In-Browser Softphone Cockpit (`modal-lead-cadence` in `templates/backoffice_operations.html`):**
     - Embed Twilio Voice JavaScript SDK directly into the calling console.
     - Real-time audio indicators: In-Call timer, live mute/unmute microphone toggle, and call disconnect.
     - Headset direct stream: Zero external OS app prompts or FaceTime popups.
  3. **Automated Post-Call Workflows:**
     - Automatic activity creation in `GlobalActivities` with empirical call duration.
     - 1-Click "Send 1-Page Info Sheet" triggering Microsoft Graph API outbound email.
     - Automatic queue advance upon hang-up or outcome button selection.

#### 2.5 Corporate Umbrella & Parent Organization Data Architecture [Planning Target: Tomorrow 10/04/2026]
- **Objective:** Enable multi-unit commercial clustering, parent-child account mapping, and centralized procurement routing for regional daycare franchises, healthcare clinics, and property management portfolios.
- **Implementation Deliverables for Tomorrow:**
  1. **Parent-Child Schema Architecture (`core/models/crm.py` & PostgreSQL):**
     - `umbrella_organization_id`: Foreign key or UUID linking branch facility locations to an overarching parent corporate entity.
     - `parent_company_name`: Verified parent enterprise name (e.g., *KinderCare Learning Companies, Inc.*, *Primrose Schools Corporate*, *Transwestern Property Group*).
     - `corporate_structure_type`: Standardized taxonomy (`FRANCHISE_INDEPENDENT`, `FRANCHISE_CORPORATE_OWNED`, `CORPORATE_CHAIN`, `INDEPENDENT_STANDALONE`, `GOVERNMENT_DISTRICT`).
     - `decision_making_tier`: Operational authority level (`LOCAL_DIRECTOR_AUTONOMY`, `REGIONAL_DIRECTOR_APPROVAL`, `CENTRALIZED_CORPORATE_PROCUREMENT`).
     - `cleaning_delivery_model`: Operational janitorial model populated via opt-out feedback survey (`IN_HOUSE_STAFF` vs `OUTSOURCED_CONTRACT`).
     - `parent_headquarters_ref`: Corporate procurement contact, HQ address, and master contract agreement reference.
  2. **Automated Brand Clustering:**
     - Pattern matching engine scanning incoming leads to auto-associate childcare chains with their verified corporate parent.
     - Centralized reporting rollup: View aggregated square footage, student capacity, and contract value across all centers under a single umbrella.
  3. **Verified Calendar Appointment Engine (DEPLOYED & ACTIVE):**
     - Active Booking URL: `https://bookings.cloud.microsoft/book/FacilityWalkthroughquote@NETORGFT3163094.onmicrosoft.com/` (15-min discovery walkthroughs with Humberto Dominguez).
     - Integrated with Poka-Yoke legacy click intercept in `blueprints/telemetry.py` and `PendingOutbox` marketing pipeline.

#### 2.6 Application User Support Technical Manual (Chapters 1–6) [Top Priority Tomorrow 10/06/2026]
- **Objective:** Create, build, and deploy the comprehensive, role-gated Application User Support Technical Manual to empower team members to operate the web platform with zero training friction and eliminate support phone calls.
- **Master Chapter Architecture:**
  - **Chapter 1: Personal Account, Login & Security Settings:** Logging in, session timeouts (30-min auto-logout), password recovery, and personal security hygiene.
  - **Chapter 2: CRM & Leads Pipeline:** Navigating the lead table, column customizer presets, territory filtering, manual lead intake, and facility specifications.
  - **Chapter 3: Commercial Bidding, Takeoffs & Public Sector Programs:** Commercial GC pipeline, Yamamoto Moto AI Estimator, area takeoff calculations, ISSA 612 production rates, Dallas Living Wage compliance, and proposal generation.
  - **Chapter 4: Marketing Campaigns, Daycare Outreach & Email Delivery:** Childcare targeting, automated cadence sequences, Microsoft Graph API delivery, and CAN-SPAM opt-out handling.
  - **Chapter 5: Field Operations, Dispatch, Workforce & Safety:** Shift dispatching, cleaner W-2 & subcontractor 1099 management, safety standards (HWB-EHS), and inspection logs.
  - **Chapter 6: IT Command Hub, System Administration & Data Integrity:** 11-Rack monitoring, user permission governance (Custom zero-trust role), database backups, and SOC 2 / ISO 27001 audit controls.
- **In-App Delivery Architecture:**
  - Dedicated contextual in-app view or slide-out drawer opening directly to the user's active screen.
  - Role-filtered visibility: Users only see chapters and sections matching their active role permissions.

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
| **Living Chronicles** | Act V: The Living Chronicles | Entries 001–025 Synchronized |
| **Data Integrity** | Empirical Data Integrity Mandate | Zero Synthetic Data; Empirical Heuristic Tags Active |
| **Recovery** | Peter Sentinel Shadow Snapshots | Active (`shadow_snapshots/`) |
| **Outbound Freeze** | CEO Humberto Dominguez Approval Rule | 100% Frozen; Stage in `PendingOutbox/` only |
| **Calendar Booking** | Microsoft Bookings (Facility Walkthrough) | Active & Verified (`FacilityWalkthroughquote@NETORGFT3163094.onmicrosoft.com`) |

---

| Priority | Feature / Module | Target Date | Executive Owner | Unit Cost Floor | Operational Impact | Automation Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **P0** | **Application User Support Technical Manual (Chapters 1–6)** | **Tomorrow (10/06/2026)** | George (Architect) & Yamamoto Moto (Estimator) | In-house ($0.00) | End-to-end user manual across all 6 modules (Personal Settings, CRM Leads, Commercial Bidding, Marketing Campaigns, Operations/Safety, IT Command Hub) with in-app slide-out drawer | **STAGED FOR TOMORROW (TOP PRIORITY)** |
| **P0** | **Corporate Umbrella & Parent Entity Data Architecture** | 10/06/2026 | Silas Sync (CRM) & George (Architect) | In-house ($0.00) | Hierarchical multi-unit clustering, corporate parent IDs, and procurement decision routing | Staged |
| **P1** | **Twilio WebRTC Softphone & Calling Console** | 10/07/2026 | Hunter Vance (Sales) & Silas Sync (CRM) | $0.0180/min + $1.15/mo | 50 calls/hr inside browser; zero manual dialing | Staged |
| **P1** | **ARCH-006 Frontier 2: Automated Addenda Tracker** | 10/08/2026 | Yamamoto Moto (Lead Estimator) | In-house ($0.00) | Auto-diffing bid specs & deadline drift alerts | Queued |
| **P1** | **ARCH-006 Frontier 3: Prime Contractor Radar** | 10/09/2026 | George (Systems Architect) | In-house ($0.00) | Harvesting planholder lists & JV teaming proposals | Queued |
| **P2** | **Texas Statewide CCL & GIS Sync Daemon** | 10/10/2026 | Silas Sync (VP of CRM) | State Open Data ($0.00) | Statewide expansion across Austin, Houston, DFW | Queued |
| **P2** | **Standalone Mobile App for Cleaning Techs** | Phase 3 | Engineering & Peter (Recovery) | In-house ($0.00) | Offline-first React Scope of Work engine | Active Branch |

---

*End of Strategic Master Plan — Persisted for Instant Session Handover*
