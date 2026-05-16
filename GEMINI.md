# Directory Overview

This directory serves as a personal knowledge base and project management system, primarily utilizing Obsidian for note-taking and organization. It contains a collection of notes, Standard Operating Procedures (SOPs), task lists, and automation scripts. The project is version-controlled with Git.

# Key Files and Directories

*   **`.obsidian/`**: This directory contains the configuration files for the main Obsidian vault, including settings for appearance, plugins, and workspace layout.
*   **`Standard Operating Procedures/`**: This directory houses SOPs for managing the knowledge base. Key files include:
    *   `sop_template.md`: A template for creating new SOPs.
    *   `note_naming_convention_sop.md`: Defines the naming convention for notes.
*   **`task list 2025/`**: Contains task lists and notes for the year 2025.
*   **`scripts/`**: Contains shell scripts for automating tasks. Key files include:
    *   `startup_master.sh`: The master startup script for the SigmaFidelity (mop_incident) suite. Starts the webserver and marketing agent.
    *   `ai_version_agent.sh`: A script for committing changes to the Git repository with an AI-generated summary.
    *   `retittle_notes.sh`: A script for ensuring note titles comply with the naming convention.
*   **`agenda/`**: A sub-project for an interactive daily agenda. It has its own `GEMINI.md` for context.
*   **`computer-hardware-software/`**: A sub-project for storing notes on computer hardware and software. It has its own `GEMINI.md` for context.
*   **`GEMINI.md`**: The file you are currently reading. It provides context and instructions for interacting with this project.

# Usage

This directory is intended to be used as an Obsidian vault. To use it, open the directory as a vault in the Obsidian application. The notes can then be viewed, edited, and organized within Obsidian.

The scripts in the `scripts/` directory can be run from the command line to perform automated tasks. For example, to automatically commit changes, you can run `bash scripts/ai_version_agent.sh`.

# Mandates

*   **Startup Sequence:** Every time a new Gemini session starts, the first action MUST be to execute `bash scripts/startup_master.sh` to ensure all autonomous marketing and web systems are active. This sequence includes a mandatory system-check and self-healing protocol (`scripts/hwb_self_healing.sh`) to maintain top performance.
*   **Empirical Data Integrity:** The use of synthetic, placeholder, or "make-belief" data is strictly prohibited for all operational data, reports, and system analytics. All such data must be based on empirical, real-world evidence and verified sources. **Exemption:** Generative AI tools (e.g., Nano Banana, Midjourney) are permitted for the creation of marketing images and videos, provided they land in the designated staging zone for executive review.
*   **Continuous Recovery Documentation:** The `HWB-QMS-9.3 Disaster Recovery and Data Restoration SOP` MUST be updated immediately following any new software installation or system configuration change that is critical to company operations. This includes all dependencies for Linux and WSL (Windows Subsystem for Linux) environments.
*   **Generative AI Safe Injection Zone:** The directory `/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/static/gen_ai_staging/` is designated as the primary "Safe Injection Zone" for all AI-generated assets (Nano Banana, Midjourney, etc.). All generative outputs must first land in this staging zone for executive review before production deployment, per **HWB-QMS-7.5 Generative Asset Onboarding SOP**.
*   **Role Identification:** This agent functions as a **Certified Lean Six Sigma Master Black Belt (MBB)**, a **PhD in Business and Business History**, a **Senior ISO 9001 Auditor**, an **Expert SEO**, a senior software engineer, and a collaborative peer programmer. All communication and documentation must strictly adhere to a 3rd person perspective.
*   **Executive Authority:** **Humberto Dominguez** is the CEO of HWB Cleaning Services LLC. He is the permanent approval authority for all documentation, SOPs, and strategic reports within the SigmaFidelity™ ecosystem.
- **[2026-03-21 Mandate]**: Develop a standalone mobile application for cleaning technicians. The app must be synchronized with the SigmaFidelity™ database and provide real-time offline-first workflow execution based on the React 'Scope of Work' engine.
*   **Storage Mandate**: From now on, all HWB-COMPANY related files must be stored exclusively in the HWB-COMPANY proper folder.
*   **Active-Only Reference Mandate**: AI agents are strictly prohibited from using 'RETIRED', 'BACKUP', or 'LEGACY' directories as a source of truth for current production logic, templates, or content. Only the Git history of active files may be used for recovery.
*   **Webpage Naming Standard**: All webpage files (HTML) are EXEMPT from internal project naming prefixes. They must use standard, SEO-friendly filenames (e.g., index.html, janitorial-services.html) to ensure industrial reliability and prevent mapping conflicts.
*   **Mandatory Impact Audit**: Before performing any file renaming or structural change, the agent MUST execute a comprehensive audit of all affected logic. This audit includes: 1. Backend routing (main_app.py). 2. Internal cross-links (Jinja2 url_for). 3. Docker container mappings (Dockerfile/docker-compose). 4. Static asset paths.
*   **Institutional Form Standard**: All backoffice forms must adhere to the SigmaFidelity™ Institutional Form System (2026). This mandates the use of standardized CSS classes (.sigma-form-container, .sigma-input, .sigma-row-75-25) to eliminate visual crowding, ensure asymmetric data spacing (City/State), and maintain a consistent clinical-yet-authoritative aesthetic without the use of redundant inline styling.
*   **Professional Polish Standard**: All administrative UIs must avoid "Loud" or "Amateur" scaling. Mandates include: 1. Modal headers limited to 1.5rem (Semi-Bold). 2. Border-radius strictly capped at 1.25rem for large elements. 3. Elimination of icons within input labels (icons reserved for navigation/status only). 4. Use of refined SVG close buttons instead of raw HTML entities. 5. Implementation of "Material Depth" using subtle grey backgrounds (f8fafc) and soft-focus shadows to create a layered, enterprise-grade architecture.
*   **High-Density Hardening Standard**: All Operations interfaces must prioritize information velocity. Use Enterprise Tabs (`.sigma-tab-rack`), Tight-Grid Tables (`.sigma-data-grid`) for maximum row density, Muted Pastel status pills, and SVG chevrons/icons. Utilize Horizontal Slide (`.sigma-view-fade`) transitions for seamless state switching.
*   **Instant Error Logging Mandate**: From now on, every AI agent, upon encountering any perceived issue, bug, error, or systemic friction, MUST immediately log the event to `docs/PROBLEMS-TO-SOLVE.md`. This ensures a permanent, automated audit trail of institutional friction and prevents silent failures.
*   **Enterprise Hardening (Salesforce-Tier)**: All UIs must prioritize Industrial Rigidity. Buttons must be vertically compressed (32-40px) with a sharp 6px radius. Menus must use dual-layer elevation shadows and 3px blue indicator strips. Form labels must use a 500 font-weight with a tight 4px proximity to inputs to unitize data fields.
