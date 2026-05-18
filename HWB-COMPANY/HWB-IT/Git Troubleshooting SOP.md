| **Document Control** |                             |
| :------------------- | :-------------------------- |
| **Document Title**   | **Git Troubleshooting SOP** |
| **Document ID**      | SOP-GIT-001                 |
| **Version**          | 3.0                         |
| **Status**           | Approved                    |
| **Author**           | Gemini                      |
| **Approved By**      | User                        |
| **Date**             | 2025-11-01                  |

---

# Standard Operating Procedure: **Git Troubleshooting SOP**

## 1.0 Purpose

This SOP documents the issues encountered when initializing a Git repository on a GVFS-mounted OneDrive and the steps taken to resolve them. It serves as a reference for troubleshooting similar issues on filesystems with limited POSIX compliance.

## 2.0 Scope

This SOP applies to users attempting to use Git on filesystems that do not fully support standard POSIX file permissions, leading to errors with `chmod` and other common Git operations.

## 3.0 Prerequisites

*   A Linux system with `git` installed.
*   A project directory located on a GVFS-mounted filesystem or similar non-standard filesystem.

## 4.0 Procedure

This section details the chronological troubleshooting process.

### 4.1 Problem 1: `git init` Fails

*   **Symptom:** The `git init` command fails with an error related to `chmod` and an inability to set `core.filemode`.
*   **Analysis:** The underlying GVFS filesystem does not support the file permission changes (`chmod`) that Git attempts to make during initialization.

*   **Attempted Solution 1: Simple Retry:** Re-running `git init` resulted in the same failure.

*   **Attempted Solution 2: Post-Init Configuration:** Attempting to run `git config core.filemode false` after a failed `git init` also failed, with Git reporting that the directory was not a valid Git repository. This indicated the initialization process was corrupting the `.git` directory.

*   **Attempted Solution 3: `safe.directory` Configuration:** Adding the directory to Git's global `safe.directory` list did not resolve the issue, as the core problem was with the filesystem, not Git's security model.

*   **Successful Solution: Manual Repository Creation:** The following manual process was used to create a functional repository:
    1.  A temporary, "bare" Git repository was created in the `/tmp` directory (`git init --bare /tmp/tempgit`).
    2.  A new `.git` directory was manually created in the project folder.
    3.  The contents of the bare repository were copied into the new `.git` directory.
    4.  The `.git/config` file was manually edited to set `bare = false` and `filemode = false`, bypassing the failing `git config` commands.

### 4.2 Problem 2: Script Execution (`chmod +x`) Fails

*   **Symptom:** The `chmod +x` command failed with an "Operation not supported" error when attempting to make a shell script executable.
*   **Analysis:** This is the same underlying filesystem limitation as in Problem 1.
*   **Successful Solution:** The script was executed by passing it as an argument to the `bash` interpreter (`bash script_name.sh`), which does not require the file to have execute permissions.

## 5.0 Verification

The successful resolution was verified when the `git status` command executed without errors, correctly showing the untracked files in the project directory.

## 6.0 Notes and Cautions

*   Working with Git on non-standard filesystems like GVFS can be challenging and may require manual intervention.
*   The core issue is the filesystem's lack of support for POSIX file permissions.
*   When `chmod` fails, always consider running scripts with the appropriate interpreter (e.g., `bash`, `python`) as a workaround.
*   Directly editing the `.git/config` file is a powerful but potentially risky operation. It should only be done when automated commands fail and you understand the changes you are making.

## 7.0 Undoing Changes

Git provides powerful tools to undo changes. Here are some common scenarios:

### 7.1 Discarding Uncommitted Changes

If you have made changes to your files but have not yet committed them, you can discard all uncommitted changes and revert your working directory to the last committed state.

*   **Command:**
    ```bash
    git restore .
    ```
    (For older Git versions, you might use `git checkout .`)

### 7.2 Undoing the Last Commit

If you have made a commit and immediately realize you want to undo it (and discard the changes made in that commit), you can reset to the previous commit.

*   **Command:**
    ```bash
    git reset --hard HEAD~1
    ```
    **Caution:** This command will permanently discard the last commit and any changes introduced by it. Use with care.

### 7.3 Reverting a Specific Commit

If you want to undo the changes introduced by a specific commit while keeping the history intact (by creating a new commit that reverses the changes), you can use `git revert`.

*   **Command:**
    ```bash
    git revert <commit-hash>
    ```
    Replace `<commit-hash>` with the actual hash of the commit you wish to revert (you can find this using `git log`).

## 8.0 Revision History

| Version | Date | Author | Change Description |
| :--- | :--- | :--- | :--- |
| 1.0 | 2025-11-01 | Gemini | Initial Release |
| 2.0 | 2025-11-01 | Gemini | Updated to ISO 9001 compliant template. |
| 3.0 | 2025-11-01 | Gemini | Applied new title convention. |

## 9.0 Document Conventions

*   **Title:** The document title should follow the format: **[Subject] [Process Name] SOP**. For example: "**Audio Recording and Playback SOP**". Use Title Case for each word and do not use hyphens. The title is already formatted to be bold.
*   **Document ID:** The document ID should follow the format: `[DEPT-XXX-YYY]`, where DEPT is a short code for the department or subject (e.g., `AUD` for Audio).