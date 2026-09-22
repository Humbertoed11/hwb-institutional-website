| **Document Control** | |
| :--- | :--- |
| **Document Title** | **HWB-MOB-2026 Data Collection Plan** |
| **Document ID** | HWB-QMS-BB-003 |
| **Version** | 1.0 |
| **Status** | Active / Measure Phase |
| **Author** | George (Master Black Belt) |
| **Approved By** | Humberto Dominguez, CEO |
| **Date** | 2026-03-20 |

---

# Data Collection Plan: **HWB-MOB-2026 Mobile Execution Engine**

## 1.0 Purpose
The purpose of this document is to define the methodology for collecting baseline (pre-intervention) data to establish the current Sigma level of cleaning operations and identify specific areas of "Payroll Mopping" waste.

## 2.0 Measurement Strategy
We will utilize a combination of legacy paper logs, CRM timestamps, and manual audits to benchmark the current process performance.

### 2.1 Key Performance Indicators (KPIs)
| **Metric Name** | **Type** | **Operational Definition** | **Data Source** |
| :--- | :--- | :--- | :--- |
| **Cycle Time (CT)** | KPOV | Total time from technician arrival to site departure. | CRM Clock-in/Out Logs |
| **Defect Rate (DR)** | KPOV | Number of missed tasks found during a 20-point supervisor audit. | Manual Audit Forms |
| **Labor Utilization %** | KPIV | (Actual cleaning hours / Paid payroll hours) * 100. | QuickBooks vs. CRM |
| **Sync Latency** | KPIV | Time elapsed between task completion and visibility in CRM. | Technician Self-Report |

## 3.0 Sampling Plan
To ensure statistical significance (95% Confidence Level), the following sampling strategy will be employed:
*   **Sample Size:** Minimum 30 site visits across 5 different facility types (Daycare, Office, Medical, Industrial, Construction).
*   **Timeframe:** 14 consecutive days of legacy process tracking.
*   **Method:** Random selection of technicians and shifts to avoid bias.

## 4.0 Measurement System Analysis (MSA)
Before finalizing the baseline, we must verify the integrity of our data collection system:
1.  **Gage R&R (Attributes):** Two supervisors will audit the same 5 sites independently to ensure consistency in "Defect" identification.
2.  **Accuracy Check:** Compare CRM timestamps against physical security logs (where available) to verify clock-in accuracy.

## 5.0 Data Collection Template
Technicians and Supervisors will utilize the following data points during the 14-day baseline period:
*   `site_id`: Facility being serviced.
*   `tech_id`: Assigned technician.
*   `scheduled_start`: Planned arrival time.
*   `actual_start`: Verified arrival time.
*   `actual_end`: Verified departure time.
*   `tasks_missed`: Count of SOW items not performed.
*   `photo_evidence_count`: Number of tasks documented via mobile photo.

---

## 6.0 Approval & Sign-off
**CEO/Operations Director:** _________________________ **Date:** 2026-03-20

---

## 7.0 Revision History
| Version | Date | Author | Description |
| :--- | :--- | :--- | :--- |
| 1.0 | 2026-03-20 | George (MBB) | Initial Data Collection Plan for Black Belt track. |
