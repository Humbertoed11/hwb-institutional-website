/**
 * SigmaFidelity Finance & Accounting Department Engine (ARCH-017)
 * Standard: HWB-ACC-001, HWB-ACC-002, HWB-ACC-003
 * Custodians: Maria Bolanos (VP of Finance) & George (Systems Architect)
 */

function switchAccountingSubTab(subTab) {
    const panes = ['invoices', 'progress', 'bills', 'expenses', 'ledger', 'reports'];
    panes.forEach(p => {
        const el = document.getElementById('acc-pane-' + p);
        const btn = document.getElementById('acc-tab-btn-' + p);
        if (el) el.style.display = (p === subTab) ? 'block' : 'none';
        if (btn) {
            if (p === subTab) btn.classList.add('active');
            else btn.classList.remove('active');
        }
    });
}

// Auto-switch subtab if URL hash matches (#invoices, #progress, #bills, #expenses, #ledger, #reports)
document.addEventListener('DOMContentLoaded', function() {
    const hash = (window.location.hash || '').replace('#', '').trim().toLowerCase();
    if (['invoices', 'progress', 'bills', 'expenses', 'ledger', 'reports'].includes(hash)) {
        switchAccountingSubTab(hash);
    }
});

function openCreateInvoiceModal(defaultBillingMode) {
    const modeSel = document.getElementById('inv-billing-mode');
    const retInput = document.getElementById('inv-retainage-pct');
    if (defaultBillingMode && modeSel) {
        modeSel.value = defaultBillingMode;
        if (retInput) {
            retInput.value = defaultBillingMode.includes('Construction') ? '10' : '0';
        }
    }
    openModal('modal-create-invoice');
}

function onInvoiceCustomerSelect(sel) {
    if (!sel) return;
    const opt = sel.options[sel.selectedIndex];
    if (!opt || !opt.value) return;
    const nameEl = document.getElementById('inv-client-name');
    const emailEl = document.getElementById('inv-client-email');
    const addrEl = document.getElementById('inv-facility-address');
    if (nameEl && opt.dataset.name) nameEl.value = opt.dataset.name;
    if (emailEl && opt.dataset.email) emailEl.value = opt.dataset.email;
    if (addrEl && opt.dataset.address) addrEl.value = opt.dataset.address;
}

function onInvoiceBillingModeChange(sel) {
    const retInput = document.getElementById('inv-retainage-pct');
    const descInput = document.getElementById('inv-description');
    if (!sel) return;
    if (sel.value.includes('Construction')) {
        if (retInput) retInput.value = '10';
        if (descInput) descInput.value = 'Post-Construction Cleaning (Rough / Final / Fluff Turnover)';
    } else if (sel.value.includes('One-Time')) {
        if (retInput) retInput.value = '0';
        if (descInput) descInput.value = 'Commercial Floor Strip & Wax / Deep Sanitization';
    } else {
        if (retInput) retInput.value = '0';
        if (descInput) descInput.value = 'Monthly Commercial Janitorial Services';
    }
}

async function submitCreateInvoice(evt) {
    evt.preventDefault();
    const btn = document.getElementById('btn-save-invoice');
    if (window.spinAndLock && btn) window.spinAndLock(btn);

    const payload = {
        customer_id: document.getElementById('inv-customer-select')?.value || null,
        billing_mode: document.getElementById('inv-billing-mode')?.value || 'Recurring Janitorial',
        client_name: document.getElementById('inv-client-name')?.value || '',
        client_email: document.getElementById('inv-client-email')?.value || '',
        facility_address: document.getElementById('inv-facility-address')?.value || '',
        description: document.getElementById('inv-description')?.value || 'Commercial Cleaning Services',
        amount: document.getElementById('inv-amount')?.value || '0',
        retainage_pct: parseFloat(document.getElementById('inv-retainage-pct')?.value || '0'),
        is_tax_exempt: Boolean(document.getElementById('inv-tax-exempt')?.checked),
        tax_exempt_cert_number: document.getElementById('inv-tax-cert')?.value || ''
    };

    try {
        const res = await fetch('/api/v1/accounting/invoices', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.status === 'success') {
            closeModal('modal-create-invoice');
            showToast(data.message || 'Invoice created and posted to General Ledger.', 'success');
            setTimeout(() => window.location.reload(), 600);
        } else {
            showToast(data.message || 'Failed to create invoice.', 'error');
        }
    } catch (err) {
        showToast('Network error creating invoice.', 'error');
    } finally {
        if (window.restoreButton && btn) window.restoreButton(btn);
    }
}

