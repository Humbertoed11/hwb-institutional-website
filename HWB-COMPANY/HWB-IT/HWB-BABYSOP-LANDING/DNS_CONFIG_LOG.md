# Institutional DNS Configuration: babysop.com

| **Document Control** |                                              |
| :------------------- | :------------------------------------------- |
| **Document Title**   | **DNS Handshake Parameters: babysop.com**    |
| **Document ID**      | HWB-IT-DNS-BSOP-001                          |
| **Version**          | 1.0                                          |
| **Status**           | PENDING PROPAGATION                          |
| **Date**             | 2026-03-12                                   |

---

## 1.0 Record Summary
The following records point the root and www subdomain to the Azure App Service `hwb-babysop-landing`.

| Type  | Host  | Value                                                              |
| :---  | :---  | :---                                                               |
| A     | @     | 20.40.202.30                                                       |
| CNAME | www   | hwb-babysop-landing.azurewebsites.net                              |
| TXT   | asuid | 79668832871F4BA0A42124DA4E7C436C46A2BFD1EBA663C994C1BA27BFCBE6C2 |

## 2.0 Azure Verification
*   **App Name:** `hwb-babysop-landing`
*   **Resource Group:** `HWB-SIGMAJAN-PROD`
*   **Verification ID:** `796688328...`

---
*Produced by George under the SigmaFidelity™ Quality Mandate.*
