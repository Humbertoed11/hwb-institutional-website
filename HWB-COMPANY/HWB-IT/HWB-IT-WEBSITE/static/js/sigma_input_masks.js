/**
 * SigmaFidelity™ Enterprise Universal Input Masking & Validation Engine (BUG-142)
 * Standard: HWB-QMS-7.6 / Everyday Words & Zero-Error Data Entry Standard
 *
 * Provides deterministic, mobile-safe input formatting across all public and backoffice forms:
 *  1. Federal Tax ID (EIN: XX-XXXXXXX / SSN: XXX-XX-XXXX, adaptive to Tax Classification)
 *  2. Social Security Number (XXX-XX-XXXX, preserving encrypted vault masks ***-**-XXXX)
 *  3. North American Phone Number ((###)-###-####, stripping leading +1 autofill)
 *  4. US Postal ZIP / ZIP+4 (##### or #####-####)
 *  5. ABA Bank Routing Number (9 digits: #########)
 *  6. US 2-Letter State Code (Uppercase AA: TX)
 */
(function () {
    "use strict";

    function resolveInput(elOrEvent) {
        if (!elOrEvent) return null;
        if (elOrEvent.target && elOrEvent.target.tagName) return elOrEvent.target;
        if (elOrEvent.tagName) return elOrEvent;
        return null;
    }

    function isVaultMaskedValue(val) {
        if (!val) return false;
        return val.indexOf("*") !== -1 || val.indexOf("•") !== -1;
    }

    function detectTaxIdMode(inputEl, explicitTaxClassSelectId) {
        if (!inputEl) return "ein";
        const attrMode = (inputEl.getAttribute("data-tax-mode") || "").toLowerCase();
        if (attrMode === "ssn") return "ssn";
        if (attrMode === "ein") return "ein";

        const selectId =
            explicitTaxClassSelectId ||
            inputEl.getAttribute("data-tax-class-select") ||
            "onb-tax-class";
        const sel = document.getElementById(selectId);
        if (sel && sel.value) {
            const v = sel.value.toLowerCase();
            if (v.indexOf("individual") !== -1 || v.indexOf("sole") !== -1 || v.indexOf("ssn") !== -1) {
                return "ssn";
            }
            return "ein";
        }
        return "ein";
    }

    /**
     * Adaptive Federal Tax ID Mask:
     *  - Business Entities (LLC, S-Corp, C-Corp, Partnership): XX-XXXXXXX (maxlength 10)
     *  - Individual / Sole Proprietor: XXX-XX-XXXX (maxlength 11)
     *  - Preserves server-masked tokens (**-***0455 / ***-**-9012) until user edits
     */
    function maskTaxIdInput(elOrEvent, taxClassSelectId) {
        const input = resolveInput(elOrEvent);
        if (!input) return;

        const mode = detectTaxIdMode(input, taxClassSelectId);
        input.setAttribute("inputmode", "numeric");
        input.setAttribute("maxlength", mode === "ssn" ? "11" : "10");

        const raw = input.value || "";
        if (isVaultMaskedValue(raw)) {
            const digitsAfterMask = raw.replace(/[*•\-\s]/g, "");
            if (digitsAfterMask.length <= 4) {
                return;
            }
        }

        let digits = raw.replace(/\D/g, "").slice(0, 9);
        if (!digits) {
            input.value = "";
            return;
        }

        if (mode === "ssn") {
            if (digits.length <= 3) {
                input.value = digits;
            } else if (digits.length <= 5) {
                input.value = digits.slice(0, 3) + "-" + digits.slice(3);
            } else {
                input.value = digits.slice(0, 3) + "-" + digits.slice(3, 5) + "-" + digits.slice(5, 9);
            }
        } else {
            if (digits.length <= 2) {
                input.value = digits;
            } else {
                input.value = digits.slice(0, 2) + "-" + digits.slice(2, 9);
            }
        }
    }

    /**
     * Synchronizes the Tax ID field placeholder, format badge, and current digits
     * whenever the user switches the Federal Tax Classification dropdown.
     */
    function syncTaxClassificationMask(selectElOrId, targetInputId) {
        const sel =
            typeof selectElOrId === "string"
                ? document.getElementById(selectElOrId)
                : resolveInput(selectElOrId);
        const input = document.getElementById(targetInputId || "onb-ein-ssn");
        if (!input) return;

        const tcVal = sel && sel.value ? sel.value.toLowerCase() : "llc";
        const isSsn = tcVal.indexOf("individual") !== -1 || tcVal.indexOf("sole") !== -1;

        input.setAttribute("data-tax-mode", isSsn ? "ssn" : "ein");
        input.setAttribute("maxlength", isSsn ? "11" : "10");
        input.setAttribute("placeholder", isSsn ? "XXX-XX-XXXX (9-Digit SSN)" : "XX-XXXXXXX (9-Digit EIN)");

        const hintBadge = document.getElementById("onb-tax-id-format-badge");
        if (hintBadge) {
            hintBadge.textContent = isSsn ? "Format: XXX-XX-XXXX (SSN)" : "Format: XX-XXXXXXX (EIN)";
        }

        if (input.value && !isVaultMaskedValue(input.value)) {
            maskTaxIdInput(input);
        }
    }

    /**
     * Social Security Number Mask: XXX-XX-XXXX (maxlength 11)
     */
    function maskSSNInput(elOrEvent) {
        const input = resolveInput(elOrEvent);
        if (!input) return;
        input.setAttribute("inputmode", "numeric");
        input.setAttribute("maxlength", "11");

        const raw = input.value || "";
        if (isVaultMaskedValue(raw)) {
            return;
        }
        const digits = raw.replace(/\D/g, "").slice(0, 9);
        if (!digits) {
            input.value = "";
        } else if (digits.length <= 3) {
            input.value = digits;
        } else if (digits.length <= 5) {
            input.value = digits.slice(0, 3) + "-" + digits.slice(3);
        } else {
            input.value = digits.slice(0, 3) + "-" + digits.slice(3, 5) + "-" + digits.slice(5, 9);
        }
    }

    /**
     * Employer Identification Number Mask: XX-XXXXXXX (maxlength 10)
     */
    function maskEINInput(elOrEvent) {
        const input = resolveInput(elOrEvent);
        if (!input) return;
        maskTaxIdInput(input);
    }

    /**
     * North American Phone Mask: (###)-###-#### (maxlength 14)
     */
    function maskPhoneInput(elOrEvent) {
        const input = resolveInput(elOrEvent);
        if (!input) return;
        input.setAttribute("inputmode", "tel");
        input.setAttribute("maxlength", "14");

        let digits = (input.value || "").replace(/\D/g, "");
        if (digits.length === 11 && digits.charAt(0) === "1") {
            digits = digits.slice(1);
        }
        digits = digits.slice(0, 10);

        if (!digits) {
            input.value = "";
        } else if (digits.length <= 3) {
            input.value = "(" + digits;
        } else if (digits.length <= 6) {
            input.value = "(" + digits.slice(0, 3) + ")-" + digits.slice(3);
        } else {
            input.value =
                "(" +
                digits.slice(0, 3) +
                ")-" +
                digits.slice(3, 6) +
                "-" +
                digits.slice(6, 10);
        }

        if (input.classList && input.classList.contains("has-error") && digits.length === 10) {
            input.classList.remove("has-error");
        }
    }

    /**
     * US ZIP / ZIP+4 Mask: ##### or #####-#### (maxlength 10)
     */
    function maskZipInput(elOrEvent) {
        const input = resolveInput(elOrEvent);
        if (!input) return;
        input.setAttribute("inputmode", "numeric");
        const maxLen = parseInt(input.getAttribute("maxlength") || "10", 10);
        const digits = (input.value || "").replace(/\D/g, "").slice(0, maxLen === 5 ? 5 : 9);
        if (!digits) {
            input.value = "";
        } else if (digits.length <= 5 || maxLen === 5) {
            input.value = digits.slice(0, 5);
        } else {
            input.value = digits.slice(0, 5) + "-" + digits.slice(5, 9);
        }
    }

    /**
     * US Bank 9-Digit ABA Routing Number Mask: ######### (maxlength 9)
     */
    function maskRoutingInput(elOrEvent) {
        const input = resolveInput(elOrEvent);
        if (!input) return;
        input.setAttribute("inputmode", "numeric");
        input.setAttribute("maxlength", "9");
        input.value = (input.value || "").replace(/\D/g, "").slice(0, 9);
    }

    /**
     * US 2-Letter State Code Mask: Uppercase AA (maxlength 2)
     */
    function maskStateInput(elOrEvent) {
        const input = resolveInput(elOrEvent);
        if (!input) return;
        input.setAttribute("maxlength", "2");
        input.value = (input.value || "")
            .replace(/[^a-zA-Z]/g, "")
            .toUpperCase()
            .slice(0, 2);
    }

    const PHONE_IDS = [
        "onb-phone",
        "emp-phone",
        "emp-emg-phone",
        "tech-phone",
        "sub-phone",
        "onboard-phone",
        "onboard-emergency-phone",
        "edit-emp-phone",
        "edit-emp-emergency-phone",
        "sub-onboard-phone",
        "edit-sub-phone",
        "phone_home",
        "phone_page",
        "phone"
    ];

    const TAX_ID_IDS = [
        "onb-ein-ssn",
        "sub-onboard-ein",
        "edit-sub-ein"
    ];

    const SSN_IDS = [
        "emp-ssn",
        "edit-emp-ssn"
    ];

    const ZIP_IDS = [
        "onb-zip",
        "emp-zip",
        "edit-emp-zip",
        "quote-zipcode",
        "edit-lead-zip",
        "form-acc-zip",
        "zipcode"
    ];

    const ROUTING_IDS = [
        "emp-bank-routing",
        "edit-emp-bank-routing"
    ];

    const STATE_IDS = [
        "onb-state",
        "emp-state",
        "sub-onboard-state",
        "edit-lead-state",
        "form-acc-state"
    ];

    function attachHandlerOnce(el, fn) {
        if (!el || el.dataset.sigmaMaskBound === "1") return;
        el.dataset.sigmaMaskBound = "1";
        el.addEventListener("input", function () {
            fn(el);
        });
        el.addEventListener("paste", function () {
            setTimeout(function () {
                fn(el);
            }, 10);
        });
        el.addEventListener("blur", function () {
            fn(el);
        });
        if (el.value && !isVaultMaskedValue(el.value)) {
            fn(el);
        }
    }

    function bindAllSigmaInputMasks() {
        PHONE_IDS.forEach(function (id) {
            const el = document.getElementById(id);
            if (el) attachHandlerOnce(el, maskPhoneInput);
        });
        document.querySelectorAll('input[type="tel"], input[data-mask="phone"]').forEach(function (el) {
            attachHandlerOnce(el, maskPhoneInput);
        });

        TAX_ID_IDS.forEach(function (id) {
            const el = document.getElementById(id);
            if (el) attachHandlerOnce(el, maskTaxIdInput);
        });
        document.querySelectorAll('input[data-mask="tax-id"], input[data-mask="ein"]').forEach(function (el) {
            attachHandlerOnce(el, maskTaxIdInput);
        });

        SSN_IDS.forEach(function (id) {
            const el = document.getElementById(id);
            if (el) attachHandlerOnce(el, maskSSNInput);
        });
        document.querySelectorAll('input[data-mask="ssn"]').forEach(function (el) {
            attachHandlerOnce(el, maskSSNInput);
        });

        ZIP_IDS.forEach(function (id) {
            const el = document.getElementById(id);
            if (el) attachHandlerOnce(el, maskZipInput);
        });
        document.querySelectorAll('input[data-mask="zip"]').forEach(function (el) {
            attachHandlerOnce(el, maskZipInput);
        });

        ROUTING_IDS.forEach(function (id) {
            const el = document.getElementById(id);
            if (el) attachHandlerOnce(el, maskRoutingInput);
        });
        document.querySelectorAll('input[data-mask="routing"]').forEach(function (el) {
            attachHandlerOnce(el, maskRoutingInput);
        });

        STATE_IDS.forEach(function (id) {
            const el = document.getElementById(id);
            if (el) attachHandlerOnce(el, maskStateInput);
        });
        document.querySelectorAll('input[data-mask="state"]').forEach(function (el) {
            attachHandlerOnce(el, maskStateInput);
        });

        const taxClassSel = document.getElementById("onb-tax-class");
        if (taxClassSel && !taxClassSel.dataset.sigmaTaxClassBound) {
            taxClassSel.dataset.sigmaTaxClassBound = "1";
            taxClassSel.addEventListener("change", function () {
                syncTaxClassificationMask(taxClassSel, "onb-ein-ssn");
            });
            syncTaxClassificationMask(taxClassSel, "onb-ein-ssn");
        }
    }

    window.SigmaInputMaskEngine = {
        maskTaxIdInput: maskTaxIdInput,
        syncTaxClassificationMask: syncTaxClassificationMask,
        maskEINInput: maskEINInput,
        maskSSNInput: maskSSNInput,
        maskPhoneInput: maskPhoneInput,
        maskZipInput: maskZipInput,
        maskRoutingInput: maskRoutingInput,
        maskStateInput: maskStateInput,
        bindAll: bindAllSigmaInputMasks
    };

    window.maskTaxIdInput = maskTaxIdInput;
    window.syncTaxClassificationMask = syncTaxClassificationMask;
    window.maskEINInput = maskEINInput;
    if (typeof window.maskSSNInput !== "function") {
        window.maskSSNInput = maskSSNInput;
    }
    window.maskPhoneInput = maskPhoneInput;
    if (typeof window.maskPhone !== "function") {
        window.maskPhone = maskPhoneInput;
    }
    window.maskZipInput = maskZipInput;
    window.maskRoutingInput = maskRoutingInput;
    window.maskStateInput = maskStateInput;

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", bindAllSigmaInputMasks);
    } else {
        bindAllSigmaInputMasks();
    }
})();
