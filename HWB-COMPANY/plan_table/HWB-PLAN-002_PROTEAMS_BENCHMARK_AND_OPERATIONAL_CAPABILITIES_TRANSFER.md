| **Document Control** |                                                                    |
| :------------------- | :----------------------------------------------------------------- |
| **Document Title**   | **HWB Plan Table: ProTeams Operational Machinery & Contract Defense Transfer** |
| **Document ID**      | [HWB-PLAN-002]                                                     |
| **Planning Code**    | [PLAN-TABLE-HWB-2026-02]                                           |
| **Version**          | 1.0.0                                                              |
| **Status**           | Placed on HWB Plan Table for Executive Discussion                  |
| **Author**           | Super George (Special Ops Command & Lead Systems Architect)        |
| **Target Builder**   | George Bytes (HWB Lead Systems Builder)                            |
| **Approved By**      | Humberto Dominguez (Chief Executive Officer)                       |
| **Fiscal Authority** | Maria Bolanos (Vice President of Finance)                          |
| **Effective Date**   | 10/12/2026                                                         |
| **Standard Baseline**| ISO 9001:2026 (ISO 9001:2015+Amd 1:2024) Clause 8.2 • Mandate 1 (Empirical Truth) • Mandate 9 (Everyday Words) |

---

# HWB Planning Table: ProTeams Operational Machinery & Contract Defense Transfer

```text
+─────────────────────────────────────────────────────────────────────────────────────────+
|                                HWB CLEANING SERVICES LLC                                |
|                        EXECUTIVE STRATEGY & PLANNING TABLE BRIEF                        |
|        Fidelity • Safety • Respect • ISO 9001:2026 (ISO 9001:2015+Amd 1:2024) Certified • McKinney, Texas          |
+─────────────────────────────────────────────────────────────────────────────────────────+
```

## 1.0 Executive Context: Transferring ProTeams Field Capabilities to HWB

On 10/12/2026, CEO Humberto Dominguez reviewed the competitive audit of ProTeams.io and instructed Special Ops Command to place these capabilities directly onto the **HWB Planning Table for executive discussion and technical execution**.

ProTeams is a specialized commercial cleaning software company operating across New York, New Jersey, and Dallas. Their entire business is built around one core operational reality:
> *"Most cleaning contracts are not lost because of price. They are lost because a cleaner failed to show up, or the building owner believes the work was skipped."*

HWB already holds a substantial competitive edge in lead generation (23,610+ verified Texas leads), complex government bidding ($10.5M+ active pipeline), and ISO 9001 quality management. 

By integrating ProTeams' field defense tools into HWB's web portal and mobile app, HWB can eliminate customer doubt, deliver proof of work after every shift, and capture high-intent commercial leads directly from its public website.

---

## 2.0 The Five Strategic Initiatives on the HWB Plan Table

```text
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                          HWB PLANNING TABLE INITIATIVE MATRIX                           │
├─────────────────────────┬─────────────────────────────┬─────────────────────────────────┤
│ Initiative Code         │ Strategic Package           │ Core Operational Value          │
├─────────────────────────┼─────────────────────────────┼─────────────────────────────────┤
│ [HWB-PLAN-07]           │ Automated Post-Shift        │ Sends building managers photo   │
│                         │ "Proof of Work" Email       │ proof and GPS check-ins after   │
│                         │ Engine                      │ every shift, killing no-shows.  │
├─────────────────────────┼─────────────────────────────┼─────────────────────────────────┤
│ [HWB-PLAN-08]           │ Public Cleaning Cost        │ Turns website visitors into     │
│                         │ Estimator on HWB Website    │ qualified sales leads using     │
│                         │                             │ square footage & frequency math.│
├─────────────────────────┼─────────────────────────────┼─────────────────────────────────┤
│ [HWB-PLAN-09]           │ Task-Level Photo Capture    │ Requires cleaners to upload     │
│                         │ in Mobile Scope of Work     │ before-and-after photos for key │
│                         │                             │ tasks before closing a shift.   │
├─────────────────────────┼─────────────────────────────┼─────────────────────────────────┤
│ [HWB-PLAN-10]           │ Automated Field Training &  │ Sends two-minute safety quizzes │
│                         │ Procedure Quizzes via Bot   │ to cleaners' phones weekly to   │
│                         │                             │ enforce ISO/EHSQ standards.     │
├─────────────────────────┼─────────────────────────────┼─────────────────────────────────┤
│ [HWB-PLAN-11]           │ Real-Time No-Show Sentinel  │ Alerts supervisors 15 minutes   │
│                         │ & Rapid Crew Reassignment   │ before opening if a cleaner has │
│                         │                             │ not checked in at a site.       │
└─────────────────────────┴─────────────────────────────┴─────────────────────────────────┘
```

---

## 3.0 Detailed Operational Discussion Points

### 3.1 Initiative 7: Automated Post-Shift "Proof of Work" Email Engine
* **The Field Problem:** Property managers often arrive in the morning doubting whether nighttime janitorial crews actually cleaned the building. When a trash can is missed or a floor looks dull, the client assumes nobody showed up.
* **The HWB Execution:** 
  1. As soon as a cleaner taps "Complete Shift" in the field system, the backend compiles:
     * GPS-verified arrival and departure timestamps.
     * Total labor hours delivered.
     * Checklist of completed scope tasks.
     * Before-and-after photos of high-visibility areas (lobbies, restrooms, breakrooms).
  2. The system formats this data into an official HWB branded digital report and emails it directly to the property manager at 6:00 AM.
* **Discussion Question for the Table:** Should HWB activate this feature for all commercial office contracts by default, or offer it as a premium Tier 2 service feature?

