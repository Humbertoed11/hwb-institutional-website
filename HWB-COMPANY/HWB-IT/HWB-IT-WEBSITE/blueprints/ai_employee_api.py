"""
HWB Cleaning 24/7 Enterprise AI Employee Web & Webhook Blueprint (BUG-163)
==========================================================================
Exposes:
- GET  /api/v1/ai-employee/status
- POST /api/v1/ai-employee/directive
- POST /api/v1/ai-employee/changeset/<int:cs_id>/apply
- POST /api/v1/ai-employee/changeset/<int:cs_id>/rollback
- POST /api/v1/telegram/webhook
"""

from typing import Any, Tuple
from flask import Blueprint, jsonify, request
from flask_login import current_user

from core.ai_employee import get_ai_employee

ai_employee_bp = Blueprint("ai_employee_bp", __name__)


def _require_exec_auth() -> bool:
    return bool(getattr(current_user, "is_authenticated", False))


@ai_employee_bp.route("/api/v1/ai-employee/status", methods=["GET"])
def api_ai_employee_status() -> Tuple[Any, int]:
    """Returns 24/7 AI Employee heartbeat, FinOps budget status, and recent Change-Sets."""
    emp = get_ai_employee()
    allowed, budget = emp.check_finops_budget()
    hb = emp.record_heartbeat("hwb_web_command_hub")
    status_text, _ = emp.tool_employee_status_and_budget(8564340073)
    return (
        jsonify(
            {
                "status": "success",
                "employee_state": "ONLINE_24X7",
                "heartbeat": hb,
                "finops_budget": budget,
                "budget_allowed": allowed,
                "summary_report": status_text,
            }
        ),
        200,
    )


@ai_employee_bp.route("/api/v1/ai-employee/directive", methods=["POST"])
def api_ai_employee_directive() -> Tuple[Any, int]:
    """Executes an executive directive from the Web Command Hub or automated test suite."""
    if not _require_exec_auth():
        return jsonify({"status": "error", "message": "Authentication required"}), 401

    payload = request.get_json(silent=True) or {}
    text = str(payload.get("directive") or payload.get("text") or "").strip()
    chat_id = int(payload.get("chat_id") or 8564340073)
    if not text:
        return jsonify({"status": "error", "message": "Directive text is required"}), 400

    emp = get_ai_employee()
    handled, response_text, markup = emp.handle_executive_directive(text, chat_id)
    if not handled:
        # Fallback to status + SQL summary if general query
        response_text, markup = emp.tool_employee_status_and_budget(chat_id)
    safe_text = emp.apply_citation_firewall(response_text)
    return (
        jsonify(
            {
                "status": "success",
                "handled_deterministically": handled,
                "response": safe_text,
                "actions": markup,
            }
        ),
        200,
    )


@ai_employee_bp.route(
    "/api/v1/ai-employee/changeset/<int:cs_id>/apply", methods=["POST"]
)
def api_apply_changeset(cs_id: int) -> Tuple[Any, int]:
    """Applies a staged Change-Set from the Web Command Hub."""
    if not _require_exec_auth():
        return jsonify({"status": "error", "message": "Authentication required"}), 401
    emp = get_ai_employee()
    ok, msg, markup = emp.apply_changeset(cs_id, 8564340073)
    return (
        jsonify({"status": "success" if ok else "error", "message": msg, "actions": markup}),
        200 if ok else 400,
    )


@ai_employee_bp.route(
    "/api/v1/ai-employee/changeset/<int:cs_id>/rollback", methods=["POST"]
)
def api_rollback_changeset(cs_id: int) -> Tuple[Any, int]:
    """Rolls back an applied Change-Set restoring exact BEFORE values."""
    if not _require_exec_auth():
        return jsonify({"status": "error", "message": "Authentication required"}), 401
    emp = get_ai_employee()
    ok, msg, _ = emp.rollback_changeset(cs_id, 8564340073)
    return (
        jsonify({"status": "success" if ok else "error", "message": msg}),
        200 if ok else 400,
    )
