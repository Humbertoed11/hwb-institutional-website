/**
 * SigmaFidelity™ Enterprise Client Breadcrumbs & Micro-Interaction Sensor
 * Standard: HWB-QMS-11.2 / SOC 2 CC6.8 / ISO 27001 Control A.8.15
 * Custodian: George (Systems Architect & mbB)
 */
(function() {
    'use strict';

    // 1. Session Identity (Session-scoped anonymous ID)
    const STORAGE_KEY = 'sigma_bc_session_id';
    let sessionId = '';
    try {
        sessionId = sessionStorage.getItem(STORAGE_KEY);
        if (!sessionId) {
            sessionId = 'bc_' + Math.random().toString(36).substring(2, 12) + '_' + Date.now().toString(36);
            sessionStorage.setItem(STORAGE_KEY, sessionId);
        }
    } catch (e) {
        sessionId = 'bc_fallback_' + Date.now();
    }

    const INGESTION_ENDPOINT = '/api/v1/telemetry/breadcrumbs';
    const queue = [];
    const MAX_QUEUE_SIZE = 50;
    const FLUSH_INTERVAL_MS = 15000;
    let lastClickTime = 0;
    let lastClickTarget = null;
    let clickCountOnTarget = 0;

    // 2. Sensitive PII Pattern Guard (Poka-Yoke / TDPSA Compliance)
    const SENSITIVE_PATTERN = /(pass|ssn|tax|card|cvv|account|secret|token)/i;

    function sanitizeText(str) {
        if (!str) return '';
        return String(str).trim().replace(/\s+/g, ' ').substring(0, 100);
    }

    function isSensitiveElement(el) {
        if (!el) return false;
        const type = (el.type || '').toLowerCase();
        if (type === 'password') return true;
        const name = (el.name || '').toLowerCase();
        const id = (el.id || '').toLowerCase();
        return SENSITIVE_PATTERN.test(name) || SENSITIVE_PATTERN.test(id);
    }

    function enqueueEvent(eventType, el, details) {
        if (queue.length >= MAX_QUEUE_SIZE) {
            queue.shift(); // Evict oldest
        }

        let tag = '';
        let elId = '';
        let elClass = '';
        let text = '';

        if (el && el.nodeType === Node.ELEMENT_NODE) {
            tag = (el.tagName || '').toLowerCase();
            elId = (el.id || '').substring(0, 100);
            elClass = (el.className && typeof el.className === 'string' ? el.className : '').substring(0, 150);

            if (!isSensitiveElement(el)) {
                text = sanitizeText(el.innerText || el.getAttribute('aria-label') || el.getAttribute('title') || el.value);
            } else {
                text = '[REDACTED_PII]';
            }
        }

        queue.push({
            event_type: eventType,
            page_url: window.location.pathname.substring(0, 255),
            element_tag: tag,
            element_id: elId,
            element_class: elClass,
            element_text: text,
            details: details || {},
            timestamp: new Date().toISOString()
        });

        // Instant flush on high-severity events
        if (eventType === 'RAGE_CLICK' || eventType === 'JS_ERROR') {
            flushQueue();
        }
    }

    function flushQueue() {
        if (queue.length === 0) return;
        const payload = JSON.stringify({
            session_id: sessionId,
            page_url: window.location.pathname,
            events: queue.splice(0, queue.length)
        });

        if (navigator.sendBeacon) {
            const blob = new Blob([payload], { type: 'application/json' });
            navigator.sendBeacon(INGESTION_ENDPOINT, blob);
        } else {
            fetch(INGESTION_ENDPOINT, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: payload,
                keepalive: true
            }).catch(function() {});
        }
    }

    // 3. Global Click & Rage Click Listener
    document.addEventListener('click', function(e) {
        try {
            const target = e.target;
            if (!target) return;

            const interactive = target.closest('button, a, input, select, textarea, [role="button"], .facility-chip, .calib-city-btn, .calib-freq-btn, .sigma-tab');
            const el = interactive || target;

            // Rage Click Detection: 3+ rapid clicks on same element within 1s
            const now = Date.now();
            if (lastClickTarget === el && (now - lastClickTime) < 1000) {
                clickCountOnTarget++;
                if (clickCountOnTarget === 3) {
                    enqueueEvent('RAGE_CLICK', el, { rapid_clicks: clickCountOnTarget });
                }
            } else {
                lastClickTarget = el;
                clickCountOnTarget = 1;
            }
            lastClickTime = now;

            // Record standard click for interactive elements or named IDs
            if (interactive || el.id || el.getAttribute('data-action')) {
                enqueueEvent('CLICK', el, {
                    x: Math.round(e.clientX),
                    y: Math.round(e.clientY)
                });
            }
        } catch (err) {}
    }, true);

    // 4. Client-Side JavaScript Runtime Error Listener (ISO 27001 A.8.15)
    window.addEventListener('error', function(e) {
        try {
            enqueueEvent('JS_ERROR', null, {
                message: sanitizeText(e.message),
                filename: sanitizeText(e.filename),
                lineno: e.lineno,
                colno: e.colno
            });
        } catch (err) {}
    });

    window.addEventListener('unhandledrejection', function(e) {
        try {
            enqueueEvent('JS_ERROR', null, {
                message: sanitizeText(e.reason ? (e.reason.message || e.reason) : 'Unhandled Promise Rejection')
            });
        } catch (err) {}
    });

    // 5. Lifecycle Flush Triggers
    setInterval(flushQueue, FLUSH_INTERVAL_MS);

    document.addEventListener('visibilitychange', function() {
        if (document.visibilityState === 'hidden') {
            flushQueue();
        }
    });

    window.addEventListener('pagehide', flushQueue);

    // Initial page view event
    enqueueEvent('PAGE_VIEW', null, { referrer: document.referrer || '' });
})();
