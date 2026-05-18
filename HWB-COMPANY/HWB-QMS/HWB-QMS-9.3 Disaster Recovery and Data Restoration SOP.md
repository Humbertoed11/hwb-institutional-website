| **Document Control** |                                                |
| :------------------- | :--------------------------------------------- |
| **Document Title**   | **Disaster Recovery and Data Restoration SOP** |
| **Document ID**      | HWB-QMS-9.3                                    |
| **Version**          | 7.0                                            |
| **Status**           | Approved                                       |
| **Author**           | George (System Architect)                      |
| **Approved By**      | Humberto Dominguez, CEO                        |
| **Date**             | 2026-03-23                                     |

---

# Standard Operating Procedure: **Disaster Recovery and Data Restoration SOP**

## 1.0 Purpose
This SOP defines the procedures for ensuring business continuity and data integrity for HWB Cleaning Services LLC in the event of catastrophic data loss, hardware failure, or system compromise. It specifically outlines the process for restoring the QMS infrastructure, absolute institutional paths, and operational code from the GitHub remote repository.

## 2.0 Scope
Applies to all digital assets within the `gemini_projects` workspace and the dedicated `hwb-institutional-website` repository for Azure cloud operations.

## 3.0 Prerequisites
*   Git and GitHub CLI (gh) installed on the restoration machine.
*   Authorized access to the GitHub repositories via Personal Access Token (PAT).

### 3.1 Critical Software Dependencies
The following software must be installed and configured on the recovery machine (supporting both Linux and WSL environments) to ensure full system functionality:

| Category | Program / Library | Platform | Purpose |
| :--- | :--- | :--- | :--- |
| **OS Environment** | **WSL 2 (Ubuntu 24.04 LTS)** | Windows | Primary Linux kernel for script execution. |
| **Version Control** | **Git** (latest) | Linux/WSL | Repository cloning and version management. |
| **Version Control** | **gh (GitHub CLI)** | Linux/WSL | Automated repository management and Azure publishing. |
| **Scripting** | **Python 3.12+** | Linux/WSL | Core execution environment for AI agents. |
| **Package Manager** | **pip** | Linux/WSL | Python package installer for virtual environments. |
| **Security Lib** | **libsecret-1-0 / libsecret-common** | Linux/WSL | Native keychain support for extensions. |
| **Data Library** | **Pandas / xlrd** | Linux/WSL | Empirical data analysis and legacy Excel support. |
| **Data Format** | **JSON** | Linux/WSL | Standard library for configuration and queue management. |
| **Auth Library** | **msal** | Linux/WSL | Microsoft Authentication Library for Graph API access. |
| **Webserver** | **Flask** (via .venv) | Linux/WSL | Backend engine for the SigmaFidelity™ suite. |
| **Security Auth** | **Flask-Login** | Linux/WSL | Secure backoffice session and identity management. |
| **Database** | **SQLite3** | Linux/WSL | Empirical data storage. |
| **Virtualization** | **python3-venv** | Linux/WSL | Isolated environment management. |
| **Reverse Proxy** | **Nginx** | Linux/WSL | Front-end web proxy and security filtering. |
| **Extensions** | **YouTube-to-Docs** | Gemini CLI | YouTube content processing and document generation. |
| **Extensions** | **ElevenLabs MCP** | Gemini CLI | AI voice synthesis and text-to-speech. |
| **Extensions** | **Deep Research** | Gemini CLI | Automated data synthesis and research. |
| **Extensions** | **Nano Banana** | Gemini CLI | Generative marketing asset production. |

### 3.2 Secret Management and API Keys
To maintain the security and integrity of the SigmaFidelity™ infrastructure, the following rules apply to all API keys (Gemini, Google, Vibe, SAM.gov, Microsoft Graph, GitHub, Azure):
1.  **Zero Raw Storage:** No raw API keys or secrets shall be stored within `.md` files or any other version-controlled documentation.
2.  **Institutional Vault:** Keys must be stored in secure `.env` files which are excluded from Git per HWB-QMS-9.5.
3.  **GitHub Token Scopes:** Personal Access Tokens (PAT) for `gh` must include `repo`, `workflow`, and `admin:org` (if applicable) for Azure-automated CI/CD.
4.  **Azure Service Principal:** The AI agent (George) operates via the `hwb-sigmafidelity-agent` service principal (App ID: `8226641a-7d76-429d-9954-e22fe98ea47a`) with `Contributor` role assigned at the subscription level.

## 4.0 Procedure

1.  **Isolation:** Disconnect the affected machine from the network.
2.  **Assessment:** Identify the extent of data loss.
3.  **Notification:** Notify the Managing Director (Humberto Dominguez).

### 4.1 Cloud Infrastructure Restoration (Azure)
In the event of an Azure environment failure:
1.  **Verify Agent Identity:** Ensure `AZURE_CLIENT_ID` and `AZURE_CLIENT_SECRET` are correctly populated in the `.env` file.
2.  **Service Principal Recovery:** If the service principal is deleted, re-provision using the `8226641a-7d76-429d-9954-e22fe98ea47a` application ID.
3.  **App Service Recovery:** Use the GitHub Actions workflow to redeploy the `hwb-institutional-website` from its dedicated repository.
4.  **Internal Server Error (500) Resolution:** If the site returns a 500 error after deployment, verify:
    - `main_app.py` for duplicate route registrations (e.g., `/services/office` vs `/services/warehouse`).
    - `init_db()` correctly creates the `database/` directory using `BASE_DIR` for absolute path resolution.
    - Template links are synchronized with registered route endpoints (e.g., `url_for('service_builder')`).

