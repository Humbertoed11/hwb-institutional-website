# HWB-IT-010 YouTube Automation & Metadata Protocol

| **Document Control** | |
| :--- | :--- |
| **Document Title** | **YouTube Automation & Metadata Protocol** |
| **Document ID** | HWB-IT-010 |
| **Version** | 1.0 |
| **Status** | Approved |
| **Author** | George (Systems Architect) |
| **Approved By** | Humberto Dominguez (CEO) |
| **Date** | 2026-03-13 |

---

## 1.0 Purpose
To define the technical governance and authorization framework for automated YouTube channel management within the SigmaFidelity™ ecosystem.

## 2.0 Official Identity & Authority
*   **Official YouTube Account:** `hwbclean@gmail.com`
*   **Authorization Level:** Permanent Authority for all HWB Cleaning Services LLC video assets.
*   **Service Agent:** George (Systems Architect) is authorized to execute API calls on behalf of this account.

## 3.0 Technical Infrastructure
*   **API:** YouTube Data API v3.
*   **Credentials:** Stored in institutional `.env` under `YOUTUBE_CLIENT_ID` and `YOUTUBE_CLIENT_SECRET`.
*   **Token Management:** Handshake tokens are archived in `scripts/youtube_token.pickle`.

## 4.0 Operational Mandates
1.  **SEO Fidelity:** All video descriptions must be synchronized with the **Expert SEO** keyword strategy.
2.  **Synthetic Media Disclosure:** Automated updates must set `status.containsSyntheticMedia` to `true` for all AI-generated or significantly altered assets.
3.  **Institutional Branding:** All metadata must include links to the **Official Corporate Intranet** and the `www.hwbcleaning.com` corporate site.

## 5.0 Revision History
| Version | Date | Author | Description |
| :--- | :--- | :--- | :--- |
| 1.0 | 2026-03-13 | George | Initial Protocol Release. Established hwbclean@gmail.com as the official authority. |

---
*Produced by George under the SigmaFidelity™ Institutional Standard.*
