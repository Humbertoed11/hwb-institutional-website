| **Document Control** |                                  |
| :------------------- | :------------------------------- |
| **Document Title**   | **Marketing Form Standard**      |
| **Document ID**      | HWB-MKT-FORM-001                 |
| **Version**          | 2.1.0                            |
| **Status**           | APPROVED                         |
| **Author**           | George (Architect)               |
| **Approved By**      | Humberto Dominguez, CEO          |
| **Date**             | 05/21/2026                       |
| **ISO 9001 Clause**  | 8.2.1 (Communication)            |

---

# Standard Operating Procedure: **Marketing Form Standard**

## 1.0 Purpose
To define how our website forms should look and work. This ensures we get the right information from customers and can help them quickly.

## 2.0 Scope
Applies to the Home Page Form and the Quote Form.

## 3.0 Universal Mandates (2026 Baseline)
1. **Physical Truth:** Use absolute paths for form templates.
2. **Clinical Hardening:** All inputs must look clean and professional.
3. **No Synthetic Data:** Examples must be clearly marked.

## 4.0 Standard Form Protocols

### 4.1 Detailed Plan (Version 1)
*   **Use Case:** Special service pages (Janitorial, Industrial).
*   **Fields:** Name, Email, Phone, Building Type, Size Slider.
*   **Goal:** Get full details for a complete cleaning plan.

### 4.2 Simple Registration (Version 2)
*   **Use Case:** Home Page.
*   **Fields:** Business Name, Your Name, Email, Phone.
*   **Goal:** Make it fast and easy for customers to connect with us. A team member will call later to get more details.

## 5.0 Technical Logic
*   **Method:** `POST`.
*   **Route:** `/get-quote`.
*   **Result:** Data added to our list; Team member gets an alert.

## 6.0 Verification (Zero-Defect Check)
*   Form works and shows a "Success" page.
*   The action is logged in our system.

## 7.0 Revision History
| Version | Date | Author | Change Description |
| :--- | :--- | :--- | :--- |
| 2.1.0 | 05/21/2026 | George | Removed specific names and simplified vocabulary for young managers. |
| 2.0.0 | 05/21/2026 | George | Initial Modernization. |
