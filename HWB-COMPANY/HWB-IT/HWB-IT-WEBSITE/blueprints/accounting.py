"""
SigmaFidelity™ Finance & Accounting Department Blueprint (ARCH-017)
Standard: HWB-ACC-001 (General Ledger), HWB-ACC-002 (Accounts Receivable & Stripe), HWB-ACC-003 (Accounts Payable & 1099-NEC)
Custodians: Maria Bolanos (VP of Finance), George (Systems Architect) & Humberto Dominguez (CEO)
"""

import os
import csv
import io
import json
import hashlib
import secrets
import datetime
from typing import Any, Dict, List, Optional
from flask import (
    Blueprint,
    request,
    jsonify,
    render_template,
    Response,
    current_app,
    url_for,
    abort,
)
from flask_login import login_required, current_user

from core.security import roles_required
from core.services.database import get_db
from core.services.security_logger import log_security_event
from database.schema_engine import ensure_enterprise_accounting_schema
from core.services.stripe_billing_service import (
    dollars_to_cents,
    cents_to_dollars_str,
    calculate_stripe_fee_cents,
    calculate_invoice_totals,
    post_balanced_journal_entry,
    create_stripe_checkout_or_portal_link,
    verify_stripe_webhook_signature,
    generate_texas_statutory_lien_waiver_html,
    compute_financial_dashboard_and_reports,
)

accounting_bp = Blueprint("accounting", __name__)


def _require_accounting_permission(action: str = "view") -> bool:
    """Enforces strict RBAC for Finance & Accounting (CEO / Executive & VP of Finance / Admin)."""
    if not current_user.is_authenticated:
        return False
    if getattr(current_user, "role", "") in ("Executive", "Admin"):
        return True
    if hasattr(current_user, "has_permission") and current_user.has_permission("accounting", action):
        return True
    return False


def _get_accounting_db():
    """Returns a database connection and ensures the ARCH-017 schema is initialized."""
    conn = get_db(current_app.config["DATABASE_URL"])
    ensure_enterprise_accounting_schema(conn)
    return conn


# ==============================================================================
# 1. LIVE FINANCIAL OVERVIEW & DASHBOARD API
# ==============================================================================

@accounting_bp.route("/api/v1/accounting/overview", methods=["GET"])
@login_required
def api_accounting_overview():
    if not _require_accounting_permission("view"):
        return jsonify({"status": "error", "message": "Access restricted to Executive and Finance clearance."}), 403

    conn = _get_accounting_db()
    try:
        data = compute_financial_dashboard_and_reports(conn)
        return jsonify({"status": "success", "data": data})
    finally:
        conn.close()


# ==============================================================================
# 2. CLIENT INVOICES, STRIPE PAYMENT LINKS & TEXAS 8.25% SALES TAX ENGINE
# ==============================================================================

