/**
 * Horizon Diagnostics Sound Feedback
 *
 * Independent browser-beep system for Horizon diagnostics devices.
 * Does not use the global GCS sound system.
 *
 * Rules:
 * - ping >= 1 means online
 * - ping < 1 means offline
 * - first packet stores state silently
 * - online -> offline plays one offline beep
 * - offline -> online plays one online beep
 * - sound only plays while the Diagnostics page is active
 */

(function () {
    const previousDeviceStates = {};
    let audioContext = null;

    function isHorizonRocket() {
        return (
            window.location.href.includes("rocket=horizon") ||
            document.body.classList.contains("horizon")
        );
    }

    function isDiagnosticsPageActive() {
        const hashActive = window.location.hash === "#page-diagnostics";
        const mainActive = document.querySelector("main")?.id === "page-diagnostics";
    
        return isHorizonRocket() && (hashActive || mainActive);
    }

    function getAudioContext() {
        if (!audioContext) {
            const AudioContextClass = window.AudioContext || window.webkitAudioContext;

            if (!AudioContextClass) {
                return null;
            }

            audioContext = new AudioContextClass();
        }

        if (audioContext.state === "suspended") {
            audioContext.resume();
        }

        return audioContext;
    }

    function playBeep(type) {
        if (!isDiagnosticsPageActive()) {
            return;
        }

        const ctx = getAudioContext();

        if (!ctx) {
            return;
        }

        const now = ctx.currentTime;
        const oscillator = ctx.createOscillator();
        const gain = ctx.createGain();

        oscillator.type = "sine";

        if (type === "online") {
            // Higher rising beep: device recovered
            oscillator.frequency.setValueAtTime(650, now);
            oscillator.frequency.linearRampToValueAtTime(900, now + 0.12);
        } else {
            // Lower falling beep: device went offline
            oscillator.frequency.setValueAtTime(360, now);
            oscillator.frequency.linearRampToValueAtTime(180, now + 0.18);
        }

        gain.gain.setValueAtTime(0.001, now);
        gain.gain.exponentialRampToValueAtTime(0.12, now + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.22);

        oscillator.connect(gain);
        gain.connect(ctx.destination);

        oscillator.start(now);
        oscillator.stop(now + 0.24);
    }

    function processDevice(deviceName, ping) {
        const alive = ping >= 1;
        const previousAlive = previousDeviceStates[deviceName];

        // Always update memory, even if user is not on Diagnostics page.
        // This prevents old transitions from playing later.
        previousDeviceStates[deviceName] = alive;

        // First time seeing this device: store state only, no sound.
        if (previousAlive === undefined) {
            return null;
        }

        // No state change: no sound.
        if (previousAlive === alive) {
            return null;
        }

        return alive ? "online" : "offline";
    }

    function processPacket(apiData) {
        if (!isHorizonRocket()) {
            return;
        }

        if (!apiData || apiData.id !== 50) {
            return;
        }

        let hasOnlineTransition = false;
        let hasOfflineTransition = false;

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

            const transition = processDevice(deviceName, ping);

            if (transition === "online") {
                hasOnlineTransition = true;
            }

            if (transition === "offline") {
                hasOfflineTransition = true;
            }
        });

        // Play at most one offline and one online beep per packet.
        // This avoids a sound explosion if many devices change together.
        if (isDiagnosticsPageActive()) {
            if (hasOfflineTransition) {
                playBeep("offline");
            }

            if (hasOnlineTransition) {
                setTimeout(() => {
                    playBeep("online");
                }, hasOfflineTransition ? 260 : 0);
            }
        }
    }

    // Expose only one global function for GCS_API.js to call.
    window.horizonDiagSoundProcessPacket = processPacket;

    // Browser audio unlock helper.
    // Most browsers require one user interaction before generated audio can play.
    function unlockAudio() {
        getAudioContext();
    }

    window.addEventListener("pointerdown", unlockAudio, { once: true });
    window.addEventListener("keydown", unlockAudio, { once: true });
})();