### 3.2 Initiative 8: Public Commercial Cleaning Cost Estimator on HWB Website
* **The Field Problem:** Most website visitors leave without filling out a generic "Contact Us" or "Request a Quote" form because they do not want a sales call before knowing rough price ranges.
* **The HWB Execution:**
  1. Build an interactive calculator on `hwbcleaning.com/calculator`.
  2. The visitor selects their facility type (Commercial Office, Medical Clinic, Daycare, School, Post-Construction), inputs total square footage, and chooses service frequency (1x/week, 3x/week, 5x/night).
  3. The calculator displays estimated monthly ranges and estimated weekly labor hours based on HWB standard production rates.
  4. To download a detailed itemized breakdown, the user enters their email, company name, and phone number, automatically inserting a new record into HWB's `Leads` table.
* **Discussion Question for the Table:** What baseline square-foot production rate (e.g., 2,500 to 3,500 sq ft per hour) should George calibrate into the public formula?

### 3.3 Initiative 9: Task-Level Photo Capture in Mobile Scope of Work Engine
* **The Field Problem:** Cleaners sometimes rush through shifts and sign off on tasks without actually doing the deep cleaning required by the contract.
* **The HWB Execution:**
  1. In the upcoming Standalone Mobile App (Mandate 2026-03-21), designated high-risk tasks are flagged with a `photo_required=true` attribute in the `ScopeLibrary` table.
  2. Cleaners cannot mark tasks like "Disinfect Restroom Fixtures", "Mop Kitchen Tile", or "Buff Entry Lobby" as complete without taking a live photo through the camera (blocking gallery uploads to prevent old photos).
  3. Photos are compressed, watermarked with GPS coordinates and timestamps, and stored in the secure HWB document repository.
* **Discussion Question for the Table:** How many required photo tasks per shift should be mandated (recommended: 3 to 5 key tasks per site) so cleaner speed is preserved?

### 3.4 Initiative 10: Automated Field Training & Procedure Quizzes via Bot
* **The Field Problem:** Cleaning technicians forget safety rules, chemical dilutions, and OSHA bloodborne pathogen procedures after their first week of onboarding.
* **The HWB Execution:**
  1. Connect HWB's existing `AcademyCourses` and `AcademyQuizQuestions` tables to the Telegram bot gateway.
  2. Every Tuesday at 2:00 PM, the system pushes a two-minute situational question to active cleaners (e.g., *"What is the minimum dwell time for chemical disinfectant on restroom counters?"*).
  3. Cleaners answer directly with one tap on their phone. Correct answers earn recognition points; incorrect answers instantly provide the correct standard operating procedure.
  4. Cleaners who maintain a 90-day streak receive a monthly safety bonus verified in the payroll ledger.
* **Discussion Question for the Table:** Should passing weekly quizzes be tied to 1099 subcontractor preferred status and higher hourly wage tiers?

### 3.5 Initiative 11: Real-Time No-Show Sentinel & Rapid Crew Reassignment
* **The Field Problem:** When a cleaner gets sick or has car trouble, managers only find out when the building owner calls at 8:00 AM asking why the facility is locked and dirty.
* **The HWB Execution:**
  1. The system monitors scheduled shift start times against live GPS clock-ins.
  2. If a cleaner has not clocked in 15 minutes before the shift start time, the system sends an SMS and Telegram alert to the cleaner.
  3. If no check-in occurs within 10 minutes of start time, an immediate alert fires to Humberto Dominguez and the field supervisor showing:
     * Site name and address.
     * Missing cleaner name.
     * Three nearest available cleaners or vetted 1099 subcontractors ranked by proximity.
  4. The supervisor can tap one button to reassign the shift immediately.
* **Discussion Question for the Table:** What buffer time (15 minutes vs 30 minutes before shift) gives supervisors enough lead time to dispatch backup crews across Dallas-Fort Worth?

---

## 4.0 Technical Architecture & Implementation Map

```text
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           TECHNICAL ARCHITECTURE FLOWCHART                              │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│   [hwbcleaning.com] ──> Interactive Cost Calculator ──> Leads Table (PostgreSQL)       │
│                                                                                         │
│   [Mobile Scope Engine] ──> Task Photos + GPS Stamp ──> WorkOrders & S3 Repository      │
│                                                                                         │
│   [Shift Complete] ──> Notification Service ──────────> Branded Client PDF / Email      │
│                                                                                         │
│   [Academy Engine] ────> Weekly 2-Minute Quizzes ─────> Telegram Dispatch Gateway       │
│                                                                                         │
│   [No-Show Sentinel] ──> 15-Minute Geo-Trigger ───────> Supervisor Reassignment Alert   │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5.0 Action Plan & Builder Assignments

Upon executive approval by CEO Humberto Dominguez:
1. **George Bytes (Lead Builder):**
   * Code the interactive commercial cleaning calculator into `HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/templates/calculator.html` and wire it to `/api/v1/leads/calculator-intake`.
   * Add `photo_required` boolean column to the `ScopeLibrary` and `WorkOrders` tables in `schema_engine.py`.
2. **Super George (Systems Architect):**
   * Draft the HTML email template for post-shift Proof of Work reports using HWB official letterhead styling.
   * Configure the Telegram quiz pusher inside `core/services/telegram_service.py` reading from `AcademyQuizQuestions`.
3. **Peter (Recovery Specialist):**
   * Verify photo upload storage limits and ensure backup snapshots include task media attachments.
4. **Humberto Dominguez (CEO):**
   * Review discussion questions regarding buffer times and customer report tiers.
