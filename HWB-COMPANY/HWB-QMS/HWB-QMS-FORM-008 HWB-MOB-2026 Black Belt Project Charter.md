| **Document Control** | |
| :--- | :--- |
| **Document Title** | **HWB-MOB-2026 Black Belt Project Charter** |
| **Document ID** | HWB-QMS-FORM-008-BB-001 |
| **Version** | 1.0 |
| **Status** | Active / Define Phase |
| **Author** | George (Master Black Belt) |
| **Approved By** | Humberto Dominguez, CEO |
| **Date** | 2026-03-20 |

---

# S4/IEE Project Charter: **HWB-MOB-2026 Mobile Execution Engine**

| **Project Name:** | **HWB-MOB-2026 Mobile App** | **Project ID:** | BB-2026-001 |
| :--- | :--- | :--- | :--- |
| **Project Description:** | Development and deployment of a standalone mobile application for cleaning technicians to ensure 100% adherence to SigmaFidelity™ sanitation protocols (Scope of Work) and eliminate labor waste via real-time GPS-verified workflow management. |
| **Start Date:** | 2026-03-20 | **Target Completion:** | 2026-06-20 |

---

### 1.0 Metric Definition & Integrity
| **Base Metrics:** | Current labor waste estimated at 15% per contract; average technician response time to SOP updates: 48 hours. |
| :--- | :--- |
| **Primary Metrics:** | **KPOV:** Process Cycle Efficiency (PCE) of cleaning tasks; **Defect Rate:** Number of missed 'Scope of Work' items per audit. |
| **Secondary Metrics:** | **KPIVs:** App uptime, GPS check-in accuracy, time-to-completion per room type. |
| **Operational Def:** | A "Defect" is defined as any 'Scope of Work' item not marked as "Complete" and verified with a photo/timestamp within the allocated shift window. |
| **Error Proofing:** | **Poka-Yoke:** The app will lock sequential tasks; technicians cannot "Clock Out" until all Critical-to-Quality (CTQ) sanitation steps are photo-verified. |

---

### 2.0 Strategic Benefits & Financials
| **Customer Benefit:** | 100% transparent, audit-ready sanitation reports delivered in real-time to facility managers. |
| :--- | :--- |
| **Financial Benefit:** | Projected 15% reduction in COPQ (Cost of Poor Quality) and 10% increase in labor utilization efficiency. |
| **Annualized $:** | Estimated $45,000 - $60,000 in recovered payroll waste across initial 10 pilot accounts. |
| **Internal Productivity:** | Recovery of 5 hours/week per supervisor previously spent on manual site audits and paper-log verification. |

---

### 3.0 S4/IEE Execution & Statistical Verification
| **Milestone** | **Target Date** | **Deliverable / Statistical Proof** |
| :--- | :--- | :--- |
| **Define** | 2026-03-25 | VOC (Voice of Customer) analysis and High-Level SIPOC. |
| **Measure** | 2026-04-10 | Baseline 30k-foot chart of labor efficiency vs. budget. |
| **Analyze** | 2026-04-25 | ANOVA/Pareto analysis of task variance across different facility types. |
| **Design/Imp** | 2026-05-20 | Full React mobile app deployment; Beta testing with 3 crews. |
| **Verify/Cont** | 2026-06-20 | Final Cpk improvement calculation and hand-off to Operations. |

---

### 4.0 Governance & Readiness Checklist
| **Governance Question** | **Response / Status** |
| :--- | :--- |
| **Financial Alignment:** | YES - Validated by VP Finance (Maria Bolanos). |
| **Representativeness:** | Data will be pulled directly from SQLite 'WorkOrders' and 'ClientActivities'. |
| **MSA Status:** | MSA planned for GPS/Photo verification system in Measure phase. |
| **Improvements:** | Design verification will use Pilot vs. Control group performance. |
| **30k-Foot Chart:** | Planned for monthly executive review sessions. |
| **Communication:** | Weekly SigmaFidelity™ Pulse reports via PendingOutbox. |
| **Wisdom of Org:** | Technicians and Supervisors included in JAD (Joint Application Design) sessions. |
| **Database/Comm:** | `sigma_leads.db` and `clients.db` are primary sinks. |
| **Motivation:** | CEO-mandated priority; high alignment with "Payroll Mopping" strategy. |
| **Barriers/Schedule:** | Offline-first sync is the primary technical barrier (Mitigation: Service Workers). |

---

### 5.0 Resource Allocation
| **Team Support:** | Full access to Azure Cloud staging and SigmaFidelity™ datasets. |
| :--- | :--- |
| **Team Members:** | George (Systems Architect), Humberto Dominguez (Project Sponsor), Silas Sync (CRM/DB Integration). |

---

## 6.0 Approval & Sign-off
**CEO/Operations Director:** _________________________ **Date:** 2026-03-20

---

## 7.0 Revision History
| Version | Date | Author | Description |
| :--- | :--- | :--- | :--- |
| 1.0 | 2026-03-20 | George (MBB) | Initial Charter for Black Belt Certification track. |
