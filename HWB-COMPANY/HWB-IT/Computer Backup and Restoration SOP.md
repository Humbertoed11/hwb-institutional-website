| **Document Control** |                                         |
| :------------------- | :-------------------------------------- |
| **Document Title**   | **Computer Backup and Restoration SOP** |
| **Document ID**      | SOP-BCK-001                             |
| **Version**          | 1.1                                     |
| **Status**           | Approved                                |
| **Author**           | Gemini                                  |
| **Approved By**      | User                                    |
| **Date**             | 2025-11-04                              |

---

# Standard Operating Procedure: **Computer Backup and Restoration**

## 1.0 Purpose

This SOP provides a routine for backing up and restoring a Linux-based computer system to ensure data integrity and availability in case of system failure.

## 2.0 Scope

This SOP applies to the user's primary Linux computer and covers the backup of personal data and system configuration.

## 3.0 Prerequisites

*   An external hard drive or network storage location with sufficient capacity for the backup.
*   The `rsync` utility installed on the system.

## 4.0 Backup Procedure

### 4.1 Full System Backup (Recommended Weekly)

1.  Connect the external backup drive to the computer.
2.  Open a terminal.
3.  Execute the following `rsync` command, replacing `/path/to/backup/destination` with the actual path to your backup drive:

    ```bash
    sudo rsync -aAXv --exclude={"/dev/*","/proc/*","/sys/*","/tmp/*","/run/*","/mnt/*","/media/*","/lost+found"} / /path/to/backup/destination
    ```

    *   **-a:** Archive mode (preserves permissions, ownership, etc.)
    *   **-A:** Preserves ACLs (Access Control Lists)
    *   **-X:** Preserves extended attributes
    *   **-v:** Verbose output
    *   **--exclude:** Excludes specified directories that are not necessary for restoration.

### 4.2 Home Directory Backup (Recommended Daily)

For more frequent backups of your personal files, a backup of your home directory is recommended.

1.  Connect the external backup drive.
2.  Open a terminal.
3.  Execute the following command, replacing `/path/to/backup/destination/home` with the desired backup location:

    ```bash
    rsync -avz --progress ~ /path/to/backup/destination/home
    ```

    *   **-z:** Compresses file data during transfer.
    *   **--progress:** Shows the progress of the transfer.

## 5.0 Restoration Procedure

### 5.1 Full System Restoration

1.  Boot from a live Linux USB drive.
2.  Mount your system's root partition and the backup drive.
3.  Open a terminal.
4.  Execute the following `rsync` command to restore the files:

    ```bash
    sudo rsync -aAXv /path/to/backup/destination/ /path/to/your/system/root
    ```

### 5.2 Home Directory Restoration

1.  Open a terminal.
2.  Execute the following command to restore your home directory:

    ```bash
    rsync -avz /path/to/backup/destination/home/ ~/
    ```

## 6.0 Notes and Cautions

*   **Test your backups!** Periodically test your backups by attempting to restore a few files to ensure the backup is working correctly.
*   Store your backup drive in a safe, separate location from your computer.
*   This SOP is a draft and should be reviewed and approved by the user.

## 7.0 Revision History

| Version | Date | Author | Change Description |
| :--- | :--- | :--- | :--- |
| 1.0 | 2025-11-04 | Gemini | Initial Release |
| 1.1 | 2025-11-04 | Gemini | User Approved. |
