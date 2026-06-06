| **Document Control** | |
| :--- | :--- |
| **Document Title** | **Pre-Execution Impact Study for BabySOP Terminal Integration** |
| **Document ID** | HWB-QMS-9.8 |
| **Version** | 1.0 |
| **Status** | APPROVED |
| **Author** | George (Systems Architect) |
| **Approved By** | Humberto Dominguez, CEO |
| **Date** | 2026-06-06 |
| **ISO 9001 Clause** | 8.5.6 (Control of Changes) |

---

# Standard Operating Procedure / Report: **Pre-Execution Impact Study for BabySOP Terminal Integration**

## 1.0 Purpose
This document conducts a pre-execution impact study for integrating the hex-terminal view viewport page into the BabySOP production environment (`www.babysop.com/hud/terminal`). This ensures the projects portal and dropdown options resolve successfully instead of returning 404 errors.

## 2.0 Scope
This study applies to:
1. The route mapping: `HWB-COMPANY/HWB-IT/HWB-BABYSOP-LANDING/app.py`.
2. The template: `HWB-COMPANY/HWB-IT/HWB-BABYSOP-LANDING/templates/hud_terminal.html`.
3. The static file: `HWB-COMPANY/HWB-IT/HWB-BABYSOP-LANDING/static/js/hud-dock.js`.

---

## 3.0 Pre-Execution Impact Study

### 3.1 Context & Dependency Analysis
*   **Asset Dependencies**:
    *   The `hud_terminal.html` template uses global projects contexts. Since `global_projects` is already injected in `app.py` via a template context processor, there are no missing variables.
    *   The template requires the static asset `js/hud-dock.js` which is now copied into the destination folder.
*   **Environment Parity**:
    *   This is a static template and path routing change. There are no direct environment variable changes or database schema modifications required.

### 3.2 Rollback Path
In the event of a deployment failure:
1.  **Immediate Revert**: Revert the git commit and push the previous master branch state to GitHub.
2.  **Azure CLI Rollback**: Re-run `az webapp deployment source config-zip` with the last backed up package file.

---

## 4.0 Verification Checklist
*   [ ] Does `hud_terminal.html` load successfully?
*   [ ] Does `hud-dock.js` resolve on the client browser with status code 200?
*   [ ] Are the project dropdown selection parameters mapped correctly?