async function syncMonthlyContractInvoices(btn) {
    if (window.spinAndLock && btn) window.spinAndLock(btn);
    try {
        const res = await fetch('/api/v1/accounting/invoices/sync-from-contracts', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'}
        });
        const data = await res.json();
        if (data.status === 'success') {
            showToast(data.message || 'Contract invoices synchronized.', 'success');
            setTimeout(() => window.location.reload(), 700);
        } else {
            showToast(data.message || 'Unable to sync contract invoices.', 'error');
        }
    } catch (err) {
        showToast('Network error syncing contract invoices.', 'error');
    } finally {
        if (window.restoreButton && btn) window.restoreButton(btn);
    }
}

function markInvoicePaid(invoiceId, invoiceNumber, paymentMethod, triggerBtn) {
    showDecision({
        title: `Record Payment for ${invoiceNumber}?`,
        text: `This will settle ${invoiceNumber} via Stripe ACH (${paymentMethod}), post a balanced Double-Entry Journal Entry, and release any Unconditional Texas Lien Waiver.`,
        confirmText: 'Confirm Payment',
        isDestructive: false,
        icon: 'fa-check-circle',
        onConfirm: async () => {
            if (window.spinAndLock && triggerBtn) window.spinAndLock(triggerBtn);
            try {
                const res = await fetch(`/api/v1/accounting/invoices/${invoiceId}/pay`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ payment_method: paymentMethod || 'us_bank_account' })
                });
                const data = await res.json();
                if (data.status === 'success') {
                    showToast(data.message || `Invoice ${invoiceNumber} marked Paid.`, 'success');
                    setTimeout(() => window.location.reload(), 600);
                } else {
                    showToast(data.message || 'Payment settlement failed.', 'error');
                }
            } finally {
                if (window.restoreButton && triggerBtn) window.restoreButton(triggerBtn);
            }
        }
    });
}

function deleteInvoiceRecord(invoiceId, invoiceNumber, triggerBtn) {
    showDecision({
        title: `Delete Invoice ${invoiceNumber}?`,
        text: `This will remove ${invoiceNumber} and its associated journal entry. A 10-second Undo snapshot will be available immediately after deletion.`,
        confirmText: 'Delete Invoice',
        isDestructive: true,
        icon: 'fa-trash-alt',
        onConfirm: async () => {
            if (window.spinAndLock && triggerBtn) window.spinAndLock(triggerBtn);
            try {
                const res = await fetch(`/api/v1/accounting/invoices/${invoiceId}`, { method: 'DELETE' });
                const data = await res.json();
                if (data.status === 'success') {
                    const row = document.getElementById(`invoice-row-${invoiceId}`);
                    if (row) row.remove();
                    showToast(
                        data.message || `Invoice ${invoiceNumber} deleted.`,
                        'info',
                        data.undo_token ? {
                            actionLabel: '↩ Undo Delete',
                            durationMs: 10000,
                            onAction: async () => {
                                const rUndo = await fetch('/api/v1/accounting/restore-deleted', {
                                    method: 'POST',
                                    headers: {'Content-Type': 'application/json'},
                                    body: JSON.stringify({ undo_token: data.undo_token })
                                });
                                const dUndo = await rUndo.json();
                                if (dUndo.status === 'success') {
                                    showToast(`Restored ${invoiceNumber}!`, 'success');
                                    setTimeout(() => window.location.reload(), 500);
                                }
                            }
                        } : null
                    );
                } else {
                    showToast(data.message || 'Failed to delete invoice.', 'error');
                }
            } finally {
                if (window.restoreButton && triggerBtn) window.restoreButton(triggerBtn);
            }
        }
    });
}

function openCreateBillModal() {
    openModal('modal-create-bill');
}

function onBillSubcontractorSelect(sel) {
    if (!sel) return;
    const opt = sel.options[sel.selectedIndex];
    if (!opt || !opt.value) return;
    const vName = document.getElementById('bill-vendor-name');
    if (vName && opt.dataset.name) vName.value = opt.dataset.name;
}

async function submitCreateVendorBill(evt) {
    evt.preventDefault();
    const payload = {
        subcontractor_id: document.getElementById('bill-sub-select')?.value || null,
        vendor_name: document.getElementById('bill-vendor-name')?.value || '',
        job_site_name: document.getElementById('bill-job-site')?.value || 'Commercial Cleaning Job Site',
        gross_amount: document.getElementById('bill-gross-amount')?.value || '0',
        w9_verified: Boolean(document.getElementById('bill-w9-verified')?.checked),
        coi_verified: Boolean(document.getElementById('bill-coi-verified')?.checked)
    };
    try {
        const res = await fetch('/api/v1/accounting/bills', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.status === 'success') {
            closeModal('modal-create-bill');
            showToast(data.message || 'Subcontractor bill logged.', 'success');
            setTimeout(() => {
                window.location.hash = '#bills';
                window.location.reload();
            }, 600);
        } else {
            showToast(data.message || 'Unable to log bill.', 'error');
        }
    } catch (err) {
        showToast('Network error logging bill.', 'error');
    }
}

