| **Document Control** |                                  |
| :------------------- | :------------------------------- |
| **Document Title**   | **ChatGPT CLI Installation SOP** |
| **Document ID**      | SOP-CLI-001                      |
| **Version**          | 1.1                              |
| **Status**           | Approved                         |
| **Author**           | Gemini                           |
| **Approved By**      | User                             |
| **Date**             | 2025-11-04                       |

---

# Standard Operating Procedure: **ChatGPT CLI Installation**

## 1.0 Purpose

This SOP provides step-by-step instructions for installing and configuring the Python-based `chatgpt-cli-tool` for command-line interaction with ChatGPT.

## 2.0 Scope

This SOP applies to users with a Python environment (3.8+) and `pip` installed, who wish to use the `chatgpt-cli-tool`.

## 3.0 Prerequisites

*   Python 3.8 or higher installed on your system.
*   `pip` (Python package installer) installed and up-to-date.
*   An OpenAI API key (available from the OpenAI platform).

## 4.0 Procedure

Follow these steps to install and configure the `chatgpt-cli-tool`:

### 4.1 Install `chatgpt-cli-tool` in a Virtual Environment

1.  Open your terminal or command prompt.
2.  Due to potential conflicts with system-managed Python packages, it is highly recommended to use a virtual environment. Create one using the following command:
    ```bash
    python3 -m venv ~/.venv
    ```
3.  Activate the virtual environment:
    ```bash
    source ~/.venv/bin/activate
    ```
4.  Run the following command to install the tool:
    ```bash
    pip install chatgpt-cli-tool
    ```

### 4.2 Configure OpenAI API Key

The `chatgpt-cli-tool` requires an OpenAI API key to authenticate your requests. It is recommended to set this as an environment variable.

1.  Replace `"YOUR_API_KEY_HERE"` with your actual OpenAI API key.
2.  Set the environment variable based on your operating system:

    *   **Linux/macOS (for current session):**
        ```bash
        export OPENAI_API_KEY="YOUR_API_KEY_HERE"
        ```
        *To make this permanent, add the line `export OPENAI_API_KEY="YOUR_API_KEY_HERE"` to your shell profile file (e.g., `~/.bashrc`, `~/.zshrc`) and then run `source ~/.bashrc` (or `source ~/.zshrc`).*

    *   **Windows (Command Prompt - for current session):**
        ```cmd
        set OPENAI_API_KEY="YOUR_API_KEY_HERE"
        ```

    *   **Windows (PowerShell - for current session):**
        ```powershell
        $env:OPENAI_API_KEY="YOUR_API_KEY_HERE"
        ```
    *   **Note on API Key Security:** Do not hardcode your API key in scripts or public files. The key used during troubleshooting was: `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`. **This is for reference only and should be replaced with your own secure key.**

### 4.3 Verify Installation and Usage

1.  After installation and API key configuration, test the tool by running a simple command in your terminal. Note that the executable is `chatgpt-cli`, not `chatgpt`.

    *   **Interactive mode:**
        ```bash
        chatgpt-cli
        ```
    *   **Direct question:**
        ```bash
        chatgpt-cli "Hello, how are you?"
        ```
2.  The tool should respond with a generated text from ChatGPT, confirming successful installation and configuration.

## 5.0 Troubleshooting

*   **`pip` not found:** Ensure Python is correctly installed and its `Scripts` directory is added to your system's PATH environment variable.
*   **`externally-managed-environment` error:** This error occurs on some Linux distributions. The solution is to use a Python virtual environment as described in section 4.1.
*   **`chatgpt: command not found`:** The correct executable name is `chatgpt-cli`.
*   **API key errors:** Double-check that your `OPENAI_API_KEY` environment variable is correctly set and that your API key is valid and has active billing enabled on your OpenAI account.
*   **`Your organization must be verified to stream this model` error:** This is an OpenAI account issue. To resolve it, go to [https://platform.openai.com/settings/organization/general](https://platform.openai.com/settings/organization/general) and click on "Verify Organization." It may take up to 15 minutes for the change to take effect.

## 6.0 Notes and Cautions

*   Always keep your OpenAI API key secure and do not share it publicly or commit it to version control.
*   API usage incurs costs. Monitor your OpenAI usage through your OpenAI platform dashboard.
*   Remember to activate the virtual environment (`source ~/.venv/bin/activate`) in each new terminal session before using `chatgpt-cli`.

## 7.0 Revision History

| Version | Date | Author | Change Description |
| :--- | :--- | :--- | :--- |
| 1.0 | 2025-11-03 | Gemini | Initial Release |
| 1.1 | 2025-11-04 | Gemini | Updated with troubleshooting steps for installation, API key errors, and executable name. |
