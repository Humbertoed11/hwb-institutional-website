# HWB-QMS-7.2: SigmaFidelity™ Web & UI Standardization SOP

| **Document Control** | |
| :--- | :--- |
| **Document Title** | **SigmaFidelity™ Web & UI Standardization SOP** |
| **Document ID** | HWB-QMS-7.2 |
| **Version** | 5.0 |
| **Status** | Approved |
| **Author** | George (Systems Architect) |
| **Approved By** | Humberto Dominguez (CEO) |

---

## 1. Purpose
This Standard Operating Procedure (SOP) establishes the official design and linguistic standards for the HWB Cleaning Services LLC web ecosystem. The objective is to ensure visual stability, "Class A" corporate authority, and accessibility for regular users.

## 2. Scope
This standard applies to all public-facing service templates, the global `base.html` architecture, and the SigmaFidelity™ Backoffice environment.

## 3. Linguistic Standard ("Everyday Words")
All website content must be written for a regular person (20-year-old reading level).
- **Rule**: Replace high-academic or "super-institutional" jargon with simple, direct terms.
- **Service Focus**: Always lead with cleaning results. Use "Clean," "Clear," or "Debris Removal" instead of "Safety" when describing the work performed.
- **Perspective**: All official communications must maintain a **3rd person perspective**.

## 4. Visual Specifications: Image Framing
To prevent technical cropping errors (e.g., cut-off heads), all split-section images MUST follow the **Floating Composition** architecture.
- **Implementation**: Use a standalone `<img>` tag with `object-fit: contain` nested inside a `.split-image-container`.
- **Fidelity**: Padded frames must use the institutional `#fcfdfe` or `#f8fafc` backgrounds with a 20px - 50px executive shadow.

## 5. Navigation Architecture: The Mega-Bar
The global navigation must utilize the full-width Mega Menu system.
- **Trigger**: Parent headers (e.g., "Services") must be **non-clickable** triggers (`javascript:void(0)`).
- **Submenu**: Every option must include a bold **Title** and a 1-sentence **Description** in Everyday Words.

## 6. Form Standards: The Procurement Matrix
All quote request forms must utilize the high-density **2-Column Procurement Matrix** layout.
- **Column 1**: Building Details (Type, Cycle, SQF).
- **Column 2**: Contact Information (Name, Org, Email, Phone).
- **Parameters**: SQF range must be **500 to 1,000,000**. Cleaning cycles must be **Slow Traffic**, **High Traffic**, or **24/7 Production Traffic**.

## 8. Brand Animation: The Logo Merge
All primary brand animations must follow the "Converging Forces" standard to represent the meeting of Effort and Trust.
- **Vertical Split**: The logo MUST be split at the **28% mark**, bisecting the center black connector bar.
- **Animation Logic**: Components must start **180px apart** using clean 2D linear horizontal motion.
- **Timing**: Use `cubic-bezier(0.2, 1, 0.3, 1)` for a 1.8-second smooth-stop convergence.
- **Recreation Prompt**: 
    > "Implement the HWB 2D Logo Merge Animation using CSS clip-path at the 28% mark. Animate units starting 180px apart using simple translateX over 1.8s with a smooth-stop cubic-bezier."

## 7. SigmaFidelity™ Institutional Form System (2026)
All backoffice forms must adhere to the SigmaFidelity™ Institutional Form System.
- **Structure**: Use `.sigma-form-container`, `.sigma-form-section` (grid), and `.sigma-form-group`.
- **Headers**: Section headers must use `.sigma-form-header` (0.85rem, bold, blue bottom accent).
- **Inputs**: Inputs must use `.sigma-input` (f8fafc background, 12px radius, focused glow).
- **Layouts**: Use asymmetric row splits (`.sigma-row-75-25` for City/State, `.sigma-row-60-40` for Quote/Freq).
- **Clutter**: Eliminate redundant inline styles and excessive visual clutter (icons kept to headers or labels only).

