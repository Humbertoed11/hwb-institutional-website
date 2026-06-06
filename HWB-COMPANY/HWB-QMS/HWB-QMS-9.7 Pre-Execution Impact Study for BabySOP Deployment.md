| **Document Control** | |
| :--- | :--- |
| **Document Title** | **Pre-Execution Impact Study for BabySOP Deployment** |
| **Document ID** | HWB-QMS-9.7 |
| **Version** | 1.0 |
| **Status** | DRAFT |
| **Author** | George (Systems Architect) |
| **Approved By** | Humberto Dominguez, CEO |
| **Date** | 2026-06-06 |
| **ISO 9001 Clause** | 8.5.1 (Control of Production & Service Provision) |

---

# Standard Operating Procedure / Report: **Pre-Execution Impact Study for BabySOP Deployment**

## 1.0 Purpose
This document conducts a pre-execution impact study for the upcoming deployment of the BabySOP landing page and spatial routing engine to the production slot of `www.babysop.com`. This audit satisfies the Pre-Execution Impact Study Mandate (Executive Directive HEX-REPORT-17.0 Section 3.3) to ensure zero downtime and prevent configuration regression.

## 2.0 Scope
This study applies to:
1. The deployment workflow: `.github/workflows/babysop-deploy.yml` in `/home/humbertoed/gemini_projects/`.
2. The BabySOP Flask application: `HWB-COMPANY/HWB-IT/HWB-BABYSOP-LANDING/app.py`.
3. The Azure App Service target: `hwb-babysop-landing` under resource group `HWB-SIGMAJAN-PROD`.

---

## 3.0 Pre-Execution Impact Study

### 3.1 Environment Parity Assessment
*   **Local Sandbox Configuration**:
    *   Runs locally over HTTP without TLS/SSL.
    *   Session cookies do not require the `Secure` flag, preventing login verification loops.
    *   Connection target: `postgresql://hexadmin:hexpassword@hex_postgis_db:5432/hex_dev_db`.
*   **Production Configuration (`www.babysop.com`)**:
    *   Enforces HTTPS-only traffic.
    *   Requires `SESSION_COOKIE_SECURE=True` to prevent credential exposure.
    *   App Service must bind to the standard dynamic `$PORT` assigned by Azure.
    *   Connection target: Managed Azure PostGIS instance defined via Azure App Service configuration.

### 3.2 System Dependency Risks
1.  **Packaging Directory Pathing**:
    *   *Risk*: The existing GitHub Actions workflow `babysop-deploy.yml` packages the entire `gemini_projects` repository. Since there is no `app.py` or `Procfile` at the root, Azure Web App will fail to resolve the application entry point, resulting in a **500 Internal Server Error**.
    *   *Mitigation*: Adjust the packaging step to transition (`cd`) into `HWB-COMPANY/HWB-IT/HWB-BABYSOP-LANDING` before zip compilation, placing `app.py` and `Procfile` at the root of the output `release.zip`.
2.  **Session Cookie Exposure**:
    *   *Risk*: If `SESSION_COOKIE_SECURE` is not conditionally configured based on the environment, session cookies could be transmitted in plaintext or logins could fail on local dev sandboxes.
    *   *Mitigation*: Implement conditional cookie configuration in `app.py` mirroring `main_app.py`.
3.  **Database Connection Handshake**:
    *   *Risk*: If Azure App Service does not have the `DATABASE_URL` or `SECRET_KEY` configured in its application settings, the application will crash during database initialization on startup.
    *   *Mitigation*: Verify and stage application settings in the Azure Portal before releasing.

### 3.3 Rollback Path
In the event of a deployment failure:
1.  **Immediate Revert**: Revert the `git push` by pushing the previous working commit SHA to the master branch.
2.  **Manual Package Deployment**: Redeploy the last validated local package (`release_backup_06-04-2026.zip`) directly using the Azure CLI:
    ```bash
    az webapp deployment source config-zip --resource-group HWB-SIGMAJAN-PROD --name babysop-landing --src HWB-COMPANY/HWB-IT/HWB-BABYSOP-LANDING/release_backup_06-04-2026.zip
    ```

---

## 4.0 Action Plan

### 4.1 Step 1: Code-Level Hardening
1.  Update `HWB-COMPANY/HWB-IT/HWB-BABYSOP-LANDING/app.py` to conditionally configure `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_HTTPONLY`, and `SESSION_COOKIE_SAMESITE`.
2.  Import `timedelta` from `datetime` to support permanent session lifetime timeouts.

### 4.2 Step 2: Build Workflow Correction
Modify `gemini_projects/.github/workflows/babysop-deploy.yml` to:
1.  Run `pip install -r requirements.txt` from the `HWB-COMPANY/HWB-IT/HWB-BABYSOP-LANDING` folder.
2.  Change packaging directory to zip only files within `HWB-COMPANY/HWB-IT/HWB-BABYSOP-LANDING` directly into the root of `release.zip`.

### 4.3 Step 3: Staging and Verification
1.  Verify the local Flask instance running on Port 5100 functions correctly.
2.  Perform a trial zip compilation locally to verify the structure matches.

---

## 5.0 Verification Checklist
*   [ ] Does `unzip -l release.zip` confirm `app.py` and `Procfile` are at the root level?
*   [ ] Does the conditional cookie configuration allow local login without loops?
*   [ ] Is `DATABASE_URL` configured on the production Azure App Service?
*   [ ] Is the GitHub secret `AZUREAPPSERVICE_PUBLISHPROFILE_BABYSOP` verified?

---

## 6.0 Revision History
| Version | Date | Author | Change Description |
| :--- | :--- | :--- | :--- |
| 1.0 | 2026-06-06 | George | Initial release of Pre-Execution Impact Study for BabySOP landing page. |