@accounting_bp.route("/api/v1/accounting/invoices", methods=["POST"])
@login_required
def api_create_invoice():
    if not _require_accounting_permission("edit"):
        return jsonify({"status": "error", "message": "Finance edit permission required."}), 403

    payload = request.get_json(silent=True) or {}
    client_name = str(payload.get("client_name") or "").strip()
    client_email = str(payload.get("client_email") or "").strip()
    facility_address = str(payload.get("facility_address") or "").strip()
    customer_id = payload.get("customer_id")
    construction_bid_id = payload.get("construction_bid_id")
    billing_mode = str(payload.get("billing_mode") or "Recurring Janitorial").strip()
    payment_terms = str(payload.get("payment_terms") or "Net 15").strip()
    is_tax_exempt = bool(payload.get("is_tax_exempt", False))
    tax_exempt_reason = str(payload.get("tax_exempt_reason") or "").strip()
    tax_exempt_cert_number = str(payload.get("tax_exempt_cert_number") or "").strip()
    preferred_payment_method = str(payload.get("preferred_payment_method") or "us_bank_account").strip()
    notes = str(payload.get("notes") or "").strip()

    # Default 10% retainage on Construction Progress Billing if not explicitly overridden
    if "retainage_pct" in payload and payload.get("retainage_pct") is not None:
        retainage_pct = float(payload.get("retainage_pct") or 0.0)
    else:
        retainage_pct = 10.0 if "Construction" in billing_mode else 0.0

    raw_lines = payload.get("line_items")
    if not raw_lines or not isinstance(raw_lines, list):
        # Support single-amount quick invoice form
        desc = str(payload.get("description") or f"{billing_mode} — Commercial Cleaning Services").strip()
        rev_acct = "4100" if "Construction" in billing_mode else ("4200" if "Floor" in billing_mode else "4000")
        raw_lines = [{
            "description": desc,
            "qty": float(payload.get("qty") or 1.0),
            "unit_price": payload.get("amount") or payload.get("subtotal") or 0,
            "unit_price_cents": payload.get("subtotal_cents"),
            "revenue_account_code": rev_acct,
        }]

    conn = _get_accounting_db()
    try:
        with conn.cursor() as cur:
            # Resolve customer details if customer_id provided
            if customer_id and not client_name:
                cur.execute(
                    'SELECT company_name, email, company_address, city, state, zip FROM "Customers" WHERE customer_id = %s;',
                    (int(customer_id),),
                )
                c_row = cur.fetchone()
                if c_row:
                    client_name = c_row["company_name"] or "Commercial Client"
                    client_email = client_email or (c_row["email"] or "")
                    if not facility_address:
                        parts = [c_row.get("company_address"), c_row.get("city"), c_row.get("state"), c_row.get("zip")]
                        facility_address = ", ".join([str(p) for p in parts if p])

            if not client_name:
                return jsonify({"status": "error", "message": "Client or company name is required."}), 400

            totals = calculate_invoice_totals(
                line_items=raw_lines,
                is_tax_exempt=is_tax_exempt,
                retainage_pct=retainage_pct,
            )
            if totals["subtotal_cents"] <= 0:
                return jsonify({"status": "error", "message": "Invoice subtotal must be greater than $0.00."}), 400

            cur.execute('SELECT COUNT(*) FROM "ClientInvoices";')
            cnt_row = cur.fetchone()
            inv_seq = (cnt_row["count"] if isinstance(cnt_row, dict) else cnt_row[0]) + 1001
            invoice_number = str(payload.get("invoice_number") or f"INV-{datetime.date.today().year}-{inv_seq}")
            payment_token = secrets.token_urlsafe(24)

            issue_date = payload.get("issue_date") or datetime.date.today().isoformat()
            days_net = 30 if "30" in payment_terms else (0 if "Receipt" in payment_terms else 15)
            due_date = payload.get("due_date") or (
                datetime.date.fromisoformat(str(issue_date)[:10]) + datetime.timedelta(days=days_net)
            ).isoformat()

            lien_waiver_status = (
                "Conditional Ready"
                if ("Construction" in billing_mode or totals["retainage_cents"] > 0)
                else "Not Applicable"
            )

            # Build Stripe / Hosted Portal Link
            inv_preview = {
                "invoice_number": invoice_number,
                "client_name": client_name,
                "client_email": client_email,
                "balance_due_cents": totals["current_due_cents"],
                "total_cents": totals["total_cents"],
                "payment_token": payment_token,
            }
            base_url = request.host_url.rstrip("/") if request.host_url else "https://www.hwbcleaning.com"
            stripe_id, checkout_url, stripe_mode = create_stripe_checkout_or_portal_link(inv_preview, base_url=base_url)

            # Post Balanced Accrual Double-Entry Journal Entry:
            # DR 1100 Accounts Receivable (current_due_cents)
            # DR 1150 Construction Retainage Receivable (retainage_cents, if > 0)
            # CR 4000/4100/4200 Revenue (subtotal_cents)
            # CR 2100 Texas Sales & Use Tax Payable (tax_cents, if > 0)
            rev_code = totals["line_items"][0].get("revenue_account_code") or (
                "4100" if "Construction" in billing_mode else "4000"
            )
            je_lines = [
                {
                    "account_code": "1100",
                    "debit_cents": totals["current_due_cents"],
                    "credit_cents": 0,
                    "customer_id": int(customer_id) if customer_id else None,
                    "construction_bid_id": int(construction_bid_id) if construction_bid_id else None,
                    "line_memo": f"AR Invoice {invoice_number} — {client_name}",
                },
                {
                    "account_code": rev_code,
                    "debit_cents": 0,
                    "credit_cents": totals["subtotal_cents"],
                    "customer_id": int(customer_id) if customer_id else None,
                    "construction_bid_id": int(construction_bid_id) if construction_bid_id else None,
                    "line_memo": f"Earned Revenue {invoice_number} — {client_name}",
                },
            ]
            if totals["retainage_cents"] > 0:
                je_lines.append({
                    "account_code": "1150",
                    "debit_cents": totals["retainage_cents"],
                    "credit_cents": 0,
                    "customer_id": int(customer_id) if customer_id else None,
                    "construction_bid_id": int(construction_bid_id) if construction_bid_id else None,
                    "line_memo": f"10% Construction Retainage Held — {invoice_number}",
                })
            if totals["tax_cents"] > 0:
                je_lines.append({
                    "account_code": "2100",
                    "debit_cents": 0,
                    "credit_cents": totals["tax_cents"],
                    "customer_id": int(customer_id) if customer_id else None,
                    "line_memo": f"Texas 8.25% Sales Tax Payable — {invoice_number}",
                })

            je_receipt = post_balanced_journal_entry(
                conn=conn,
                memo=f"Client Invoice {invoice_number} issued to {client_name} ({billing_mode})",
                lines=je_lines,
                source_module="Invoice",
                reference_code=invoice_number,
                entry_date=str(issue_date)[:10],
                created_by=getattr(current_user, "full_name", None) or getattr(current_user, "username", "Maria Bolanos"),
            )

            cur.execute("""
                INSERT INTO "ClientInvoices" (
                    invoice_number, customer_id, construction_bid_id,
                    client_name, client_email, facility_address,
                    billing_mode, payment_terms, issue_date, due_date,
                    line_items_json, subtotal_cents, is_tax_exempt,
                    tax_exempt_reason, tax_exempt_cert_number, tax_rate_pct,
                    tax_cents, retainage_pct, retainage_cents,
                    total_cents, amount_paid_cents, balance_due_cents,
                    preferred_payment_method, stripe_invoice_id, stripe_checkout_url,
                    payment_token, status, lien_waiver_status, notes,
                    journal_entry_id, created_by
                )
                VALUES (
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s,
                    %s::jsonb, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, 0, %s,
                    %s, %s, %s,
                    %s, 'Sent', %s, %s,
                    %s, %s
                )
                RETURNING id;
            """, (
                invoice_number,
                int(customer_id) if customer_id else None,
                int(construction_bid_id) if construction_bid_id else None,
                client_name,
                client_email,
                facility_address,
                billing_mode,
                payment_terms,
                str(issue_date)[:10],
                str(due_date)[:10],
                json.dumps(totals["line_items"]),
                totals["subtotal_cents"],
                totals["is_tax_exempt"],
                tax_exempt_reason,
                tax_exempt_cert_number,
                totals["tax_rate_pct"],
                totals["tax_cents"],
                totals["retainage_pct"],
                totals["retainage_cents"],
                totals["total_cents"],
                totals["current_due_cents"],
                preferred_payment_method,
                stripe_id,
                checkout_url,
                payment_token,
                lien_waiver_status,
                notes,
                je_receipt["journal_entry_id"],
                getattr(current_user, "full_name", None) or getattr(current_user, "username", "Maria Bolanos"),
            ))
            inv_id_row = cur.fetchone()
            invoice_id = inv_id_row["id"] if isinstance(inv_id_row, dict) else inv_id_row[0]

            # Link source_id on the journal entry
            cur.execute(
                'UPDATE "AccountingJournalEntries" SET source_id = %s WHERE id = %s;',
                (invoice_id, je_receipt["journal_entry_id"]),
            )
        conn.commit()

        log_security_event(
            event_category="ACCOUNTING",
            event_action="INVOICE_CREATED_AND_POSTED_TO_GL",
            severity="INFO",
            status_code=200,
            details={
                "invoice_id": invoice_id,
                "invoice_number": invoice_number,
                "client_name": client_name,
                "subtotal_cents": totals["subtotal_cents"],
                "tax_cents": totals["tax_cents"],
                "retainage_cents": totals["retainage_cents"],
                "balance_due_cents": totals["current_due_cents"],
                "journal_entry_number": je_receipt["entry_number"],
                "entry_sha256": je_receipt["entry_sha256"],
                "stripe_mode": stripe_mode,
            },
        )

        return jsonify({
            "status": "success",
            "message": f"Invoice {invoice_number} created and posted to Double-Entry General Ledger.",
            "invoice": {
                "id": invoice_id,
                "invoice_number": invoice_number,
                "client_name": client_name,
                "subtotal_cents": totals["subtotal_cents"],
                "tax_cents": totals["tax_cents"],
                "retainage_cents": totals["retainage_cents"],
                "total_cents": totals["total_cents"],
                "balance_due_cents": totals["current_due_cents"],
                "total_formatted": cents_to_dollars_str(totals["total_cents"]),
                "balance_due_formatted": cents_to_dollars_str(totals["current_due_cents"]),
                "ach_savings_formatted": cents_to_dollars_str(totals["ach_savings_cents"]),
                "payment_token": payment_token,
                "stripe_checkout_url": checkout_url,
                "lien_waiver_status": lien_waiver_status,
                "journal_entry": je_receipt,
            },
        })
    except Exception as exc:
        conn.rollback()
        return jsonify({"status": "error", "message": str(exc)}), 400
    finally:
        conn.close()


