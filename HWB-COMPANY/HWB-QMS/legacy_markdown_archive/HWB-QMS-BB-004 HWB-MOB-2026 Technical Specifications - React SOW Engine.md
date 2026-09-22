| **Document Control** | |
| :--- | :--- |
| **Document Title** | **HWB-MOB-2026 Technical Specifications - React SOW Engine** |
| **Document ID** | HWB-QMS-BB-004 |
| **Version** | 1.0 |
| **Status** | Active / Design Phase |
| **Author** | George (System Architect / MBB) |
| **Approved By** | Humberto Dominguez, CEO |
| **Date** | 2026-03-20 |

---

# Technical Specifications: **React 'Scope of Work' Engine**

## 1.0 Architectural Overview
The 'Scope of Work' (SOW) engine is the core execution logic of the HWB-MOB-2026 mobile app. It is designed as a standalone React component that renders facility-specific cleaning protocols and enforces Six Sigma "Zero Defect" discipline through sequential task locking and empirical evidence capture.

### 1.1 Core Stack
*   **Frontend:** React (TypeScript) with Vanilla CSS for high-fidelity performance on low-end mobile devices.
*   **State Management:** Context API with `useReducer` for robust local state persistence.
*   **Offline Protocol:** Service Workers (PWA) + IndexedDB for local storage during zero-connectivity windows (Offline-First).
*   **Backend Integration:** RESTful API handshake with the SigmaFidelity™ Python/SQLite server.

---

## 2.0 Critical-to-Quality (CTQ) Logic Enforcement

### 2.1 Poka-Yoke: Sequential Task Locking
*   **Logic:** Technicians cannot proceed to Task *N+1* until Task *N* is marked as complete.
*   **High-Stakes Gate:** Tasks flagged as "High-Stakes" (e.g., medical-grade disinfection) require a photo upload before the "Complete" button is enabled.
*   **Exception Handling:** Any task marked as "Unable to Complete" triggers an immediate mandatory comment box and a real-time supervisor alert (once online).

### 2.2 Integrity: GPS Geofencing Handshake
*   **Handshake:** The `Clock-In` and `Clock-Out` functions are cryptographically disabled if the device GPS coordinates are >50 meters from the facility centroid stored in `clients.db`.
*   **Validation:** Every task completion record includes a nested `lat/long` coordinate pair for post-process audit.

---

## 3.0 Data Model & Synchronization

### 3.1 Local SOW Object Structure (JSON)
```json
{
  "work_order_id": "WO-2026-001",
  "facility_id": "PLANO-DAYCARE-01",
  "technician_id": "TECH-04",
  "start_time": "2026-03-20T18:00:00Z",
  "tasks": [
    {
      "task_id": "TSK-001",
      "description": "Disinfect all door handles",
      "is_high_stakes": true,
      "status": "pending",
      "evidence_url": null,
      "timestamp": null
    }
  ],
  "sync_status": "local_only"
}
```

### 3.2 Sync Protocol
*   **Mechanism:** Periodic heartbeat (every 30 seconds) checks for network availability.
*   **Speed Requirement:** Batched JSON payloads must synchronize with the Azure server in <60 seconds upon heartbeat restoration.

---

## 4.0 User Experience (UX) Fidelity
*   **Visual Feedback:** Color-coded status (Pending: Yellow, Complete: Green, Blocked: Red).
*   **Interaction:** Large, high-contrast buttons for use with gloved hands.
*   **Persistence:** Auto-save to IndexedDB on every task state change to prevent data loss on app crash or battery depletion.

---

## 5.0 Verification & Readiness
*   **Unit Tests:** Jest suite covering task locking logic.
*   **Integration Tests:** Simulated offline-to-online state transitions.
*   **User Acceptance:** Pilot test with "Crew A" using the initial prototype.

---

## 6.0 Approval & Sign-off
**CEO/Operations Director:** _________________________ **Date:** 2026-03-20

---

## 7.0 Revision History
| Version | Date | Author | Description |
| :--- | :--- | :--- | :--- |
| 1.0 | 2026-03-20 | George | Initial Technical Specs for SOW Engine. |
