"""
SigmaFidelity™ Enterprise Double-Entry Accounting, QuickBooks Replacement & Stripe Billing Engine
Standard: ARCH-017 / HWB-ACC-001, HWB-ACC-002, HWB-ACC-003
Custodians: Maria Bolanos (VP of Finance), George (Systems Architect) & Humberto Dominguez (CEO)
"""

import os
import csv
import io
import hmac
import json
import hashlib
import secrets
import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple
import requests


TEXAS_SALES_TAX_RATE_PCT = Decimal("8.250")
TEXAS_STATE_TAX_PCT = Decimal("6.250")
TEXAS_LOCAL_TAX_PCT = Decimal("2.000")
STRIPE_ACH_FEE_PCT = Decimal("0.008")
STRIPE_ACH_CAP_CENTS = 500  # $5.00 max ACH fee
STRIPE_CARD_FEE_PCT = Decimal("0.029")
STRIPE_CARD_FIXED_CENTS = 30  # $0.30 fixed fee


def dollars_to_cents(value: Any) -> int:
    """Safely converts a dollar amount (float, str, Decimal) into integer cents."""
    if value is None or str(value).strip() == "":
        return 0
    cleaned = str(value).replace("$", "").replace(",", "").strip()
    try:
        dec = Decimal(cleaned).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return int(dec * 100)
    except Exception:
        return 0


def cents_to_dollars_str(cents: Any) -> str:
    """Formats integer cents as a standard USD currency string ($1,234.56)."""
    try:
        c = int(cents or 0)
    except Exception:
        c = 0
    sign = "-" if c < 0 else ""
    abs_c = abs(c)
    dollars = abs_c // 100
    rem = abs_c % 100
    return f"{sign}${dollars:,}.{rem:02d}"


