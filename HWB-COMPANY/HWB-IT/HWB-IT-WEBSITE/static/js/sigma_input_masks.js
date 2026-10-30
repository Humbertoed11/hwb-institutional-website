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

    const INVALID_EIN_PREFIXES = {
        "00": true, "07": true, "08": true, "09": true,
        "17": true, "18": true, "19": true, "28": true,
        "29": true, "49": true, "69": true, "70": true,
        "78": true, "79": true, "89": true
    };

    const DUMMY_NINE_DIGIT_TINS = {
        "000000000": true, "111111111": true, "222222222": true,
        "333333333": true, "444444444": true, "555555555": true,
        "666666666": true, "777777777": true, "888888888": true,
        "999999999": true, "123456789": true, "987654321": true,
        "123451234": true
    };

    function detectTaxIdMode(inputEl, explicitTaxClassSelectId) {
        if (!inputEl) return "ein";
        const rawVal = (inputEl.value || "").trim();
        if (/^[0-9*•]{3}-[0-9*•]{2}-[0-9*•]{1,4}$/.test(rawVal)) {
            inputEl.setAttribute("data-tax-mode", "ssn");
            return "ssn";
        }
        if (/^[0-9*•]{2}-[0-9*•]{5,7}$/.test(rawVal)) {
            inputEl.setAttribute("data-tax-mode", "ein");
            return "ein";
        }

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

    function updateTaxModePillsUI(inputId, mode, badgeId) {
        const isSsn = mode === "ssn";
        const input = typeof inputId === "string" ? document.getElementById(inputId) : inputId;
        const resolvedId = input ? input.id : String(inputId || "onb-ein-ssn");

        const einBtn = document.querySelector('[data-tin-pill-for="' + resolvedId + '"][data-tin-mode="ein"]');
        const ssnBtn = document.querySelector('[data-tin-pill-for="' + resolvedId + '"][data-tin-mode="ssn"]');
        if (einBtn && ssnBtn) {
            if (isSsn) {
                ssnBtn.style.background = "#1d4ed8";
                ssnBtn.style.color = "#ffffff";
                ssnBtn.style.borderColor = "#1d4ed8";
                ssnBtn.setAttribute("aria-pressed", "true");
                einBtn.style.background = "#ffffff";
                einBtn.style.color = "#475569";
                einBtn.style.borderColor = "#cbd5e1";
                einBtn.setAttribute("aria-pressed", "false");
            } else {
                einBtn.style.background = "#1d4ed8";
                einBtn.style.color = "#ffffff";
                einBtn.style.borderColor = "#1d4ed8";
                einBtn.setAttribute("aria-pressed", "true");
                ssnBtn.style.background = "#ffffff";
                ssnBtn.style.color = "#475569";
                ssnBtn.style.borderColor = "#cbd5e1";
                ssnBtn.setAttribute("aria-pressed", "false");
            }
        }

        const hiddenModeInput = document.getElementById(resolvedId + "-mode") || (resolvedId === "onb-ein-ssn" ? document.getElementById("onb-tax-id-mode") : null);
        if (hiddenModeInput) {
            hiddenModeInput.value = isSsn ? "ssn" : "ein";
        }

        const hintBadge = document.getElementById(badgeId || (resolvedId === "onb-ein-ssn" ? "onb-tax-id-format-badge" : resolvedId + "-format-badge"));
        if (hintBadge) {
            hintBadge.textContent = isSsn ? "Format: XXX-XX-XXXX (SSN)" : "Format: XX-XXXXXXX (EIN)";
        }
    }

    /**
     * Explicitly switches a Tax ID input between EIN (XX-XXXXXXX) and SSN/ITIN (XXX-XX-XXXX),
     * reformatting any 9 digits currently in the input field in place.
     */
    function setTaxIdMode(inputIdOrEl, mode, badgeId) {
        const input = typeof inputIdOrEl === "string" ? document.getElementById(inputIdOrEl) : resolveInput(inputIdOrEl);
        if (!input) return;
        const cleanMode = String(mode || "ein").toLowerCase() === "ssn" ? "ssn" : "ein";
        input.setAttribute("data-tax-mode", cleanMode);
        input.setAttribute("data-user-selected-mode", "true");
        input.setAttribute("maxlength", cleanMode === "ssn" ? "11" : "10");
        input.setAttribute(
            "placeholder",
            cleanMode === "ssn" ? "XXX-XX-XXXX (9-Digit SSN / ITIN)" : "XX-XXXXXXX (9-Digit EIN)"
        );

        updateTaxModePillsUI(input, cleanMode, badgeId);

        if (input.value && !isVaultMaskedValue(input.value)) {
            const rawDigits = input.value.replace(/\D/g, "").slice(0, 9);
            input.value = rawDigits;
            maskTaxIdInput(input);
        }
        validateTaxIdClientSide(input);
    }

    /**
     * Validates a 9-digit Federal Tax ID against IRS EIN Campus Prefix rules and SSA SSN/ITIN rules.
     */
    function validateTaxIdClientSide(inputIdOrEl, feedbackId) {
        const input = typeof inputIdOrEl === "string" ? document.getElementById(inputIdOrEl) : resolveInput(inputIdOrEl);
        if (!input) return { valid: true, message: "" };
        const fbEl = document.getElementById(feedbackId || (input.id + "-validation-msg")) ||
            (input.id === "onb-ein-ssn" ? document.getElementById("onb-ein-validation-msg") : null);

        const raw = (input.value || "").trim();
        const mode = detectTaxIdMode(input);

        if (!raw || isVaultMaskedValue(raw)) {
            if (fbEl) {
                fbEl.style.display = "none";
                fbEl.textContent = "";
            }
            input.setCustomValidity("");
            return { valid: true, message: "" };
        }

        const digits = raw.replace(/\D/g, "");
        if (digits.length > 0 && digits.length < 9) {
            const msg = "Enter all 9 digits (" + (mode === "ssn" ? "XXX-XX-XXXX" : "XX-XXXXXXX") + "). Currently " + digits.length + " of 9 digits.";
            if (fbEl) {
                fbEl.style.display = "block";
                fbEl.style.color = "#b45309";
                fbEl.textContent = msg;
            }
            input.setCustomValidity(msg);
            return { valid: false, message: msg };
        }

        if (digits.length === 9) {
            if (DUMMY_NINE_DIGIT_TINS[digits]) {
                const msg = "Test or sequential numbers (such as 123-45-6789) are not valid IRS Taxpayer Identification Numbers.";
                if (fbEl) {
                    fbEl.style.display = "block";
                    fbEl.style.color = "#dc2626";
                    fbEl.textContent = msg;
                }
                input.setCustomValidity(msg);
                return { valid: false, message: msg };
            }
            if (mode === "ssn") {
                const area = digits.slice(0, 3);
                const group = digits.slice(3, 5);
                const serial = digits.slice(5, 9);
                if (area === "000" || area === "666" || group === "00" || serial === "0000") {
                    const msg = "Invalid SSN / ITIN format (cannot begin with 000 or 666 or contain all-zero segments).";
                    if (fbEl) {
                        fbEl.style.display = "block";
                        fbEl.style.color = "#dc2626";
                        fbEl.textContent = msg;
                    }
                    input.setCustomValidity(msg);
                    return { valid: false, message: msg };
                }
            } else {
                const prefix = digits.slice(0, 2);
                if (INVALID_EIN_PREFIXES[prefix]) {
                    const msg = "Prefix '" + prefix + "' is not a valid IRS EIN campus prefix. If entering a Social Security Number, click 'SSN / ITIN (XXX-XX-XXXX)' above.";
                    if (fbEl) {
                        fbEl.style.display = "block";
                        fbEl.style.color = "#dc2626";
                        fbEl.textContent = msg;
                    }
                    input.setCustomValidity(msg);
                    return { valid: false, message: msg };
                }
                if (digits.slice(2) === "0000000") {
                    const msg = "Invalid EIN: the last 7 digits cannot be all zeros.";
                    if (fbEl) {
                        fbEl.style.display = "block";
                        fbEl.style.color = "#dc2626";
                        fbEl.textContent = msg;
                    }
                    input.setCustomValidity(msg);
                    return { valid: false, message: msg };
                }
            }

            if (fbEl) {
                fbEl.style.display = "block";
                fbEl.style.color = "#15803d";
                fbEl.textContent = "✓ Valid 9-digit " + (mode === "ssn" ? "SSN / ITIN (XXX-XX-XXXX)" : "IRS EIN (XX-XXXXXXX)") + " format verified.";
            }
            input.setCustomValidity("");
            return { valid: true, message: "" };
        }

        input.setCustomValidity("");
        return { valid: true, message: "" };
    }

    /**
     * Adaptive Federal Tax ID Mask:
     *  - Business Entities (LLC, S-Corp, C-Corp, Partnership): XX-XXXXXXX (maxlength 10)
     *  - Individual / Sole Proprietor or SSN pill selected: XXX-XX-XXXX (maxlength 11)
     *  - Preserves server-masked tokens (**-***0455 / ***-**-9012) until user edits
     */
    function maskTaxIdInput(elOrEvent, taxClassSelectId) {
        const input = resolveInput(elOrEvent);
        if (!input) return;

        const raw = input.value || "";
        // Auto-detect pasted XXX-XX-XXXX vs XX-XXXXXXX
        if (/^\d{3}-\d{2}-\d{4}$/.test(raw.trim())) {
            input.setAttribute("data-tax-mode", "ssn");
            updateTaxModePillsUI(input, "ssn");
        } else if (/^\d{2}-\d{7}$/.test(raw.trim())) {
            input.setAttribute("data-tax-mode", "ein");
            updateTaxModePillsUI(input, "ein");
        }

        const mode = detectTaxIdMode(input, taxClassSelectId);
        input.setAttribute("inputmode", "numeric");
        input.setAttribute("maxlength", mode === "ssn" ? "11" : "10");

        if (isVaultMaskedValue(raw)) {
            const digitsAfterMask = raw.replace(/[*•\-\s]/g, "");
            if (digitsAfterMask.length <= 4) {
                return;
            }
        }

        let digits = raw.replace(/\D/g, "").slice(0, 9);
        if (!digits) {
            input.value = "";
            validateTaxIdClientSide(input);
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
        validateTaxIdClientSide(input);
    }

    /**
     * Synchronizes the Tax ID field placeholder, format badge, pill toggle, and W-9 Line 1/2
     * helper labels whenever the user switches the Federal Tax Classification dropdown.
     */
    function syncTaxClassificationMask(selectElOrId, targetInputId) {
        const sel =
            typeof selectElOrId === "string"
                ? document.getElementById(selectElOrId)
                : resolveInput(selectElOrId);
        const input = document.getElementById(targetInputId || "onb-ein-ssn");
        if (!input) return;

        const tcVal = sel && sel.value ? sel.value.toLowerCase() : "llc";
        const isSoleProp = tcVal.indexOf("individual") !== -1 || tcVal.indexOf("sole") !== -1;
        const isSingleMemberLlc = tcVal.indexOf("single-member") !== -1 || tcVal.indexOf("disregarded") !== -1;

        // If Single-Member LLC and user already clicked SSN pill, keep their choice; otherwise set default
        let targetMode = isSoleProp ? "ssn" : "ein";
        if (isSingleMemberLlc && input.getAttribute("data-user-selected-mode") === "true") {
            targetMode = input.getAttribute("data-tax-mode") === "ssn" ? "ssn" : "ein";
        }

        input.setAttribute("data-tax-mode", targetMode);
        input.setAttribute("maxlength", targetMode === "ssn" ? "11" : "10");
        input.setAttribute(
            "placeholder",
            targetMode === "ssn" ? "XXX-XX-XXXX (9-Digit SSN / ITIN)" : "XX-XXXXXXX (9-Digit EIN)"
        );

        updateTaxModePillsUI(input, targetMode);

        // Update dynamic W-9 Line 1 / Line 2 labels and Single-Member LLC guidance banner if present
        const legalLabel = document.getElementById("onb-legal-entity-label");
        const legalHint = document.getElementById("onb-legal-entity-hint");
        const smLlcBanner = document.getElementById("onb-single-member-llc-tip");
        if (legalLabel) {
            if (isSoleProp) {
                legalLabel.textContent = "Individual / Owner Full Legal Name (W-9 Line 1) *";
            } else if (isSingleMemberLlc) {
                legalLabel.textContent = "Owner or Registered Entity Legal Name (W-9 Line 1) *";
            } else {
                legalLabel.textContent = "Registered Legal Entity Name (W-9 Line 1) *";
            }
        }
        if (legalHint) {
            if (isSoleProp) {
                legalHint.textContent = "Enter your personal legal name exactly as shown on your tax return. Put your DBA / trade name in Business Name on the left.";
            } else if (isSingleMemberLlc) {
                legalHint.textContent = "Single-Member LLC: Enter the LLC's EIN (XX-XXXXXXX), or click 'SSN / ITIN' above if filing under the owner's personal Social Security Number.";
            } else {
                legalHint.textContent = "Must match Line 1 of your IRS Form W-9 for 1099-NEC filing.";
            }
        }
        if (smLlcBanner) {
            smLlcBanner.style.display = isSingleMemberLlc ? "block" : "none";
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
     * US 2-Letter State Code Canonical Dictionary & Normalizer (BUG-156)
     * Eliminates 'tx', 'Texas', 'Tejas', 'TX.' variations across all forms.
     */
    const US_STATES_LIST = [
        { code: "TX", name: "Texas", group: "Primary" },
        { code: "OK", name: "Oklahoma", group: "Regional" },
        { code: "LA", name: "Louisiana", group: "Regional" },
        { code: "AR", name: "Arkansas", group: "Regional" },
        { code: "NM", name: "New Mexico", group: "Regional" },
        { code: "AL", name: "Alabama", group: "All" },
        { code: "AK", name: "Alaska", group: "All" },
        { code: "AZ", name: "Arizona", group: "All" },
        { code: "CA", name: "California", group: "All" },
        { code: "CO", name: "Colorado", group: "All" },
        { code: "CT", name: "Connecticut", group: "All" },
        { code: "DE", name: "Delaware", group: "All" },
        { code: "DC", name: "District of Columbia", group: "All" },
        { code: "FL", name: "Florida", group: "All" },
        { code: "GA", name: "Georgia", group: "All" },
        { code: "HI", name: "Hawaii", group: "All" },
        { code: "ID", name: "Idaho", group: "All" },
        { code: "IL", name: "Illinois", group: "All" },
        { code: "IN", name: "Indiana", group: "All" },
        { code: "IA", name: "Iowa", group: "All" },
        { code: "KS", name: "Kansas", group: "All" },
        { code: "KY", name: "Kentucky", group: "All" },
        { code: "ME", name: "Maine", group: "All" },
        { code: "MD", name: "Maryland", group: "All" },
        { code: "MA", name: "Massachusetts", group: "All" },
        { code: "MI", name: "Michigan", group: "All" },
        { code: "MN", name: "Minnesota", group: "All" },
        { code: "MS", name: "Mississippi", group: "All" },
        { code: "MO", name: "Missouri", group: "All" },
        { code: "MT", name: "Montana", group: "All" },
        { code: "NE", name: "Nebraska", group: "All" },
        { code: "NV", name: "Nevada", group: "All" },
        { code: "NH", name: "New Hampshire", group: "All" },
        { code: "NJ", name: "New Jersey", group: "All" },
        { code: "NY", name: "New York", group: "All" },
        { code: "NC", name: "North Carolina", group: "All" },
        { code: "ND", name: "North Dakota", group: "All" },
        { code: "OH", name: "Ohio", group: "All" },
        { code: "OR", name: "Oregon", group: "All" },
        { code: "PA", name: "Pennsylvania", group: "All" },
        { code: "RI", name: "Rhode Island", group: "All" },
        { code: "SC", name: "South Carolina", group: "All" },
        { code: "SD", name: "South Dakota", group: "All" },
        { code: "TN", name: "Tennessee", group: "All" },
        { code: "UT", name: "Utah", group: "All" },
        { code: "VT", name: "Vermont", group: "All" },
        { code: "VA", name: "Virginia", group: "All" },
        { code: "WA", name: "Washington", group: "All" },
        { code: "WV", name: "West Virginia", group: "All" },
        { code: "WI", name: "Wisconsin", group: "All" },
        { code: "WY", name: "Wyoming", group: "All" }
    ];

    const STATE_ALIAS_LOOKUP = (function () {
        const map = {
            tejas: "TX",
            tex: "TX",
            "tx.": "TX",
            "t.x.": "TX",
            "texas, usa": "TX",
            "tx - texas": "TX",
            "tx — texas": "TX",
            okla: "OK",
            "ok.": "OK",
            "la.": "LA",
            ark: "AR",
            "n.m.": "NM",
            "new mex": "NM",
            calif: "CA",
            fla: "FL",
            wash: "WA",
            "d.c.": "DC",
            "washington dc": "DC"
        };
        US_STATES_LIST.forEach(function (item) {
            map[item.code.toLowerCase()] = item.code;
            map[item.name.toLowerCase()] = item.code;
            map[(item.code + " — " + item.name).toLowerCase()] = item.code;
            map[(item.code + " - " + item.name).toLowerCase()] = item.code;
        });
        return map;
    })();

    function normalizeUspsStateCode(rawVal, fallback) {
        const def = fallback !== undefined ? fallback : "TX";
        if (!rawVal) return def;
        const s = String(rawVal).trim();
        if (!s) return def;
        if (s.indexOf("—") !== -1 || s.indexOf(" - ") !== -1) {
            const prefix = s.split(/\s*[—-]\s*/)[0].trim().toUpperCase();
            if (STATE_ALIAS_LOOKUP[prefix.toLowerCase()]) {
                return STATE_ALIAS_LOOKUP[prefix.toLowerCase()];
            }
        }
        const cleaned = s.replace(/[^a-zA-Z\s.]/g, "").trim().toLowerCase();
        const noDots = cleaned.replace(/\./g, "").trim();
        if (STATE_ALIAS_LOOKUP[cleaned]) return STATE_ALIAS_LOOKUP[cleaned];
        if (STATE_ALIAS_LOOKUP[noDots]) return STATE_ALIAS_LOOKUP[noDots];
        const up = noDots.toUpperCase();
        if (up.length === 2 && STATE_ALIAS_LOOKUP[up.toLowerCase()]) {
            return up;
        }
        return def;
    }

    function installSmartStateValueDescriptor(selectEl) {
        if (!selectEl || selectEl.dataset.sigmaStateDescriptorBound === "1") return;
        selectEl.dataset.sigmaStateDescriptorBound = "1";
        const proto = Object.getPrototypeOf(selectEl);
        const desc = Object.getOwnPropertyDescriptor(proto, "value") ||
            Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value");
        if (!desc || !desc.get || !desc.set) return;
        Object.defineProperty(selectEl, "value", {
            configurable: true,
            enumerable: true,
            get: function () {
                return desc.get.call(this);
            },
            set: function (v) {
                const norm = normalizeUspsStateCode(v, "TX");
                desc.set.call(this, norm);
            }
        });
    }

    function populateStateSelectOptions(selectEl, initialValue) {
        if (!selectEl) return;
        const targetCode = normalizeUspsStateCode(initialValue || selectEl.value || "TX", "TX");
        if (selectEl.dataset.sigmaStatePopulated !== "1") {
            selectEl.innerHTML = "";
            const optGroupPrimary = document.createElement("optgroup");
            optGroupPrimary.label = "Primary Operating State";
            const optGroupRegional = document.createElement("optgroup");
            optGroupRegional.label = "Regional States";
            const optGroupAll = document.createElement("optgroup");
            optGroupAll.label = "All US States & DC";

            US_STATES_LIST.forEach(function (st) {
                const opt = document.createElement("option");
                opt.value = st.code;
                opt.textContent = st.code + " — " + st.name;
                if (st.group === "Primary") {
                    optGroupPrimary.appendChild(opt);
                } else if (st.group === "Regional") {
                    optGroupRegional.appendChild(opt);
                } else {
                    optGroupAll.appendChild(opt);
                }
            });
            selectEl.appendChild(optGroupPrimary);
            selectEl.appendChild(optGroupRegional);
            selectEl.appendChild(optGroupAll);
            selectEl.dataset.sigmaStatePopulated = "1";
        }
        installSmartStateValueDescriptor(selectEl);
        selectEl.value = targetCode;
    }

    function upgradeStateInputToSelect(el) {
        if (!el) return null;
        if (el.tagName === "SELECT") {
            populateStateSelectOptions(el, el.getAttribute("data-initial-state") || el.value || "TX");
            return el;
        }
        if (el.tagName !== "INPUT") return el;
        if (el.type === "hidden") {
            el.value = normalizeUspsStateCode(el.value, "TX");
            return el;
        }

        const selectEl = document.createElement("select");
        if (el.id) selectEl.id = el.id;
        if (el.name) selectEl.name = el.name;
        selectEl.className = el.className || "sigma-input";
        if (el.style && el.style.cssText) {
            selectEl.style.cssText = el.style.cssText;
        }
        if (el.required) selectEl.required = true;
        if (el.disabled) selectEl.disabled = true;
        const ariaLabel = el.getAttribute("aria-label") || "State (2-Letter USPS Code)";
        selectEl.setAttribute("aria-label", ariaLabel);
        selectEl.setAttribute("data-mask", "state");

        Array.from(el.attributes).forEach(function (attr) {
            if (attr.name.indexOf("data-") === 0 && attr.name !== "data-sigma-mask-bound") {
                selectEl.setAttribute(attr.name, attr.value);
            }
        });

        populateStateSelectOptions(selectEl, el.value || "TX");

        if (el.parentNode) {
            el.parentNode.replaceChild(selectEl, el);
        }
        return selectEl;
    }

    /**
     * US 2-Letter State Code Mask: Normalizes any state input or select to canonical 2-letter code
     */
    function maskStateInput(elOrEvent) {
        const input = resolveInput(elOrEvent);
        if (!input) return;
        if (input.tagName === "SELECT") {
            input.value = normalizeUspsStateCode(input.value, "TX");
            return;
        }
        const raw = (input.value || "").trim();
        if (raw.length > 2) {
            input.value = normalizeUspsStateCode(raw, "TX");
        } else {
            input.value = raw.replace(/[^a-zA-Z]/g, "").toUpperCase().slice(0, 2);
        }
    }

    /**
     * USPS Publication 28 Address Line 1 -> Address Line 2 Auto-Splitter & Full Address Paste Parser
     */
    function splitAddressLine1Value(rawAddr1, rawAddr2) {
        let addr1 = String(rawAddr1 || "").replace(/\s+/g, " ").trim();
        let addr2 = String(rawAddr2 || "").replace(/\s+/g, " ").trim();
        let parsedCity = "";
        let parsedState = "";
        let parsedZip = "";

        if (!addr1) {
            return { addr1: "", addr2: addr2, city: "", state: "", zip: "" };
        }

        // 1. Check if a full single-line Google Maps address was pasted:
        // e.g. "5800 Granite Pkwy Ste 250, Plano, TX 75024"
        const fullPasteRegex = /^(.*?),\s*([A-Za-z.\s'-]{2,35}),\s*([A-Za-z.]{2,15})\s+(\d{5}(?:-\d{4})?)$/;
        const fullMatch = addr1.match(fullPasteRegex);
        if (fullMatch) {
            addr1 = fullMatch[1].trim();
            parsedCity = fullMatch[2].trim();
            parsedState = normalizeUspsStateCode(fullMatch[3].trim(), "TX");
            parsedZip = fullMatch[4].trim();
        }

        // 2. Check for secondary unit designators (Suite, Ste, Bldg, Unit, Apt, Floor, Rm, #)
        if (!addr2) {
            const unitRegex = /^(.*?)(?:,|\s+)\b((?:suite|ste\.?|bldg\.?|building|unit|apt\.?|apartment|fl\.?|floor|rm\.?|room|spc\.?|space)\s*[#a-zA-Z0-9-]+|#\s*[a-zA-Z0-9-]+)\s*$/i;
            const unitMatch = addr1.match(unitRegex);
            if (unitMatch && unitMatch[1].trim()) {
                addr1 = unitMatch[1].trim().replace(/,+$/, "").trim();
                let extracted = unitMatch[2].trim();
                extracted = extracted.replace(/^ste\.?\s+/i, "Suite ");
                extracted = extracted.replace(/^bldg\.?\s+/i, "Bldg ");
                addr2 = extracted;
            }
        }

        return {
            addr1: addr1,
            addr2: addr2,
            city: parsedCity,
            state: parsedState,
            zip: parsedZip
        };
    }

    function findSiblingAddressLine2(addr1El) {
        if (!addr1El) return null;
        const explicitTarget = addr1El.getAttribute("data-address-line2-target");
        if (explicitTarget) {
            const byId = document.getElementById(explicitTarget);
            if (byId) return byId;
        }
        const scope = addr1El.closest("form, .sigma-modal, .lead-tab-pane, .acc-tab-pane, .sigma-card") || document;
        return scope.querySelector(
            'input[name="address_line_2"], input[data-mask="address-line-2"], #add-lead-address-line2, #edit-lead-address-line2, #add-acc-address-line2, #form-acc-address-line2, #bid-address-line2, #sub-address-line2, #onb-address-line2'
        );
    }

    function bindAddressLineAutoSplit(addr1El) {
        if (!addr1El || addr1El.dataset.sigmaAddrSplitBound === "1") return;
        addr1El.dataset.sigmaAddrSplitBound = "1";

        function runSplit() {
            const addr2El = findSiblingAddressLine2(addr1El);
            const currentAddr2 = addr2El ? addr2El.value : "";
            const res = splitAddressLine1Value(addr1El.value, currentAddr2);
            if (res.addr1 && res.addr1 !== addr1El.value) {
                addr1El.value = res.addr1;
            }
            if (addr2El && res.addr2 && !addr2El.value) {
                addr2El.value = res.addr2;
            }
            const scope = addr1El.closest("form, .sigma-modal, .lead-tab-pane, .acc-tab-pane, .sigma-card");
            if (scope) {
                if (res.city) {
                    const cityEl = scope.querySelector('input[name="city"], #edit-lead-city, #add-lead-city, #form-acc-city, #add-acc-city');
                    if (cityEl && !cityEl.value) cityEl.value = res.city;
                }
                if (res.state) {
                    const stateEl = scope.querySelector('select[name="state"], input[name="state"], #edit-lead-state, #add-lead-state, #form-acc-state, #add-acc-state');
                    if (stateEl) stateEl.value = res.state;
                }
                if (res.zip) {
                    const zipEl = scope.querySelector('input[name="zipcode"], input[name="zip"], #edit-lead-zip, #add-lead-zip, #form-acc-zip, #add-acc-zip');
                    if (zipEl && !zipEl.value) {
                        zipEl.value = res.zip;
                        zipEl.dispatchEvent(new Event("change", { bubbles: true }));
                    }
                }
            }
        }

        addr1El.addEventListener("blur", runSplit);
        addr1El.addEventListener("paste", function () {
            setTimeout(runSplit, 25);
        });
    }

    /**
     * Texas ZIP <-> City / State / County Bidirectional Lookup Table
     */
    const TX_ZIP_GEO_MAP = {
        "75001": { city: "Addison", county: "Dallas" },
        "75002": { city: "Allen", county: "Collin" },
        "75006": { city: "Carrollton", county: "Dallas" },
        "75007": { city: "Carrollton", county: "Denton" },
        "75010": { city: "Carrollton", county: "Denton" },
        "75013": { city: "Allen", county: "Collin" },
        "75019": { city: "Coppell", county: "Dallas" },
        "75023": { city: "Plano", county: "Collin" },
        "75024": { city: "Plano", county: "Collin" },
        "75025": { city: "Plano", county: "Collin" },
        "75028": { city: "Flower Mound", county: "Denton" },
        "75032": { city: "Rockwall", county: "Rockwall" },
        "75033": { city: "Frisco", county: "Collin" },
        "75034": { city: "Frisco", county: "Collin" },
        "75035": { city: "Frisco", county: "Collin" },
        "75038": { city: "Irving", county: "Dallas" },
        "75039": { city: "Irving", county: "Dallas" },
        "75040": { city: "Garland", county: "Dallas" },
        "75041": { city: "Garland", county: "Dallas" },
        "75042": { city: "Garland", county: "Dallas" },
        "75043": { city: "Garland", county: "Dallas" },
        "75044": { city: "Garland", county: "Dallas" },
        "75048": { city: "Sachse", county: "Dallas" },
        "75050": { city: "Grand Prairie", county: "Dallas" },
        "75051": { city: "Grand Prairie", county: "Dallas" },
        "75052": { city: "Grand Prairie", county: "Dallas" },
        "75056": { city: "The Colony", county: "Denton" },
        "75057": { city: "Lewisville", county: "Denton" },
        "75060": { city: "Irving", county: "Dallas" },
        "75061": { city: "Irving", county: "Dallas" },
        "75062": { city: "Irving", county: "Dallas" },
        "75063": { city: "Irving", county: "Dallas" },
        "75067": { city: "Lewisville", county: "Denton" },
        "75068": { city: "Little Elm", county: "Denton" },
        "75069": { city: "McKinney", county: "Collin" },
        "75070": { city: "McKinney", county: "Collin" },
        "75071": { city: "McKinney", county: "Collin" },
        "75072": { city: "McKinney", county: "Collin" },
        "75074": { city: "Plano", county: "Collin" },
        "75075": { city: "Plano", county: "Collin" },
        "75078": { city: "Prosper", county: "Collin" },
        "75080": { city: "Richardson", county: "Dallas" },
        "75081": { city: "Richardson", county: "Dallas" },
        "75082": { city: "Richardson", county: "Collin" },
        "75087": { city: "Rockwall", county: "Rockwall" },
        "75088": { city: "Rowlett", county: "Dallas" },
        "75089": { city: "Rowlett", county: "Dallas" },
        "75093": { city: "Plano", county: "Collin" },
        "75094": { city: "Murphy", county: "Collin" },
        "75098": { city: "Wylie", county: "Collin" },
        "75104": { city: "Cedar Hill", county: "Dallas" },
        "75115": { city: "DeSoto", county: "Dallas" },
        "75116": { city: "Duncanville", county: "Dallas" },
        "75126": { city: "Forney", county: "Kaufman" },
        "75149": { city: "Mesquite", county: "Dallas" },
        "75150": { city: "Mesquite", county: "Dallas" },
        "75154": { city: "Red Oak", county: "Ellis" },
        "75165": { city: "Waxahachie", county: "Ellis" },
        "75189": { city: "Royse City", county: "Rockwall" },
        "75201": { city: "Dallas", county: "Dallas" },
        "75202": { city: "Dallas", county: "Dallas" },
        "75204": { city: "Dallas", county: "Dallas" },
        "75205": { city: "Dallas", county: "Dallas" },
        "75206": { city: "Dallas", county: "Dallas" },
        "75207": { city: "Dallas", county: "Dallas" },
        "75219": { city: "Dallas", county: "Dallas" },
        "75220": { city: "Dallas", county: "Dallas" },
        "75225": { city: "Dallas", county: "Dallas" },
        "75230": { city: "Dallas", county: "Dallas" },
        "75231": { city: "Dallas", county: "Dallas" },
        "75234": { city: "Farmers Branch", county: "Dallas" },
        "75235": { city: "Dallas", county: "Dallas" },
        "75240": { city: "Dallas", county: "Dallas" },
        "75243": { city: "Dallas", county: "Dallas" },
        "75244": { city: "Dallas", county: "Dallas" },
        "75247": { city: "Dallas", county: "Dallas" },
        "75248": { city: "Dallas", county: "Dallas" },
        "75251": { city: "Dallas", county: "Dallas" },
        "75252": { city: "Dallas", county: "Collin" },
        "75254": { city: "Dallas", county: "Dallas" },
        "75287": { city: "Dallas", county: "Denton" },
        "76001": { city: "Arlington", county: "Tarrant" },
        "76002": { city: "Arlington", county: "Tarrant" },
        "76006": { city: "Arlington", county: "Tarrant" },
        "76010": { city: "Arlington", county: "Tarrant" },
        "76011": { city: "Arlington", county: "Tarrant" },
        "76012": { city: "Arlington", county: "Tarrant" },
        "76013": { city: "Arlington", county: "Tarrant" },
        "76014": { city: "Arlington", county: "Tarrant" },
        "76015": { city: "Arlington", county: "Tarrant" },
        "76016": { city: "Arlington", county: "Tarrant" },
        "76017": { city: "Arlington", county: "Tarrant" },
        "76018": { city: "Arlington", county: "Tarrant" },
        "76021": { city: "Bedford", county: "Tarrant" },
        "76022": { city: "Bedford", county: "Tarrant" },
        "76028": { city: "Burleson", county: "Johnson" },
        "76034": { city: "Colleyville", county: "Tarrant" },
        "76039": { city: "Euless", county: "Tarrant" },
        "76040": { city: "Euless", county: "Tarrant" },
        "76051": { city: "Grapevine", county: "Tarrant" },
        "76053": { city: "Hurst", county: "Tarrant" },
        "76054": { city: "Hurst", county: "Tarrant" },
        "76063": { city: "Mansfield", county: "Tarrant" },
        "76092": { city: "Southlake", county: "Tarrant" },
        "76102": { city: "Fort Worth", county: "Tarrant" },
        "76104": { city: "Fort Worth", county: "Tarrant" },
        "76107": { city: "Fort Worth", county: "Tarrant" },
        "76109": { city: "Fort Worth", county: "Tarrant" },
        "76116": { city: "Fort Worth", county: "Tarrant" },
        "76132": { city: "Fort Worth", county: "Tarrant" },
        "76137": { city: "Fort Worth", county: "Tarrant" },
        "76155": { city: "Fort Worth", county: "Tarrant" },
        "76177": { city: "Fort Worth", county: "Tarrant" },
        "76180": { city: "North Richland Hills", county: "Tarrant" },
        "76201": { city: "Denton", county: "Denton" },
        "76205": { city: "Denton", county: "Denton" },
        "76210": { city: "Denton", county: "Denton" },
        "76226": { city: "Argyle", county: "Denton" },
        "76244": { city: "Keller", county: "Tarrant" },
        "76248": { city: "Keller", county: "Tarrant" },
        "76262": { city: "Roanoke", county: "Denton" },
        "77002": { city: "Houston", county: "Harris" },
        "77056": { city: "Houston", county: "Harris" },
        "78205": { city: "San Antonio", county: "Bexar" },
        "78701": { city: "Austin", county: "Travis" }
    };

    function bindZipGeoAutoFill(zipEl) {
        if (!zipEl || zipEl.dataset.sigmaZipGeoBound === "1") return;
        zipEl.dataset.sigmaZipGeoBound = "1";

        function enrichFromZip() {
            const digits = (zipEl.value || "").replace(/\D/g, "").slice(0, 5);
            if (digits.length !== 5) return;
            const scope = zipEl.closest("form, .sigma-modal, .lead-tab-pane, .acc-tab-pane, .sigma-card");
            if (!scope) return;

            const geo = TX_ZIP_GEO_MAP[digits];
            const cityEl = scope.querySelector('input[name="city"], #edit-lead-city, #add-lead-city, #form-acc-city, #add-acc-city, #onb-city, #emp-city');
            const stateEl = scope.querySelector('select[name="state"], input[name="state"], #edit-lead-state, #add-lead-state, #form-acc-state, #add-acc-state, #onb-state, #emp-state');
            const countyEl = scope.querySelector('input[name="county"], #edit-lead-county, #add-lead-county');

            if (geo) {
                if (cityEl && !cityEl.value.trim()) {
                    cityEl.value = geo.city;
                }
                if (stateEl) {
                    stateEl.value = "TX";
                }
                if (countyEl && !countyEl.value.trim()) {
                    countyEl.value = geo.county;
                }
            } else if (/^7[5-9]\d{3}$/.test(digits) && stateEl) {
                stateEl.value = "TX";
            }
        }

        zipEl.addEventListener("change", enrichFromZip);
        zipEl.addEventListener("blur", enrichFromZip);
        zipEl.addEventListener("input", function () {
            const d = (zipEl.value || "").replace(/\D/g, "");
            if (d.length === 5) enrichFromZip();
        });
    }

    /**
     * Website URL Normalizer & Corporate Email Domain Inference
     */
    const CONSUMER_EMAIL_DOMAINS_JS = {
        "gmail.com": 1,
        "yahoo.com": 1,
        "outlook.com": 1,
        "hotmail.com": 1,
        "icloud.com": 1,
        "aol.com": 1,
        "msn.com": 1,
        "live.com": 1,
        "me.com": 1,
        "sbcglobal.net": 1,
        "att.net": 1,
        "comcast.net": 1,
        "verizon.net": 1,
        "protonmail.com": 1,
        "proton.me": 1,
        "ymail.com": 1,
        "mail.com": 1
    };

    function normalizeWebsiteUrl(rawVal) {
        let v = String(rawVal || "").trim();
        if (!v) return "";
        v = v.replace(/^mailto:/i, "").trim().split(/\s+/)[0];
        if (!/^https?:\/\//i.test(v)) {
            v = "https://" + v.replace(/^\/+/, "");
        }
        return v;
    }

    function bindWebsiteInputHygiene(webEl) {
        if (!webEl || webEl.dataset.sigmaWebBound === "1") return;
        webEl.dataset.sigmaWebBound = "1";
        webEl.addEventListener("blur", function () {
            if (webEl.value && webEl.value.trim()) {
                webEl.value = normalizeWebsiteUrl(webEl.value);
            }
        });
    }

    function bindEmailToWebsiteInference(emailEl) {
        if (!emailEl || emailEl.dataset.sigmaEmailWebBound === "1") return;
        emailEl.dataset.sigmaEmailWebBound = "1";
        emailEl.addEventListener("blur", function () {
            const val = (emailEl.value || "").trim().toLowerCase();
            if (!val || val.indexOf("@") === -1) return;
            const domain = val.split("@")[1];
            if (!domain || CONSUMER_EMAIL_DOMAINS_JS[domain] || domain.indexOf(".") === -1) return;
            const scope = emailEl.closest("form, .sigma-modal, .lead-tab-pane, .acc-tab-pane, .sigma-card");
            if (!scope) return;
            const webEl = scope.querySelector('input[name="website"], #add-lead-website, #edit-lead-website, #add-acc-website, #form-acc-website');
            if (webEl && !webEl.value.trim()) {
                webEl.value = domain.indexOf("www.") === 0 ? "https://" + domain : "https://www." + domain;
            }
        });
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
        "add-lead-zip",
        "form-acc-zip",
        "add-acc-zip",
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
        "add-lead-state",
        "form-acc-state",
        "add-acc-state",
        "bid-state",
        "sub-state"
    ];

    const ADDRESS_LINE1_SELECTORS = [
        'input[name="address"]',
        'input[name="street_address"]',
        "#add-lead-address",
        "#edit-lead-address",
        "#add-acc-address",
        "#form-acc-address",
        "#onb-address",
        "#emp-address"
    ].join(", ");

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
            if (el) {
                attachHandlerOnce(el, maskZipInput);
                bindZipGeoAutoFill(el);
            }
        });
        document.querySelectorAll('input[data-mask="zip"], input[name="zipcode"], input[name="zip"]').forEach(function (el) {
            attachHandlerOnce(el, maskZipInput);
            bindZipGeoAutoFill(el);
        });

        ROUTING_IDS.forEach(function (id) {
            const el = document.getElementById(id);
            if (el) attachHandlerOnce(el, maskRoutingInput);
        });
        document.querySelectorAll('input[data-mask="routing"]').forEach(function (el) {
            attachHandlerOnce(el, maskRoutingInput);
        });

        // Upgrade all State inputs/selects to standardized USPS 2-Letter State dropdowns
        STATE_IDS.forEach(function (id) {
            const el = document.getElementById(id);
            if (el) {
                const upgraded = upgradeStateInputToSelect(el);
                if (upgraded) attachHandlerOnce(upgraded, maskStateInput);
            }
        });
        document.querySelectorAll('input[name="state"], select[name="state"], input[data-mask="state"], select[data-mask="state"]').forEach(function (el) {
            const upgraded = upgradeStateInputToSelect(el);
            if (upgraded) attachHandlerOnce(upgraded, maskStateInput);
        });

        // Address Line 1 -> Address Line 2 USPS Pub 28 auto-splitter
        document.querySelectorAll(ADDRESS_LINE1_SELECTORS).forEach(function (el) {
            bindAddressLineAutoSplit(el);
        });

        // Website URL normalization & corporate email domain inference
        document.querySelectorAll('input[name="website"], input[type="url"], #add-lead-website, #edit-lead-website, #add-acc-website, #form-acc-website').forEach(function (el) {
            bindWebsiteInputHygiene(el);
        });
        document.querySelectorAll('input[name="email"], input[type="email"], #add-lead-email, #edit-lead-email, #add-acc-email, #form-acc-email').forEach(function (el) {
            bindEmailToWebsiteInference(el);
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
        setTaxIdMode: setTaxIdMode,
        validateTaxIdClientSide: validateTaxIdClientSide,
        syncTaxClassificationMask: syncTaxClassificationMask,
        maskEINInput: maskEINInput,
        maskSSNInput: maskSSNInput,
        maskPhoneInput: maskPhoneInput,
        maskZipInput: maskZipInput,
        maskRoutingInput: maskRoutingInput,
        maskStateInput: maskStateInput,
        normalizeUspsStateCode: normalizeUspsStateCode,
        upgradeStateInputToSelect: upgradeStateInputToSelect,
        splitAddressLine1Value: splitAddressLine1Value,
        normalizeWebsiteUrl: normalizeWebsiteUrl,
        US_STATES_LIST: US_STATES_LIST,
        bindAll: bindAllSigmaInputMasks
    };

    window.maskTaxIdInput = maskTaxIdInput;
    window.setTaxIdMode = setTaxIdMode;
    window.validateTaxIdClientSide = validateTaxIdClientSide;
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
    window.normalizeUspsStateCode = normalizeUspsStateCode;

    function startInputMaskMutationObserver() {
        bindAllSigmaInputMasks();
        if (typeof MutationObserver !== "undefined" && document.body && !window.__sigmaInputMaskObserverActive) {
            window.__sigmaInputMaskObserverActive = true;
            let debounceTimer = null;
            const obs = new MutationObserver(function (mutations) {
                let hasAddedNodes = false;
                for (let i = 0; i < mutations.length; i++) {
                    if (mutations[i].addedNodes && mutations[i].addedNodes.length > 0) {
                        hasAddedNodes = true;
                        break;
                    }
                }
                if (hasAddedNodes) {
                    if (debounceTimer) clearTimeout(debounceTimer);
                    debounceTimer = setTimeout(bindAllSigmaInputMasks, 60);
                }
            });
            obs.observe(document.body, { childList: true, subtree: true });
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", startInputMaskMutationObserver);
    } else {
        startInputMaskMutationObserver();
    }
})();
