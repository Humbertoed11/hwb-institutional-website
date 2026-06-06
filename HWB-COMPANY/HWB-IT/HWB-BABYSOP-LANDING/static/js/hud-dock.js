// HEXGROWTH HUD Docking & Draggable Control Standard (Option A)
// Clinically designed for absolute parity, responsiveness, and state synchronization.

(function() {
    // Selectors for docking zones
    const DOCK_ZONES = [
        { id: 'deal-manager', side: 'left' },
        { id: 'stick-ledger', side: 'right' }
    ];

    // Track active dragging state
    let activeDragEl = null;
    let dragOffsetX = 0;
    let dragOffsetY = 0;
    let isUndocking = false;
    let startX = 0;
    let startY = 0;
    let initialDockedState = false;
    
    // Global telemetry to prevent click actions immediately following a drag
    window.HEX_HUD_Dock = {
        lastDragTime: 0,
        init: initDraggables,
        dock: dockElement,
        undock: undockElement
    };

    // Inject css for drag styling and resizable states
    const style = document.createElement('style');
    style.innerHTML = `
        .hud-draggable {
            transition: border-color 0.2s, box-shadow 0.2s;
        }
        .hud-draggable:not(.docked) {
            position: absolute !important;
            z-index: 9999 !important;
            box-shadow: 0 15px 35px rgba(0,0,0,0.8);
            margin: 0 !important;
        }
        .hud-draggable.dragging {
            opacity: 0.85;
            cursor: grabbing !important;
            user-select: none;
            border-color: var(--hex-cyan) !important;
            box-shadow: 0 0 20px rgba(6, 182, 212, 0.4);
        }
        .hud-draggable .card-header, 
        .hud-draggable .legend-header {
            cursor: grab;
            user-select: none;
        }
        .dock-zone-highlight {
            box-shadow: inset 0 0 25px rgba(6, 182, 212, 0.25) !important;
            border: 1.5px dashed var(--hex-cyan) !important;
            transition: all 0.2s ease;
        }
        /* Resizable container style */
        .hud-draggable:not(.docked).resizable {
            resize: both;
            overflow: auto;
            min-width: 200px;
            min-height: 100px;
        }
    `;
    document.head.appendChild(style);

    // Initialize all draggable elements
    function initDraggables() {
        // Find elements with class 'hud-draggable'
        const elements = document.querySelectorAll('.hud-draggable');
        elements.forEach(el => {
            // Find header for dragging handle
            const header = el.querySelector('.card-header') || el.querySelector('.legend-header') || el;
            
            // Check if element is already inside a docking zone initially
            let parentZone = null;
            for (const zone of DOCK_ZONES) {
                const zoneEl = document.getElementById(zone.id);
                if (zoneEl && zoneEl.contains(el)) {
                    parentZone = zoneEl;
                    break;
                }
            }

            if (parentZone) {
                el.classList.add('docked');
            } else {
                el.classList.remove('docked');
                el.classList.add('resizable');
            }

            // Remove existing listener if any, and attach new one
            header.removeEventListener('mousedown', onMouseDownWrapper);
            header.addEventListener('mousedown', (e) => onMouseDownWrapper(e, el));
        });
    }

    function onMouseDownWrapper(e, el) {
        onMouseDown(e, el);
    }

    function onMouseDown(e, el) {
        // Only allow left click
        if (e.button !== 0) return;
        
        // Skip drag if user clicked an interactive input inside the header (like a button or checkbox)
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'BUTTON' || e.target.tagName === 'A' || e.target.closest('.command-chip')) {
            return;
        }

        // Prevent default text selection
        e.preventDefault();

        // Calculate offset from top-left of element
        const rect = el.getBoundingClientRect();
        dragOffsetX = e.clientX - rect.left;
        dragOffsetY = e.clientY - rect.top;

        activeDragEl = el;
        startX = e.clientX;
        startY = e.clientY;
        initialDockedState = el.classList.contains('docked');
        isUndocking = false;

        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);
    }

    function onMouseMove(e) {
        if (!activeDragEl) return;

        const dx = e.clientX - startX;
        const dy = e.clientY - startY;

        if (initialDockedState && !isUndocking) {
            // Only undock if dragged past 8px threshold
            if (Math.sqrt(dx * dx + dy * dy) > 8) {
                undockElement(activeDragEl, e.clientX, e.clientY);
                isUndocking = true;
            }
            return;
        }

        // Standard dragging behavior
        activeDragEl.classList.add('dragging');
        
        // Update position (account for parent offset if attached to container)
        const parentContainer = activeDragEl.offsetParent || document.body;
        const parentRect = parentContainer.getBoundingClientRect();
        
        const left = e.clientX - parentRect.left - dragOffsetX;
        const top = e.clientY - parentRect.top - dragOffsetY;
        
        activeDragEl.style.left = left + 'px';
        activeDragEl.style.top = top + 'px';

        // Check if cursor is over any docking zones to show feedback
        DOCK_ZONES.forEach(zone => {
            const zoneEl = document.getElementById(zone.id);
            if (zoneEl) {
                const zoneRect = zoneEl.getBoundingClientRect();
                if (e.clientX >= zoneRect.left && e.clientX <= zoneRect.right &&
                    e.clientY >= zoneRect.top && e.clientY <= zoneRect.bottom) {
                    zoneEl.classList.add('dock-zone-highlight');
                } else {
                    zoneEl.classList.remove('dock-zone-highlight');
                }
            }
        });
    }

    function onMouseUp(e) {
        if (!activeDragEl) return;

        document.removeEventListener('mousemove', onMouseMove);
        document.removeEventListener('mouseup', onMouseUp);

        activeDragEl.classList.remove('dragging');

        const dx = e.clientX - startX;
        const dy = e.clientY - startY;
        const totalDragDist = Math.sqrt(dx * dx + dy * dy);

        if (totalDragDist > 3) {
            window.HEX_HUD_Dock.lastDragTime = Date.now();
        }

        // Check if dropped in any docking zone
        let dockedToZone = null;
        DOCK_ZONES.forEach(zone => {
            const zoneEl = document.getElementById(zone.id);
            if (zoneEl) {
                zoneEl.classList.remove('dock-zone-highlight');
                
                const zoneRect = zoneEl.getBoundingClientRect();
                if (e.clientX >= zoneRect.left && e.clientX <= zoneRect.right &&
                    e.clientY >= zoneRect.top && e.clientY <= zoneRect.bottom) {
                    dockedToZone = zoneEl;
                }
            }
        });

        if (dockedToZone) {
            dockElement(activeDragEl, dockedToZone);
        } else {
            // Stay floating where dropped
            if (initialDockedState && !isUndocking) {
                // Clicked without dragging, don't change anything
            } else {
                activeDragEl.classList.remove('docked');
                activeDragEl.classList.add('resizable');
            }
        }

        activeDragEl = null;
    }

    function undockElement(el, mouseX, mouseY) {
        const rect = el.getBoundingClientRect();
        
        // Remove from current parent in DOM
        el.parentNode.removeChild(el);
        
        // Reset absolute positioning properties
        el.style.position = 'absolute';
        el.style.width = rect.width + 'px';
        el.style.height = rect.height + 'px';
        
        // Attach to main map container (or fallback to body)
        const mapContainer = document.getElementById('map-container') || document.body;
        mapContainer.appendChild(el);
        
        const mapRect = mapContainer.getBoundingClientRect();
        el.style.left = (mouseX - mapRect.left - dragOffsetX) + 'px';
        el.style.top = (mouseY - mapRect.top - dragOffsetY) + 'px';
        
        el.classList.remove('docked');
        el.classList.add('resizable');
        el.classList.add('dragging');
    }

    function dockElement(el, zoneEl) {
        // Remove from absolute position parent
        el.parentNode.removeChild(el);
        
        // Reset styles for normal document flow
        el.style.position = '';
        el.style.left = '';
        el.style.top = '';
        el.style.width = '';
        el.style.height = '';
        
        el.classList.remove('resizable');
        el.classList.add('docked');

        // Append to the docking container. If the container is a tab container or has specific children slot, put it there.
        // For deal-manager, append to the active tab-content if any.
        if (zoneEl.id === 'deal-manager') {
            const activeTabContent = zoneEl.querySelector('.tab-content.active');
            if (activeTabContent) {
                activeTabContent.appendChild(el);
            } else {
                zoneEl.appendChild(el);
            }
        } else {
            zoneEl.appendChild(el);
        }
    }

    // Run initialization on DOM load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initDraggables);
    } else {
        initDraggables();
    }
})();
