| **Document Control** |                                              |
| :------------------- | :------------------------------------------- |
| **Document Title**   | **Official Institutional Letterhead**        |
| **Document ID**      | HWB-COM-001                                  |
| **Version**          | 2.1.0                                        |
| **Status**           | APPROVED                                     |
| **Author**           | George (Architect)                           |
| **Approved By**      | Humberto Dominguez, CEO                      |
| **Date**             | 09/19/2026                                   |
| **ISO 9001 Clause**  | 8.2.1 (Customer Communication)               |

---

# Standard Operating Procedure: **Official Institutional Letterhead**

## 1.0 Purpose
To provide a standardized, high-fidelity letterhead for all HWB Cleaning Services LLC correspondence. This ensures brand authority and operational excellence in all digital and physical communications.

## 2.0 Universal Mandates (2026 Baseline)
1. **Third-Person Perspective:** All correspondence using this letterhead must use the 3rd person standard.
2. **Physical Truth:** Use canonical server paths for the corporate logo asset (`/static/logo_standard.png`).
3. **Outbox Protocol:** Stage all high-stakes correspondence in the **PendingOutbox** for CEO approval.

## 3.0 Letterhead Template (HTML)
```html
<div class="hwb-letterhead" style="font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 40px; border: 1px solid #e2e8f0; border-radius: 8px; max-width: 800px; margin: 0 auto; background: #ffffff;">
    <div class="hwb-header" style="display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid #0f172a; padding-bottom: 20px;">
        <div style="display: flex; align-items: center; gap: 14px;">
            <img src="/static/logo_standard.png" alt="HWB Cleaning Services LLC" height="48" style="display: block;">
            <div>
                <div style="font-weight: 800; font-size: 16px; color: #0f172a; letter-spacing: -0.01em;">HWB CLEANING SERVICES LLC</div>
                <div style="font-weight: 700; font-size: 11px; color: #2563eb; letter-spacing: 0.05em; text-transform: uppercase;">Institutional Division • SigmaFidelity™</div>
            </div>
        </div>
        <div style="text-align: right; font-size: 11px; color: #475569; line-height: 1.45;">
            <b>Corporate Headquarters:</b><br>
            3342 FM 1827 Ste 8d, McKinney, TX 75071<br>
            Switchboard: (214) 586-0257 | Mobile: (972) 800-7808<br>
            <a href="https://www.hwbcleaning.com" style="color: #2563eb; text-decoration: none;">www.hwbcleaning.com</a>
        </div>
    </div>
    <div class="hwb-content" style="padding: 36px 0; min-height: 400px; line-height: 1.7; color: #1e293b; font-size: 14px;">
        [BODY_CONTENT]
    </div>
    <div class="hwb-footer" style="border-top: 1px solid #e2e8f0; padding-top: 20px; text-align: center; font-size: 10px; color: #94a3b8; line-height: 1.5;">
        <b>FIDELITY. SAFETY. RESPECT.</b><br>
        Texas Charter #802920409 • CAGE (SAM) #082830635 • Commercial EMR: .43<br>
        © 2026 HWB Cleaning Services LLC. ISO 9001:2015 Compliant.
    </div>
</div>
```

## 4.0 Verification (Zero-Defect Check)
*   Logo renders clearly in Microsoft Outlook and Gmail with crisp edges.
*   McKinney headquarters address and EMR `.43` are verified and present.
*   The tagline "Fidelity. Safety. Respect." is present and accurate.

## 5.0 Revision History
| Version | Date | Author | Change Description |
| :--- | :--- | :--- | :--- |
| 2.1.0 | 09/19/2026 | George | BRAND HARMONIZATION. Integrated official commercial building logo and McKinney HQ coordinates per CEO approval. |
| 2.0.0 | 05/21/2026 | George | TOTAL MODERNIZATION. Added 2026 mandates and Inter font standard. |
| 1.0 | 2026-03-13 | Maria Bolanos | Initial Release. |
