| **Document Control** |                                  |
| :------------------- | :------------------------------- |
| **Document Title**   | **Secret Management and API Governance** |
| **Document ID**      | HWB-QMS-9.5                      |
| **Version**          | 2.0.0                            |
| **Status**           | APPROVED                         |
| **Author**           | George (Architect)               |
| **Approved By**      | Humberto Dominguez, CEO          |
| **Date**             | 05/21/2026                       |
| **ISO 9001 Clause**  | 7.1.3 (Infrastructure)           |

---

# Standard Operating Procedure: **Secret Management and API Governance**

## 1.0 Purpose
To define the procedure for securing, tracking, and rotating HWB digital secrets and API keys. This SOP ensures that all credentials are moved from vulnerable text files into the **SigmaVault** database to prevent system outages and unauthorized access.

## 2.0 Universal Mandates (2026 Baseline)
1. **The SigmaVault Standard:** 100% of production API keys and system secrets must be stored in the `SigmaVault` SQL table.
2. **Rotation Alert:** Every secret must have a recorded **Expiration Date**. The system must flag any key within 30 days of expiring.
3. **No Secret Printing:** AI agents are strictly prohibited from printing actual secret values in logs or chat interfaces.

## 3.0 Critical Expiration Registry (2027 Warning)
| Secret Name | Service | Expiration Date | Action Required |
| :--- | :--- | :--- | :--- |
| **GRAPH_CLIENT_SECRET** | Microsoft Graph | **03/02/2027** | Rotation required prior to date. |
| **AZURE_OPENAI_KEY** | Azure AI | 05/20/2027 | Standard annual review. |

## 4.0 Procedure

### 4.1 Migration to SigmaVault
1.  **Extraction:** Identify keys in `.env` and `HWB-COMPANY-Logins.md`.
2.  **Injection:** Use the `SigmaVault` injection script to move keys to the encrypted database.
3.  **Purging:** Once verified in SQL, remove actual values from Markdown files, leaving only the **Key Name** and **Audit ID**.

### 4.2 Morning Sentinel Check
Every morning, the AI team member must:
1.  Query the `SigmaVault` for keys expiring within 30 days.
2.  If a match is found, add an alert to the **Executive Pulse** dashboard.
3.  Include the alert in the Daily Executive Summary for the CEO.

## 5.0 Verification (Zero-Defect Check)
*   The `.env` file contains zero actual production secrets (only links to Vault IDs).
*   The `SigmaVault` table has 100% of keys mapped to a service owner.

## 6.0 Notes and Cautions
> **NOTE:** Use simple "Everyday Words" when discussing security needs with managers.
> **CAUTION:** Never commit the `.env` file to the Git repository.

## 7.0 Revision History
| Version | Date | Author | Change Description |
| :--- | :--- | :--- | :--- |
| 2.0.0 | 05/21/2026 | George | TOTAL MODERNIZATION. Retired Markdown login tracking and launched the SQL-based SigmaVault. Added 2027 Graph Secret warning. |
