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
This SOP defines the procedures for keeping the business running and ensuring accurate information for HWB Cleaning Services LLC if data is lost, hardware breaks, or the system is hacked. It explains how to get the company setup, exact file locations, and code back from GitHub.

## 2.0 Scope
Applies to all digital files in the `gemini_projects` folder and the `hwb-institutional-website` for Azure cloud work.

## 3.0 Prerequisites
*   Git and GitHub CLI (gh) installed on the computer.
*   Authorized access to GitHub using a Personal Access Token (PAT).

### 3.1 Critical Software Dependencies
The following software must be installed and set up on the recovery computer (works on both Linux and Windows WSL) to make sure everything works:

| Category | Program / Library | Platform | Purpose |
| :--- | :--- | :--- | :--- |
| **OS Environment** | **WSL 2 (Ubuntu 24.04 LTS)** | Windows | Main Linux system for running scripts. |
| **Version Control** | **Git** (latest) | Linux/WSL | Downloading and managing code versions. |
| **Version Control** | **gh (GitHub CLI)** | Linux/WSL | Managing code and publishing to Azure. |
| **Scripting** | **Python 3.12+** | Linux/WSL | Main environment for running AI tools. |
| **Package Manager** | **pip** | Linux/WSL | Tool for installing Python packages. |
| **Security Lib** | **libsecret-1-0 / libsecret-common** | Linux/WSL | Security support for extensions. |
| **Data Library** | **Pandas / xlrd** | Linux/WSL | Analyzing real-world data and old Excel files. |
| **Data Format** | **JSON** | Linux/WSL | Standard for settings and task lists. |
| **Auth Library** | **msal** | Linux/WSL | Microsoft tool for logging in. |
| **Webserver** | **Flask** (via .venv) | Linux/WSL | Background engine for the HWB suite. |
| **Security Auth** | **Flask-Login** | Linux/WSL | Secure login and identity management. |
| **Database** | **SQLite3** | Linux/WSL | Storing real-world data. |
| **Virtualization** | **python3-venv** | Linux/WSL | Keeping environments separate. |
| **Reverse Proxy** | **Nginx** | Linux/WSL | Web helper and security filter. |
| **Extensions** | **YouTube-to-Docs** | Gemini CLI | Turning YouTube content into documents. |
| **Extensions** | **ElevenLabs MCP** | Gemini CLI | AI voice and text-to-speech. |
| **Extensions** | **Deep Research** | Gemini CLI | Automated research and data gathering. |
| **Extensions** | **Nano Banana** | Gemini CLI | Creating marketing images and videos. |

### 3.2 Secret Management and API Keys
To keep the HWB system safe, these rules apply to all API keys:
1.  **No Raw Storage:** Never save API keys or passwords in `.md` files or other shared documents.
2.  **Private Vault:** Keys must be kept in secure `.env` files that are not shared on Git.
3.  **GitHub Token Scopes:** Access tokens for `gh` must have the right permissions for automated work.
4.  **Azure Service Principal:** The AI agent (George) works through a special "service principal" account with `Contributor` access.

## 4.0 Procedure

1.  **Isolation:** Disconnect the computer from the internet.
2.  **Assessment:** Figure out how much data was lost.
3.  **Notification:** Tell the boss (Humberto Dominguez).

### 4.1 Cloud Infrastructure Restoration (Azure)
If the Azure system fails:
1.  **Verify Agent Identity:** Make sure the login IDs and passwords are correct in the `.env` file.
2.  **Account Recovery:** If the service account is deleted, set it up again.
3.  **Website Recovery:** Use GitHub to redeploy the website.
4.  **Error (500) Resolution:** If the site doesn't load after deployment, check:
    - `main_app.py` for duplicate page links.
    - `init_db()` correctly creates the database folder.
    - Links in the templates match the actual page addresses.

### 4.2 Restoring from GitHub (Primary Source)
1.  **Download Main Code:**
    ```bash
    git clone https://github.com/Humbertoed11/gemini_projects.git
    ```
2.  **Download Website Code:**
    ```bash
    git clone https://github.com/hwb-it-website/hwb-institutional-website.git
    ```
3.  **Restart System (The Reset):**
    ```bash
    bash scripts/startup_master.sh
    ```

### 4.3 Gemini Extension Recovery (Nano Banana / Vibe / ElevenLabs)
If extensions don't see the API keys:
1.  **Check Security Library:** Look for `libsecret` errors.
2.  **Force Key Update:** Manually add the key using the command line.
3.  **Verify Backup:** Make sure the system uses the fallback storage if needed.

### 4.4 Database Restoration (Real-World Data)
1.  **Backups:** Get the `clients.db` and `sigma_leads.db` from the latest cloud backup.
2.  **File Location:** Put the database files in the right folder.
3.  **Check:** Run the diagnostic dashboard to make sure it works.
4.  **Login Sync:** If the login fails, make sure the passwords are updated on startup.

### 4.5 AI System Initialization (Master Prompt)
If starting the AI from scratch, give this "Master Prompt" to the agent:

```markdown
# SYSTEM INITIALIZATION: HWB Cleaning Services LLC (HWB Standard)

## 1.0 AI Role & Identity Designation
You are the Lead Assistant for HWB Cleaning Services LLC. Official roles:
1. Certified Lean Six Sigma Master Black Belt (MBB)
2. Senior Software Engineer & Collaborative Peer Programmer
3. PhD in Business and Business History
4. Senior ISO 9001:2015 Auditor
5. Expert SEO

**George (Lead Developer):** In charge of high-quality software setup, infrastructure, and data flows. (Skill: `saas-dev-master`).
**Nick Doria (AI Governance):** In charge of AI personality and rules.
**Lauri Tells (VP Sales & Marketing):** In charge of finding leads and market data.
**CRM Specialist:** In charge of client data and backoffice tools.
**Innovation Leader (Natalie Navy):** In charge of new software ideas and future tech planning.

**Mandatory Rules:** Always speak in the 3rd person.
```

## 5.0 Verification
*   Successful code download with everything matching.
*   The diagnostic dashboard runs with no errors.
*   Created 1 test image via Nano Banana to confirm the quality is good.

## 7.0 Revision History
| Version | Date | Author | Change Description |
| :--- | :--- | :--- | :--- |
| 1.0 | 2026-02-28 | Gemini | Initial Release. |
| 3.5 | 2026-03-09 | George | Added login support, updated secret rules, and added SEO role. |
| 4.0 | 2026-03-10 | George | Standardized on Azure/M365 as main platforms. |
| 5.0 | 2026-03-12 | George | Updated logins, added Natalie Navy to the team, and set up dashboard checks. |
| 6.0 | 2026-03-20 | George | Added fixes for website errors and password updates. |
| 7.0 | 2026-03-23 | George | Added security support, extension fixes, and formalized the reset procedure. |
| 8.0 | 2026-04-27 | George | Integrated Docker, new login procedures, and code hardening. |

## 4.6 Deployment and Secret Restoration (GitHub/ACR)
If the deployment fails because of login issues:
1.  **Adding Login Details:** Get the passwords from the Azure Portal and add them as GitHub Secrets.
2.  **Fixing Login Connection:** Make sure the GitHub settings have the right permissions.
3.  **Cleaning Up Code:** Keep the code "clean" by making sure non-essential folders are ignored by Git.
