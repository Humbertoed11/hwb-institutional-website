"""
HWB Cleaning 24/7 Enterprise AI Employee Package (BUG-163)
==========================================================
Provides the 10-Standard Fortune 500 Autonomous AI Employee Runtime:
- Stateful Working Desk Memory ("AIEmployeeWorkingMemory")
- Permanent Standing Orders & Brand Playbooks ("AIEmployeeStandingOrders")
- Transactional Before/After Rollback Ledger ("AIEmployeeChangeLedger")
- Hard FinOps Circuit Breaker ($0.50/day, $15.00/month cap in "AIEmployeeBudgetLedger")
- 24/7 Heartbeat & Autonomous Shift Scheduler ("AIEmployeeHeartbeat")
- Schema-Aware Read-Only SQL Analyst & Deterministic Citation Firewall
"""

from .engine import HWBEnterpriseAIEmployee, get_ai_employee

__all__ = ["HWBEnterpriseAIEmployee", "get_ai_employee"]
