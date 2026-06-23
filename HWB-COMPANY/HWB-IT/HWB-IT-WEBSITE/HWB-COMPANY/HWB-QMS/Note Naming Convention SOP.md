| **Document Control** |                                      |
| :------------------- | :----------------------------------- |
| **Document Title**   | **Note Title Naming Convention SOP** |
| **Document ID**      | SOP-NAM-001                          |
| **Version**          | 1.1                                  |
| **Status**           | Approved                             |
| **Author**           | Gemini                               |
| **Approved By**      | User                                 |
| **Date**             | 2025-11-01                           |

---

# Standard Operating Procedure: **Note Title Naming Convention SOP**

## 1.0 Purpose

This SOP defines the standard naming convention for main titles within all Markdown-based notes to ensure consistency and clarity across the documentation.

## 2.0 Scope

*   This convention applies to the primary, level-1 heading of all Markdown notes (`.md`) within the Obsidian vault.
*   This convention also applies to the filenames of any new files created by the Gemini AI assistant.

## 3.0 Prerequisites

None.

## 4.0 Procedure

The naming convention for note titles is defined by the following rules:

1.  **H1 Heading:** The main title must be a level-1 heading, indicated by a single hash (`#`) followed by a space at the beginning of the line.
2.  **First Line:** The title must be the first line of the document.
3.  **Title Case:** The title should be written in Title Case, where the first letter of each major word is capitalized.
4.  **No Hyphens or Underscores:** The title must not contain hyphens (`-`) or underscores (`_`). Spaces should be used as word separators.

### 4.1 Examples

*   **Correct / Compliant Examples:**
    ```markdown
    # This Is a Correct Title
    # Another Example of a Good Title
    ```

*   **Incorrect / Non-Compliant Examples:**
    ```markdown
    # this is an incorrect title (not Title Case)
    # This-Is-Incorrect (contains hyphens)
    # This_Is_Also_Incorrect (contains underscores)
    ## Not a Main Title (this is a level-2 heading)
    ```

## 5.0 Verification

Compliance with this naming convention can be verified by running the `retittle_notes.sh` script.

1.  Open a terminal in the root project directory.
2.  Execute the command: `bash retittle_notes.sh`
3.  If all note titles are compliant, the script will run and report "Note retitling process complete" without suggesting any changes.

## 6.0 Notes and Cautions

*   Enforcing this convention ensures that automated scripts and search functions can operate on titles more reliably.
*   The `retittle_notes.sh` script is the approved tool for correcting non-compliant titles in bulk.

## 7.0 Revision History

| Version | Date | Author | Change Description |
| :--- | :--- | :--- | :--- |
| 1.0 | 2025-11-01 | Gemini | Initial Release |
| 1.1 | 2025-11-01 | Gemini | Added note about AI adherence to convention. |

## 8.0 Document Conventions

*   **Title:** The document title (and filename) should follow the format: **[Subject] [Process Name] SOP**. For example: "**Audio Recording and Playback SOP.md**". Use Title Case for each word. Do not use hyphens (`-`) or underscores (`_`); use spaces instead. The title is already formatted to be bold.
*   **Document ID:** The document ID should follow the format: `[DEPT-XXX-YYY]`, where DEPT is a short code for the department or subject (e.g., `AUD` for Audio).