| **Document Control** | |
| :--- | :--- |
| **Document Title** | **Strategic Analytical Hierarchy Process (AHP)** |
| **Document ID** | HWB-QMS-STRAT-007 |
| **Version** | 1.0 |
| **Status** | Approved |
| **Author** | LSS Black Belt / Decision Scientist |
| **Date** | 2026-02-21 |

---

# Strategic AHP: Vertical Prioritization

## 1.0 Hierarchy Tree
This diagram illustrates the decision levels for prioritizing SigmaFidelity™ project categories.

```mermaid
graph TD
    Goal((GOAL: <br/>Strategic Leadership)) --> C1[Criteria 1: ROI]
    Goal --> C2[Criteria 2: Risk Mitigation]
    Goal --> C3[Criteria 3: Regulation]
    Goal --> C4[Criteria 4: Market Reach]

    %% Vertical Links
    C1 --- V1[Warehouse/Logistics]
    C1 --- V2[Corporate Office]
    C1 --- V3[Childcare/Medical]

    C2 --- V1
    C2 --- V2
    C2 --- V3

    C3 --- V1
    C3 --- V2
    C3 --- V3

    C4 --- V1
    C4 --- V2
    C4 --- V3

    %% Styling
    style Goal fill:#e1f5fe,stroke:#01579b
    style V1 fill:#f3e5f5,stroke:#4a148c
    style V2 fill:#f3e5f5,stroke:#4a148c
    style V3 fill:#f3e5f5,stroke:#4a148c
```

---

## 2.0 Pair-wise Comparison & Priority Weights
The following weights are assigned based on the **S4/IEE Value Chain**.

| Criteria | Weight | Logic |
| :--- | :--- | :--- |
| **ROI (Financial)** | **0.40** | High-volume contracts drive the operating margin. |
| **Risk Mitigation (CODND)** | **0.30** | Solving "Payroll Mopping" creates the strongest sales hook. |
| **Regulatory Compliance** | **0.20** | Texas Admin Code §746.1203 provides "Checkmate" leverage. |
| **Market Reach** | **0.10** | Broad visibility supports the 1M impression goal. |

---

## 3.0 Final Priority Ranking (Prioritization Matrix Inputs)
Based on the AHP weights, our service categories are ranked as follows:

1.  **WAREHOUSE & LOGISTICS (0.45 Score):** Highest ROI and High-Fidelity requirements.
2.  **CHILDCARE / MEDICAL (0.35 Score):** Highest Regulatory leverage and Risk Mitigation.
3.  **CORPORATE OFFICE (0.20 Score):** Highest Visibility but lower specialized risk.

**Strategic Action:** Direct 45% of harvesting efforts to Warehouse leads and 35% to Childcare leads.

---

## 4.0 Revision History
| Version | Date | Author | Description |
| :--- | :--- | :--- | :--- |
| 1.0 | 2026-02-21 | Gemini | Initial Release of SigmaFidelity™ AHP Model. |
