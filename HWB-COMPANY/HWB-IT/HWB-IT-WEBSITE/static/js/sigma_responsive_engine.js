/**
 * SigmaFidelity™ Universal Phone, Tablet & Adaptive Data-Table Engine (BUG-137 / 2026)
 * Scope: All Public Pages, Shared Manuals, and Backoffice Operations Modules
 * Target Viewports:
 *   - Smartphones (<= 768px: Apple iPhone 390px-430px, Google Pixel 9 412px)
 *   - Tablets (769px - 1024px: iPad & Android Tablets)
 *
 * Permanent Self-Healing Capabilities:
 *   1. Injects universal responsive CSS guardrails if not already present.
 *   2. Automatically binds <thead><th> column headers to <td>[data-label] across all
 *      current and future tables via MutationObserver.
 *   3. Converts wide data tables into 2-column CRM Touch Cards on phones (<= 768px)
 *      while providing a persistent [Cards | Table] view switcher stored in localStorage.
 *   4. Automatically classifies inline multi-column grids (repeat(4, 1fr), 2fr 1fr, etc.)
 *      so future modules collapse cleanly to 2 columns on tablets and 1-2 columns on phones.
 *   5. Provides an off-canvas slide-out drawer toggle for the QMS & Application Manual
 *      sidebar (.qms-sidebar) on screens <= 1024px.
 */
