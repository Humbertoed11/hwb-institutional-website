| **Document Control** |                                  |
| :------------------- | :------------------------------- |
| **Document Title**   | **Microsoft 365 Integration SOP** |
| **Document ID**      | HWB-QMS-7.6                      |
| **Version**          | 1.0                              |
| **Status**           | Draft                            |
| **Author**           | SigmaFidelity™ AI Assistant      |
| **Approved By**      | Managing Director                |
| **Date**             | 2026-03-02                       |

---

# Standard Operating Procedure: **Microsoft 365 Integration SOP**

## 1.0 Purpose

The purpose of this Standard Operating Procedure (SOP) is to provide standardized instructions for connecting the SigmaFidelity™ Marketing Assistant (George) to a Microsoft 365 account via the Microsoft Graph API. This ensures high-fidelity communication and autonomous scheduling capabilities.

## 2.0 Scope

This procedure applies to the HWB IT department and any personnel responsible for the maintenance of autonomous marketing systems. It covers the registration of applications within the Microsoft Entra ID portal and the subsequent configuration of the local environment.

## 3.0 Prerequisites

*   Administrative access to a Microsoft 365 Tenant.
*   Access to the Microsoft Azure Portal (portal.azure.com).
*   Python 3.12 installed in the local environment.
*   The `msal` (Microsoft Authentication Library) and `requests` Python packages.

## 4.0 Procedure

### 4.1 Application Registration

1.  Navigate to the **Microsoft Azure Portal** and sign in with administrative credentials.
2.  Select **Microsoft Entra ID** from the dashboard.
3.  Navigate to **App registrations** and select **New registration**.
4.  Enter a descriptive name (e.g., `HWB-SigmaFidelity-Agent`).
5.  Select **Accounts in this organizational directory only** as the supported account type.
6.  Click **Register**.
7.  Record the **Application (client) ID** and the **Directory (tenant) ID** from the Overview page.

### 4.2 API Permission Assignment

1.  Within the registered application, navigate to **API permissions**.
2.  Select **Add a permission** and choose **Microsoft Graph**.
3.  Select **Application permissions**.
4.  Search for and select the following permissions:
    *   `Mail.Send` (Required for outreach emails)
    *   `Mail.ReadWrite` (Required for managing responses)
    *   `Calendars.ReadWrite` (Required for audit scheduling)
5.  Select **Add permissions**.
6.  Click **Grant admin consent for [Tenant Name]** to authorize the requested scopes.

### 4.3 Client Secret Generation

1.  Navigate to **Certificates & secrets** within the application menu.
2.  Select **New client secret**.
3.  Enter a description (e.g., `SigmaFidelity-George-Secret`) and set an expiration period (e.g., 12 months).
4.  Click **Add**.
5.  **CRITICAL:** Immediately copy the secret **Value**. This value is hidden after the initial session and must be stored securely.

### 4.4 Local Environment Configuration

1.  Create or update the `.env` file in the project root directory.
2.  Append the following variables using the data recorded in steps 4.1 and 4.3:
    ```env
    MS_CLIENT_ID=your_client_id_here
    MS_TENANT_ID=your_tenant_id_here
    MS_CLIENT_SECRET=your_client_secret_here
    ```
3.  Ensure the `.env` file is listed in `.gitignore` to prevent credential leakage.

## 5.0 Verification

1.  Execute the `HWB-WEB Microsoft Client.py` diagnostic script (to be developed).
2.  Confirm the retrieval of an Access Token from the Microsoft Identity Platform.
3.  Verify that a test email is successfully transmitted through the Microsoft Graph API.

## 6.0 Notes and Cautions

*   **Secret Lifecycle:** The current Client Secret for the `sigmafidelity-george` integration is scheduled to expire on **2027-03-02**. A new secret must be generated and updated in the local `.env` file prior to this date.
*   **Security:** Never commit the Client Secret or the `.env` file to version control.
*   **Token Lifecycle:** The integration logic must handle token expiration and automatic refreshing to ensure continuous autonomous operations.
*   **Consent:** Admin consent is mandatory for Application permissions to operate without interactive user login.

## 7.0 Revision History

| Version | Date | Author | Change Description |
| :--- | :--- | :--- | :--- |
| 1.0 | 2026-03-02 | SigmaFidelity™ AI Assistant | Initial Release |

## 8.0 Document Conventions

*   **Title:** Follows the format **Microsoft 365 Integration SOP**.
*   **Document ID:** Assigned as `HWB-QMS-7.6`.
*   **Storage Location:** This document is stored in the `Standard Operating Procedures/` directory.
