| **Document Control** | |
| :--- | :--- |
| **Document Title** | **Google Home Obsidian Integration SOP** |
| **Document ID** | SOP-GHO-001 |
| **Version** | 3.0 |
| **Status** | Approved |
| **Author** | Gemini |
| **Approved By** | User |
| **Date** | 2025-11-01 |

---

# Standard Operating Procedure: **Google Home Obsidian Integration SOP**

## 1.0 Purpose

This Standard Operating Procedure (SOP) outlines the steps required to integrate Google Home with an Obsidian vault for hands-free note-taking. This procedure enables users to dictate notes to their Google Home device and have them automatically appended to a designated note within their Obsidian vault.

## 2.0 Scope

This SOP applies to all users who wish to set up a connection between their Google Home device and their Obsidian vault using IFTTT (If This Then That).

## 3.0 Prerequisites

Before beginning this procedure, you must have the following:

*   An Obsidian vault located in a cloud-synced folder (e.g., OneDrive, Google Drive, Dropbox).
*   A configured Google Home or Google Assistant-enabled device.
*   An active account with IFTTT (ifttt.com).

## 4.0 Procedure

### 4.1 Create an IFTTT Account

1.  Navigate to [https://ifttt.com](https://ifttt.com).
2.  Sign up for a new account or log in to your existing account.

### 4.2 Create a New IFTTT Applet

1.  From the IFTTT home screen, click the **"Create"** button.

### 4.3 Configure the Trigger (Google Assistant)

1.  Click the **"If This"** button.
2.  Search for and select the **"Google Assistant"** service.
3.  Choose the **"Say a phrase with a text ingredient"** trigger.
4.  In the "What do you want to say?" field, define the voice command. The `$` symbol will be replaced by your spoken note.
    *   **Example:** `add to my notes $`
5.  (Optional) Fill in the alternative phrases and the response for the assistant.
6.  Click **"Create trigger"**.

### 4.4 Configure the Action (OneDrive)

1.  Click the **"Then That"** button.
2.  Search for and select the **"OneDrive"** service.
3.  You will be prompted to connect your OneDrive account to IFTTT. Follow the on-screen instructions to authorize the connection.
4.  Choose the **"Append to a text file"** action.
5.  Configure the action fields:
    *   **File path:** Specify the path to your target note within your OneDrive-synced Obsidian vault. It is recommended to use a dedicated "inbox" file.
        *   **Example:** `/gemini_projects/inbox.md`
    *   **Content:** Click the **"Add ingredient"** button and select **"TextField"**. To include a timestamp, format the content as follows:
        *   `{{CreatedAt}} - {{TextField}}`
    *   **Create file if it does not exist:** Ensure this option is checked.
6.  Click **"Create action"**.

### 4.5 Finalize the Applet

1.  Click **"Continue"** to review the applet.
2.  Click **"Finish"** to save and activate the applet.

## 5.0 Verification

To verify that the integration is working correctly:

1.  Activate your Google Home device by saying "Hey Google" or "Okay Google".
2.  Use the phrase you defined in step 4.3. For example: "Hey Google, add to my notes '''This is a test of the Google Home to Obsidian integration.'''"
3.  Open your Obsidian vault and navigate to the file you specified in step 4.4 (e.g., `inbox.md`).
4.  Confirm that the new note, along with the timestamp, has been appended to the file.

## 6.0 Notes and Cautions

*   The file path in step 4.4 is relative to your OneDrive root folder. Ensure the path is correct.
*   There may be a slight delay (up to a few minutes) for the note to appear in your Obsidian vault.
*   This procedure can be adapted for other cloud storage services supported by IFTTT (e.g., Dropbox, Google Drive) by selecting the appropriate service in step 4.4.

## 7.0 Revision History

| Version | Date | Author | Change Description |
| :--- | :--- | :--- | :--- |
| 1.0 | 2025-11-01 | Gemini | Initial Release |
| 2.0 | 2025-11-01 | Gemini | Updated to ISO 9001 compliant template. |
| 3.0 | 2025-11-01 | Gemini | Applied new title convention. |

## 8.0 Document Conventions

*   **Title:** The document title should follow the format: **[Subject] [Process Name] SOP**. For example: "**Audio Recording and Playback SOP**". Use Title Case for each word and do not use hyphens. The title is already formatted to be bold.
*   **Document ID:** The document ID should follow the format: `[DEPT-XXX-YYY]`, where DEPT is a short code for the department or subject (e.g., `AUD` for Audio).
