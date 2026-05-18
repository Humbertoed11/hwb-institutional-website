| **Document Control** | |
| :--- | :--- |
| **Document Title** | **Audio Recording and Playback SOP** |
| **Document ID** | SOP-AUD-001 |
| **Version** | 3.0 |
| **Status** | Approved |
| **Author** | Gemini |
| **Approved By** | User |
| **Date** | 2025-11-01 |

---

# Standard Operating Procedure: **Audio Recording and Playback SOP**

## 1.0 Purpose

This Standard Operating Procedure (SOP) outlines the steps required to record and play back audio from the command line using `arecord` and `aplay`.

## 2.0 Scope

This SOP applies to all users on a Linux system with ALSA sound utilities installed.

## 3.0 Prerequisites

*   A working microphone and speakers.
*   The `arecord` and `aplay` utilities installed (part of the `alsa-utils` package on most Debian-based systems).

## 4.0 Procedure

### 4.1 Recording Audio

1.  Open a terminal window.
2.  To begin recording, execute the following command, replacing `<filename>.wav` with your desired file name:
    ```bash
    arecord -f cd -d 0 -t wav <filename>.wav
    ```
3.  To stop recording, press `Ctrl+C`.

### 4.2 Playing Back Audio

1.  Open a terminal window.
2.  To play back the audio, execute the following command, replacing `<filename>.wav` with the name of the file you want to hear:
    ```bash
    aplay <filename>.wav
    ```

## 5.0 Verification

1.  Record a short audio clip using the `arecord` command.
2.  Play back the audio clip using the `aplay` command.
3.  Confirm that you can hear the recorded audio.

## 6.0 Notes and Cautions

*   The `-f cd` option sets the recording to CD quality (16-bit little-endian, 44100 Hz, stereo).
*   The `-d 0` option will record indefinitely until you manually stop it.
*   When recording conversations, be aware of legal and ethical requirements for obtaining consent.

## 7.0 Revision History

| Version | Date | Author | Change Description |
| :--- | :--- | :--- | :--- |
| 1.0 | 2025-11-01 | Gemini | Initial Release |
| 2.0 | 2025-11-01 | Gemini | Updated to ISO 9001 compliant template. |
| 3.0 | 2025-11-01 | Gemini | Applied new title convention. |

## 8.0 Document Conventions

*   **Title:** The document title should follow the format: **[Subject] [Process Name] SOP**. For example: "**Audio Recording and Playback SOP**". Use Title Case for each word and do not use hyphens. The title is already formatted to be bold.
*   **Document ID:** The document ID should follow the format: `[DEPT-XXX-YYY]`, where DEPT is a short code for the department or subject (e.g., `AUD` for Audio).