### 4.2 Restoring from GitHub (Primary Source)
1.  **Clone Main Repository:**
    ```bash
    git clone https://github.com/Humbertoed11/gemini_projects.git
    ```
2.  **Clone Institutional Website (Azure Deployment Point):**
    ```bash
    git clone https://github.com/hwb-it-website/hwb-institutional-website.git
    ```
3.  **Re-establish Infrastructure (The Nuclear Option):**
    ```bash
    bash scripts/startup_master.sh
    ```

### 4.3 Gemini Extension Recovery (Nano Banana / Vibe / ElevenLabs)
If extensions fail to recognize API keys after reinstallation:
1.  **Diagnose Keychain:** Check for `libsecret-1.so.0` errors in the environment.
2.  **Force Key Injection:** Manually configure the extension setting using the following command (example for Nano Banana):
    ```bash
    echo "$NANOBANANA_GEMINI_API_KEY" | gemini extensions config nanobanana "API Key"
    ```
3.  **Verify Fallback:** Ensure the system reports `Using FileKeychain fallback for secure storage`.

### 4.4 Database Restoration (Empirical Data)
1.  **Secondary Backup:** Restore the `clients.db` and `sigma_leads.db` from the most recent secure cloud backup.
2.  **Institutional Path:** Place database files in `HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/database/`.
3.  **Validation:** Run `python HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/HWB-WEB Diag Dashboard.py`.
4.  **Credential Synchronization:** If backoffice login fails with "Invalid Credentials", ensure `init_db()` in `main_app.py` is configured to synchronize the `admin` and `hdominguez` password hashes on startup.

### 4.5 AI System Initialization (Master Prompt)
In a total system re-initialization, the following "Master Prompt" must be provided to the AI agent:

```markdown
# SYSTEM INITIALIZATION: HWB Cleaning Services LLC (SigmaFidelity™ Protocol)

## 1.0 AI Role & Identity Designation
You are the Lead Autonomous Agent for HWB Cleaning Services LLC. Official roles:
1. Certified Lean Six Sigma Master Black Belt (MBB)
2. Senior Software Engineer & Collaborative Peer Programmer
3. PhD in Business and Business History
4. Senior ISO 9001:2015 Auditor
5. Expert SEO

**George (System Architect):** Master SaaS VP of Development, Master Programmer, and Strategist. Responsible for high-fidelity SaaS architecture, infrastructure, and data pipelines. (Skill: `saas-dev-master`).
**Nick Doria (VP Prompt Engineering):** Responsible for AI Persona DNA and Governance.
**Lauri Tells (VP Sales & Marketing):** Responsible for Market Capture and National ETL.
**Silas Sync (VP CRM Systems):** Responsible for Relational Data and Backoffice Logic.
**Natalie Navy (Chief Dream Officer):** Responsible for Blue-Ocean SaaS ideation and future tech forecasting.

**Mandatory Protocol:** Strictly adhere to a 3rd person perspective.
```

## 5.0 Verification
*   Successful `git clone` operation with 100% file parity.
*   Successful execution of `HWB-WEB Diag Dashboard.py` with zero errors.
*   Verified generation of 1 image via Nano Banana to confirm extension fidelity.

## 7.0 Revision History
| Version | Date | Author | Change Description |
| :--- | :--- | :--- | :--- |
| 1.0 | 2026-02-28 | Gemini | Initial Release. |
| 3.5 | 2026-03-09 | George | Added MSAL dependency, updated secret vault rules, and added Expert SEO role. |
| 4.0 | 2026-03-10 | George | Standardized on Azure/M365 as exclusive and mandatory platforms. |
| 5.0 | 2026-03-12 | George | Updated credentials, added Natalie Navy (CDO) to the roster, and implemented dashboard-based outbox verification. |
| 6.0 | 2026-03-20 | George | Added recovery protocols for 500 errors and credential synchronization. |
| 7.0 | 2026-03-23 | George | Added libsecret dependency, extension recovery protocol, and formalized the 'Nuclear Option' startup sequence. |
| 8.0 | 2026-04-27 | George | Integrated Dockerized Infrastructure, OIDC authentication protocols, and 'Pure Production' repository hardening. |

## 4.6 CI/CD and Secret Restoration (GitHub/ACR)
In the event of a deployment failure citing "Missing Username" or "Unauthorized":
1.  **ACR Credential Ingestion:** Retrieve Admin credentials from Azure Portal (hwbprodacr > Access Keys) and provision as GitHub Secrets (`ACR_USERNAME`, `ACR_PASSWORD`).
2.  **OIDC Handshake Recovery:** Ensure the GitHub Actions workflow includes mandatory permissions:
    ```yaml
    permissions:
      id-token: write
      contents: read
    ```
3.  **Repository Hardening:** Maintain 'Pure Production' state by ensuring non-essential folders (recuperate, docs, clippings) are explicitly excluded in `.gitignore` and untracked from the remote index.
