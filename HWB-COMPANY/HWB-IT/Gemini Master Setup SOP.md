| **Document Control** |                             |
| :------------------- | :-------------------------- |
| **Document Title**   | **Gemini Master Setup SOP** |
| **Document ID**      | SOP-GEM-001                 |
| **Version**          | 1.0                         |
| **Status**           | Approved                    |
| **Author**           | Gemini                      |
| **Approved By**      | User                        |
| **Date**             | 2025-11-01                  |

---

# Standard Operating Procedure: **Gemini Master Setup SOP**

## 1.0 Purpose

This SOP provides a comprehensive guide for reinstalling and setting up the "Gemini" project environment from a fresh state. It documents all essential components, dependencies, and configurations.

## 2.0 Scope

This SOP covers the full restoration of the custom scripts, templates, SOPs, and projects created within the `gemini_projects` directory.

## 3.0 Prerequisites

A Linux-based operating system.

## 4.0 Procedure

### 4.1 Step 1: Install External Dependencies

Before restoring any files, ensure the following software packages are installed on your system. These are required for the custom scripts and tools to function correctly.

*   **Git:** For version control. (`sudo apt-get install git`)
*   **ALSA Utilities:** For audio recording and playback. (`sudo apt-get install alsa-utils`)

### 4.2 Step 2: Recreate Directory Structure

Create the following primary directories in your main `gemini_projects` folder:

*   `agenda/`
*   `Clippings/`
*   `computer-hardware-software/`
*   `desktop/`
*   `task list 2025/`

### 4.3 Step 3: Restore Core Scripts

Re-create the following shell scripts in the `gemini_projects` directory. The content for these files must be restored from a backup.

*   `ai_version_agent.sh`: An advanced script concept for creating version snapshots with AI-generated summaries.
*   `rename_notes.sh`: An interactive script to rename `.md` files to follow a specific naming convention (removes hyphens and underscores, applies Title Case).
*   `retittle_notes.sh`: An interactive script to modify the H1 title *inside* `.md` files to follow the naming convention.
*   `version_agent.sh`: A simple script to create a version snapshot of all files with a timestamp.

### 4.4 Step 4: Restore SOPs and Templates

Re-create the following SOP and template files. Their content must be restored from a backup.

*   `sop_template.md`: The master ISO 9001 compliant template for all SOPs.
*   `note_naming_convention_sop.md`: Documents the naming convention for note titles and filenames.
*   `obsidian_android_sync_sop.md`: Instructions for syncing the Obsidian vault with an Android device via OneDrive.
*   `task list 2025/git_troubleshooting_sop.md`: Documents the extensive troubleshooting steps for initializing Git on a GVFS filesystem.
*   `task list 2025/google_home_obsidian_sop.md`: Instructions for integrating Google Home with Obsidian via IFTTT.
*   `task list 2025/recording_and_playback_sop.md`: Instructions for recording and playing audio from the command line.

### 4.5 Step 5: Restore the Agenda Project

Re-create the following files within the `agenda/` directory. The content must be restored from a backup.

*   `agenda.html`: The single-file, interactive agenda application.
*   `GEMINI.md`: The documentation file for the agenda project.
*   `agenda one page.png`: The image asset used as a template for the current agenda.

### 4.6 Step 6: Initialize Git Repository

Once all files and directories are restored, you must re-initialize the Git repository.

1.  Navigate to the `gemini_projects` directory.
2.  Follow the detailed procedure outlined in the **`git_troubleshooting_sop.md`** document. This is a critical step due to the special requirements of the GVFS filesystem.

## 5.0 Verification

A successful restoration is verified when:
1.  The `git status` command runs without errors in the `gemini_projects` directory.
2.  All custom scripts (`rename_notes.sh`, etc.) are executable using the `bash` command.
3.  The `agenda.html` file can be opened in a browser and all interactive features work correctly.

## 6.0 Notes and Cautions

*   This SOP assumes you have a backup of the content for all the custom files listed. Without a backup, the environment cannot be fully restored to its previous state.
*   The most critical and error-prone step is the Git initialization (Step 4.6). It is essential to follow the troubleshooting SOP precisely.

## 7.0 Revision History

| Version | Date | Author | Change Description |
| :--- | :--- | :--- | :--- |
| 1.0 | 2025-11-01 | Gemini | Initial Release |

## 8.0 Document Conventions

*   **Title:** The document title should follow the format: **[Subject] [Process Name] SOP**. For example: "**Audio Recording and Playback SOP**". Use Title Case for each word and do not use hyphens. The title is already formatted to be bold.
*   **Document ID:** The document ID should follow the format: `[DEPT-XXX-YYY]`, where DEPT is a short code for the department or subject (e.g., `AUD` for Audio).