function payVendorBill(billId, billNumber, complianceLockStatus, triggerBtn) {
    const isLocked = complianceLockStatus && complianceLockStatus !== 'Cleared' && complianceLockStatus !== 'CEO Override';
    showDecision({
        title: isLocked ? `Compliance Lock on ${billNumber}` : `Release Payout for ${billNumber}?`,
        text: isLocked
            ? `3-Way Compliance Lock is active (${complianceLockStatus}). Do you want to authorize a logged Executive Override to release payment now?`
            : `This will release payout for ${billNumber} and post DR 2000 Accounts Payable / CR 1000 Operating Checking.`,
        confirmText: isLocked ? 'Authorize CEO Override' : 'Release Payout',
        isDestructive: isLocked,
        icon: isLocked ? 'fa-shield-alt' : 'fa-paper-plane',
        onConfirm: async () => {
            if (window.spinAndLock && triggerBtn) window.spinAndLock(triggerBtn);
            try {
                const res = await fetch(`/api/v1/accounting/bills/${billId}/pay`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ ceo_override: isLocked })
                });
                const data = await res.json();
                if (data.status === 'success') {
                    showToast(data.message || 'Bill paid.', 'success');
                    setTimeout(() => {
                        window.location.hash = '#bills';
                        window.location.reload();
                    }, 600);
                } else {
                    showToast(data.message || 'Unable to release payout.', 'error');
                }
            } finally {
                if (window.restoreButton && triggerBtn) window.restoreButton(triggerBtn);
            }
        }
    });
}

function openCreateExpenseModal() {
    openModal('modal-create-expense');
}

async function submitCreateExpense(evt) {
    evt.preventDefault();
    const payload = {
        merchant_name: document.getElementById('exp-merchant-name')?.value || '',
        category_account_code: document.getElementById('exp-category-code')?.value || '5200',
        amount: document.getElementById('exp-amount')?.value || '0',
        job_site_name: document.getElementById('exp-job-site')?.value || 'General Operations',
        receipt_memo: document.getElementById('exp-memo')?.value || ''
    };
    try {
        const res = await fetch('/api/v1/accounting/expenses', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.status === 'success') {
            closeModal('modal-create-expense');
            showToast(data.message || 'Expense receipt saved.', 'success');
            setTimeout(() => {
                window.location.hash = '#expenses';
                window.location.reload();
            }, 600);
        } else {
            showToast(data.message || 'Failed to log expense.', 'error');
        }
    } catch (err) {
        showToast('Network error saving expense.', 'error');
    }
}

function openManualJournalModal() {
    openModal('modal-manual-journal');
}

async function submitManualJournalEntry(evt) {
    evt.preventDefault();
    const memo = document.getElementById('je-memo')?.value || '';
    const drAcct = document.getElementById('je-debit-account')?.value || '1000';
    const crAcct = document.getElementById('je-credit-account')?.value || '3000';
    const amt = document.getElementById('je-amount')?.value || '0';

    try {
        const res = await fetch('/api/v1/accounting/journal-entries', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                memo: memo,
                lines: [
                    { account_code: drAcct, debit: amt, credit: 0, line_memo: memo },
                    { account_code: crAcct, debit: 0, credit: amt, line_memo: memo }
                ]
            })
        });
        const data = await res.json();
        if (data.status === 'success') {
            closeModal('modal-manual-journal');
            showToast(data.message || 'Journal entry posted.', 'success');
            setTimeout(() => {
                window.location.hash = '#ledger';
                window.location.reload();
            }, 600);
        } else {
            showToast(data.message || 'Failed to post journal entry.', 'error');
        }
    } catch (err) {
        showToast('Network error posting journal entry.', 'error');
    }
}

async function submitQuickBooksCsvImport(evt) {
    evt.preventDefault();
    const importType = document.getElementById('qbo-import-type')?.value || 'transactions';
    const csvText = document.getElementById('qbo-csv-text')?.value || '';
    if (!csvText.trim()) {
        showToast('Please enter or paste QuickBooks CSV lines first.', 'error');
        return;
    }
    try {
        const res = await fetch('/api/v1/accounting/import-qbo-csv', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ import_type: importType, csv_text: csvText })
        });
        const data = await res.json();
        if (data.status === 'success') {
            showToast(data.message || 'QuickBooks CSV imported!', 'success');
            setTimeout(() => {
                window.location.hash = '#ledger';
                window.location.reload();
            }, 700);
        } else {
            showToast(data.message || 'QuickBooks CSV import failed.', 'error');
        }
    } catch (err) {
        showToast('Network error importing QuickBooks CSV.', 'error');
    }
}
