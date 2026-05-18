| **Document Control** |                                              |
| :------------------- | :------------------------------------------- |
| **Document Title**   | **George (AI Assistant) Azure Infrastructure Flowchart** |
| **Document ID**      | HWB-IT-GEORGE-ARCH-001                       |
| **Version**          | 1.0                                          |
| **Status**           | Active                                       |
| **Author**           | George (AI Marketing, Web Assistant & Expert SEO) |
| **Approved By**      | Humberto Dominguez (CEO)                     |
| **Date**             | 2026-03-11                                   |

---

# 1.0 Purpose
This document provides a high-fidelity visualization of the **George (AI Assistant)** infrastructure within the Microsoft Azure ecosystem. It outlines the authentication flow, permission structures, and secret management protocols ensuring 100% compliance with SigmaFidelity™ security standards.

# 2.0 Azure Infrastructure Flowchart

```mermaid
graph TD
    subgraph "Microsoft Azure Portal (Entra ID)"
        A[App Registration: SigmaFidelity-George]
        B[Application ID: 8226641a-...]
        C[Directory/Tenant ID: f4e215a9-...]
        D[Client Secret: SqR8Q~Ltra...]
    end

    subgraph "API Permissions (Application Level)"
        E[Mail.Send]
        F[Calendars.ReadWrite]
        G[Notes.ReadWrite.All - DEPRECATED for App-Only]
    end

    subgraph "Admin Consent"
        H{Grant Admin Consent for hwbcleaning.com}
        I[Green Checkmark: Authorized]
    end

    subgraph "George (Linux/WSL Engine)"
        J[.env File: Institutional Secrets]
        K[Python MSAL: Microsoft Authentication Library]
        L[OAuth 2.0 Client Credentials Flow]
    end

    subgraph "Microsoft Graph API Services"
        M[Outlook Email Dispatch]
        N[Outlook Calendar Scheduling]
    end

    A --> B
    A --> C
    A --> D
    
    B --> E
    B --> F
    B --> G
    
    E --> H
    F --> H
    G --> H
    
    H --> I
    
    J --> K
    K --> L
    D --> L
    L --> I
    
    I --> M
    I --> N
```

# 3.0 Component Descriptions

| Component | Description |
| :--- | :--- |
| **App Registration** | The central identity for George within the `hwbcleaning.com` tenant, acting as a "Service Principal." |
| **Client Secret** | The institutional password used by George's Python engine to prove its identity to Azure. |
| **OAuth 2.0 Flow** | The secure handshake protocol (Client Credentials) used to acquire an Access Token without user login. |
| **Application Permissions** | High-level "Role-Based Access Control" (RBAC) that allows George to operate autonomously. |
| **Admin Consent** | The mandatory executive override that authorizes George to interact with corporate data. |

# 4.0 Revision History
| Version | Date | Author | Change Description |
| :--- | :--- | :--- | :--- |
| 1.0 | 2026-03-11 | George | Initial infrastructure flowchart created following the activation of Mail and Calendar permissions. |

---
*Produced by George (System Architect) under the SigmaFidelity™ Quality Mandate.*