@accounting_bp.route("/api/v1/accounting/invoices/sync-from-contracts", methods=["POST"])
@login_required
def api_sync_invoices_from_active_contracts():
    """
    1-Click Automated Billing Cycle Generator:
    Reads verified active client contracts in "Customers" with annual_revenue > 0
    and generates current-month invoices with balanced Double-Entry GL entries.
    """
    if not _require_accounting_permission("edit"):
        return jsonify({"status": "error", "message": "Finance edit permission required."}), 403

    conn = _get_accounting_db()
    created_invoices = []
    try:
        today = datetime.date.today()
        month_tag = today.strftime("%Y-%m")
        base_url = request.host_url.rstrip("/") if request.host_url else "https://www.hwbcleaning.com"

        with conn.cursor() as cur:
            cur.execute("""
                SELECT customer_id, company_name, email, company_address, city, state, zip,
                       annual_revenue, facility_type, payment_terms
                FROM "Customers"
                WHERE COALESCE(annual_revenue, 0) > 0
                ORDER BY customer_id ASC;
            """)
            customers = [dict(r) for r in cur.fetchall()]

            for cust in customers:
                cid = cust["customer_id"]
                # Check if an invoice already exists for this customer in the current YYYY-MM cycle
                cur.execute("""
                    SELECT id FROM "ClientInvoices"
                    WHERE customer_id = %s
                      AND TO_CHAR(issue_date, 'YYYY-MM') = %s
                      AND status != 'Void'
                    LIMIT 1;
                """, (cid, month_tag))
                if cur.fetchone():
                    continue

                annual_rev = float(cust.get("annual_revenue") or 0.0)
                monthly_cents = int(round((annual_rev / 12.0) * 100))
                if monthly_cents <= 0:
                    continue

                cname = cust.get("company_name") or f"Client #{cid}"
                fac_type = (cust.get("facility_type") or "").lower()
                is_exempt = any(k in cname.lower() or k in fac_type for k in ("isd", "school", "city of", "municipal", "church", "tips"))
                totals = calculate_invoice_totals(
                    line_items=[{
                        "description": f"Monthly Commercial Janitorial Contract ({today.strftime('%B %Y')}) — {cname}",
                        "qty": 1,
                        "unit_price_cents": monthly_cents,
                        "revenue_account_code": "4000",
                    }],
                    is_tax_exempt=is_exempt,
                    retainage_pct=0.0,
                )

                cur.execute('SELECT COUNT(*) FROM "ClientInvoices";')
                cnt_r = cur.fetchone()
                seq = (cnt_r["count"] if isinstance(cnt_r, dict) else cnt_r[0]) + 1001
                inv_num = f"INV-{today.year}-{seq}"
                ptoken = secrets.token_urlsafe(24)
                due_dt = (today + datetime.timedelta(days=15)).isoformat()
                addr_parts = [cust.get("company_address"), cust.get("city"), cust.get("state"), cust.get("zip")]
                addr_str = ", ".join([str(p) for p in addr_parts if p])

                _, checkout_url, _ = create_stripe_checkout_or_portal_link(
                    {
                        "invoice_number": inv_num,
                        "client_name": cname,
                        "client_email": cust.get("email"),
                        "balance_due_cents": totals["current_due_cents"],
                        "total_cents": totals["total_cents"],
                        "payment_token": ptoken,
                    },
                    base_url=base_url,
                )

                je_lines = [
                    {
                        "account_code": "1100",
                        "debit_cents": totals["current_due_cents"],
                        "credit_cents": 0,
                        "customer_id": cid,
                        "line_memo": f"Monthly Contract Invoice {inv_num} — {cname}",
                    },
                    {
                        "account_code": "4000",
                        "debit_cents": 0,
                        "credit_cents": totals["subtotal_cents"],
                        "customer_id": cid,
                        "line_memo": f"Monthly Janitorial Revenue {inv_num} — {cname}",
                    },
                ]
                if totals["tax_cents"] > 0:
                    je_lines.append({
                        "account_code": "2100",
                        "debit_cents": 0,
                        "credit_cents": totals["tax_cents"],
                        "customer_id": cid,
                        "line_memo": f"Texas 8.25% Sales Tax — {inv_num}",
                    })

                je_res = post_balanced_journal_entry(
                    conn=conn,
                    memo=f"Automated Monthly Contract Billing {inv_num} — {cname}",
                    lines=je_lines,
                    source_module="Invoice",
                    reference_code=inv_num,
                    entry_date=today.isoformat(),
                )

                cur.execute("""
                    INSERT INTO "ClientInvoices" (
                        invoice_number, customer_id, client_name, client_email,
                        facility_address, billing_mode, payment_terms, issue_date, due_date,
                        line_items_json, subtotal_cents, is_tax_exempt, tax_exempt_reason,
                        tax_rate_pct, tax_cents, retainage_pct, retainage_cents,
                        total_cents, amount_paid_cents, balance_due_cents,
                        preferred_payment_method, stripe_checkout_url, payment_token,
                        status, lien_waiver_status, journal_entry_id, created_by
                    )
                    VALUES (
                        %s, %s, %s, %s,
                        %s, 'Recurring Janitorial', %s, %s, %s,
                        %s::jsonb, %s, %s, %s,
                        %s, %s, 0.00, 0,
                        %s, 0, %s,
                        'us_bank_account', %s, %s,
                        'Sent', 'Not Applicable', %s, 'Maria Bolanos'
                    )
                    RETURNING id;
                """, (
                    inv_num,
                    cid,
                    cname,
                    cust.get("email") or "",
                    addr_str,
                    cust.get("payment_terms") or "Net 15",
                    today.isoformat(),
                    due_dt,
                    json.dumps(totals["line_items"]),
                    totals["subtotal_cents"],
                    is_exempt,
                    "Public / Educational / Exempt Contract" if is_exempt else "",
                    totals["tax_rate_pct"],
                    totals["tax_cents"],
                    totals["total_cents"],
                    totals["current_due_cents"],
                    checkout_url,
                    ptoken,
                    je_res["journal_entry_id"],
                ))
                new_id_row = cur.fetchone()
                new_id = new_id_row["id"] if isinstance(new_id_row, dict) else new_id_row[0]
                created_invoices.append({"id": new_id, "invoice_number": inv_num, "client_name": cname})
        conn.commit()
        return jsonify({
            "status": "success",
            "created_count": len(created_invoices),
            "invoices": created_invoices,
            "message": f"Synchronized {len(created_invoices)} monthly contract invoice(s) into the General Ledger.",
        })
    except Exception as exc:
        conn.rollback()
        return jsonify({"status": "error", "message": str(exc)}), 400
    finally:
        conn.close()


def _execute_invoice_payment(
    conn: Any,
    invoice_id: int,
    payment_method: str = "us_bank_account",
    amount_cents: Optional[int] = None,
    actor_name: str = "Stripe Automated Settlement",
) -> Dict[str, Any]:
    """
    Internal atomic helper that settles a ClientInvoice, posts the balanced
    Cash + Stripe Fee vs. Accounts Receivable Journal Entry, and upgrades
    any Construction Lien Waiver to 'Unconditional Released'.
    """
    with conn.cursor() as cur:
        cur.execute('SELECT * FROM "ClientInvoices" WHERE id = %s FOR UPDATE;', (invoice_id,))
        inv = cur.fetchone()
        if not inv:
            raise ValueError(f"Invoice #{invoice_id} not found.")
        inv_dict = dict(inv)
        if inv_dict.get("status") == "Paid":
            return {
                "already_paid": True,
                "invoice_id": invoice_id,
                "invoice_number": inv_dict["invoice_number"],
                "lien_waiver_status": inv_dict.get("lien_waiver_status"),
            }

        bal_due = int(inv_dict.get("balance_due_cents") or 0)
        pay_cents = int(amount_cents) if (amount_cents is not None and int(amount_cents) > 0) else bal_due
        if pay_cents <= 0:
            raise ValueError("Invoice has no remaining balance due.")

        fee_cents = calculate_stripe_fee_cents(pay_cents, payment_method)
        net_cash_cents = max(0, pay_cents - fee_cents)

        je_lines = [
            {
                "account_code": "1000",
                "debit_cents": net_cash_cents,
                "credit_cents": 0,
                "customer_id": inv_dict.get("customer_id"),
                "construction_bid_id": inv_dict.get("construction_bid_id"),
                "line_memo": f"Net Deposit for Invoice {inv_dict['invoice_number']} ({payment_method})",
            },
            {
                "account_code": "1100",
                "debit_cents": 0,
                "credit_cents": pay_cents,
                "customer_id": inv_dict.get("customer_id"),
                "construction_bid_id": inv_dict.get("construction_bid_id"),
                "line_memo": f"AR Settlement for Invoice {inv_dict['invoice_number']}",
            },
        ]
        if fee_cents > 0:
            je_lines.append({
                "account_code": "6100",
                "debit_cents": fee_cents,
                "credit_cents": 0,
                "customer_id": inv_dict.get("customer_id"),
                "line_memo": f"Stripe Merchant Processing Fee ({payment_method}) — {inv_dict['invoice_number']}",
            })

        je_receipt = post_balanced_journal_entry(
            conn=conn,
            memo=f"Payment received for Invoice {inv_dict['invoice_number']} ({inv_dict['client_name']}) via {payment_method}",
            lines=je_lines,
            source_module="StripePayment",
            source_id=invoice_id,
            reference_code=inv_dict["invoice_number"],
            created_by=actor_name,
        )

        new_paid = int(inv_dict.get("amount_paid_cents") or 0) + pay_cents
        new_bal = max(0, bal_due - pay_cents)
        new_status = "Paid" if new_bal == 0 else "Partial"

        old_waiver = inv_dict.get("lien_waiver_status") or "Not Applicable"
        if new_status == "Paid" and (old_waiver != "Not Applicable" or "Construction" in (inv_dict.get("billing_mode") or "")):
            new_waiver = "Unconditional Released"
        else:
            new_waiver = old_waiver

        cur.execute("""
            UPDATE "ClientInvoices"
            SET amount_paid_cents = %s,
                balance_due_cents = %s,
                stripe_fee_cents = COALESCE(stripe_fee_cents, 0) + %s,
                preferred_payment_method = %s,
                status = %s,
                lien_waiver_status = %s,
                paid_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s;
        """, (
            new_paid,
            new_bal,
            fee_cents,
            payment_method,
            new_status,
            new_waiver,
            invoice_id,
        ))

    return {
        "already_paid": False,
        "invoice_id": invoice_id,
        "invoice_number": inv_dict["invoice_number"],
        "client_name": inv_dict["client_name"],
        "payment_cents": pay_cents,
        "stripe_fee_cents": fee_cents,
        "net_cash_cents": net_cash_cents,
        "status": new_status,
        "lien_waiver_status": new_waiver,
        "journal_entry": je_receipt,
    }


