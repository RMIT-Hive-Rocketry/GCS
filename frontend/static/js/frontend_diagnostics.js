/**
 * Horizon Diagnostics Nav Alert + Transition Log
 *
 * Independent diagnostics notification logic.
 * Does not touch graph rendering.
 * Does not use the global sound system.
 *
 * Rules:
 * - ping >= 0 means online
 * - ping < 0 means offline
 * - first packet stores state silently
 * - state changes create a log entry
 * - state changes pulse the Diagnostics nav tab for a few seconds
 */

import { Config as cfg } from '/js/frontend_config.js';

const previous_ping = {}

function isHorizonRocket() {
    return (
        document.body.classList.contains('horizon')
        || window.location.href.includes('rocket=horizon')
    )
}

function getDiagnosticsNavLink() {
    return document.querySelector('nav a[href=\'#page-diagnostics\']')
}

function pulseDiagnosticsNav() {
    // Updates graphs?
    const navLink = getDiagnosticsNavLink()

    if (!navLink) {
        return
    }

    navLink.classList.remove('horizon-diag-nav-alert-pulse')

    // Force browser to restart the animation even if it just ran.
    void navLink.offsetWidth

    navLink.classList.add('horizon-diag-nav-alert-pulse')

    window.clearTimeout(navLink._horizonDiagPulseTimeout)

    navLink._horizonDiagPulseTimeout = window.setTimeout(() => {
        navLink.classList.remove('horizon-diag-nav-alert-pulse')
    }, 5200)
}

function formatLogTime() {
    return new Date().toLocaleTimeString('en-AU', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
    })
}

function addDiagnosticLogEntry(device_id, alive) {
    const logList = document.getElementById('diag-transition-log-list')

    if (!logList) {
        return
    }

    const emptyMessage = document.getElementById('diag-transition-log-empty')

    if (emptyMessage) {
        emptyMessage.remove()
    }

    const entry = document.createElement('div')
    entry.className = `diag-transition-log-entry ${alive ? 'online' : 'offline'}`

    const time = document.createElement('span')
    time.className = 'diag-transition-log-time'
    time.textContent = formatLogTime()

    const device = document.createElement('span')
    device.className = 'diag-transition-log-device'
    device.textContent = device_id

    const state = document.createElement('span')
    state.className = 'diag-transition-log-state'
    state.textContent = alive ? 'ONLINE' : 'OFFLINE'

    entry.appendChild(time)
    entry.appendChild(device)
    entry.appendChild(state)

    // Latest first.
    logList.prepend(entry)

    while (logList.children.length > cfg.logging.max_size_diagnostics) {
        logList.removeChild(logList.lastChild)
    }
}

function processPacket(apiData) {
    if (!isHorizonRocket()) {
        return
    }

    if (!apiData || apiData.id !== 50) {
        return
    }

    // Variable for tracking whether to visually ping the UI (when receiving ping from devices)
    // This *might* end up being removed if it's not useful/too distracting
    let ping_ui = false

    Object.entries(apiData).forEach(([device_id, device_data]) => {
        // Validate device_id
        if (device_id === 'id' || device_id === 'state' || device_id === 'meta') {
            return
        }

        // Validate device_data
        if (typeof device_data !== 'object'
            || device_data === null) {
            return
        }

        // Get ping from device
        if (device_data?.ping) {
            // Ping UI on device (re)connection
            if (device_data.connected && previous_ping[device_id] !== undefined && !previous_ping[device_id].connected) {
                ping_ui = true
            }

            // Track previous ping for comparisons
            previous_ping[device_id] = device_data

            // Log connection state - NEEDS REFACTOR
            // addDiagnosticLogEntry(device_id, is_connected);
        }
    })

    // console.log(previous_ping);

    if (ping_ui) {
        pulseDiagnosticsNav()
    }
}

export { addDiagnosticLogEntry, processPacket }
