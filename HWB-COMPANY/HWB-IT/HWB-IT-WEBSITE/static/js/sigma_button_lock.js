/**
 * SigmaFidelity™ Enterprise Button & Navigation Spin-Lock Engine (Phase 3 UX)
 * Mandated: HWB-QMS-7.2 / Instant Visual Feedback Standard (2026)
 * Responsibility: George (Lead Systems Architect)
 * 
 * Provides:
 * 1. Immediate (<100ms) tactile button touch feedback & self-transforming spinner.
 * 2. Navigation Tab Icon spinner and highlight (Technique A).
 * 3. Sleek top-edge progress bar (YouTube / GitHub standard).
 * 4. Double-click & double-tap protection across desktop and mobile devices.
 */
(function() {
    'use strict';

    /**
     * Determines a clean, plain-spoken everyday English verb for button loading state.
     */
    function getEverydayLoadingText(btn, customText) {
        if (customText && typeof customText === 'string') return customText;
        if (btn.dataset && btn.dataset.loadingText) return btn.dataset.loadingText;

        const rawText = (btn.innerText || btn.value || '').trim().toLowerCase();
        
        if (rawText.includes('apply view') || rawText.includes('apply')) return 'Applying View...';
        if (rawText.includes('reset default') || rawText.includes('reset view') || rawText.includes('reset all')) return 'Resetting...';
        if (rawText.includes('search')) return 'Searching...';
        if (rawText.includes('filter')) return 'Filtering...';
        if (rawText.includes('save & start') || rawText.includes('start campaign')) return 'Starting Campaign...';
        if (rawText.includes('send to campaign') || rawText.includes('send')) return 'Sending...';
        if (rawText.includes('secure & save') || rawText.includes('save planner')) return 'Saving Planner...';
        if (rawText.includes('save') || rawText.includes('update')) return 'Saving...';
        if (rawText.includes('delete') || rawText.includes('remove') || rawText.includes('purge')) return 'Deleting...';
        if (rawText.includes('onboard')) return 'Onboarding...';
        if (rawText.includes('create') || rawText.includes('add')) return 'Adding...';
        if (rawText.includes('upload') || rawText.includes('import')) return 'Uploading...';
        if (rawText.includes('export') || rawText.includes('download')) return 'Exporting...';
        if (rawText.includes('log in') || rawText.includes('login') || rawText.includes('sign in')) return 'Logging In...';
        if (rawText.includes('approve')) return 'Approving...';
        if (rawText.includes('reject')) return 'Rejecting...';
        if (rawText.includes('clock in')) return 'Clocking In...';
        if (rawText.includes('clock out')) return 'Clocking Out...';
        if (rawText.includes('quote')) return 'Calculating Quote...';
        if (rawText.includes('confirm') || rawText.includes('proceed') || rawText.includes('yes')) return 'Processing...';

        return 'Working...';
    }

    /**
     * Locks a button, preserves its exact width to prevent layout jump,
     * and shows an inline spinning wheel with everyday action text.
     */
    function spinAndLock(btn, customText) {
        if (!btn || !(btn instanceof Element)) return false;
        if (btn.classList.contains('is-spinning-lock')) return false;

        // Cache original button content and physical width
        if (!btn.dataset.originalHtml) {
            btn.dataset.originalHtml = btn.innerHTML;
            const currentWidth = btn.getBoundingClientRect().width;
            if (currentWidth > 0) {
                btn.dataset.originalWidth = currentWidth + 'px';
            }
        }

        // Lock button width to prevent awkward shrinking
        if (btn.dataset.originalWidth && !btn.style.width && !btn.style.minWidth) {
            btn.style.minWidth = btn.dataset.originalWidth;
        }

        const loadingText = getEverydayLoadingText(btn, customText);

        btn.classList.add('is-spinning-lock');
        btn.disabled = true;
        btn.setAttribute('aria-busy', 'true');
        btn.setAttribute('aria-disabled', 'true');

        // Render spinner + loading label
        btn.innerHTML = `<span class="sigma-spin-circle" aria-hidden="true"></span><span class="sigma-btn-label">${loadingText}</span>`;

        // Safety fallback: auto-restore if page doesn't unload within 12 seconds
        if (btn._spinSafetyTimer) clearTimeout(btn._spinSafetyTimer);
        btn._spinSafetyTimer = setTimeout(() => {
            restoreButton(btn);
        }, 12000);

        return true;
    }

    /**
     * Restores a button back to its active, clickable state.
     */
    function restoreButton(btn) {
        if (!btn || !(btn instanceof Element)) return;
        if (btn._spinSafetyTimer) {
            clearTimeout(btn._spinSafetyTimer);
            btn._spinSafetyTimer = null;
        }
        if (!btn.classList.contains('is-spinning-lock')) return;

        btn.classList.remove('is-spinning-lock');
        btn.disabled = false;
        btn.removeAttribute('aria-busy');
        btn.removeAttribute('aria-disabled');

        if (btn.dataset.originalHtml) {
            btn.innerHTML = btn.dataset.originalHtml;
            delete btn.dataset.originalHtml;
        }
        if (btn.dataset.originalWidth) {
            if (btn.style.minWidth === btn.dataset.originalWidth) {
                btn.style.minWidth = '';
            }
            delete btn.dataset.originalWidth;
        }
    }

    // --- Top-Edge Progress Bar Engine (YouTube / GitHub Standard) ---
    let topProgressBar = null;

    function getTopProgressBar() {
        if (!topProgressBar) {
            topProgressBar = document.getElementById('sigma-top-progress');
            if (!topProgressBar) {
                topProgressBar = document.createElement('div');
                topProgressBar.id = 'sigma-top-progress';
                topProgressBar.className = 'sigma-top-progress';
                document.body.appendChild(topProgressBar);
            }
        }
        return topProgressBar;
    }

    function startTopProgress() {
        const bar = getTopProgressBar();
        if (bar) {
            bar.classList.remove('is-completed');
            bar.classList.add('is-active');
            bar.style.width = '68%';
        }
    }

    function finishTopProgress() {
        const bar = getTopProgressBar();
        if (bar && bar.classList.contains('is-active')) {
            bar.style.width = '100%';
            setTimeout(() => {
                bar.classList.remove('is-active');
                bar.classList.add('is-completed');
                bar.style.width = '0%';
            }, 300);
        }
    }

    // Expose functions globally for manual triggers in scripts & AJAX callbacks
    window.spinAndLock = spinAndLock;
    window.restoreButton = restoreButton;
    window.startTopProgress = startTopProgress;
    window.finishTopProgress = finishTopProgress;

    // --- Network-Aware Fetch Auto-Unlock Engine (BUG-160) ---
    let activeFetchCount = 0;
    let isPageUnloading = false;
    const pendingAjaxButtons = new Set();

    window.addEventListener('beforeunload', function() {
        isPageUnloading = true;
    });

    function flushPendingAjaxButtons() {
        if (activeFetchCount > 0 || isPageUnloading) return;
        pendingAjaxButtons.forEach(function(btn) {
            restoreButton(btn);
        });
        pendingAjaxButtons.clear();
        finishTopProgress();
    }

    if (typeof window.fetch === 'function' && !window.fetch._sigmaWrapped) {
        const nativeFetch = window.fetch.bind(window);
        const wrappedFetch = function(...args) {
            activeFetchCount++;
            try {
                const promise = nativeFetch(...args);
                if (promise && typeof promise.finally === 'function') {
                    return promise.finally(function() {
                        activeFetchCount = Math.max(0, activeFetchCount - 1);
                        if (activeFetchCount === 0) {
                            setTimeout(flushPendingAjaxButtons, 60);
                        }
                    });
                }
                activeFetchCount = Math.max(0, activeFetchCount - 1);
                return promise;
            } catch (err) {
                activeFetchCount = Math.max(0, activeFetchCount - 1);
                setTimeout(flushPendingAjaxButtons, 60);
                throw err;
            }
        };
        wrappedFetch._sigmaWrapped = true;
        window.fetch = wrappedFetch;
    }

    // --- Automatic Universal Event Listeners ---

    // 1. Automatic Form Submit Handler (Bubble Phase: runs after onsubmit handlers so e.defaultPrevented & origHtml are respected)
    document.addEventListener('submit', function(e) {
        const form = e.target;
        if (!form || !(form instanceof HTMLFormElement)) return;

        // If form has standard HTML5 invalid fields, don't spin yet
        if (typeof form.checkValidity === 'function' && !form.checkValidity()) {
            return;
        }

        // Identify the submit button (modern submitter API with fallback)
        let submitBtn = e.submitter;
        if (!submitBtn) {
            submitBtn = form.querySelector('button[type="submit"]:not([disabled]), input[type="submit"]:not([disabled]), button.is-spinning-lock');
        }

        if (!submitBtn) return;

        // If form submission was intercepted by an in-page JS handler (e.preventDefault()):
        if (e.defaultPrevented) {
            spinAndLock(submitBtn);
            pendingAjaxButtons.add(submitBtn);
            // If the handler was purely local (like addToScope) or exited early without starting a fetch, unlock immediately:
            setTimeout(function() {
                if (activeFetchCount === 0) {
                    restoreButton(submitBtn);
                    pendingAjaxButtons.delete(submitBtn);
                    finishTopProgress();
                }
            }, 65);
            return;
        }

        // Standard full-page form submission:
        spinAndLock(submitBtn);

        // Special handling for file exports and downloads (where page does not reload)
        const action = (form.getAttribute('action') || '').toLowerCase();
        const isDownload = action.includes('export') || action.includes('download') || 
                           form.target === '_blank' || submitBtn.classList.contains('js-download-btn');
        if (isDownload) {
            setTimeout(() => restoreButton(submitBtn), 4000);
        } else {
            startTopProgress();
        }
    }, false);

    // 2. Click Handler for Explicit Spin Buttons (buttons with data-spin="true" or .js-spin-lock)
    document.addEventListener('click', function(e) {
        const btn = e.target.closest('button[data-spin="true"], .js-spin-lock, .sigma-spin-on-click');
        if (btn && btn.type !== 'submit') {
            spinAndLock(btn);
            pendingAjaxButtons.add(btn);
            setTimeout(function() {
                if (activeFetchCount === 0 && !isPageUnloading) {
                    restoreButton(btn);
                    pendingAjaxButtons.delete(btn);
                }
            }, 400);
        }
    }, false);

    // 3. Navigation Ribbon & Menu Tab Click Handler (Technique A)
    document.addEventListener('click', function(e) {
        // Match split tabs (.sigma-split-main), ribbon buttons (.sigma-nav-btn), jump items (.sigma-jump-item)
        const navLink = e.target.closest('.sigma-split-main, .sigma-nav-btn, .sigma-jump-item');
        if (!navLink) return;

        const href = navLink.getAttribute('href');
        // Ignore anchors on current page, modals, or javascript: links
        if (!href || href.startsWith('#') || href.startsWith('javascript:')) return;

        // If clicking the exact currently active URL, ignore
        if (navLink.href === window.location.href) return;

        // Find tab container
        const splitTab = navLink.closest('.sigma-split-tab') || navLink;
        if (splitTab.classList.contains('tab-is-loading')) return;

        splitTab.classList.add('tab-is-loading');
        splitTab.style.pointerEvents = 'none';

        // Transform icon into spinner
        const icon = navLink.querySelector('i.fas, i.far, svg');
        if (icon) {
            const spinner = document.createElement('span');
            spinner.className = 'sigma-spin-circle nav-spin';
            spinner.setAttribute('aria-hidden', 'true');
            icon.parentNode.replaceChild(spinner, icon);
        }

        // Trigger top progress line
        startTopProgress();

        // Soft-dim main workspace content to signal data transition
        const mainContent = document.querySelector('.bo-main, .isc-card.fluid-data, .isc-view:not([style*="none"])');
        if (mainContent) {
            mainContent.classList.add('table-view-fading');
        }
    }, true);

    // 4. Page Show Handler (restores buttons and tabs if user presses browser back button / bfcache)
    window.addEventListener('pageshow', function(event) {
        isPageUnloading = false;
        document.querySelectorAll('.is-spinning-lock').forEach(function(lockedBtn) {
            restoreButton(lockedBtn);
        });
        pendingAjaxButtons.clear();
        document.querySelectorAll('.tab-is-loading').forEach(function(tab) {
            tab.classList.remove('tab-is-loading');
            tab.style.pointerEvents = '';
        });
        const mainContent = document.querySelector('.table-view-fading');
        if (mainContent) {
            mainContent.classList.remove('table-view-fading');
        }
        finishTopProgress();
    });

})();