@accounting_bp.route("/api/v1/accounting/invoices/<int:invoice_id>/pay", methods=["POST"])
@login_required
def api_pay_invoice(invoice_id: int):
    if not _require_accounting_permission("edit"):
        return jsonify({"status": "error", "message": "Finance edit permission required."}), 403

    payload = request.get_json(silent=True) or {}
    payment_method = str(payload.get("payment_method") or "us_bank_account").strip()
    amount_cents = payload.get("amount_cents")
    if amount_cents is None and payload.get("amount"):
        amount_cents = dollars_to_cents(payload.get("amount"))

    conn = _get_accounting_db()
    try:
        res = _execute_invoice_payment(
            conn=conn,
            invoice_id=invoice_id,
            payment_method=payment_method,
            amount_cents=amount_cents,
            actor_name=getattr(current_user, "full_name", None) or getattr(current_user, "username", "Maria Bolanos"),
        )
        conn.commit()
        log_security_event(
            event_category="ACCOUNTING",
            event_action="INVOICE_PAYMENT_SETTLED",
            severity="INFO",
            status_code=200,
            details=res,
        )
        return jsonify({
            "status": "success",
            "message": f"Payment recorded for {res['invoice_number']} ({cents_to_dollars_str(res.get('payment_cents', 0))}).",
            "settlement": res,
        })
    except Exception as exc:
        conn.rollback()
        return jsonify({"status": "error", "message": str(exc)}), 400
    finally:
        conn.close()


@accounting_bp.route("/api/v1/accounting/invoices/<int:invoice_id>", methods=["DELETE"])
@login_required
def api_delete_or_void_invoice(invoice_id: int):
    """
    Enterprise Delete with 10-Second Undo Snapshot (BUG-160 Standard).
    Captures full invoice + journal entry snapshot into SystemSettings so it can be restored in 1 click.
    """
    if not _require_accounting_permission("delete"):
        return jsonify({"status": "error", "message": "Executive or Finance delete clearance required."}), 403

    conn = _get_accounting_db()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM "ClientInvoices" WHERE id = %s;', (invoice_id,))
            inv = cur.fetchone()
            if not inv:
                return jsonify({"status": "error", "message": "Invoice not found."}), 404
            inv_dict = dict(inv)
            je_id = inv_dict.get("journal_entry_id")

            je_dict = None
            je_lines = []
            if je_id:
                cur.execute('SELECT * FROM "AccountingJournalEntries" WHERE id = %s;', (je_id,))
                je_r = cur.fetchone()
                if je_r:
                    je_dict = dict(je_r)
                cur.execute('SELECT * FROM "AccountingJournalLines" WHERE journal_entry_id = %s;', (je_id,))
                je_lines = [dict(r) for r in cur.fetchall()]

            undo_token = f"undo_invoice_{invoice_id}_{secrets.token_hex(6)}"
            snapshot_payload = {
                "entity_type": "invoice",
                "tables": {
                    "ClientInvoices": [inv_dict],
                    "AccountingJournalEntries": [je_dict] if je_dict else [],
                    "AccountingJournalLines": je_lines,
                },
            }
            cur.execute("""
                INSERT INTO "SystemSettings" (key, value)
                VALUES (%s, %s)
                ON CONFLICT (key) DO UPDATE SET
                    value = EXCLUDED.value;
            """, (undo_token, json.dumps(snapshot_payload, default=str)))

            if je_id:
                cur.execute('DELETE FROM "AccountingJournalEntries" WHERE id = %s;', (je_id,))
            cur.execute('DELETE FROM "ClientInvoices" WHERE id = %s;', (invoice_id,))

        conn.commit()
        log_security_event(
            event_category="ACCOUNTING",
            event_action="INVOICE_DELETED_WITH_UNDO_SNAPSHOT",
            severity="WARNING",
            status_code=200,
            details={"invoice_id": invoice_id, "invoice_number": inv_dict.get("invoice_number"), "undo_token": undo_token},
        )
        return jsonify({
            "status": "success",
            "deleted_id": invoice_id,
            "invoice_number": inv_dict.get("invoice_number"),
            "undo_token": undo_token,
            "message": f"Invoice {inv_dict.get('invoice_number')} deleted.",
        })
    except Exception as exc:
        conn.rollback()
        return jsonify({"status": "error", "message": str(exc)}), 400
    finally:
        conn.close()


@accounting_bp.route("/api/v1/accounting/restore-deleted", methods=["POST"])
@login_required
def api_restore_deleted_accounting_record():
    """Restores a deleted ClientInvoice and its Double-Entry Journal Entry from its SystemSettings undo snapshot."""
    if not _require_accounting_permission("edit"):
        return jsonify({"status": "error", "message": "Finance edit permission required."}), 403

    payload = request.get_json(silent=True) or {}
    undo_token = str(payload.get("undo_token") or payload.get("restore_token") or "").strip()
    if not undo_token:
        return jsonify({"status": "error", "message": "Missing undo_token."}), 400

    conn = _get_accounting_db()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT value FROM "SystemSettings" WHERE key = %s LIMIT 1;', (undo_token,))
            row = cur.fetchone()
            if not row:
                return jsonify({"status": "error", "message": "Undo snapshot not found or already restored."}), 404
            raw_val = row["value"] if isinstance(row, dict) else row[0]
            snap = json.loads(raw_val) if isinstance(raw_val, str) else (raw_val or {})
            tables = snap.get("tables") or {}

            for tbl_name in ("AccountingJournalEntries", "AccountingJournalLines", "ClientInvoices"):
                rows = tables.get(tbl_name) or []
                for rec in rows:
                    if not isinstance(rec, dict) or not rec:
                        continue
                    cols = list(rec.keys())
                    col_sql = ", ".join(f'"{c}"' for c in cols)
                    placeholders = ", ".join(["%s"] * len(cols))
                    vals = [
                        json.dumps(rec[c]) if isinstance(rec[c], (dict, list)) else rec[c]
                        for c in cols
                    ]
                    cur.execute(
                        f'INSERT INTO "{tbl_name}" ({col_sql}) VALUES ({placeholders}) ON CONFLICT DO NOTHING;',
                        tuple(vals),
                    )
            cur.execute('DELETE FROM "SystemSettings" WHERE key = %s;', (undo_token,))
        conn.commit()
        return jsonify({"status": "success", "message": "Invoice and Double-Entry Journal Entry restored."})
    except Exception as exc:
        conn.rollback()
        return jsonify({"status": "error", "message": str(exc)}), 400
    finally:
        conn.close()


@accounting_bp.route("/api/v1/accounting/invoices/<int:invoice_id>/lien-waiver", methods=["GET"])
@login_required
def api_invoice_lien_waiver(invoice_id: int):
    if not _require_accounting_permission("view"):
        abort(403)
    waiver_type = request.args.get("type", "conditional")
    conn = _get_accounting_db()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM "ClientInvoices" WHERE id = %s;', (invoice_id,))
            row = cur.fetchone()
            if not row:
                abort(404)
            html_doc = generate_texas_statutory_lien_waiver_html(dict(row), waiver_type=waiver_type)
            return Response(html_doc, mimetype="text/html")
    finally:
        conn.close()


# ==============================================================================
# 3. PUBLIC CLIENT INVOICE & STRIPE PAYMENT PORTAL (/pay/invoice/<token>)
# ==============================================================================

