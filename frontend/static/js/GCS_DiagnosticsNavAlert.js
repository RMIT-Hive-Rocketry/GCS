/**
 * Horizon Diagnostics Nav Alert + Transition Log
 *
 * Independent diagnostics notification logic.
 * Does not touch graph rendering.
 * Does not use the global sound system.
 *
 * Rules:
 * - ping >= 1 means online
 * - ping < 1 means offline
 * - first packet stores state silently
 * - state changes create a log entry
 * - state changes pulse the Diagnostics nav tab for a few seconds
 */

(function () {
    const previousDeviceStates = {};
    const MAX_LOG_ENTRIES = 40;

    function isHorizonRocket() {
        return (
            document.body.classList.contains("horizon") ||
            window.location.href.includes("rocket=horizon")
        );
    }

    function getDiagnosticsNavLink() {
        return document.querySelector("nav a[href='#page-diagnostics']");
    }

    function pulseDiagnosticsNav() {
        const navLink = getDiagnosticsNavLink();

        if (!navLink) {
            return;
        }

        navLink.classList.remove("horizon-diag-nav-alert-pulse");

        // Force browser to restart the animation even if it just ran.
        void navLink.offsetWidth;

        navLink.classList.add("horizon-diag-nav-alert-pulse");

        window.clearTimeout(navLink._horizonDiagPulseTimeout);

        navLink._horizonDiagPulseTimeout = window.setTimeout(() => {
            navLink.classList.remove("horizon-diag-nav-alert-pulse");
        }, 5200);
    }

    function formatLogTime() {
        return new Date().toLocaleTimeString("en-AU", {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
        });
    }

    function addDiagnosticLogEntry(deviceName, alive) {
        const logList = document.getElementById("diag-transition-log-list");

        if (!logList) {
            return;
        }

        const emptyMessage = document.getElementById("diag-transition-log-empty");

        if (emptyMessage) {
            emptyMessage.remove();
        }

        const entry = document.createElement("div");
        entry.className = `diag-transition-log-entry ${alive ? "online" : "offline"}`;

        const time = document.createElement("span");
        time.className = "diag-transition-log-time";
        time.textContent = formatLogTime();

        const device = document.createElement("span");
        device.className = "diag-transition-log-device";
        device.textContent = deviceName;

        const state = document.createElement("span");
        state.className = "diag-transition-log-state";
        state.textContent = alive ? "ONLINE" : "OFFLINE";

        entry.appendChild(time);
        entry.appendChild(device);
        entry.appendChild(state);

        // Latest first.
        logList.prepend(entry);

        while (logList.children.length > MAX_LOG_ENTRIES) {
            logList.removeChild(logList.lastChild);
        }
    }

    function processDevice(deviceName, ping) {
        const alive = ping >= 1;
        const previousAlive = previousDeviceStates[deviceName];

        // First time seeing this device: store state silently.
        if (previousAlive === undefined) {
            previousDeviceStates[deviceName] = alive;
            return false;
        }

        // No state change: keep quiet.
        if (previousAlive === alive) {
            previousDeviceStates[deviceName] = alive;
            return false;
        }

        // State changed.
        previousDeviceStates[deviceName] = alive;

        addDiagnosticLogEntry(deviceName, alive);

        return true;
    }

    function processPacket(apiData) {
        if (!isHorizonRocket()) {
            return;
        }

        if (!apiData || apiData.id !== 50) {
            return;
        }

        let hasAnyTransition = false;

        Object.entries(apiData).forEach(([deviceName, deviceData]) => {
            if (deviceName === "id" || deviceName === "state" || deviceName === "meta") {
                return;
            }

            if (typeof deviceData !== "object" || deviceData === null) {
                return;
            }

            if (!("ping" in deviceData)) {
                return;
            }

            const ping = Number(deviceData.ping ?? -1);

            if (!Number.isFinite(ping)) {
                return;
            }

            const changed = processDevice(deviceName, ping);

            if (changed) {
                hasAnyTransition = true;
            }
        });

        if (hasAnyTransition) {
            pulseDiagnosticsNav();
        }
    }

    window.horizonDiagNavAlertProcessPacket = processPacket;
})();