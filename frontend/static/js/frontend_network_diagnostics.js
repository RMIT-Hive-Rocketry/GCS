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
import { diagEnsureGraph, diagGraphs, diagUpdateGraph } from '/js/frontend_graphs.js';

const network_devices = {};
const previous_ping = {};
const elementCache = new Map(); // Cache DOM element references

class NetworkDevice {
    constructor(device_id) {
        // Base device variables
        this.id = device_id;
        this.connected = false;
        this.ping = -1;
        this.packet_loss = -1;
        this.packet_count = -1;

        // Setup connection log
        this.log = {}

        // Set device class
        if (cfg.network.devices.control.includes(device_id)) {
            this.group = "control"
        } else if (cfg.network.devices.gse.includes(device_id)) {
            this.group = "gse"
        } else {
            this.group = "other"
        }
    }

    update(device_data) {
        // Add data to log
        this.log[performance.now() / 1000] = device_data;

        // Update current device data
        this.connected = device_data.connected;
        this.ping = device_data.ping;
        this.packet_loss = device_data.packet_loss;
        this.packet_count = device_data.packet_count;
    }
}

function getDiagnosticsNavLink() {
    if (!elementCache.has('navLink')) {
        elementCache.set('navLink', document.querySelector('nav a[href=\'#page-diagnostics\']'));
    }
    return elementCache.get('navLink');
}

function pulseDiagnosticsNav() {
    const navLink = getDiagnosticsNavLink();
    if (!navLink)
        return;

    navLink.classList.remove('horizon-diag-nav-alert-pulse');
    void navLink.offsetWidth; // Forced reflow
    navLink.classList.add('horizon-diag-nav-alert-pulse');

    window.clearTimeout(navLink._horizonDiagPulseTimeout);
    navLink._horizonDiagPulseTimeout = window.setTimeout(() => {
        navLink.classList.remove('horizon-diag-nav-alert-pulse');
    }, 5200);
}

function formatLogTime() {
    return new Date().toLocaleTimeString('en-AU', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
    });
}

function addDiagnosticLogEntry(device_id, alive) {
    const logList = document.getElementById('diag-transition-log-list');
    if (!logList)
        return;

    const emptyMessage = document.getElementById('diag-transition-log-empty');
    if (emptyMessage)
        emptyMessage.remove();

    const entry = document.createElement('div');
    entry.className = `diag-transition-log-entry ${alive ? 'online' : 'offline'}`;
    entry.innerHTML = `
        <span class="diag-transition-log-time">${formatLogTime()}</span>
        <span class="diag-transition-log-device">${device_id}</span>
        <span class="diag-transition-log-state">${alive ? 'ONLINE' : 'OFFLINE'}</span>
    `;

    logList.prepend(entry);

    while (logList.children.length > cfg.logging.max_size_diagnostics) {
        logList.removeChild(logList.lastChild);
    }
}

function updateNetworkDiagnostics(apiData) {
    let ping_ui = false;

    Object.entries(apiData).forEach(([device_id, device_data]) => {
        if (device_id === 'id' || device_id === 'state' || device_id === 'meta')
            return;
        if (typeof device_data !== 'object' || device_data === null)
            return;

        if (device_data?.ping) {
            // Only pulse if connection state actually changed
            if (device_data.connected &&
                previous_ping[device_id]?.connected === false) {
                ping_ui = true;
            }

            previous_ping[device_id] = device_data;
        }
    });

    if (ping_ui)
        pulseDiagnosticsNav();
}


function updateNetworkDiagnostics2(apiData) {
    // This function actually does something!

    Object.entries(apiData).forEach(([device_id, device_data]) => {
        // Check that we're receiving valid data
        if (device_id === "id" || device_id === "state" || device_id === "meta")
            return;
        if (typeof device_data !== "object" || device_data === null)
            return;
        if (device_data.ping === undefined) {
            device_data.ping = -1;
            device_data.connected = false;
        }

        // Make sure device is been registered in network_devices
        if (!Object.keys(network_devices).includes(device_id) && device_data.connected === true) {
            // Device not found, create new network device
            network_devices[device_id] = new NetworkDevice(device_id);
        }

        // Check if device exists in list before updating stuff (has connected at least once)
        if (Object.keys(network_devices).includes(device_id)) {
            const current_device = network_devices[device_id];

            // Update connection status of device
            current_device.update(device_data);

            // Left panel
            diagUpdateDeviceCard(device_id, device_data);

            // Middle panel
            if (diagGraphs[device_id] === undefined) {
                diagEnsureGraph(device_id);
            }
            diagUpdateGraph(device_id, device_data);
        }

        // if (cfg.network.lan_devices.includes(device_id) && alive) {
        //     lanWorstPing =
        //         lanWorstPing == null
        //             ? ping
        //             : Math.max(lanWorstPing, ping);
        // }
    });

    // Count number of connected devices
    let connected_gse = 0;
    let connected_control = 0;
    let connected_total = 0;
    for (const [, device] of Object.entries(network_devices)) {
        if (device.connected) {
            // Count total number of active connections
            connected_total++;

            // Also count number of connections in each expected area
            switch (device.group) {
                case "gse":
                    connected_gse++;
                    break;
                case "control":
                    connected_control++;
                    break;
            }
        }
    }

    // Right panel
    diagSetSummaryOnlineBox("diag-summary-gse", connected_gse);
    diagSetSummaryOnlineBox("diag-summary-lan", connected_control);

    const avIndicator = document.querySelector('[data-key="state.av.radio"][data-type="state"]');
    if (avIndicator) {
        const avOnline = avIndicator.classList.contains("green");

        diagSetSummaryOnlineBox("diag-summary-av", avOnline);
        diagSetAvIndicator(avOnline);
    }

    // Bottom bar
    diagUpdateBottomBar(network_devices.length, connected_total);

    // Last updated
    const lastUpdated = document.getElementById("diag-last-updated");
    if (lastUpdated) {
        const now = new Date();
        lastUpdated.textContent = `Last updated: ${now.toLocaleTimeString("en-AU")} AEST`;
    }
}