@accounting_bp.route("/pay/invoice/<payment_token>", methods=["GET"])
def public_invoice_payment_portal(payment_token: str):
    """
    Client-facing Invoice & Online Payment Portal (ACH Bank Transfer & Credit Card).
    Zero internal process jargon (BUG-147 compliant) and 100% WCAG explicit labels (BUG-149 compliant).
    """
    conn = _get_accounting_db()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM "ClientInvoices" WHERE payment_token = %s LIMIT 1;', (payment_token,))
            row = cur.fetchone()
            if not row:
                abort(404)
            inv = dict(row)
            line_items = inv.get("line_items_json")
            if isinstance(line_items, str):
                try:
                    line_items = json.loads(line_items)
                except Exception:
                    line_items = []
            inv["line_items"] = line_items or []
            inv["subtotal_formatted"] = cents_to_dollars_str(inv.get("subtotal_cents"))
            inv["tax_formatted"] = cents_to_dollars_str(inv.get("tax_cents"))
            inv["retainage_formatted"] = cents_to_dollars_str(inv.get("retainage_cents"))
            inv["total_formatted"] = cents_to_dollars_str(inv.get("total_cents"))
            inv["balance_due_formatted"] = cents_to_dollars_str(inv.get("balance_due_cents"))
            inv["amount_paid_formatted"] = cents_to_dollars_str(inv.get("amount_paid_cents"))
            ach_fee = calculate_stripe_fee_cents(int(inv.get("balance_due_cents") or 0), "us_bank_account")
            card_fee = calculate_stripe_fee_cents(int(inv.get("balance_due_cents") or 0), "card")
            inv["ach_fee_formatted"] = cents_to_dollars_str(ach_fee)
            inv["card_fee_formatted"] = cents_to_dollars_str(card_fee)

            return render_template("public_invoice_pay.html", invoice=inv)
    finally:
        conn.close()


@accounting_bp.route("/pay/invoice/<payment_token>/complete", methods=["POST"])
def public_invoice_payment_complete(payment_token: str):
    """Processes online client invoice payment from the hosted payment portal."""
    payload = request.get_json(silent=True) or request.form.to_dict() or {}
    payment_method = str(payload.get("payment_method") or "us_bank_account").strip()
    payer_name = str(payload.get("payer_name") or "Authorized Client Payer").strip()
    authorized_consent = payload.get("ach_authorization_consent") in (True, "true", "1", "on", "yes")

    if not authorized_consent:
        return jsonify({
            "status": "error",
            "message": "Please check the payment authorization box before submitting payment.",
        }), 400

    conn = _get_accounting_db()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT id, invoice_number FROM "ClientInvoices" WHERE payment_token = %s LIMIT 1;', (payment_token,))
            row = cur.fetchone()
            if not row:
                return jsonify({"status": "error", "message": "Invoice not found."}), 404
            inv_id = row["id"] if isinstance(row, dict) else row[0]

        settlement = _execute_invoice_payment(
            conn=conn,
            invoice_id=inv_id,
            payment_method=payment_method,
            actor_name=f"Client Portal ({payer_name})",
        )
        conn.commit()
        log_security_event(
            event_category="ACCOUNTING",
            event_action="CLIENT_PORTAL_INVOICE_PAID",
            severity="INFO",
            status_code=200,
            details=settlement,
        )
        return jsonify({
            "status": "success",
            "message": f"Thank you! Payment for Invoice {settlement['invoice_number']} has been confirmed.",
            "settlement": settlement,
        })
    except Exception as exc:
        conn.rollback()
        return jsonify({"status": "error", "message": str(exc)}), 400
    finally:
        conn.close()


# ==============================================================================
# 4. SIGNED STRIPE WEBHOOK RECEIVER (/api/v1/webhooks/stripe)
# ==============================================================================

@accounting_bp.route("/api/v1/webhooks/stripe", methods=["POST"])
def stripe_webhook_receiver():
    """
    Signed Stripe Webhook Receiver (ARCH-017 Pillar 2).
    Verifies Stripe-Signature HMAC-SHA256 when STRIPE_WEBHOOK_SECRET is configured,
    settles the matching invoice, posts the balanced Double-Entry Journal Entry,
    and releases the Texas Unconditional Lien Waiver.
    """
    raw_body = request.get_data()
    sig_header = request.headers.get("Stripe-Signature", "")
    webhook_secret = (os.environ.get("STRIPE_WEBHOOK_SECRET") or "").strip()

    if webhook_secret:
        if not verify_stripe_webhook_signature(raw_body, sig_header, webhook_secret):
            log_security_event(
                event_category="SECURITY_VIOLATION",
                event_action="STRIPE_WEBHOOK_INVALID_SIGNATURE",
                severity="WARNING",
                status_code=400,
                details={"sig_header_present": bool(sig_header)},
            )
            return jsonify({"status": "error", "message": "Invalid Stripe webhook signature."}), 400

    event = request.get_json(silent=True) or {}
    event_type = str(event.get("type") or "")
    obj = (event.get("data") or {}).get("object") or {}
    metadata = obj.get("metadata") or {}

    if event_type in ("checkout.session.completed", "invoice.paid", "payment_intent.succeeded"):
        inv_num = metadata.get("invoice_number") or obj.get("invoice_number")
        pay_token = metadata.get("payment_token")
        pm_types = obj.get("payment_method_types") or ["us_bank_account"]
        pm = pm_types[0] if isinstance(pm_types, list) and pm_types else "us_bank_account"

        conn = _get_accounting_db()
        try:
            with conn.cursor() as cur:
                if pay_token:
                    cur.execute('SELECT id FROM "ClientInvoices" WHERE payment_token = %s LIMIT 1;', (pay_token,))
                elif inv_num:
                    cur.execute('SELECT id FROM "ClientInvoices" WHERE invoice_number = %s LIMIT 1;', (inv_num,))
                else:
                    cur.execute("SELECT NULL WHERE FALSE;")
                r = cur.fetchone()
                if r:
                    inv_id = r["id"] if isinstance(r, dict) else r[0]
                    settlement = _execute_invoice_payment(
                        conn=conn,
                        invoice_id=inv_id,
                        payment_method=pm,
                        actor_name=f"Stripe Webhook ({event_type})",
                    )
                    conn.commit()
                    log_security_event(
                        event_category="ACCOUNTING",
                        event_action="STRIPE_WEBHOOK_PAYMENT_SETTLED",
                        severity="INFO",
                        status_code=200,
                        details=settlement,
                    )
                    return jsonify({"status": "success", "event_type": event_type, "settlement": settlement})
        except Exception as exc:
            conn.rollback()
            return jsonify({"status": "error", "message": str(exc)}), 400
        finally:
            conn.close()

    return jsonify({"status": "received", "event_type": event_type})


# ==============================================================================
# 5. ACCOUNTS PAYABLE, 1099-NEC SUBCONTRACTOR BILLS & 3-WAY COMPLIANCE LOCK
# ==============================================================================

