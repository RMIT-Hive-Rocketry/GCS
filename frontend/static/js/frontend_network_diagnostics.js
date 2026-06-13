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

function updateNetworkDiagnostics(apiData) {

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

// ================================================================
// DIAGNOSTICS — Full redesign
// Manages: device list cards, ping graphs, status boxes, bottom bar
// Called by frontend_api.js when packet ID 50 arrives
// ================================================================
function diagNowSeconds() {
    return performance.now() / 1000;
}

function diagClampGraphPing(value) {
    return Math.max(1, Math.min(498, value));
}

// Returns a CSS-safe ID string from a device name
function format_device_id(device_id) {
    return device_id.replace(/[^a-z0-9]/gi, "-").toLowerCase();
}

// ── Left panel: create/update a device card ──────────────────────
function diagUpdateDeviceCard(device_id, device_data) {
    // Get safe device ID
    const device_id_safe = format_device_id(device_id);
    const device_list = document.getElementById("diag-device-list");
    if (device_list === undefined)
        return;

    // Network device info element
    let elem = document.getElementById(`diag-card-${device_id_safe}`);
    if (!elem) {
        // Create network device element
        elem = document.createElement("div");
        elem.classList.add("network-device");
        elem.id = `diag-card-${device_id_safe}`;

        // Setup inner html
        elem.innerHTML = `
        <div class="status">
            <div class="indicator-network"></div>
            <span>${device_id}</span>
        </div>
        <div class="details">
            <div>
                <span>Loss</span>
                <span id="${device_id_safe}-loss" ></span>
            </div>
            <div>
                <span>Ping</span>
                <span id="${device_id_safe}-ping"></span>
            </div>
            <div>
                <span>Packets</span>
                <span id="${device_id_safe}-packets"></span>
            </div>
        </div>
        `;

        // Add card to list
        device_list.appendChild(elem);
    }

    if (device_data.connected) {
        elem.classList.add("connected");
    } else {
        elem.classList.remove("connected");
    }

    // Loss
    const elem_loss = document.getElementById(`${device_id_safe}-loss`);
    if (elem_loss && elem_loss !== undefined) {
        elem_loss.textContent = device_data.packet_loss != null ? `${device_data.packet_loss}%` : "-";
    }

    // Ping
    const elem_ping = document.getElementById(`${device_id_safe}-ping`);
    if (elem_ping && elem_ping !== undefined) {
        elem_ping.textContent = device_data.connected ? `${device_data.ping.toPrecision(3)} ms` : "- ms";
    }

    // Packet count
    const elem_packets = document.getElementById(`${device_id_safe}-packets`);
    if (elem_packets && elem_packets !== undefined) {
        elem_packets.textContent = device_data.packet_count ?? "-";
    }
}


// ── Bottom bar: update summary counts ────────────────────────────
function diagUpdateBottomBar(totalDevices, onlineCount) {
    const offlineCount = totalDevices - onlineCount;
    const allOnline = offlineCount === 0 && totalDevices > 0;

    const elAll = document.getElementById("diag-bottom-all-online");
    const elOffline = document.getElementById("diag-bottom-offline");
    const elOnline = document.getElementById("diag-bottom-online");

    if (elAll) {
        elAll.textContent = allOnline ? "Yes" : "No";
        elAll.style.background = allOnline ? "#16a34a" : "#dc2626";
    }
    if (elOffline) {
        elOffline.textContent = offlineCount;
        elOffline.style.background = offlineCount > 0 ? "#dc2626" : "#16a34a";
    }
    if (elOnline) {
        elOnline.textContent = onlineCount;
        elOnline.style.background = onlineCount > 0 ? "#16a34a" : "rgba(255,255,255,0.1)";
    }
}

export { diagClampGraphPing, diagNowSeconds, diagUpdateBottomBar, diagUpdateDeviceCard, format_device_id, updateNetworkDiagnostics }
