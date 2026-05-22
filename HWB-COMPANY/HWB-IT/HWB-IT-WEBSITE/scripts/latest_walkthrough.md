# QMS Web Manual Display Modernization

This document details the successful execution of the visual and structural modernization for the HWB Institutional Operating Manual web interface. The changes address the usability concerns raised in **BUG-032** by applying high-density layout rules, clinical color palettes, and interactive navigation tools.

## Modernized Components

### 1. Web Application Controller
- **File:** [main_app.py](file:///home/humbertoed/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/main_app.py)
- **Upgrades:**
  - Configured `@app.route('/manual')` and `@app.route('/manual/<path:filename>')` to parse `qms_index.json` and build the department-grouped `sops_by_dept` dictionary.
  - Injected `active_file=filename` into the context for individual document views, enabling structural navigation highlighting.

### 2. Layout & Page Templates
- **File:** [sop_base.html](file:///home/humbertoed/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/templates/sop_base.html)
- **Upgrades:**
  - Implemented the clinical slate background (`#f8fafc`) with a soft geometric grid.
  - Set the global layout card border-radius to exactly `1.25rem` (20px).
  - Developed a dynamic sidebar using Jinja2 loops to group SOP links under interactive, SVG-accordion department dropdowns.
  - Added a client-side real-time keyword search bar inside the sidebar that filters SOP titles, IDs, and departments, automatically expanding matching groups.
  - Structured active navigation links with a `3px` solid blue vertical indicator strip.
  - Integrated the **Active SOW Queue** and **Recently Viewed Tracker** containers right below the Master Index link.
  - Wrote local storage query scripts that dynamically render pinned files and recent clicks, featuring full cross-page parity syncing.
  - **Clinical Command Card TOC Overhaul (Option A):** Overhauled the right-side table-of-contents into a modern, clinical sidebar card (`#ffffff`) with soft slate border (`#e2e8f0`), soft shadows, and capped `1.25rem` border-radius.
  - **Premium Indicator Styling:** Suppressed basic TocBot styling (removed legacy green/purple bullets and crude lines) and engineered high-density Salesforce-tier items:
    - Default link: High-density muted text (`#64748b`), font size `0.8rem`, weight 500, with a hover transition.
    - Hover state: slides slightly (`padding-left: 1rem`) and darkens (`#0f172a`), showing a slate preview indicator track.
    - Active state: highlights the section with a custom `2.5px` vertical indicator strip in enterprise blue (`#2563eb`), font weight 600, blue text color, and a subtle translucent blue highlight background (`rgba(37, 99, 235, 0.04)`).
    - Subheadings nested with a clinical dashed vertical track (`border-left: 1px dashed #e2e8f0`) to establish a pristine visual hierarchy.
  - **Drag-to-Resize Handle (WSL/Desktop Hardening):** Integrated an absolute-positioned vertical handle (`#qms-sidebar-resizer`) on the right edge of the sidebar. Engineered a custom cursor drag listener (`mousemove`) constraining sidebar widths dynamically between `280px` and `500px` to prevent viewport breakages.
  - **Dynamic State Persistence**: Width values are synchronized dynamically to browser `localStorage` on dragging, securing consistent panel dimensions across navigation clicks.
  - **Option A Elevated Document Link Cards (De-bunching)**: Upgraded raw, vertical `.dept-sop-link` layouts into distinct rounded card compartments (`background: rgba(255,255,255,0.02)`, border, margins). Spaced cards with a `0.5rem` bottom margin, expanded line height to `1.4` to isolate wrapped text, and colored active panels with high-contrast translucent highlights (`rgba(37, 99, 235, 0.12)`).

- **File:** [qms_manual_index.html](file:///home/humbertoed/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/templates/qms_manual_index.html)
- **Upgrades:**
  - Deployed a top-level department filter controller (`.sigma-tab-rack`) to isolate specific department SOPs in the viewport.
  - Created high-density list cards with elegant hover transitions and soft focus shadows.
  - Configured pastel compliance badges (`UPDATED` in soft green, `OUTDATED` in soft yellow).
  - Styled compressed action buttons (36px high, sharp 6px border-radius) for quick printing.

- **File:** [qms_shell.html](file:///home/humbertoed/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/templates/qms_shell.html)
- **Upgrades:**
  - Confined all header tags (`h1`, `h2`, `h3`) within the document inject zone to a maximum size of `1.5rem` (Semi-Bold) to increase row density.
  - Wrapped content in a slide-fade transition container (`.sigma-view-fade`) to provide visual feedback during document loads.
  - Programmed smart Next/Previous navigation buttons that traverse the active sidebar DOM links to calculate sequential paths automatically.
  - Embedded the **"Pin to Active Queue"** toggle button right above the document inject zone, complete with instant localStorage state sync.
  - Programmed auto-recent tracker logic that registers opened SOPs in the Recently Viewed history with automatic duplicate filtering.

### 3. Official Documentation Mapping
- **File:** [HWB-QMS-7.5 Institutional QMS Web Layout SOP.html](file:///home/humbertoed/gemini_projects/HWB-COMPANY/HWB-QMS/HWB-QMS-7.5%20Institutional%20QMS%20Web%20Layout%20SOP.html)
- **Upgrades:**
  - Created a new clinical, standard-compliant HTML standard procedure to serve as the visual map for the QMS manual system.
  - Outlined the exact data flows and technical roles of the global base shell, sidebar search indexing, and sequential buttons.
  - Embedded an architectural flowchart mapping out the system topology to ensure clear logic mapping for future audits.

---

## Verification & Testing

### 1. Script Compilation
- Executed `scripts/migrate_sops.py` to compile the standard operating procedures. The compilation generated **166 active HTML fragments** in the static output directory:
  ```bash
  .venv_agent/bin/python scripts/migrate_sops.py
  ```
  **Result:** Successful execution with zero errors or syntax issues.

### 2. Gunicorn Server Boot Audit
- Restarted the web application docker container (`hwb_web_app`) to verify production server initialization.
- **Log Telemetry Output:**
  ```log
  [2026-05-22 11:54:17 -0500] [1] [INFO] Starting gunicorn 26.0.0
  [2026-05-22 11:54:17 -0500] [1] [INFO] Listening at: http://0.0.0.0:5000 (1)
  [2026-05-22 11:54:17 -0500] [7] [INFO] Booting worker with pid: 7
  [BOOT] SigmaFidelity™ High-Fidelity Startup Sequence Initiated.
  [BOOT] Infrastructure Handshake Complete.
  ```
  **Result:** Server booted cleanly with zero warnings or exceptions.

### 3. Endpoint Diagnostics
- Conducted HTTP requests on both the index and individual SOP viewer endpoints:
  - `curl -Is http://localhost:5000/manual` -> **200 OK**
  - `curl -Is http://localhost:5000/manual/hwb-acc-001_accounting_management_sop.html` -> **200 OK**
  - `curl -Is http://localhost:5000/manual/hwb-qms-7.5_institutional_qms_web_layout_sop.html` -> **200 OK**
  **Result:** All endpoints responded successfully.

---

## Visual Summary of Features

1. **Tab-Based Filtering:** The index tabs allow rapid filtering across departments (Accounting, IT, Operations, Sales, etc.) with a single click.
2. **Instant Sidebar Search:** Typing into the search bar dynamically filters the sidebar links and expands matching accordion groups, simplifying manual lookups.
3. **Sequential Reading Flow:** Next/Previous buttons allow simple walkthrough transitions across related SOP documents.
4. **Professional Print Styling:** Print stylesheets ensure all sidebar search inputs, tab racks, and header bars are hidden, generating a clean paper copy of QMS files.