@accounting_bp.route("/api/v1/accounting/bills", methods=["POST"])
@login_required
def api_create_vendor_bill():
    if not _require_accounting_permission("edit"):
        return jsonify({"status": "error", "message": "Finance edit permission required."}), 403

    payload = request.get_json(silent=True) or {}
    subcontractor_id = payload.get("subcontractor_id")
    vendor_name = str(payload.get("vendor_name") or "").strip()
    vendor_email = str(payload.get("vendor_email") or "").strip()
    vendor_tax_classification = str(payload.get("vendor_tax_classification") or "1099-NEC Subcontractor").strip()
    job_site_name = str(payload.get("job_site_name") or "Commercial Cleaning Job Site").strip()
    expense_account_code = str(payload.get("expense_account_code") or "5100").strip()
    gross_cents = (
        int(payload["gross_amount_cents"])
        if payload.get("gross_amount_cents") is not None
        else dollars_to_cents(payload.get("gross_amount") or payload.get("amount") or 0)
    )
    retainage_cents = (
        int(payload["retainage_withheld_cents"])
        if payload.get("retainage_withheld_cents") is not None
        else dollars_to_cents(payload.get("retainage_withheld") or 0)
    )
    notes = str(payload.get("notes") or "").strip()

    if gross_cents <= 0:
        return jsonify({"status": "error", "message": "Bill amount must be greater than $0.00."}), 400

    net_payable_cents = max(0, gross_cents - retainage_cents)
    w9_verified = bool(payload.get("w9_verified", False))
    coi_verified = bool(payload.get("coi_verified", False))

    conn = _get_accounting_db()
    try:
        with conn.cursor() as cur:
            # Automatically check SubcontractorPartners compliance vault if subcontractor_id is linked
            if subcontractor_id:
                cur.execute('SELECT * FROM "SubcontractorPartners" WHERE id = %s;', (int(subcontractor_id),))
                sub_row = cur.fetchone()
                if sub_row:
                    vendor_name = vendor_name or (sub_row.get("company_name") or "1099 Subcontractor")
                    vendor_email = vendor_email or (sub_row.get("email") or "")
                    has_tax_id = bool(sub_row.get("ein_or_ssn") or sub_row.get("w9_tin_last4") or sub_row.get("w9_file_url"))
                    has_coi = bool(sub_row.get("coi_file_url") or (sub_row.get("coi_status") or "").lower() in ("active", "verified", "approved"))
                    w9_verified = w9_verified or has_tax_id
                    coi_verified = coi_verified or has_coi

            if not vendor_name:
                return jsonify({"status": "error", "message": "Vendor or subcontractor name is required."}), 400

            is_1099 = "1099" in vendor_tax_classification or expense_account_code == "5100"
            if is_1099 and (not w9_verified or not coi_verified):
                compliance_lock_status = "Hold: Missing W-9/COI"
                bill_status = "Compliance Hold"
            else:
                compliance_lock_status = "Cleared"
                bill_status = "Approved"

            cur.execute('SELECT COUNT(*) FROM "VendorBills";')
            cnt_r = cur.fetchone()
            b_seq = (cnt_r["count"] if isinstance(cnt_r, dict) else cnt_r[0]) + 2001
            bill_number = str(payload.get("bill_number") or f"BILL-{datetime.date.today().year}-{b_seq}")
            bill_date = payload.get("bill_date") or datetime.date.today().isoformat()
            due_date = payload.get("due_date") or (datetime.date.today() + datetime.timedelta(days=15)).isoformat()

            # Post Balanced AP Accrual Journal Entry:
            # DR 5100 (or Expense Account) = gross_cents
            # CR 2000 Accounts Payable = net_payable_cents
            # CR 2050 Subcontractor Retainage Payable = retainage_cents (if > 0)
            je_lines = [
                {
                    "account_code": expense_account_code,
                    "debit_cents": gross_cents,
                    "credit_cents": 0,
                    "subcontractor_id": int(subcontractor_id) if subcontractor_id else None,
                    "line_memo": f"Vendor Bill {bill_number} — {vendor_name} ({job_site_name})",
                },
                {
                    "account_code": "2000",
                    "debit_cents": 0,
                    "credit_cents": net_payable_cents,
                    "subcontractor_id": int(subcontractor_id) if subcontractor_id else None,
                    "line_memo": f"AP Liability {bill_number} — {vendor_name}",
                },
            ]
            if retainage_cents > 0:
                je_lines.append({
                    "account_code": "2050",
                    "debit_cents": 0,
                    "credit_cents": retainage_cents,
                    "subcontractor_id": int(subcontractor_id) if subcontractor_id else None,
                    "line_memo": f"Subcontractor Retainage Held — {bill_number}",
                })

            je_res = post_balanced_journal_entry(
                conn=conn,
                memo=f"Vendor Bill {bill_number} from {vendor_name} for {job_site_name}",
                lines=je_lines,
                source_module="VendorBill",
                reference_code=bill_number,
                entry_date=str(bill_date)[:10],
            )

            cur.execute("""
                INSERT INTO "VendorBills" (
                    bill_number, subcontractor_id, vendor_name, vendor_email,
                    vendor_tax_classification, job_site_name, expense_account_code,
                    bill_date, due_date, gross_amount_cents, retainage_withheld_cents,
                    net_payable_cents, w9_verified, coi_verified, compliance_lock_status,
                    is_1099_eligible, status, journal_entry_id, notes
                )
                VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s
                )
                RETURNING id;
            """, (
                bill_number,
                int(subcontractor_id) if subcontractor_id else None,
                vendor_name,
                vendor_email,
                vendor_tax_classification,
                job_site_name,
                expense_account_code,
                str(bill_date)[:10],
                str(due_date)[:10],
                gross_cents,
                retainage_cents,
                net_payable_cents,
                w9_verified,
                coi_verified,
                compliance_lock_status,
                is_1099,
                bill_status,
                je_res["journal_entry_id"],
                notes,
            ))
            b_row = cur.fetchone()
            bill_id = b_row["id"] if isinstance(b_row, dict) else b_row[0]
        conn.commit()
        return jsonify({
            "status": "success",
            "message": f"Vendor Bill {bill_number} logged ({bill_status}).",
            "bill": {
                "id": bill_id,
                "bill_number": bill_number,
                "vendor_name": vendor_name,
                "gross_amount_cents": gross_cents,
                "net_payable_cents": net_payable_cents,
                "compliance_lock_status": compliance_lock_status,
                "status": bill_status,
                "journal_entry": je_res,
            },
        })
    except Exception as exc:
        conn.rollback()
        return jsonify({"status": "error", "message": str(exc)}), 400
    finally:
        conn.close()


@accounting_bp.route("/api/v1/accounting/bills/<int:bill_id>/pay", methods=["POST"])
@login_required
def api_pay_vendor_bill(bill_id: int):
    """
    Releases payment for a VendorBill after verifying the 3-Way Subcontractor Compliance Lock
    (W-9 + Active COI). Posts DR 2000 Accounts Payable / CR 1000 Operating Checking Account.
    """
    if not _require_accounting_permission("edit"):
        return jsonify({"status": "error", "message": "Finance edit permission required."}), 403

    payload = request.get_json(silent=True) or {}
    ceo_override = bool(payload.get("ceo_override", False))
    payment_reference = str(payload.get("payment_reference") or f"ACH-OUT-{secrets.token_hex(3).upper()}").strip()

    conn = _get_accounting_db()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM "VendorBills" WHERE id = %s FOR UPDATE;', (bill_id,))
            b_row = cur.fetchone()
            if not b_row:
                return jsonify({"status": "error", "message": "Bill not found."}), 404
            bill = dict(b_row)
            if bill.get("status") == "Paid":
                return jsonify({"status": "error", "message": "Bill is already paid."}), 400

            if bill.get("compliance_lock_status") != "Cleared" and not ceo_override:
                return jsonify({
                    "status": "error",
                    "compliance_blocked": True,
                    "message": (
                        f"3-Way Compliance Lock Active: {bill.get('vendor_name')} is missing a verified "
                        f"W-9 or Certificate of Insurance (COI). Verify compliance documents first or authorize CEO override."
                    ),
                }), 409

            net_cents = int(bill.get("net_payable_cents") or 0)
            je_res = post_balanced_journal_entry(
                conn=conn,
                memo=f"Payout released for Bill {bill['bill_number']} to {bill['vendor_name']} ({payment_reference})",
                lines=[
                    {
                        "account_code": "2000",
                        "debit_cents": net_cents,
                        "credit_cents": 0,
                        "subcontractor_id": bill.get("subcontractor_id"),
                        "line_memo": f"AP Bill Settled — {bill['bill_number']}",
                    },
                    {
                        "account_code": "1000",
                        "debit_cents": 0,
                        "credit_cents": net_cents,
                        "subcontractor_id": bill.get("subcontractor_id"),
                        "line_memo": f"Operating Checking Payout ({payment_reference}) — {bill['vendor_name']}",
                    },
                ],
                source_module="VendorBill",
                source_id=bill_id,
                reference_code=bill["bill_number"],
            )

            cur.execute("""
                UPDATE "VendorBills"
                SET status = 'Paid',
                    compliance_lock_status = CASE WHEN %s THEN 'CEO Override' ELSE compliance_lock_status END,
                    paid_at = CURRENT_TIMESTAMP,
                    payment_reference = %s
                WHERE id = %s;
            """, (ceo_override, payment_reference, bill_id))
        conn.commit()
        return jsonify({
            "status": "success",
            "message": f"Bill {bill['bill_number']} paid ({cents_to_dollars_str(net_cents)}) and posted to General Ledger.",
            "journal_entry": je_res,
        })
    except Exception as exc:
        conn.rollback()
        return jsonify({"status": "error", "message": str(exc)}), 400
    finally:
        conn.close()


# ==============================================================================
# 6. EXPENSE & RECEIPT VAULT + PER-BUILDING JOB COSTING
# ==============================================================================