(function () {
    'use strict';

    if (window.SigmaResponsiveTableEngine) return;

    const STORAGE_KEY_MODE = 'sigma_mobile_table_mode'; // 'cards' (default) | 'table'

    const UNIVERSAL_CSS = `
/* === SigmaFidelity Universal Phone, Tablet & Data-Table Engine (BUG-137) === */
@media (max-width: 1024px) {
    html, body {
        max-width: 100vw !important;
        overflow-x: hidden !important;
        -webkit-text-size-adjust: 100%;
    }
    .top-utility-bar {
        padding: 0.4rem clamp(10px, 2.5vw, 20px) !important;
        max-width: 100vw !important;
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch;
    }
    .top-utility-bar > div {
        flex-wrap: nowrap !important;
        gap: 0.5rem !important;
        min-width: max-content;
    }
    /* Single-row horizontal swipe department ribbon on tablets and phones */
    .sigma-nav-ribbon {
        flex-wrap: nowrap !important;
        overflow-x: auto !important;
        overflow-y: hidden !important;
        -webkit-overflow-scrolling: touch;
        scrollbar-width: none;
        padding-bottom: 0.5rem !important;
        margin-bottom: 0.85rem !important;
        gap: 0.45rem !important;
        max-width: 100%;
    }
    .sigma-nav-ribbon::-webkit-scrollbar {
        display: none;
    }
    .sigma-split-tab,
    .sigma-nav-btn {
        flex: 0 0 auto !important;
        white-space: nowrap !important;
    }
    /* Prevent overflow-x clipping of flyout menus on tablets and phones */
    .sigma-jump-menu,
    .sigma-jump-menu.sigma-jump-menu-right,
    #add-menu {
        position: fixed !important;
        left: 12px !important;
        right: 12px !important;
        top: 68px !important;
        width: auto !important;
        min-width: 0 !important;
        max-width: calc(100vw - 24px) !important;
        max-height: 78dvh !important;
        overflow-y: auto !important;
        -webkit-overflow-scrolling: touch;
        z-index: 4500 !important;
    }
    /* Tablet 2-Column KPI Scorecards & Stacked Split Panels */
    [style*="repeat(4, 1fr)"],
    [style*="repeat(4,1fr)"],
    .kpi-rack,
    .kpi-grid,
    .audit-strip,
    [data-sigma-grid="kpi-4"] {
        grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
        gap: 0.85rem !important;
    }
    .workspace-grid,
    [style*="1fr 380px"],
    [style*="380px 1fr"],
    [style*="280px 1fr"],
    [style*="1.5fr 1fr"],
    [style*="2fr 1fr"],
    [data-sigma-grid="split"] {
        grid-template-columns: 1fr !important;
        gap: 1.15rem !important;
    }
    /* Smooth horizontal scroll wrapper for all tables on tablets */
    .isc-table-wrap,
    .sigma-table-scroll-wrap {
        width: 100% !important;
        max-width: 100% !important;
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch !important;
    }
    /* QMS & Application Manual Off-Canvas Drawer on Tablets & Phones */
    body.qms-clinical-shell .main-header {
        display: none !important;
    }
    body.qms-clinical-shell .qms-sidebar {
        top: 48px !important;
        height: calc(100dvh - 48px) !important;
        width: min(310px, 86vw) !important;
        transform: translateX(-105%) !important;
        transition: transform 0.25s cubic-bezier(0.2, 0.8, 0.2, 1) !important;
        z-index: 4800 !important;
        border-top-right-radius: 12px !important;
    }
    body.qms-clinical-shell.qms-drawer-open .qms-sidebar {
        transform: translateX(0) !important;
    }
    body.qms-clinical-shell .qms-main {
        margin-left: 0 !important;
        margin-top: 52px !important;
        padding: 1.25rem clamp(12px, 3vw, 24px) !important;
        grid-template-columns: 1fr !important;
        gap: 1.5rem !important;
        width: 100% !important;
        max-width: 100vw !important;
        box-sizing: border-box !important;
    }
    body.qms-clinical-shell .qms-toc-container {
        display: none !important;
    }
    .sigma-qms-drawer-btn {
        display: inline-flex !important;
        align-items: center;
        gap: 0.5rem;
        background: #0f172a;
        color: #ffffff;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 0.55rem 0.95rem;
        font-size: 0.82rem;
        font-weight: 800;
        cursor: pointer;
        margin-bottom: 1rem;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.12);
    }
    .sigma-qms-backdrop {
        display: none;
        position: fixed;
        inset: 0;
        background: rgba(15, 23, 42, 0.45);
        backdrop-filter: blur(2px);
        z-index: 4700;
    }
    body.qms-clinical-shell.qms-drawer-open .sigma-qms-backdrop {
        display: block !important;
    }
}

@media (min-width: 1025px) {
    .sigma-qms-drawer-btn,
    .sigma-qms-backdrop {
        display: none !important;
    }
}

@media (max-width: 768px) {
    /* Consolidate Backoffice Top Headers on Smartphones */
    body.backoffice-body .main-header {
        display: none !important;
    }
    body.backoffice-body .bo-command-bar {
        padding: 0.45rem 4px !important;
        margin-bottom: 0.65rem !important;
        flex-direction: row !important;
        flex-wrap: wrap !important;
        justify-content: space-between !important;
        align-items: center !important;
        gap: 0.5rem !important;
    }
    body.backoffice-body footer {
        padding: 1.5rem 12px !important;
        margin-top: 2.5rem !important;
    }
    /* 2x2 Compact KPI Scorecards on Phones */
    [style*="repeat(4, 1fr)"],
    [style*="repeat(4,1fr)"],
    [style*="repeat(3, 1fr)"],
    [style*="repeat(3,1fr)"],
    .kpi-rack,
    .kpi-grid,
    .audit-strip,
    [data-sigma-grid="kpi-4"],
    [data-sigma-grid="kpi-3"] {
        grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
        gap: 0.6rem !important;
    }
    /* Single-Column Split Grids & Form Grids on Phones */
    [style*="1fr 1fr"],
    [style*="2fr 1fr"],
    [style*="1fr 2fr"],
    [style*="1.5fr 1fr"],
    [style*="1fr 380px"],
    [style*="380px 1fr"],
    [style*="280px 1fr"],
    .two-col-grid,
    .workspace-grid,
    [data-sigma-grid="split"],
    .isc-modal [style*="grid-template-columns"],
    form [style*="grid-template-columns"] {
        grid-template-columns: 1fr !important;
        gap: 0.85rem !important;
    }
    /* Prevent Search Inputs & Select Filters from Overflowing Phone Width */
    input[style*="min-width"],
    input[style*="width: 2"],
    select[style*="min-width"],
    .search-box {
        min-width: 0 !important;
        width: 100% !important;
        max-width: 100% !important;
        flex: 1 1 100% !important;
    }
    /* Swipeable Filter Chip Rails on Phones */
    #leads-category-bar,
    #leads-stage-bar,
    #accounts-filter-bar,
    #bids-filter-bar,
    #dispatch-filter-bar,
    .filter-controls {
        flex-wrap: nowrap !important;
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch;
        scrollbar-width: none;
        max-width: 100% !important;
        padding-bottom: 4px !important;
    }
    #leads-category-bar::-webkit-scrollbar,
    #leads-stage-bar::-webkit-scrollbar,
    .filter-controls::-webkit-scrollbar {
        display: none;
    }
    #leads-category-bar > *,
    #leads-stage-bar > *,
    .filter-controls > * {
        flex: 0 0 auto !important;
        white-space: nowrap !important;
    }

    /* === Enterprise Adaptive Table-to-Card Mode on Smartphones (<= 768px) === */
    .sigma-table-mode-bar {
        display: flex !important;
        justify-content: space-between;
        align-items: center;
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 0.4rem 0.65rem;
        margin-bottom: 0.65rem;
        gap: 0.5rem;
    }
    .sigma-table-mode-label {
        font-size: 0.72rem;
        font-weight: 800;
        color: #475569;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .sigma-table-mode-pills {
        display: inline-flex;
        background: #e2e8f0;
        border-radius: 6px;
        padding: 2px;
        gap: 2px;
    }
    .sigma-table-mode-btn {
        border: none;
        background: transparent;
        color: #475569;
        font-size: 0.72rem;
        font-weight: 800;
        padding: 0.3rem 0.6rem;
        border-radius: 5px;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    .sigma-table-mode-btn.active {
        background: #2563eb;
        color: #ffffff;
        box-shadow: 0 1px 3px rgba(37, 99, 235, 0.25);
    }

    body.sigma-phone-card-mode table[data-sigma-responsive="true"] {
        display: block !important;
        width: 100% !important;
        min-width: 0 !important;
        border: none !important;
        background: transparent !important;
    }
    body.sigma-phone-card-mode table[data-sigma-responsive="true"] thead {
        display: none !important;
    }
    body.sigma-phone-card-mode table[data-sigma-responsive="true"] tbody {
        display: block !important;
        width: 100% !important;
        min-width: 0 !important;
    }
    body.sigma-phone-card-mode table[data-sigma-responsive="true"] tbody tr {
        display: grid !important;
        grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
        gap: 0.5rem 0.75rem !important;
        background: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 12px !important;
        padding: 0.85rem 0.95rem !important;
        margin-bottom: 0.75rem !important;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05) !important;
        height: auto !important;
        width: 100% !important;
        box-sizing: border-box !important;
    }
    body.sigma-phone-card-mode table[data-sigma-responsive="true"] tbody td {
        display: flex !important;
        flex-direction: column !important;
        align-items: flex-start !important;
        justify-content: flex-start !important;
        padding: 0.2rem 0 !important;
        border: none !important;
        width: 100% !important;
        min-width: 0 !important;
        max-width: 100% !important;
        white-space: normal !important;
        word-break: break-word !important;
        position: static !important;
        background: transparent !important;
        box-shadow: none !important;
        text-align: left !important;
        font-size: 0.84rem !important;
    }
    body.sigma-phone-card-mode table[data-sigma-responsive="true"] tbody td[data-label]::before {
        content: attr(data-label);
        font-size: 0.64rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #64748b;
        margin-bottom: 0.15rem;
        display: block;
        line-height: 1.2;
    }
    body.sigma-phone-card-mode table[data-sigma-responsive="true"] tbody td.sigma-card-primary-cell,
    body.sigma-phone-card-mode table[data-sigma-responsive="true"] tbody td[data-col-title="true"],
    body.sigma-phone-card-mode table[data-sigma-responsive="true"] tbody td[colspan] {
        grid-column: 1 / -1 !important;
        border-bottom: 1px solid #f1f5f9 !important;
        padding-bottom: 0.45rem !important;
        margin-bottom: 0.1rem !important;
        font-size: 0.94rem !important;
    }
    body.sigma-phone-card-mode table[data-sigma-responsive="true"] tbody td.sigma-card-checkbox-cell {
        grid-column: 1 / -1 !important;
        flex-direction: row !important;
        align-items: center !important;
        justify-content: space-between !important;
        padding-bottom: 0.2rem !important;
    }
    body.sigma-phone-card-mode table[data-sigma-responsive="true"] tbody td.sigma-card-actions-cell,
    body.sigma-phone-card-mode table[data-sigma-responsive="true"] tbody td[data-col-actions="true"] {
        grid-column: 1 / -1 !important;
        border-top: 1px solid #f1f5f9 !important;
        padding-top: 0.5rem !important;
        margin-top: 0.15rem !important;
        flex-direction: row !important;
        flex-wrap: wrap !important;
        align-items: center !important;
        justify-content: flex-end !important;
        gap: 0.45rem !important;
    }
    body.sigma-phone-card-mode table[data-sigma-responsive="true"] tbody td[data-cell-empty="true"] {
        display: none !important;
    }
}

@media (min-width: 769px) {
    .sigma-table-mode-bar {
        display: none !important;
    }
}

/* === Universal Dual Horizontal Scrollbar (Top Rail + Sticky Bottom Dock) Engine (BUG-168) === */
.isc-table-wrap,
.sigma-table-scroll-wrap {
    width: 100%;
    max-width: 100%;
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: auto;
    scrollbar-color: #64748b #f1f5f9;
    position: relative;
}
.isc-table-wrap::-webkit-scrollbar,
.sigma-table-scroll-wrap::-webkit-scrollbar,
.sigma-top-scroll-track::-webkit-scrollbar,
.sigma-sticky-bottom-track::-webkit-scrollbar {
    height: 11px;
}
.isc-table-wrap::-webkit-scrollbar-track,
.sigma-table-scroll-wrap::-webkit-scrollbar-track,
.sigma-top-scroll-track::-webkit-scrollbar-track,
.sigma-sticky-bottom-track::-webkit-scrollbar-track {
    background: #f1f5f9;
    border-radius: 6px;
}
.isc-table-wrap::-webkit-scrollbar-thumb,
.sigma-table-scroll-wrap::-webkit-scrollbar-thumb,
.sigma-top-scroll-track::-webkit-scrollbar-thumb,
.sigma-sticky-bottom-track::-webkit-scrollbar-thumb {
    background: #64748b;
    border-radius: 6px;
    border: 2px solid #f1f5f9;
}
.isc-table-wrap::-webkit-scrollbar-thumb:hover,
.sigma-table-scroll-wrap::-webkit-scrollbar-thumb:hover,
.sigma-top-scroll-track::-webkit-scrollbar-thumb:hover,
.sigma-sticky-bottom-track::-webkit-scrollbar-thumb:hover {
    background: #2563eb;
}
.sigma-table-scroll-wrap.has-right-overflow {
    box-shadow: inset -12px 0 12px -10px rgba(15, 23, 42, 0.16);
}
.sigma-top-scroll-rail {
    display: none;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 0.35rem 0.65rem;
    margin-bottom: 0.45rem;
    box-sizing: border-box;
    width: 100%;
}
.sigma-top-scroll-rail.is-active {
    display: flex;
}
.sigma-top-scroll-meta {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    flex-shrink: 0;
}
.sigma-top-scroll-badge {
    font-size: 0.68rem;
    font-weight: 800;
    color: #1e40af;
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 999px;
    padding: 0.15rem 0.55rem;
    white-space: nowrap;
    letter-spacing: 0.02em;
}
.sigma-top-scroll-btns {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
}
.sigma-scroll-step-btn {
    height: 24px;
    padding: 0 0.5rem;
    font-size: 0.68rem;
    font-weight: 800;
    color: #334155;
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 5px;
    cursor: pointer;
    line-height: 1;
    transition: all 0.15s ease;
    white-space: nowrap;
}
.sigma-scroll-step-btn:hover:not(:disabled) {
    background: #2563eb;
    color: #ffffff;
    border-color: #2563eb;
}
.sigma-scroll-step-btn:disabled {
    opacity: 0.4;
    cursor: default;
}
.sigma-top-scroll-track {
    flex: 1 1 auto;
    overflow-x: auto;
    overflow-y: hidden;
    height: 12px;
    min-width: 100px;
    scrollbar-width: auto;
    scrollbar-color: #64748b #e2e8f0;
}
.sigma-top-scroll-spacer {
    height: 1px;
}
.sigma-sticky-bottom-scrollbar {
    position: fixed;
    bottom: 0;
    left: 0;
    width: 100%;
    z-index: 940;
    background: rgba(248, 250, 252, 0.96);
    border-top: 1px solid #cbd5e1;
    box-shadow: 0 -4px 12px rgba(15, 23, 42, 0.08);
    padding: 3px 8px;
    box-sizing: border-box;
    backdrop-filter: blur(4px);
    display: none;
}
.sigma-sticky-bottom-scrollbar.is-visible {
    display: block;
}
.sigma-sticky-bottom-track {
    width: 100%;
    overflow-x: auto;
    overflow-y: hidden;
    height: 13px;
    scrollbar-width: auto;
    scrollbar-color: #475569 #e2e8f0;
}
.sigma-sticky-bottom-spacer {
    height: 1px;
}
@media (max-width: 768px) {
    body.sigma-phone-card-mode .sigma-top-scroll-rail,
    body.sigma-phone-card-mode .sigma-sticky-bottom-scrollbar {
        display: none !important;
    }
}
`;

    function injectUniversalStyles() {
        if (document.getElementById('sigma-universal-responsive-styles')) return;
        const style = document.createElement('style');
        style.id = 'sigma-universal-responsive-styles';
        style.textContent = UNIVERSAL_CSS;
        (document.head || document.documentElement).appendChild(style);
    }

    function getSavedTableMode() {
        try {
            return localStorage.getItem(STORAGE_KEY_MODE) || 'cards';
        } catch (e) {
            return 'cards';
        }
    }

    function applyTableModeClass(mode) {
        if (!document.body) return;
        const activeMode = mode || getSavedTableMode();
        if (activeMode === 'table') {
            document.body.classList.remove('sigma-phone-card-mode');
            document.body.classList.add('sigma-phone-table-mode');
        } else {
            document.body.classList.add('sigma-phone-card-mode');
            document.body.classList.remove('sigma-phone-table-mode');
        }
        document.querySelectorAll('.sigma-table-mode-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.mode === activeMode);
        });
    }

    function setTableMode(mode) {
        try {
            localStorage.setItem(STORAGE_KEY_MODE, mode);
        } catch (e) {}
        applyTableModeClass(mode);
    }

    /**
     * Scans any inline grid-template-columns elements and tags them with
     * data-sigma-grid="kpi-4" | "kpi-3" | "split" for automatic responsive layout.
     */
    function hydrateResponsiveGrids(root) {
        const scope = root && root.querySelectorAll ? root : document;
        scope.querySelectorAll('[style*="grid-template-columns"]').forEach(el => {
            if (el.dataset.sigmaGrid) return;
            const st = (el.getAttribute('style') || '').toLowerCase();
            if (st.includes('repeat(4')) {
                el.dataset.sigmaGrid = 'kpi-4';
            } else if (st.includes('repeat(3')) {
                el.dataset.sigmaGrid = 'kpi-3';
            } else if (st.includes('fr') || st.includes('px')) {
                el.dataset.sigmaGrid = 'split';
            }
        });
    }

    let activeStickyWrap = null;
    let stickyBottomBar = null;
    let stickyBottomTrack = null;
    let stickyBottomSpacer = null;
    let isStickySyncing = false;
    let sharedResizeObserver = null;

    function ensureStickyBottomScrollbar() {
        if (!document.body) return null;
        if (stickyBottomBar && document.body.contains(stickyBottomBar)) return stickyBottomBar;

        stickyBottomBar = document.getElementById('sigma-sticky-bottom-scrollbar');
        if (!stickyBottomBar) {
            stickyBottomBar = document.createElement('div');
            stickyBottomBar.id = 'sigma-sticky-bottom-scrollbar';
            stickyBottomBar.className = 'sigma-sticky-bottom-scrollbar';
            stickyBottomBar.setAttribute('aria-label', 'Sticky bottom horizontal table scrollbar');
            stickyBottomBar.innerHTML = `
                <div class="sigma-sticky-bottom-track" title="Drag to scroll table columns left or right">
                    <div class="sigma-sticky-bottom-spacer"></div>
                </div>
            `;
            document.body.appendChild(stickyBottomBar);
        }
        stickyBottomTrack = stickyBottomBar.querySelector('.sigma-sticky-bottom-track');
        stickyBottomSpacer = stickyBottomBar.querySelector('.sigma-sticky-bottom-spacer');

        if (stickyBottomTrack && !stickyBottomTrack.dataset.boundScroll) {
            stickyBottomTrack.dataset.boundScroll = 'true';
            stickyBottomTrack.addEventListener('scroll', function () {
                if (isStickySyncing || !activeStickyWrap) return;
                isStickySyncing = true;
                activeStickyWrap.scrollLeft = stickyBottomTrack.scrollLeft;
                if (activeStickyWrap._sigmaTopTrack) {
                    activeStickyWrap._sigmaTopTrack.scrollLeft = stickyBottomTrack.scrollLeft;
                }
                updateWrapEdgeCues(activeStickyWrap);
                window.requestAnimationFrame(function () {
                    isStickySyncing = false;
                });
            }, { passive: true });
        }
        return stickyBottomBar;
    }

    function updateWrapEdgeCues(wrap) {
        if (!wrap) return;
        const maxScroll = Math.max(0, wrap.scrollWidth - wrap.clientWidth);
        const hasOverflow = maxScroll > 6;
        const atStart = wrap.scrollLeft <= 2;
        const atEnd = wrap.scrollLeft >= maxScroll - 3;

        wrap.classList.toggle('has-right-overflow', hasOverflow && !atEnd);
        wrap.classList.toggle('has-left-overflow', hasOverflow && !atStart);

        const rail = wrap._sigmaTopRail;
        if (rail) {
            const btnStart = rail.querySelector('[data-dir="start"]');
            const btnLeft = rail.querySelector('[data-dir="left"]');
            const btnRight = rail.querySelector('[data-dir="right"]');
            const btnEnd = rail.querySelector('[data-dir="end"]');
            if (btnStart) btnStart.disabled = atStart;
            if (btnLeft) btnLeft.disabled = atStart;
            if (btnRight) btnRight.disabled = atEnd;
            if (btnEnd) btnEnd.disabled = atEnd;
        }
    }

    function syncSingleWrapMetrics(wrap) {
        if (!wrap) return;
        const maxScroll = Math.max(0, wrap.scrollWidth - wrap.clientWidth);
        const hasOverflow = maxScroll > 6 && wrap.clientWidth > 0;
        const rail = wrap._sigmaTopRail;
        const topTrack = wrap._sigmaTopTrack;
        const topSpacer = wrap._sigmaTopSpacer;

        if (rail && topTrack && topSpacer) {
            if (hasOverflow) {
                rail.classList.add('is-active');
                rail.style.display = '';
                topSpacer.style.width = wrap.scrollWidth + 'px';
                if (Math.abs(topTrack.scrollLeft - wrap.scrollLeft) > 1) {
                    topTrack.scrollLeft = wrap.scrollLeft;
                }
            } else {
                rail.classList.remove('is-active');
                rail.style.display = 'none';
            }
        }
        updateWrapEdgeCues(wrap);
    }

    function updateStickyBottomScrollbar() {
        ensureStickyBottomScrollbar();
        if (!stickyBottomBar || !stickyBottomTrack || !stickyBottomSpacer) return;

        if (window.innerWidth <= 768 && document.body && document.body.classList.contains('sigma-phone-card-mode')) {
            stickyBottomBar.classList.remove('is-visible');
            activeStickyWrap = null;
            return;
        }

        const wraps = document.querySelectorAll('.sigma-table-scroll-wrap, .isc-table-wrap');
        let candidate = null;
        const vh = window.innerHeight || document.documentElement.clientHeight || 800;

        for (let i = 0; i < wraps.length; i++) {
            const w = wraps[i];
            if (!w || w.offsetParent === null) continue;
            const maxScroll = w.scrollWidth - w.clientWidth;
            if (maxScroll <= 6) continue;

            const rect = w.getBoundingClientRect();
            if (rect.width < 120 || rect.height < 60) continue;

            // Show sticky bottom bar when the table is in view but its native bottom scrollbar is below the viewport
            if (rect.top < vh - 64 && rect.bottom > vh + 12) {
                candidate = { wrap: w, rect: rect };
                break;
            }
        }

        if (!candidate) {
            stickyBottomBar.classList.remove('is-visible');
            activeStickyWrap = null;
            return;
        }

        activeStickyWrap = candidate.wrap;
        const leftPx = Math.max(0, Math.round(candidate.rect.left));
        const widthPx = Math.max(120, Math.min(Math.round(candidate.rect.width), window.innerWidth - leftPx));

        stickyBottomBar.style.left = leftPx + 'px';
        stickyBottomBar.style.width = widthPx + 'px';
        stickyBottomSpacer.style.width = activeStickyWrap.scrollWidth + 'px';
        stickyBottomBar.classList.add('is-visible');

        if (!isStickySyncing && Math.abs(stickyBottomTrack.scrollLeft - activeStickyWrap.scrollLeft) > 1) {
            isStickySyncing = true;
            stickyBottomTrack.scrollLeft = activeStickyWrap.scrollLeft;
            window.requestAnimationFrame(function () {
                isStickySyncing = false;
            });
        }
    }

    function refreshAllScrollbars() {
        document.querySelectorAll('.sigma-table-scroll-wrap, .isc-table-wrap').forEach(syncSingleWrapMetrics);
        updateStickyBottomScrollbar();
    }

    function resolveTableScrollWrap(table) {
        const parent = table.parentElement;
        if (!parent) return null;
        if (parent.matches('.isc-table-wrap, .sigma-table-scroll-wrap, .table-responsive')) {
            parent.classList.add('sigma-table-scroll-wrap');
            return parent;
        }
        const parentStyle = (parent.getAttribute('style') || '').toLowerCase();
        if (parentStyle.includes('overflow-x')) {
            parent.classList.add('sigma-table-scroll-wrap');
            return parent;
        }
        // If parent has only the table (or table + mode bar), mark parent directly; otherwise wrap table cleanly
        const nonMetaChildren = Array.from(parent.children).filter(
            ch => !ch.classList.contains('sigma-table-mode-bar') && !ch.classList.contains('sigma-top-scroll-rail')
        );
        if (nonMetaChildren.length === 1 && nonMetaChildren[0] === table) {
            parent.classList.add('sigma-table-scroll-wrap');
            return parent;
        }
        const wrapper = document.createElement('div');
        wrapper.className = 'sigma-table-scroll-wrap';
        parent.insertBefore(wrapper, table);
        wrapper.appendChild(table);
        return wrapper;
    }

    function bindDualTableScrollbars(table, wrap) {
        if (!wrap) return;
        if (wrap.dataset.sigmaScrollBound === 'true') {
            syncSingleWrapMetrics(wrap);
            return;
        }
        wrap.dataset.sigmaScrollBound = 'true';

        if (wrap.parentElement && !wrap.previousElementSibling?.classList?.contains('sigma-top-scroll-rail')) {
            const rail = document.createElement('div');
            rail.className = 'sigma-top-scroll-rail';
            rail.setAttribute('aria-label', 'Horizontal column scroll controls');
            rail.innerHTML = `
                <div class="sigma-top-scroll-meta">
                    <span class="sigma-top-scroll-badge" title="More columns extend to the right — drag scrollbar, click arrows, or hold Shift + Mouse Wheel"><i class="fas fa-arrows-alt-h"></i> Scroll Columns</span>
                    <div class="sigma-top-scroll-btns">
                        <button type="button" class="sigma-scroll-step-btn" data-dir="start" title="Jump to leftmost column">⏮</button>
                        <button type="button" class="sigma-scroll-step-btn" data-dir="left" title="Scroll columns left">◀ Left</button>
                        <button type="button" class="sigma-scroll-step-btn" data-dir="right" title="Scroll columns right">Right ▶</button>
                        <button type="button" class="sigma-scroll-step-btn" data-dir="end" title="Jump to rightmost column">⏭</button>
                    </div>
                </div>
                <div class="sigma-top-scroll-track" title="Drag to scroll columns left or right">
                    <div class="sigma-top-scroll-spacer"></div>
                </div>
            `;
            wrap.parentElement.insertBefore(rail, wrap);

            const topTrack = rail.querySelector('.sigma-top-scroll-track');
            const topSpacer = rail.querySelector('.sigma-top-scroll-spacer');
            wrap._sigmaTopRail = rail;
            wrap._sigmaTopTrack = topTrack;
            wrap._sigmaTopSpacer = topSpacer;

            let isLocalSyncing = false;
            topTrack.addEventListener('scroll', function () {
                if (isLocalSyncing) return;
                isLocalSyncing = true;
                wrap.scrollLeft = topTrack.scrollLeft;
                if (activeStickyWrap === wrap && stickyBottomTrack) {
                    stickyBottomTrack.scrollLeft = topTrack.scrollLeft;
                }
                updateWrapEdgeCues(wrap);
                window.requestAnimationFrame(function () {
                    isLocalSyncing = false;
                });
            }, { passive: true });

            wrap.addEventListener('scroll', function () {
                if (!isLocalSyncing && topTrack) {
                    isLocalSyncing = true;
                    topTrack.scrollLeft = wrap.scrollLeft;
                    window.requestAnimationFrame(function () {
                        isLocalSyncing = false;
                    });
                }
                if (!isStickySyncing && activeStickyWrap === wrap && stickyBottomTrack) {
                    isStickySyncing = true;
                    stickyBottomTrack.scrollLeft = wrap.scrollLeft;
                    window.requestAnimationFrame(function () {
                        isStickySyncing = false;
                    });
                }
                updateWrapEdgeCues(wrap);
            }, { passive: true });

            rail.querySelectorAll('.sigma-scroll-step-btn').forEach(btn => {
                btn.addEventListener('click', function () {
                    const dir = this.getAttribute('data-dir');
                    const step = Math.max(260, Math.round(wrap.clientWidth * 0.55));
                    if (dir === 'start') {
                        wrap.scrollTo({ left: 0, behavior: 'smooth' });
                    } else if (dir === 'end') {
                        wrap.scrollTo({ left: wrap.scrollWidth, behavior: 'smooth' });
                    } else if (dir === 'left') {
                        wrap.scrollBy({ left: -step, behavior: 'smooth' });
                    } else if (dir === 'right') {
                        wrap.scrollBy({ left: step, behavior: 'smooth' });
                    }
                });
            });
        }

        if (window.ResizeObserver) {
            if (!sharedResizeObserver) {
                let roRaf = null;
                sharedResizeObserver = new ResizeObserver(function () {
                    if (!roRaf) {
                        roRaf = window.requestAnimationFrame(function () {
                            roRaf = null;
                            refreshAllScrollbars();
                        });
                    }
                });
            }
            sharedResizeObserver.observe(wrap);
            sharedResizeObserver.observe(table);
        }

        syncSingleWrapMetrics(wrap);
    }

    /**
     * Hydrates a single <table> with data-label attributes, responsive scroll wrapper,
     * dual horizontal scrollbars (top rail + sticky bottom dock), and the mobile [Cards | Table] switcher bar.
     */
    function hydrateTable(table) {
        if (!table || !(table instanceof HTMLTableElement)) return;
        const thead = table.querySelector('thead');
        const tbody = table.querySelector('tbody');

        // Only convert structured data tables that have a <thead> or explicit table class
        const isExplicitDataGrid = table.matches('.isc-grid, .isc-grid-expansive, .sigma-table, .leads-table, .field-table');
        if (!thead && !isExplicitDataGrid) return;

        table.setAttribute('data-sigma-responsive', 'true');

        // Ensure table is wrapped in a scrollable container across desktop, tablet, and mobile
        const wrap = resolveTableScrollWrap(table) || table;

        // Inject [Cards | Table] mode switcher bar above primary data tables
        const anchorEl = wrap._sigmaTopRail || wrap;
        if (anchorEl && anchorEl.parentElement && !anchorEl.previousElementSibling?.classList?.contains('sigma-table-mode-bar') && !wrap.previousElementSibling?.classList?.contains('sigma-table-mode-bar')) {
            const currentMode = getSavedTableMode();
            const bar = document.createElement('div');
            bar.className = 'sigma-table-mode-bar';
            bar.innerHTML = `
                <span class="sigma-table-mode-label"><i class="fas fa-mobile-alt"></i> Mobile View</span>
                <div class="sigma-table-mode-pills">
                    <button type="button" class="sigma-table-mode-btn ${currentMode === 'cards' ? 'active' : ''}" data-mode="cards">
                        <i class="fas fa-id-card"></i> Cards
                    </button>
                    <button type="button" class="sigma-table-mode-btn ${currentMode === 'table' ? 'active' : ''}" data-mode="table">
                        <i class="fas fa-table"></i> Table
                    </button>
                </div>
            `;
            bar.querySelectorAll('.sigma-table-mode-btn').forEach(btn => {
                btn.addEventListener('click', function () {
                    setTableMode(this.dataset.mode);
                });
            });
            anchorEl.parentElement.insertBefore(bar, anchorEl);
        }

        // Bind Top Synced Horizontal Scroll Rail + Sticky Bottom Viewport Scrollbar (BUG-168)
        if (wrap !== table) {
            bindDualTableScrollbars(table, wrap);
        }

        // Extract column header labels from <thead>
        const headers = [];
        if (thead) {
            thead.querySelectorAll('tr:first-child th, tr:first-child td').forEach(th => {
                let label = (th.getAttribute('data-col-label') || th.innerText || th.textContent || '').replace(/\s+/g, ' ').trim();
                headers.push(label);
            });
        }

        if (!tbody) return;

        tbody.querySelectorAll('tr').forEach(tr => {
            const cells = Array.from(tr.children).filter(c => c.tagName === 'TD');
            if (cells.length <= 1) return; // Skip colspan empty-state rows

            let foundPrimary = false;
            cells.forEach((td, idx) => {
                const headerText = headers[idx] || '';
                const hasCheckbox = !!td.querySelector('input[type="checkbox"]');

                if (hasCheckbox && idx === 0) {
                    td.classList.add('sigma-card-checkbox-cell');
                    td.removeAttribute('data-label');
                    return;
                }

                if (headerText && !td.hasAttribute('data-label')) {
                    td.setAttribute('data-label', headerText);
                }

                // Identify Primary Identity Cell (first non-checkbox cell or explicit data-col-title)
                if (!foundPrimary && (td.getAttribute('data-col-title') === 'true' || idx === 0 || (idx === 1 && cells[0].classList.contains('sigma-card-checkbox-cell')))) {
                    td.classList.add('sigma-card-primary-cell');
                    foundPrimary = true;
                }

                // Identify Actions Cell (last cell with action buttons/menus or explicit data-col-actions)
                const isLast = idx === cells.length - 1;
                if (td.getAttribute('data-col-actions') === 'true' || headerText.toLowerCase().includes('action') || (isLast && td.querySelector('button, a.isc-btn, .isc-row-menu-wrap'))) {
                    td.classList.add('sigma-card-actions-cell');
                }

                // Detect empty placeholder cells ('--', '—', '') with no interactive controls
                const rawVal = (td.innerText || td.textContent || '').trim();
                const hasControls = !!td.querySelector('input, select, textarea, button, a, img, svg');
                if (!hasControls && (rawVal === '' || rawVal === '--' || rawVal === '—' || rawVal === '-')) {
                    td.setAttribute('data-cell-empty', 'true');
                } else {
                    td.removeAttribute('data-cell-empty');
                }
            });
        });
    }

    function hydrateAllTables(root) {
        const scope = root && root.querySelectorAll ? root : document;
        scope.querySelectorAll('table').forEach(hydrateTable);
        refreshAllScrollbars();
    }

    function initGlobalScrollAndResizeListeners() {
        let scrollRaf = null;
        window.addEventListener('scroll', function () {
            if (!scrollRaf) {
                scrollRaf = window.requestAnimationFrame(function () {
                    scrollRaf = null;
                    updateStickyBottomScrollbar();
                });
            }
        }, { passive: true });

        window.addEventListener('resize', function () {
            if (!scrollRaf) {
                scrollRaf = window.requestAnimationFrame(function () {
                    scrollRaf = null;
                    refreshAllScrollbars();
                });
            }
        }, { passive: true });

        document.addEventListener('click', function (e) {
            if (e.target && e.target.closest && e.target.closest('.sigma-split-tab, .sigma-nav-btn, [onclick*="switchView"], [onclick*="setLeadPreset"], [onclick*="applyColumns"]')) {
                window.setTimeout(refreshAllScrollbars, 60);
            }
        }, true);
    }

    /**
     * Initializes the Off-Canvas Sidebar Drawer for QMS & Application Manuals (/manual, /manual/app)
     * on tablets and smartphones (<= 1024px).
     */
    function initQmsManualDrawer() {
        if (!document.body || !document.body.classList.contains('qms-clinical-shell')) return;
        const main = document.querySelector('.qms-main');
        const sidebar = document.querySelector('.qms-sidebar');
        if (!main || !sidebar || document.getElementById('sigma-qms-drawer-toggle')) return;

        const btn = document.createElement('button');
        btn.type = 'button';
        btn.id = 'sigma-qms-drawer-toggle';
        btn.className = 'sigma-qms-drawer-btn';
        btn.innerHTML = '<i class="fas fa-bars"></i> Manual Sections &amp; Search';

        const backdrop = document.createElement('div');
        backdrop.className = 'sigma-qms-backdrop';

        btn.addEventListener('click', function () {
            document.body.classList.toggle('qms-drawer-open');
        });
        backdrop.addEventListener('click', function () {
            document.body.classList.remove('qms-drawer-open');
        });
        sidebar.addEventListener('click', function (e) {
            if (e.target.closest('a')) {
                document.body.classList.remove('qms-drawer-open');
            }
        });

        main.insertBefore(btn, main.firstChild);
        document.body.appendChild(backdrop);
    }

    /**
     * Automatically centers the active tab in .sigma-nav-ribbon on mobile/tablet load.
     */
    function centerActiveNavTab() {
        if (window.innerWidth > 1024) return;
        const activeTab = document.querySelector('.sigma-nav-ribbon .sigma-split-tab.active, .sigma-nav-ribbon .sigma-nav-btn.active');
        if (activeTab && typeof activeTab.scrollIntoView === 'function') {
            try {
                activeTab.scrollIntoView({ inline: 'center', block: 'nearest', behavior: 'smooth' });
            } catch (e) {}
        }
    }

    /**
     * Initializes the MutationObserver so any future module, dynamic AJAX table row,
     * or newly rendered view automatically inherits responsive table & grid behavior.
     */
    function initMutationObserver() {
        if (!window.MutationObserver || !document.body) return;
        let rafId = null;
        const observer = new MutationObserver(function (mutations) {
            let needsHydration = false;
            for (let i = 0; i < mutations.length; i++) {
                if (mutations[i].addedNodes && mutations[i].addedNodes.length > 0) {
                    needsHydration = true;
                    break;
                }
            }
            if (needsHydration && !rafId) {
                rafId = window.requestAnimationFrame(function () {
                    rafId = null;
                    hydrateAllTables(document);
                    hydrateResponsiveGrids(document);
                });
            }
        });
        observer.observe(document.body, { childList: true, subtree: true });
    }

    function init() {
        injectUniversalStyles();
        ensureStickyBottomScrollbar();
        applyTableModeClass(getSavedTableMode());
        hydrateResponsiveGrids(document);
        hydrateAllTables(document);
        initQmsManualDrawer();
        centerActiveNavTab();
        initGlobalScrollAndResizeListeners();
        initMutationObserver();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    window.SigmaResponsiveTableEngine = {
        hydrateAllTables: hydrateAllTables,
        hydrateTable: hydrateTable,
        hydrateResponsiveGrids: hydrateResponsiveGrids,
        setTableMode: setTableMode,
        refreshAllScrollbars: refreshAllScrollbars
    };
})();