def calculate_stripe_fee_cents(amount_cents: int, payment_method: str = "us_bank_account") -> int:
    """
    Calculates Stripe merchant processing fee in cents:
      - us_bank_account (ACH Direct Debit): 0.8% capped at $5.00 (500 cents)
      - card (Credit/Debit Card): 2.9% + $0.30 (30 cents)
      - check / wire / manual: 0 cents
    """
    if amount_cents <= 0:
        return 0
    method = (payment_method or "us_bank_account").lower().strip()
    if method in ("us_bank_account", "ach", "bank", "stripe_ach"):
        raw_fee = int((Decimal(amount_cents) * STRIPE_ACH_FEE_PCT).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        return min(raw_fee, STRIPE_ACH_CAP_CENTS)
    if method in ("card", "credit_card", "stripe_card"):
        pct_fee = int((Decimal(amount_cents) * STRIPE_CARD_FEE_PCT).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        return pct_fee + STRIPE_CARD_FIXED_CENTS
    return 0


def calculate_invoice_totals(
    line_items: List[Dict[str, Any]],
    is_tax_exempt: bool = False,
    retainage_pct: float = 0.0,
    tax_rate_pct: float = 8.25,
) -> Dict[str, Any]:
    """
    Calculates subtotal, Texas 8.25% sales tax (unless tax-exempt), construction retainage,
    total invoice amount, current net balance due, and ACH vs. Card fee comparison.
    """
    normalized_lines = []
    subtotal_cents = 0

    for idx, item in enumerate(line_items or []):
        desc = str(item.get("description") or f"Commercial Cleaning Service Line #{idx + 1}").strip()
        try:
            qty = float(item.get("qty") if item.get("qty") is not None else 1.0)
        except Exception:
            qty = 1.0
        if "unit_price_cents" in item and item.get("unit_price_cents") is not None:
            unit_cents = int(item.get("unit_price_cents") or 0)
        else:
            unit_cents = dollars_to_cents(item.get("unit_price", 0))
        line_total_cents = int(
            (Decimal(str(qty)) * Decimal(unit_cents)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        )
        rev_code = str(item.get("revenue_account_code") or "4000").strip()
        normalized_lines.append({
            "description": desc,
            "qty": qty,
            "unit_price_cents": unit_cents,
            "line_total_cents": line_total_cents,
            "revenue_account_code": rev_code,
        })
        subtotal_cents += line_total_cents

    eff_tax_rate = Decimal("0.000") if is_tax_exempt else Decimal(str(tax_rate_pct or 8.25))
    tax_cents = int(
        (Decimal(subtotal_cents) * (eff_tax_rate / Decimal("100"))).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    )
    total_cents = subtotal_cents + tax_cents

    eff_ret_pct = Decimal(str(max(0.0, min(float(retainage_pct or 0.0), 50.0))))
    # Retainage is withheld against contract work subtotal per AIA G702/G703 standard
    retainage_cents = int(
        (Decimal(subtotal_cents) * (eff_ret_pct / Decimal("100"))).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    )
    current_due_cents = max(0, total_cents - retainage_cents)

    ach_fee_cents = calculate_stripe_fee_cents(current_due_cents, "us_bank_account")
    card_fee_cents = calculate_stripe_fee_cents(current_due_cents, "card")

    return {
        "line_items": normalized_lines,
        "subtotal_cents": subtotal_cents,
        "is_tax_exempt": bool(is_tax_exempt),
        "tax_rate_pct": float(eff_tax_rate),
        "tax_cents": tax_cents,
        "retainage_pct": float(eff_ret_pct),
        "retainage_cents": retainage_cents,
        "total_cents": total_cents,
        "current_due_cents": current_due_cents,
        "ach_fee_cents": ach_fee_cents,
        "card_fee_cents": card_fee_cents,
        "ach_savings_cents": max(0, card_fee_cents - ach_fee_cents),
    }


def post_balanced_journal_entry(
    conn: Any,
    memo: str,
    lines: List[Dict[str, Any]],
    source_module: str = "Manual",
    source_id: Optional[int] = None,
    reference_code: Optional[str] = None,
    entry_date: Optional[str] = None,
    created_by: str = "Maria Bolanos (VP of Finance)",
) -> Dict[str, Any]:
    """
    Posts an immutable, balanced Double-Entry Journal Entry into PostgreSQL.
    Raises ValueError if total debits != total credits or if lines are empty.
    """
    if not lines or len(lines) < 2:
        raise ValueError("Double-entry journal entry requires at least one debit line and one credit line.")

    total_debit_cents = sum(int(l.get("debit_cents") or 0) for l in lines)
    total_credit_cents = sum(int(l.get("credit_cents") or 0) for l in lines)

    if total_debit_cents <= 0 or total_debit_cents != total_credit_cents:
        raise ValueError(
            f"Unbalanced journal entry rejected: Debits ({cents_to_dollars_str(total_debit_cents)}) "
            f"!= Credits ({cents_to_dollars_str(total_credit_cents)})."
        )

    dt_str = entry_date or datetime.date.today().isoformat()

    with conn.cursor() as cur:
        # Resolve account names from AccountingChartOfAccounts
        cur.execute('SELECT account_code, account_name FROM "AccountingChartOfAccounts";')
        coa_map = {row["account_code"] if isinstance(row, dict) else row[0]: (row["account_name"] if isinstance(row, dict) else row[1]) for row in cur.fetchall()}

        cur.execute('SELECT COUNT(*) FROM "AccountingJournalEntries";')
        cnt_row = cur.fetchone()
        seq_num = (cnt_row["count"] if isinstance(cnt_row, dict) else cnt_row[0]) + 1
        entry_number = f"JE-{datetime.date.today().year}-{seq_num:04d}-{secrets.token_hex(2).upper()}"

        canonical_payload = json.dumps({
            "entry_number": entry_number,
            "entry_date": dt_str,
            "source_module": source_module,
            "reference_code": reference_code or "",
            "total_debit_cents": total_debit_cents,
            "total_credit_cents": total_credit_cents,
            "lines": [
                {
                    "account_code": str(l.get("account_code")),
                    "debit_cents": int(l.get("debit_cents") or 0),
                    "credit_cents": int(l.get("credit_cents") or 0),
                }
                for l in lines
            ],
        }, sort_keys=True)
        entry_sha256 = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()

        cur.execute("""
            INSERT INTO "AccountingJournalEntries" (
                entry_number, entry_date, source_module, source_id,
                reference_code, memo, total_debit_cents, total_credit_cents,
                status, entry_sha256, created_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Posted', %s, %s)
            RETURNING id;
        """, (
            entry_number, dt_str, source_module, source_id,
            reference_code, memo, total_debit_cents, total_credit_cents,
            entry_sha256, created_by
        ))
        je_row = cur.fetchone()
        journal_entry_id = je_row["id"] if isinstance(je_row, dict) else je_row[0]

        for line in lines:
            acct_code = str(line.get("account_code") or "4000").strip()
            acct_name = line.get("account_name") or coa_map.get(acct_code) or f"Account {acct_code}"
            cur.execute("""
                INSERT INTO "AccountingJournalLines" (
                    journal_entry_id, account_code, account_name,
                    debit_cents, credit_cents, customer_id,
                    subcontractor_id, construction_bid_id, line_memo
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
            """, (
                journal_entry_id,
                acct_code,
                acct_name,
                int(line.get("debit_cents") or 0),
                int(line.get("credit_cents") or 0),
                line.get("customer_id"),
                line.get("subcontractor_id"),
                line.get("construction_bid_id"),
                line.get("line_memo") or memo,
            ))

    return {
        "journal_entry_id": journal_entry_id,
        "entry_number": entry_number,
        "total_debit_cents": total_debit_cents,
        "total_credit_cents": total_credit_cents,
        "entry_sha256": entry_sha256,
    }


def create_stripe_checkout_or_portal_link(
    invoice_row: Dict[str, Any],
    base_url: str = "https://www.hwbcleaning.com",
) -> Tuple[Optional[str], str, str]:
    """
    Creates a live Stripe Checkout Session (if STRIPE_SECRET_KEY is configured in .env)
    with ACH Direct Debit ('us_bank_account') prioritized first, and always returns a
    hosted HWB Invoice Payment Portal URL (/pay/invoice/<payment_token>).
    Returns: (stripe_session_id, checkout_url, mode_label)
    """
    payment_token = invoice_row.get("payment_token") or secrets.token_urlsafe(24)
    local_portal_url = f"{base_url.rstrip('/')}/pay/invoice/{payment_token}"
    stripe_secret = (os.environ.get("STRIPE_SECRET_KEY") or "").strip()

    if stripe_secret and stripe_secret.startswith(("sk_live_", "sk_test_")):
        try:
            due_cents = int(invoice_row.get("balance_due_cents") or invoice_row.get("total_cents") or 0)
            inv_num = invoice_row.get("invoice_number") or "INV"
            client_name = invoice_row.get("client_name") or "Commercial Client"
            resp = requests.post(
                "https://api.stripe.com/v1/checkout/sessions",
                auth=(stripe_secret, ""),
                data={
                    "mode": "payment",
                    "payment_method_types[0]": "us_bank_account",
                    "payment_method_types[1]": "card",
                    "customer_email": invoice_row.get("client_email") or None,
                    "line_items[0][price_data][currency]": "usd",
                    "line_items[0][price_data][unit_amount]": str(due_cents),
                    "line_items[0][price_data][product_data][name]": f"HWB Cleaning Invoice {inv_num} — {client_name}",
                    "line_items[0][quantity]": "1",
                    "metadata[invoice_number]": inv_num,
                    "metadata[payment_token]": payment_token,
                    "success_url": f"{local_portal_url}?paid=1",
                    "cancel_url": local_portal_url,
                },
                timeout=6,
            )
            if resp.status_code in (200, 201):
                s_data = resp.json()
                return (
                    s_data.get("id"),
                    s_data.get("url") or local_portal_url,
                    "STRIPE_LIVE_API",
                )
        except Exception:
            pass

    return (
        f"hwb_pay_{payment_token[:12]}",
        local_portal_url,
        "HWB_HOSTED_STRIPE_PORTAL",
    )


def verify_stripe_webhook_signature(payload_bytes: bytes, sig_header: str, webhook_secret: str) -> bool:
    """
    Verifies a Stripe-Signature header (t=<timestamp>,v1=<hmac_sha256>) using constant-time HMAC comparison.
    """
    if not sig_header or not webhook_secret:
        return False
    try:
        parts = {}
        for item in sig_header.split(","):
            if "=" in item:
                k, v = item.strip().split("=", 1)
                parts[k] = v
        timestamp = parts.get("t")
        v1_sig = parts.get("v1")
        if not timestamp or not v1_sig:
            return False
        signed_payload = f"{timestamp}.{payload_bytes.decode('utf-8')}".encode("utf-8")
        expected = hmac.new(
            webhook_secret.encode("utf-8"),
            signed_payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, v1_sig)
    except Exception:
        return False


def generate_texas_statutory_lien_waiver_html(
    invoice: Dict[str, Any],
    waiver_type: str = "conditional",
) -> str:
    """
    Generates a compliant State of Texas Statutory Lien Waiver & Release
    in accordance with Texas Property Code § 53.284.
    """
    is_unconditional = (waiver_type or "").lower().strip() == "unconditional" or invoice.get("status") == "Paid"
    inv_num = invoice.get("invoice_number") or "INV-2026"
    client_name = invoice.get("client_name") or "General Contractor / Owner"
    facility_address = invoice.get("facility_address") or "Dallas-Fort Worth Commercial Job Site, TX"
    amount_cents = int(
        (invoice.get("amount_paid_cents") if is_unconditional and int(invoice.get("amount_paid_cents") or 0) > 0 else invoice.get("balance_due_cents") or invoice.get("total_cents") or 0)
    )
    retainage_cents = int(invoice.get("retainage_cents") or 0)
    amount_str = cents_to_dollars_str(amount_cents)
    retainage_str = cents_to_dollars_str(retainage_cents)
    today_mdy = datetime.date.today().strftime("%m/%d/%Y")

    if is_unconditional:
        title = "UNCONDITIONAL WAIVER AND RELEASE ON PROGRESS PAYMENT"
        statute_notice = (
            "NOTICE: THIS DOCUMENT WAIVES RIGHTS UNCONDITIONALLY AND STATES THAT YOU HAVE BEEN PAID "
            "FOR GIVING UP THOSE RIGHTS. IT IS PROHIBITED FOR A PERSON TO REQUIRE YOU TO SIGN THIS "
            "DOCUMENT IF YOU HAVE NOT BEEN PAID THE PAYMENT AMOUNT SET FORTH BELOW. IF YOU HAVE NOT "
            "BEEN PAID, USE A CONDITIONAL RELEASE FORM."
        )
        body_clause = (
            f"The signer has been paid and has received a progress payment in the sum of "
            f"<strong>{amount_str}</strong> for all labor, services, equipment, or materials furnished "
            f"to the property or to <strong>{client_name}</strong> on the property of "
            f"<strong>{client_name}</strong> located at <strong>{facility_address}</strong>."
        )
        badge_color = "#065f46"
        badge_bg = "#ecfdf5"
        badge_label = "UNCONDITIONAL RELEASE (PAYMENT VERIFIED)"
    else:
        title = "CONDITIONAL WAIVER AND RELEASE ON PROGRESS PAYMENT"
        statute_notice = (
            "NOTICE: THIS DOCUMENT WAIVES THE CLAIMANT'S LIEN, STOP PAYMENT NOTICE, AND PAYMENT BOND "
            "RIGHTS EFFECTIVE ON RECEIPT OF PAYMENT. A PERSON SHOULD NOT RELY ON THIS DOCUMENT UNLESS "
            "SATISFIED THAT THE CLAIMANT HAS RECEIVED PAYMENT."
        )
        body_clause = (
            f"On receipt by the signer of this document of a check or electronic ACH/Stripe transfer from "
            f"<strong>{client_name}</strong> in the sum of <strong>{amount_str}</strong> payable to "
            f"<strong>HWB Cleaning Services LLC</strong> and when the payment has been properly endorsed "
            f"and settled by the financial institution on which it is drawn, this document becomes effective "
            f"to release any mechanic's lien right, any right arising from a payment bond, and any claim "
            f"for payment furnished to <strong>{facility_address}</strong>."
        )
        badge_color = "#92400e"
        badge_bg = "#fffbeb"
        badge_label = "CONDITIONAL WAIVER (EFFECTIVE UPON CLEARED PAYMENT)"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — {inv_num}</title>
<style>
  body {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; color: #0f172a; background: #f8fafc; margin: 0; padding: 2rem; }}
  .waiver-sheet {{ max-width: 820px; margin: 0 auto; background: #ffffff; border: 1px solid #cbd5e1; border-radius: 12px; padding: 2.5rem; box-shadow: 0 15px 35px rgba(15,23,42,0.08); }}
  .statute-box {{ background: #fef3c7; border: 2px solid #f59e0b; border-radius: 8px; padding: 1rem 1.25rem; font-weight: 800; font-size: 0.85rem; line-height: 1.5; color: #78350f; margin-bottom: 1.5rem; }}
  .grid-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem; padding: 1rem; background: #f8fafc; border-radius: 8px; border: 1px solid #e2e8f0; }}
  .label {{ font-size: 0.72rem; font-weight: 800; text-transform: uppercase; color: #64748b; letter-spacing: 0.05em; }}
  .val {{ font-size: 0.95rem; font-weight: 700; color: #0f172a; margin-top: 0.25rem; }}
  @media print {{ body {{ background: #fff; padding: 0; }} .no-print {{ display: none !important; }} .waiver-sheet {{ box-shadow: none; border: none; }} }}
</style>
</head>
<body>
<div class="waiver-sheet">
  <div class="no-print" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1.25rem;">
    <span style="background:{badge_bg}; color:{badge_color}; padding:0.35rem 0.75rem; border-radius:6px; font-size:0.75rem; font-weight:800;">{badge_label}</span>
    <button onclick="window.print()" style="background:#2563eb; color:#fff; border:none; border-radius:6px; padding:0.5rem 1rem; font-weight:800; cursor:pointer;">Print / Save as PDF</button>
  </div>
  <div class="statute-box">{statute_notice}</div>
  <h1 style="font-size:1.25rem; font-weight:900; text-align:center; margin:0 0 0.35rem 0;">{title}</h1>
  <p style="text-align:center; font-size:0.8rem; color:#475569; font-weight:700; margin:0 0 1.5rem 0;">State of Texas Statutory Form &bull; Texas Property Code &sect; 53.284</p>

  <div class="grid-row">
    <div><div class="label">Project / Job Site Location</div><div class="val">{facility_address}</div></div>
    <div><div class="label">Invoice Reference Number</div><div class="val">{inv_num}</div></div>
    <div><div class="label">General Contractor / Customer</div><div class="val">{client_name}</div></div>
    <div><div class="label">Claimant / Subcontractor</div><div class="val">HWB Cleaning Services LLC (FEIN: 82-4377459)</div></div>
    <div><div class="label">Progress Payment Amount</div><div class="val" style="color:#166534;">{amount_str}</div></div>
    <div><div class="label">Statutory Retainage Held (10%)</div><div class="val">{retainage_str}</div></div>
  </div>

  <p style="font-size:0.92rem; line-height:1.65; color:#1e293b;">{body_clause}</p>
  <p style="font-size:0.88rem; line-height:1.6; color:#334155;">
    This release covers a progress payment for all labor, services, equipment, or materials furnished to the job site through <strong>{today_mdy}</strong> only and does not cover any retention withheld ({retainage_str}), pending modifications and changes, or items furnished after that date.
  </p>

  <div style="margin-top:2rem; padding-top:1.5rem; border-top:2px solid #e2e8f0; display:grid; grid-template-columns:1fr 1fr; gap:2rem;">
    <div>
      <div class="label">Authorized Signer (Claimant)</div>
      <div style="font-family: Georgia, serif; font-size:1.25rem; font-style:italic; font-weight:700; color:#0f172a; margin-top:0.5rem;">Humberto Dominguez</div>
      <div style="font-size:0.82rem; font-weight:700; color:#475569;">CEO, HWB Cleaning Services LLC</div>
      <div style="font-size:0.78rem; color:#64748b;">P.O. Box 38465, Dallas, TX 75238 &bull; (214)-586-0257</div>
    </div>
    <div>
      <div class="label">Date Executed</div>
      <div class="val" style="margin-top:0.5rem;">{today_mdy}</div>
      <div class="label" style="margin-top:0.75rem;">Verification Status</div>
      <div style="font-size:0.8rem; font-weight:800; color:{badge_color}; margin-top:0.2rem;">{badge_label}</div>
    </div>
  </div>
</div>
</body>
</html>"""


def compute_financial_dashboard_and_reports(conn: Any) -> Dict[str, Any]:
    """
    Computes live Double-Entry General Ledger balances, Profit & Loss (P&L),
    Balance Sheet, Accounts Receivable Aging, Texas 8.25% Sales Tax Liability (Form 01-114),
    and 1099-NEC Subcontractor Payout totals directly from PostgreSQL 16.15.
    """
    result: Dict[str, Any] = {
        "kpis": {
            "total_billed_cents": 0,
            "collected_revenue_cents": 0,
            "open_ar_cents": 0,
            "overdue_ar_cents": 0,
            "retainage_held_cents": 0,
            "texas_sales_tax_payable_cents": 0,
            "open_ap_bills_cents": 0,
            "expenses_total_cents": 0,
            "net_operating_income_cents": 0,
            "stripe_ach_savings_cents": 0,
            "qbo_annual_subscription_saved_cents": 240000,  # $2,400/yr QuickBooks Plus/Advanced saved
        },
        "chart_of_accounts": [],
        "journal_entries": [],
        "invoices": [],
        "vendor_bills": [],
        "expense_receipts": [],
        "ar_aging": {
            "current_cents": 0,
            "days_1_30_cents": 0,
            "days_31_60_cents": 0,
            "days_61_90_cents": 0,
            "days_90_plus_cents": 0,
        },
        "pnl": {
            "revenue_lines": [],
            "cogs_lines": [],
            "expense_lines": [],
            "total_revenue_cents": 0,
            "total_cogs_cents": 0,
            "gross_profit_cents": 0,
            "gross_margin_pct": 0.0,
            "total_expenses_cents": 0,
            "net_income_cents": 0,
        },
        "texas_tax_report": {
            "gross_sales_cents": 0,
            "exempt_sales_cents": 0,
            "taxable_sales_cents": 0,
            "state_tax_625_cents": 0,
            "local_tax_200_cents": 0,
            "total_tax_825_cents": 0,
        },
        "subcontractor_1099_report": [],
    }

    today = datetime.date.today()

    with conn.cursor() as cur:
        # 1. Chart of Accounts with live Debit/Credit totals from AccountingJournalLines
        cur.execute("""
            SELECT
                coa.id,
                coa.account_code,
                coa.account_name,
                coa.account_type,
                coa.normal_balance,
                coa.tax_line_mapping,
                coa.qbo_account_type,
                coa.description,
                COALESCE(SUM(jl.debit_cents), 0) AS total_debit_cents,
                COALESCE(SUM(jl.credit_cents), 0) AS total_credit_cents
            FROM "AccountingChartOfAccounts" coa
            LEFT JOIN "AccountingJournalLines" jl ON jl.account_code = coa.account_code
            WHERE coa.is_active = TRUE
            GROUP BY coa.id, coa.account_code, coa.account_name, coa.account_type,
                     coa.normal_balance, coa.tax_line_mapping, coa.qbo_account_type, coa.description
            ORDER BY coa.account_code ASC;
        """)
        coa_rows = cur.fetchall()
        for r in coa_rows:
            d = dict(r)
            deb = int(d.get("total_debit_cents") or 0)
            cred = int(d.get("total_credit_cents") or 0)
            if (d.get("normal_balance") or "Debit").lower() == "debit":
                net_cents = deb - cred
            else:
                net_cents = cred - deb
            d["net_balance_cents"] = net_cents
            d["net_balance_formatted"] = cents_to_dollars_str(net_cents)
            result["chart_of_accounts"].append(d)

            acct_type = d.get("account_type")
            if acct_type == "Revenue":
                result["pnl"]["revenue_lines"].append(d)
                result["pnl"]["total_revenue_cents"] += net_cents
            elif acct_type == "COGS":
                result["pnl"]["cogs_lines"].append(d)
                result["pnl"]["total_cogs_cents"] += net_cents
            elif acct_type == "Expense":
                result["pnl"]["expense_lines"].append(d)
                result["pnl"]["total_expenses_cents"] += net_cents

        # 2. Recent Journal Entries with lines
        cur.execute("""
            SELECT * FROM "AccountingJournalEntries"
            ORDER BY entry_date DESC, id DESC
            LIMIT 100;
        """)
        je_rows = [dict(r) for r in cur.fetchall()]
        if je_rows:
            je_ids = [r["id"] for r in je_rows]
            cur.execute("""
                SELECT * FROM "AccountingJournalLines"
                WHERE journal_entry_id = ANY(%s)
                ORDER BY id ASC;
            """, (je_ids,))
            lines_by_je: Dict[int, List[Dict[str, Any]]] = {}
            for lr in cur.fetchall():
                ld = dict(lr)
                lines_by_je.setdefault(ld["journal_entry_id"], []).append(ld)
            for jr in je_rows:
                jr["lines"] = lines_by_je.get(jr["id"], [])
                jr["total_formatted"] = cents_to_dollars_str(jr.get("total_debit_cents") or 0)
        result["journal_entries"] = je_rows

        # 3. ClientInvoices
        cur.execute("""
            SELECT * FROM "ClientInvoices"
            ORDER BY issue_date DESC, id DESC
            LIMIT 200;
        """)
        inv_rows = [dict(r) for r in cur.fetchall()]
        for inv in inv_rows:
            sub_c = int(inv.get("subtotal_cents") or 0)
            tax_c = int(inv.get("tax_cents") or 0)
            tot_c = int(inv.get("total_cents") or 0)
            paid_c = int(inv.get("amount_paid_cents") or 0)
            bal_c = int(inv.get("balance_due_cents") or 0)
            ret_c = int(inv.get("retainage_cents") or 0)

            inv["subtotal_formatted"] = cents_to_dollars_str(sub_c)
            inv["tax_formatted"] = cents_to_dollars_str(tax_c)
            inv["total_formatted"] = cents_to_dollars_str(tot_c)
            inv["amount_paid_formatted"] = cents_to_dollars_str(paid_c)
            inv["balance_due_formatted"] = cents_to_dollars_str(bal_c)
            inv["retainage_formatted"] = cents_to_dollars_str(ret_c)

            if inv.get("status") != "Void":
                result["kpis"]["total_billed_cents"] += tot_c
                result["kpis"]["collected_revenue_cents"] += paid_c
                result["kpis"]["open_ar_cents"] += bal_c
                result["kpis"]["retainage_held_cents"] += ret_c
                result["kpis"]["texas_sales_tax_payable_cents"] += tax_c

                # Texas Comptroller Form 01-114 Sales Tax aggregation
                result["texas_tax_report"]["gross_sales_cents"] += sub_c
                if inv.get("is_tax_exempt"):
                    result["texas_tax_report"]["exempt_sales_cents"] += sub_c
                else:
                    result["texas_tax_report"]["taxable_sales_cents"] += sub_c
                    result["texas_tax_report"]["total_tax_825_cents"] += tax_c

                # Stripe ACH Fee Savings vs. Card
                ach_f = calculate_stripe_fee_cents(tot_c, "us_bank_account")
                card_f = calculate_stripe_fee_cents(tot_c, "card")
                result["kpis"]["stripe_ach_savings_cents"] += max(0, card_f - ach_f)

                # AR Aging buckets
                if bal_c > 0:
                    due_dt = inv.get("due_date")
                    if isinstance(due_dt, str):
                        try:
                            due_dt = datetime.date.fromisoformat(due_dt[:10])
                        except Exception:
                            due_dt = today
                    days_past = (today - due_dt).days if isinstance(due_dt, datetime.date) else 0
                    if days_past <= 0:
                        result["ar_aging"]["current_cents"] += bal_c
                    elif days_past <= 30:
                        result["ar_aging"]["days_1_30_cents"] += bal_c
                        result["kpis"]["overdue_ar_cents"] += bal_c
                    elif days_past <= 60:
                        result["ar_aging"]["days_31_60_cents"] += bal_c
                        result["kpis"]["overdue_ar_cents"] += bal_c
                    elif days_past <= 90:
                        result["ar_aging"]["days_61_90_cents"] += bal_c
                        result["kpis"]["overdue_ar_cents"] += bal_c
                    else:
                        result["ar_aging"]["days_90_plus_cents"] += bal_c
                        result["kpis"]["overdue_ar_cents"] += bal_c

        result["invoices"] = inv_rows

        # Compute State (6.25%) vs Local (2.00%) split of Texas sales tax
        tot_tax = result["texas_tax_report"]["total_tax_825_cents"]
        state_share = int((Decimal(tot_tax) * (TEXAS_STATE_TAX_PCT / TEXAS_SALES_TAX_RATE_PCT)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        result["texas_tax_report"]["state_tax_625_cents"] = state_share
        result["texas_tax_report"]["local_tax_200_cents"] = max(0, tot_tax - state_share)

        # 4. VendorBills & 1099-NEC Tracking
        cur.execute("""
            SELECT * FROM "VendorBills"
            ORDER BY bill_date DESC, id DESC
            LIMIT 200;
        """)
        bill_rows = [dict(r) for r in cur.fetchall()]
        sub_1099_totals: Dict[str, Dict[str, Any]] = {}
        for b in bill_rows:
            gross_c = int(b.get("gross_amount_cents") or 0)
            net_c = int(b.get("net_payable_cents") or 0)
            b["gross_formatted"] = cents_to_dollars_str(gross_c)
            b["net_payable_formatted"] = cents_to_dollars_str(net_c)
            if b.get("status") not in ("Paid", "Void"):
                result["kpis"]["open_ap_bills_cents"] += net_c

            if b.get("is_1099_eligible") and b.get("status") != "Void":
                v_name = b.get("vendor_name") or "Subcontractor"
                entry = sub_1099_totals.setdefault(v_name, {
                    "vendor_name": v_name,
                    "subcontractor_id": b.get("subcontractor_id"),
                    "w9_verified": bool(b.get("w9_verified")),
                    "coi_verified": bool(b.get("coi_verified")),
                    "total_billed_cents": 0,
                    "total_paid_cents": 0,
                })
                entry["total_billed_cents"] += gross_c
                if b.get("status") == "Paid":
                    entry["total_paid_cents"] += net_c
        result["vendor_bills"] = bill_rows

        for v_name, s_info in sub_1099_totals.items():
            paid_c = s_info["total_paid_cents"]
            billed_c = s_info["total_billed_cents"]
            effective_c = max(paid_c, billed_c)
            s_info["requires_1099_nec"] = effective_c >= 60000  # $600.00 IRS 1099-NEC threshold
            s_info["total_billed_formatted"] = cents_to_dollars_str(billed_c)
            s_info["total_paid_formatted"] = cents_to_dollars_str(paid_c)
            result["subcontractor_1099_report"].append(s_info)

        # 5. ExpenseReceipts
        cur.execute("""
            SELECT * FROM "ExpenseReceipts"
            ORDER BY expense_date DESC, id DESC
            LIMIT 200;
        """)
        exp_rows = [dict(r) for r in cur.fetchall()]
        for ex in exp_rows:
            amt_c = int(ex.get("amount_cents") or 0)
            ex["amount_formatted"] = cents_to_dollars_str(amt_c)
            result["kpis"]["expenses_total_cents"] += amt_c
        result["expense_receipts"] = exp_rows

        # Finalize P&L KPIs
        rev_total = result["pnl"]["total_revenue_cents"]
        cogs_total = result["pnl"]["total_cogs_cents"]
        exp_total = result["pnl"]["total_expenses_cents"]
        gross_profit = rev_total - cogs_total
        net_income = gross_profit - exp_total
        result["pnl"]["gross_profit_cents"] = gross_profit
        result["pnl"]["gross_margin_pct"] = round((gross_profit / rev_total) * 100.0, 1) if rev_total > 0 else 0.0
        result["pnl"]["net_income_cents"] = net_income
        result["kpis"]["net_operating_income_cents"] = net_income

    return result