## 8. Professional Polish Standard (2026)
All administrative UIs must avoid "Loud" or "Amateur" scaling.
- **Modal Headers**: Limited to 1.5rem (Semi-Bold).
- **Border Radius**: Strictly capped at 1.25rem for large elements.
- **Icons**: Elimination of icons within input labels (icons reserved for navigation/status only).
- **Close Buttons**: Use refined SVG close buttons instead of raw HTML entities.
- **Materiality**: Implementation of "Material Depth" using subtle grey backgrounds (f8fafc) and soft-focus shadows.

---

## Revision History
| Version | Date | Description | Author |
| :--- | :--- | :--- | :--- |
| 1.0 | 03/27/2026 | Initial release of UI Standard for Modals. | George |
| 2.0 | 04/11/2026 | Integrated Everyday Words, Zero-Crop Image Rule, and Mega-Bar Navigation. | George |
| 2.1 | 04/11/2026 | Added mandatory cta-section structural wrapper for width synchronization. | George |
| 2.2 | 04/11/2026 | Codified the 28% Logo Merge Animation standard and prompt. | George |
| 3.0 | 04/16/2026 | Added SigmaFidelity Institutional Form System and Professional Polish Standard. | George |
| 3.1 | 04/19/2026 | Implemented Phase 3 Enterprise Hardening, High-Velocity Entry Points, and SigmaFidelity™ Decision Modal. | George |
| 4.0 | 04/20/2026 | Salesforce-Tier 3-Column Hardening, Phase 3 Weight Hierarchy, and Total Parity Grid System. | George |
| 5.0 | 07/20/2026 | Codified Phase 4 Typographic weight hierarchy, outer label standards, and split grid unification rules. | George |


## 9. Salesforce-Tier 3-Column Standard (2026)
To achieve maximum Information Velocity, all complex record modals (Leads/Accounts) must utilize the 3-column procurement matrix.
- **Organization**:
    - **Column 1: Identity & Contact**: Name, Manager, Phone, Email, Website.
    - **Column 2: Geography & Logistics**: Building Address, SQF, Usage, Start Dates.
    - **Column 3: Business & Strategic**: Status, Value, Priority, Source, Fiscal Terms.
- **Benefit**: Liquidates vertical scroll friction by keeping all 34+ mission-critical fields "above the fold."

## 10. Institutional Typography Standard (Phase 4)
The system strictly enforces a weight-based hierarchy to ensure clinical data recognition.
- **900 (Black)**: Reserved for main Modal Titles and metric counters.
- **700 (Bold)**: Reserved for Section Headers and primary page headings.
- **600 (Semi-Bold)**: Standard for all primary Data Values and Table Cell content.
- **500 (Medium)**: Mandated for all Form Field Labels, Grid Headers, and secondary descriptions.
- **Typeface**: The global standard is **'Inter'**.

## 11. Linguistic Sync (Global Mandate)
All system components must comply with the "Everyday Words" mandate.
- **Liquidated Jargon**: Terms like "Decommission", "Institutional Acquisition", and "Strategic Metrics" are strictly prohibited in the UI.
- **Permitted Terms**: Use "Delete", "Lead Details", "Key Stats", and "Save Note".

## 12. Fiscal Alignment
For storage and repository standards regarding large media assets and build artifacts, see **HWB-QMS-11.1 Fiscal Storage and Repository Standards**.

## 14. Outer Label and Grid Stability Standard
To prevent layout misalignment and design clipping across modal tab transitions:
- **Label Position**: All field labels MUST reside outside and directly above the data value or entry box. Labels inside card borders are strictly prohibited.
- **Label Style**: Enforce Title Case (e.g., "Target Date") and a standard font-size of `0.85rem` or `0.8rem`.
- **Split Grid Unification**: All views using split column configurations must share a standardized layout width (e.g., `300px 1fr`) and a uniform gap of `2.5rem`. This ensures that field lines and labels align horizontally across tabs, eliminating layout shifts when users toggle views.