@accounting_bp.route("/api/v1/accounting/expenses", methods=["POST"])
@login_required
def api_create_expense_receipt():
    if not _require_accounting_permission("edit"):
        return jsonify({"status": "error", "message": "Finance edit permission required."}), 403

    payload = request.get_json(silent=True) or {}
    merchant_name = str(payload.get("merchant_name") or "").strip()
    category_account_code = str(payload.get("category_account_code") or "5200").strip()
    amount_cents = (
        int(payload["amount_cents"])
        if payload.get("amount_cents") is not None
        else dollars_to_cents(payload.get("amount") or 0)
    )
    job_site_name = str(payload.get("job_site_name") or "General Operations").strip()
    receipt_memo = str(payload.get("receipt_memo") or "").strip()
    payment_method = str(payload.get("payment_method") or "Company Checking / Debit").strip()
    expense_date = payload.get("expense_date") or datetime.date.today().isoformat()

    if not merchant_name or amount_cents <= 0:
        return jsonify({"status": "error", "message": "Merchant name and an amount greater than $0.00 are required."}), 400

    conn = _get_accounting_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT account_name FROM "AccountingChartOfAccounts" WHERE account_code = %s LIMIT 1;',
                (category_account_code,),
            )
            c_row = cur.fetchone()
            category_name = (c_row["account_name"] if isinstance(c_row, dict) else c_row[0]) if c_row else "Operating Expense"

            cur.execute('SELECT COUNT(*) FROM "ExpenseReceipts";')
            cnt_r = cur.fetchone()
            e_seq = (cnt_r["count"] if isinstance(cnt_r, dict) else cnt_r[0]) + 3001
            receipt_number = f"EXP-{datetime.date.today().year}-{e_seq}"

            je_res = post_balanced_journal_entry(
                conn=conn,
                memo=f"Expense Receipt {receipt_number} — {merchant_name} ({job_site_name})",
                lines=[
                    {
                        "account_code": category_account_code,
                        "debit_cents": amount_cents,
                        "credit_cents": 0,
                        "line_memo": f"{merchant_name} — {receipt_memo or category_name}",
                    },
                    {
                        "account_code": "1000",
                        "debit_cents": 0,
                        "credit_cents": amount_cents,
                        "line_memo": f"Paid via {payment_method} — {receipt_number}",
                    },
                ],
                source_module="ExpenseReceipt",
                reference_code=receipt_number,
                entry_date=str(expense_date)[:10],
            )

            receipt_sha256 = hashlib.sha256(
                f"{receipt_number}|{merchant_name}|{amount_cents}|{expense_date}".encode("utf-8")
            ).hexdigest()

            cur.execute("""
                INSERT INTO "ExpenseReceipts" (
                    receipt_number, expense_date, merchant_name,
                    category_account_code, category_name, amount_cents,
                    payment_method, job_site_name, receipt_memo,
                    receipt_sha256, journal_entry_id, created_by
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
            """, (
                receipt_number,
                str(expense_date)[:10],
                merchant_name,
                category_account_code,
                category_name,
                amount_cents,
                payment_method,
                job_site_name,
                receipt_memo,
                receipt_sha256,
                je_res["journal_entry_id"],
                getattr(current_user, "full_name", None) or getattr(current_user, "username", "Maria Bolanos"),
            ))
            ex_row = cur.fetchone()
            exp_id = ex_row["id"] if isinstance(ex_row, dict) else ex_row[0]
        conn.commit()
        return jsonify({
            "status": "success",
            "message": f"Expense {receipt_number} ({cents_to_dollars_str(amount_cents)}) recorded and posted to General Ledger.",
            "expense": {
                "id": exp_id,
                "receipt_number": receipt_number,
                "merchant_name": merchant_name,
                "amount_cents": amount_cents,
                "amount_formatted": cents_to_dollars_str(amount_cents),
                "journal_entry": je_res,
            },
        })
    except Exception as exc:
        conn.rollback()
        return jsonify({"status": "error", "message": str(exc)}), 400
    finally:
        conn.close()


# ==============================================================================
# 7. MANUAL DOUBLE-ENTRY JOURNAL ENTRY & QUICKBOOKS CSV IMPORT WIZARD
# ==============================================================================

@accounting_bp.route("/api/v1/accounting/journal-entries", methods=["POST"])
@login_required
def api_create_manual_journal_entry():
    if not _require_accounting_permission("edit"):
        return jsonify({"status": "error", "message": "Finance edit permission required."}), 403

    payload = request.get_json(silent=True) or {}
    memo = str(payload.get("memo") or "").strip()
    entry_date = payload.get("entry_date") or datetime.date.today().isoformat()
    raw_lines = payload.get("lines") or []

    if not memo:
        return jsonify({"status": "error", "message": "Journal entry memo is required."}), 400

    normalized_lines = []
    for l in raw_lines:
        deb = int(l["debit_cents"]) if l.get("debit_cents") is not None else dollars_to_cents(l.get("debit", 0))
        cred = int(l["credit_cents"]) if l.get("credit_cents") is not None else dollars_to_cents(l.get("credit", 0))
        if deb > 0 or cred > 0:
            normalized_lines.append({
                "account_code": str(l.get("account_code") or "1000").strip(),
                "debit_cents": deb,
                "credit_cents": cred,
                "line_memo": str(l.get("line_memo") or memo),
            })

    conn = _get_accounting_db()
    try:
        je_res = post_balanced_journal_entry(
            conn=conn,
            memo=memo,
            lines=normalized_lines,
            source_module="Manual",
            entry_date=str(entry_date)[:10],
            created_by=getattr(current_user, "full_name", None) or getattr(current_user, "username", "Maria Bolanos"),
        )
        conn.commit()
        return jsonify({
            "status": "success",
            "message": f"Balanced Journal Entry {je_res['entry_number']} posted.",
            "journal_entry": je_res,
        })
    except Exception as exc:
        conn.rollback()
        return jsonify({"status": "error", "message": str(exc)}), 400
    finally:
        conn.close()


