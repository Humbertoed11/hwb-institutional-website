| **Document Control** |                               |
| :------------------- | :---------------------------- |
| **Document Title**   | **Obsidian Android Sync SOP** |
| **Document ID**      | SOP-OBS-001                   |
| **Version**          | 3.0                           |
| **Status**           | Approved                      |
| **Author**           | Gemini                        |
| **Approved By**      | User                          |
| **Date**             | 2025-11-01                    |

---

# Standard Operating Procedure: **Obsidian Android Sync SOP**

## 1.0 Purpose

This SOP provides instructions for accessing and editing an existing Obsidian vault, stored in OneDrive, from an Android device. This will enable seamless synchronization of notes between a desktop computer and a Google Pixel phone.

## 2.0 Scope

This procedure applies to users who have an existing Obsidian vault in a OneDrive folder and a Google Pixel phone (or other Android device) with both the Obsidian and OneDrive applications installed.

## 3.0 Prerequisites

*   An existing Obsidian vault located in a OneDrive folder.
*   A Google Pixel phone with the official **Obsidian** and **OneDrive** apps installed from the Google Play Store.
*   You must be logged into the **same Microsoft OneDrive account** on both your desktop computer and your Pixel phone.

## 4.0 Procedure

### 4.1 Step 1: Make Your Vault Available Offline in OneDrive

For Obsidian to be able to see and edit your notes, the files must be physically present on your phone. The OneDrive app has a feature to make files and folders available "offline" for this purpose.

1.  Open the **OneDrive** app on your Pixel phone.
2.  Navigate to the folder that contains your Obsidian vault (e.g., `gemini_projects`).
3.  Tap the **three dots (...)** next to your vault folder's name.
4.  From the menu that appears, select **"Keep offline"** (it may also be represented by a parachute icon).
5.  OneDrive will now download a copy of your entire vault to your phone. This may take some time depending on the size of your vault and your internet connection speed.

### 4.2 Step 2: Open the Vault in Obsidian on Your Phone

Now that your notes are on your phone, you need to tell the Obsidian app where to find them.

1.  Open the **Obsidian** app on your Pixel phone.
2.  On the initial screen, select **"Open folder as vault"**.
3.  This will open your phone's file navigator. Use the method in **Section 4.3** to find the exact path to your vault.
4.  Once you have navigated to your vault folder, tap on it.
5.  A button will appear at the bottom of the screen that says **"Use this folder"**. Tap it.
6.  Obsidian will ask for permission to access the files. Grant the permission.

### 4.3 Step 3: Finding the Exact Vault Path on Android

Android's file system can make it difficult to find the exact path for cloud-synced files. This method provides a reliable way to locate your vault.

1.  **Create a Test File:** On your desktop computer, create a new, uniquely named file inside your Obsidian vault. For example, `find_my_vault_123.txt`.
2.  **Sync to Your Phone:** Wait a moment for OneDrive to sync this new file to your Pixel phone. You can open the OneDrive app on your phone and look for the file to confirm it has arrived.
3.  **Use a File Manager:** On your Pixel phone, open a file manager app. The built-in "Files" app can work, but a more advanced file manager from the Play Store like **Solid Explorer** or **FX File Explorer** is recommended as they make it easier to see full file paths.
4.  **Search for the Test File:** Use the search function within your file manager app to search for your unique file (e.g., `find_my_vault_123.txt`).
5.  **View File Properties:** Once the file manager finds the file, **long-press** on it and look for an option in the menu called **"Properties"**, **"Details"**, or **"Info"**.
6.  **Identify the Path:** The properties view will show you the full **"Parent path"** or **"Location"** of the file. This is the folder path you need to navigate to in Obsidian. It will look something like this:
    *   `/storage/emulated/0/Android/data/com.microsoft.skydrive/files/your_folder/...`

### 4.4 Step 4: Verification

Your Obsidian vault should now load on your phone, looking identical to your desktop setup.

1.  To confirm that the sync is working, create a new note on your phone with a title like "Test note from Pixel".
2.  Wait a few moments for OneDrive to sync the new file.
3.  Open Obsidian on your desktop computer. You should see the "Test note from Pixel" appear in your vault.

## 5.0 Notes and Cautions

*   **Sync Delays:** Be aware that there can be a delay when syncing between devices. Always give OneDrive a moment to sync before switching devices to avoid potential conflicts.
*   **Sync Conflicts:** If you edit the same note on both your phone and computer before a sync can complete, OneDrive may create a "conflicted copy" of the file. You will need to manually merge the changes from the conflicted copy into the original.
*   **Background Sync:** Ensure that the OneDrive app on your phone has permission to run in the background to keep your notes up to date automatically.

## 7.0 Revision History

| Version | Date | Author | Change Description |
| :--- | :--- | :--- | :--- |
| 1.0 | 2025-11-01 | Gemini | Initial Release |
| 1.1 | 2025-11-01 | Gemini | Added detailed instructions for finding vault path. |
| 2.0 | 2025-11-01 | Gemini | Updated to ISO 9001 compliant template. |
| 3.0 | 2025-11-01 | Gemini | Applied new title convention. |

## 8.0 Document Conventions

*   **Title:** The document title should follow the format: **[Subject] [Process Name] SOP**. For example: "**Audio Recording and Playback SOP**". Use Title Case for each word and do not use hyphens. The title is already formatted to be bold.
*   **Document ID:** The document ID should follow the format: `[DEPT-XXX-YYY]`, where DEPT is a short code for the department or subject (e.g., `AUD` for Audio).