function diagSetStatusBox(id, pingValue) {
    const elem = elementCache.get(id) || document.getElementById(id);
    if (!elem)
        return;
    elementCache.set(id, elem);

    let newClass;
    if (pingValue == null || pingValue < 0) {
        newClass = '';
    } else if (pingValue <= 100) {
        newClass = 'good';
    } else if (pingValue <= 200) {
        newClass = 'warn';
    } else {
        newClass = 'bad';
    }

    // Only update if class actually changed
    const currentClass = elem.className.match(/good|warn|bad/)?.[0] || '';
    if (currentClass !== newClass) {
        elem.classList.remove('good', 'warn', 'bad');
        if (newClass)
            elem.classList.add(newClass);
    }
}

function diagSetSummaryOnlineBox(id, online) {
    const el = elementCache.get(id) || document.getElementById(id);
    if (!el)
        return;
    elementCache.set(id, el);

    // Use a class instead of inline styles
    if (online && !el.classList.contains('online')) {
        el.classList.add('online');
        el.classList.remove('offline');
        el.textContent = 'GOOD';
    } else if (!online && !el.classList.contains('offline')) {
        el.classList.add('offline');
        el.classList.remove('online');
        el.textContent = 'DOWN';
    }
}

function diagSetAvIndicator(online) {
    const el = elementCache.get('av-indicator') || document.getElementById('diag-av-indicator');
    if (!el)
        return;
    elementCache.set('av-indicator', el);

    // Use a class for styling
    if (online && !el.classList.contains('online')) {
        el.classList.add('online');
        el.classList.remove('offline');
    } else if (!online && !el.classList.contains('offline')) {
        el.classList.add('offline');
        el.classList.remove('online');
    }
}

function diagClampGraphPing(value) {
    return Math.max(1, Math.min(498, value));
}

function format_device_id(device_id) {
    return device_id.replace(/[^a-z0-9]/gi, '-').toLowerCase();
}

function diagUpdateDeviceCard(device_id, device_data) {
    const device_id_safe = format_device_id(device_id);
    const cacheKey = `card-${device_id_safe}`;

    let elem = elementCache.get(cacheKey);
    const device_list = elementCache.get('device-list') || document.getElementById('diag-device-list');

    if (!device_list)
        return;
    elementCache.set('device-list', device_list);

    if (!elem) {
        elem = document.createElement('div');
        elem.classList.add('network-device');
        elem.id = `diag-card-${device_id_safe}`;
        elem.innerHTML = `
            <div class="status">
                <div class="indicator-network"></div>
                <span>${device_id}</span>
            </div>
            <div class="details">
                <div><span>Loss</span><span id="${device_id_safe}-loss"></span></div>
                <div><span>Ping</span><span id="${device_id_safe}-ping"></span></div>
                <div><span>Packets</span><span id="${device_id_safe}-packets"></span></div>
            </div>
        `;
        device_list.appendChild(elem);
        elementCache.set(cacheKey, elem);
    }

    // Only update class if connection state changed
    if (device_data.connected && !elem.classList.contains('connected')) {
        elem.classList.add('connected');
    } else if (!device_data.connected && elem.classList.contains('connected')) {
        elem.classList.remove('connected');
    }

    // Cache and update text content with change detection
    const updateTextContent = (subKey, newText) => {
        const elemKey = `${cacheKey}-${subKey}`;
        let subElem = elementCache.get(elemKey);

        if (!subElem) {
            subElem = document.getElementById(`${device_id_safe}-${subKey}`);
            if (subElem)
                elementCache.set(elemKey, subElem);
        }

        if (subElem && subElem.textContent !== newText) {
            subElem.textContent = newText;
        }
    };

    updateTextContent('loss', device_data.packet_loss != null ? `${device_data.packet_loss}%` : '-');
    updateTextContent('ping', device_data.connected ? `${device_data.ping.toPrecision(3)} ms` : '- ms');
    updateTextContent('packets', device_data.packet_count ?? '-');
}

function diagUpdateBottomBar(totalDevices, onlineCount) {
    const offlineCount = totalDevices - onlineCount;
    const allOnline = offlineCount === 0 && totalDevices > 0;

    const updateElement = (id, text, isOnline) => {
        const el = elementCache.get(id) || document.getElementById(id);
        if (!el)
            return;
        elementCache.set(id, el);

        if (el.textContent !== text) {
            el.textContent = text;
        }

        // Use classes instead of inline styles
        if (isOnline && !el.classList.contains('online')) {
            el.classList.add('online');
            el.classList.remove('offline');
        } else if (!isOnline && !el.classList.contains('offline')) {
            el.classList.add('offline');
            el.classList.remove('online');
        }
    };

    updateElement('diag-bottom-all-online', allOnline ? 'Yes' : 'No', allOnline);
    updateElement('diag-bottom-offline', offlineCount, offlineCount > 0);
    updateElement('diag-bottom-online', onlineCount, onlineCount > 0);
}

export {
    addDiagnosticLogEntry,
    diagClampGraphPing,
    diagSetAvIndicator,
    diagSetStatusBox,
    diagSetSummaryOnlineBox,
    diagUpdateBottomBar,
    diagUpdateDeviceCard,
    format_device_id,
    network_devices,
    NetworkDevice,
    updateNetworkDiagnostics,
    updateNetworkDiagnostics2
};