@accounting_bp.route("/api/v1/accounting/import-qbo-csv", methods=["POST"])
@login_required
def api_import_quickbooks_csv():
    """
    1-Click QuickBooks Online (QBO) Exit & Historical CSV Import Wizard (ARCH-017 Pillar 6).
    Accepts either a multipart CSV file upload or JSON {'csv_text': ..., 'import_type': ...},
    archives a copy in HWB-COMPANY/HWB-ACCOUNTING/, and imports rows into PostgreSQL 16.15.
    """
    if not _require_accounting_permission("edit"):
        return jsonify({"status": "error", "message": "Finance edit permission required."}), 403

    import_type = "transactions"
    csv_text = ""

    if "file" in request.files and request.files["file"].filename:
        f = request.files["file"]
        csv_text = f.read().decode("utf-8-sig", errors="replace")
        import_type = request.form.get("import_type", "transactions")
    else:
        payload = request.get_json(silent=True) or {}
        csv_text = str(payload.get("csv_text") or "").strip()
        import_type = str(payload.get("import_type") or "transactions").strip()

    if not csv_text:
        return jsonify({"status": "error", "message": "No QuickBooks CSV content provided."}), 400

    # Archive raw CSV inside HWB-COMPANY/HWB-ACCOUNTING/
    try:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
        acc_vault_dir = os.path.join(project_root, "HWB-COMPANY", "HWB-ACCOUNTING", "qbo_migrations")
        os.makedirs(acc_vault_dir, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%m-%d-%Y_%H%M%S")
        archive_path = os.path.join(acc_vault_dir, f"QBO_Import_{import_type}_{stamp}.csv")
        with open(archive_path, "w", encoding="utf-8") as af:
            af.write(csv_text)
    except Exception:
        archive_path = "HWB-COMPANY/HWB-ACCOUNTING/qbo_migrations"

    reader = csv.DictReader(io.StringIO(csv_text))
    imported_count = 0
    conn = _get_accounting_db()
    try:
        with conn.cursor() as cur:
            for row in reader:
                norm_row = {str(k or "").strip().lower(): str(v or "").strip() for k, v in row.items() if k}
                if not any(norm_row.values()):
                    continue

                if import_type == "chart_of_accounts" or ("account_code" in norm_row and "account_type" in norm_row):
                    code = norm_row.get("account_code") or norm_row.get("number") or norm_row.get("code") or f"9{imported_count + 100}"
                    name = norm_row.get("account_name") or norm_row.get("name") or norm_row.get("account") or f"Imported QBO Account {code}"
                    atype = norm_row.get("account_type") or norm_row.get("type") or "Expense"
                    nbal = "Credit" if atype in ("Liability", "Equity", "Revenue", "Income") else "Debit"
                    cur.execute("""
                        INSERT INTO "AccountingChartOfAccounts" (
                            account_code, account_name, account_type, normal_balance,
                            qbo_account_type, description, is_system_account, is_active
                        )
                        VALUES (%s, %s, %s, %s, %s, 'Imported from QuickBooks Online CSV', FALSE, TRUE)
                        ON CONFLICT (account_code) DO UPDATE SET
                            account_name = EXCLUDED.account_name;
                    """, (code[:20], name[:180], atype[:40], nbal, atype[:80]))
                    imported_count += 1
                else:
                    # Transaction / Expense / Revenue row import with balanced double-entry
                    desc = (
                        norm_row.get("description")
                        or norm_row.get("memo")
                        or norm_row.get("name")
                        or norm_row.get("client")
                        or norm_row.get("vendor")
                        or "QuickBooks Historical Entry"
                    )
                    amt_str = norm_row.get("amount") or norm_row.get("total") or norm_row.get("debit") or norm_row.get("credit") or "0"
                    amt_cents = abs(dollars_to_cents(amt_str))
                    if amt_cents <= 0:
                        continue
                    dt_raw = norm_row.get("date") or datetime.date.today().isoformat()
                    try:
                        if "/" in dt_raw:
                            parts = dt_raw.split("/")
                            dt_iso = f"{int(parts[2]):04d}-{int(parts[0]):02d}-{int(parts[1]):02d}"
                        else:
                            dt_iso = dt_raw[:10]
                    except Exception:
                        dt_iso = datetime.date.today().isoformat()

                    acct_code = norm_row.get("account_code") or ("4000" if "invoice" in import_type.lower() else "5200")
                    if acct_code.startswith("4"):
                        lines = [
                            {"account_code": "1000", "debit_cents": amt_cents, "credit_cents": 0, "line_memo": f"QBO Import: {desc}"},
                            {"account_code": acct_code, "debit_cents": 0, "credit_cents": amt_cents, "line_memo": f"QBO Import: {desc}"},
                        ]
                    else:
                        lines = [
                            {"account_code": acct_code, "debit_cents": amt_cents, "credit_cents": 0, "line_memo": f"QBO Import: {desc}"},
                            {"account_code": "3200", "debit_cents": 0, "credit_cents": amt_cents, "line_memo": f"QBO Opening Equity Offset: {desc}"},
                        ]
                    post_balanced_journal_entry(
                        conn=conn,
                        memo=f"QuickBooks CSV Migration: {desc}",
                        lines=lines,
                        source_module="QBOImport",
                        entry_date=dt_iso,
                    )
                    imported_count += 1

        conn.commit()
        log_security_event(
            event_category="ACCOUNTING",
            event_action="QUICKBOOKS_CSV_MIGRATION_IMPORTED",
            severity="INFO",
            status_code=200,
            details={"import_type": import_type, "imported_count": imported_count, "archive_path": archive_path},
        )
        return jsonify({
            "status": "success",
            "imported_count": imported_count,
            "archive_path": archive_path,
            "message": f"Successfully imported {imported_count} QuickBooks Online record(s) into PostgreSQL 16.15.",
        })
    except Exception as exc:
        conn.rollback()
        return jsonify({"status": "error", "message": str(exc)}), 400
    finally:
        conn.close()


# ==============================================================================
# 8. CPA FINANCIAL STATEMENT & TEXAS COMPTROLLER CSV EXPORTS
# ==============================================================================

@accounting_bp.route("/api/v1/accounting/export/<export_type>", methods=["GET"])
@login_required
def api_export_accounting_csv(export_type: str):
    if not _require_accounting_permission("view"):
        abort(403)

    conn = _get_accounting_db()
    try:
        report = compute_financial_dashboard_and_reports(conn)
        output = io.StringIO()
        writer = csv.writer(output)
        today_str = datetime.date.today().strftime("%m-%d-%Y")

        if export_type == "pnl":
            writer.writerow(["Account Code", "Account Name", "Category", "Net Balance (USD)", "Tax Line Mapping"])
            for r in report["pnl"]["revenue_lines"] + report["pnl"]["cogs_lines"] + report["pnl"]["expense_lines"]:
                writer.writerow([
                    r["account_code"],
                    r["account_name"],
                    r["account_type"],
                    r["net_balance_formatted"],
                    r.get("tax_line_mapping") or "",
                ])
            writer.writerow([])
            writer.writerow(["SUMMARY", "Total Revenue", "Revenue", cents_to_dollars_str(report["pnl"]["total_revenue_cents"]), ""])
            writer.writerow(["SUMMARY", "Total Cost of Goods Sold (COGS)", "COGS", cents_to_dollars_str(report["pnl"]["total_cogs_cents"]), ""])
            writer.writerow(["SUMMARY", "Gross Profit", "Gross Profit", cents_to_dollars_str(report["pnl"]["gross_profit_cents"]), f"{report['pnl']['gross_margin_pct']}%"])
            writer.writerow(["SUMMARY", "Total Operating Expenses", "Expense", cents_to_dollars_str(report["pnl"]["total_expenses_cents"]), ""])
            writer.writerow(["SUMMARY", "Net Operating Income", "Net Income", cents_to_dollars_str(report["pnl"]["net_income_cents"]), ""])
            filename = f"HWB_Profit_and_Loss_{today_str}.csv"

        elif export_type == "texas_sales_tax":
            tx = report["texas_tax_report"]
            writer.writerow(["Texas Comptroller Form 01-114 Line", "Description", "Amount (USD)"])
            writer.writerow(["Item 1", "Total Gross Sales (All Commercial Cleaning Invoices)", cents_to_dollars_str(tx["gross_sales_cents"])])
            writer.writerow(["Item 2", "Tax-Exempt Sales (Texas ISD / Municipal / TIPS / Resale)", cents_to_dollars_str(tx["exempt_sales_cents"])])
            writer.writerow(["Item 3", "Taxable Commercial Real Property Cleaning Sales", cents_to_dollars_str(tx["taxable_sales_cents"])])
            writer.writerow(["Item 4a", "Texas State Sales Tax Liability (6.25%)", cents_to_dollars_str(tx["state_tax_625_cents"])])
            writer.writerow(["Item 4b", "Local City/County/Transit Sales Tax Liability (2.00%)", cents_to_dollars_str(tx["local_tax_200_cents"])])
            writer.writerow(["Item 5", "Total Combined Texas Sales Tax Payable (8.25%)", cents_to_dollars_str(tx["total_tax_825_cents"])])
            filename = f"HWB_Texas_Form_01_114_Sales_Tax_{today_str}.csv"

        elif export_type == "1099_nec":
            writer.writerow(["Subcontractor Name", "W-9 Verified", "COI Verified", "Total Billed (USD)", "Total Paid (USD)", "IRS 1099-NEC Required ($600+)"])
            for sub in report["subcontractor_1099_report"]:
                writer.writerow([
                    sub["vendor_name"],
                    "YES" if sub["w9_verified"] else "NO",
                    "YES" if sub["coi_verified"] else "NO",
                    sub["total_billed_formatted"],
                    sub["total_paid_formatted"],
                    "YES — FILE 1099-NEC" if sub["requires_1099_nec"] else "Below $600 Threshold",
                ])
            filename = f"HWB_IRS_1099_NEC_Subcontractor_Summary_{today_str}.csv"

        else:
            writer.writerow(["Entry Number", "Date", "Module", "Reference", "Memo", "Total Debit (USD)", "Total Credit (USD)", "SHA-256 Audit Hash"])
            for je in report["journal_entries"]:
                writer.writerow([
                    je["entry_number"],
                    je["entry_date"],
                    je["source_module"],
                    je.get("reference_code") or "",
                    je["memo"],
                    cents_to_dollars_str(je["total_debit_cents"]),
                    cents_to_dollars_str(je["total_credit_cents"]),
                    je.get("entry_sha256") or "",
                ])
            filename = f"HWB_General_Ledger_Journal_{today_str}.csv"

        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    finally:
        conn.close()
