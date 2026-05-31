/**
 * GCS API
 *
 * Receives data from the API and loads it into memory to be accessed by other javascript modules.
 *
 * Functions and constants should be prefixed with "api_"
 */

// Constants
const initialReconnectInterval = 200; // Initial reconnection wait time
const maxReconnectInterval = 5000; // Maximum amount of time between reconnect attempts
const graphRenderRate = 20; // FPS for rendering graphs
const metricOffline = {}; // key -> boolean

// WebSocket API connection
const ws_url = `ws://${window.location.host.split(":")[0]}:1887`
// const ws_url = `ws://${_ws["host"]}:${_ws["port"]}`
const apiSocket = new WebSocket(ws_url);
var reconnectInterval = initialReconnectInterval;
var reconnectTimeout;
var connected = false;
var then, now, fpsInterval;

// Logging
const indicatorStates = ["off", "green", "yellow", "red", "timeout", "error"];
const logVerbose = false;
const logIncomingMessages = false;
const errors = [];

/* Combine all timeouts into one array of objects (only for radios).
 * This makes it easier to program sound alarms in a queue, with
 * past rockets included just so that their functionality is (hopefully)
 * preserved, as there used to be a data-timeout attribute.
*/
const timeoutsList = [
    // This allows for customisation (note duration in ms)
    { name: "av", duration: 3000, state: 4, rocket: "Legacy3" },
    { name: "av", duration: 10000, state: 5, rocket: "Legacy3" },
    { name: "gse", duration: 3000, state: 4, rocket: "Legacy3" },
    { name: "gse", duration: 10000, state: 5, rocket: "Legacy3" },

    { name: "av", duration: 3000, state: 4, rocket: "Atlas" },
    { name: "av", duration: 10000, state: 5, rocket: "Atlas" },
    { name: "gse", duration: 3000, state: 4, rocket: "Atlas" },
    { name: "gse", duration: 10000, state: 5, rocket: "Atlas" },

    { name: "av", duration: 5000, state: 4, rocket: "Horizon" },
    { name: "gse", duration: 5000, state: 4, rocket: "Horizon" },
];

// Global display values
var altitudeMax;
var altitudeHistory = [];
var packetsAV1 = 0;
var packetsAV1offset = 0;
var packetsGSE = 0;
var packetsGSEoffset = 0;
var timestampLocalLoad = Date.now(); // Timestamp upon page load (refreshed with API to keep time-alignment)
var timestampLocal = 0; // Local timekeeping (for page to keep updating even if API stops sending signals)
var timestampApi = 0; // Timestamp sent by the API
var timestampApiConnect; // First API timestamp sent upon connection with API
var timeDrift;
const timers = {
    gasFillTimer: 0,
    gasFillTimerTotal: 0,
    gasTimestamp: 0,
    launchTimestamp: 0,
};

// Generate the loss sounds (1st 2 have a quicker version - see timeoutsList)
// Note: Horizon doesn't have 2 Australis boards (which is Dual_Board_Loss)
const filenames_losses = ["GSE_Loss", "AV_Loss", "GPS_Fix_Loss"];
const soundsList_losses = filenames_losses.map(src => {
    // Create the audio object that will return upon ending
    const audioObject = new Audio("sounds/" + src + ".mp3");

    // Mute sound by default
    audioObject.muted = true;

    // Self-return after playing
    audioObject.addEventListener('ended', () => {
        audioObject.pause();
        audioObject.currentTime = 0;
    });

    /* Active means whether the sound should be playing
     * but the mute status is stored inside source
    */
    return { source: audioObject, active: false };
});

// Other non-alarm sounds (uncomment the below when done).
/* TODO: Add "Rocket_Hit" to this list when the application can detect the rocket imminently
 * about to hit someone on the head, using playOtherSound(). At this stage, though, same as Rocket_Warn
 *
 * To put this sound into Combined_Sounds, add it to the end of the corresponding track/
 * segment in the attached Audacity project (static/sounds), continuing the pattern
 * of 0.5 seconds between each sound.
*/
const filenames_other = ["Apogee", "Parachute", "Rocket_Warn"];
const soundsList_other = filenames_other.map(src => {
    // Create the audio object that will return upon ending
    const audioObject = new Audio("sounds/" + src + ".mp3");

    // Mute sound by default
    audioObject.muted = true;

    /* This time there is no queue so no active, but keep
     * track of how many times a sound has been looping for
     * (if required)
    */
    let returnValue = { source: audioObject, loopCount: 0 };

    // Loop in case required, else self-return after playing
    audioObject.addEventListener('ended', () => {
        if (src === "Rocket_Warn") {
            audioObject.currentTime = 0;
            audioObject.play();
            returnValue.loopCount++;
        }
        else {
            audioObject.pause();
            audioObject.currentTime = 0;
        }
    });

    return returnValue;
});

// Check if all sounds (alarms and otherwise) are unmuted
function allUnmuted() {
    return soundsList_losses.every(item => !item.source.muted) &&
        soundsList_other.every(item => !item.source.muted);
}

// Call at the start and whenever a state updates
function checkStateIndicator(elem = null) {
    // Select rocket for below
    let currRocket = "";
    if (window.location.href.includes("rocket=legacy")) {
        currRocket = "Legacy3";
    }
    else if (window.location.href.includes("rocket=atlas")) {
        currRocket = "Atlas";
    }
    else if (window.location.href.includes("rocket=horizon")) {
        currRocket = "Horizon";
    }

    function stateToSound(e1) {
        let sound = "",
            indicator = e1.attributes[0].textContent;

        /* See horizon_preflight.html for sound sources. Also set the corresponding
         * summary light for the 1st 2 states if the function exists.
        */
        if (indicator.includes("av.radio")) {
            sound = "AV_Loss";

            const avOnline = e1.classList.value.includes("green");

            if (typeof diagSetSummaryOnlineBox === "function") {
                diagSetSummaryOnlineBox("diag-summary-av", avOnline);
            }

            if (typeof diagSetAvIndicator === "function") {
                diagSetAvIndicator(avOnline);
            }
        }
        else if (indicator.includes("gse.radio")) {
            sound = "GSE_Loss";
            if (typeof diagSetStatusBox === 'function') {
                const alive = ["vulcan-esp32", "wifi-bridge-gse"].every((device, index) => {
                    let ping = document.querySelector(`[data-key="${device}.ping"]`);
                    return ping && ping.getAttribute('value') >= 0;
                });

                diagSetStatusBox("diag-summary-gse", alive && e1.classList.value.includes("green"));
            }

            // // Track summary status, unless alive has already been set false
            // let alive = true;
            // if ((["Vulcan ESP32", "WiFi Bridge @ GSE"].includes(deviceName)) && alive) {
            //     // GSE: Check if the GSE radio indicator and the above pings are > 0
            //     const gseIndicator = document.querySelector('[data-key="state.gse.radio"][data-type="state"]');
            //     if (gseIndicator) {
            //         alive = gseIndicator.classList.contains("green") && (ping >= 0);
            //         diagSetStatusBox("diag-summary-gse", alive);
            //     }
            // }
        }
        else if (indicator.includes("gpsFix")) {
            sound = "GPS_Fix_Loss";
        }
        // Currently moved out of scope
        // else if (indicator.includes("dualBoard")) {
        //     sound = "Dual_Board_Loss";
        // }

        // Should only execute with one of the above values
        if (sound !== "") {
            /* Can be changed, but at this stage only green is a good state,
            * where the sound resets (otherwise continues playing). Also,
            * elem.classList.value is the styling itself (use this so that
            * in case the interested state/s exist elsewhere in the string)
            */
            updateSound(sound, !e1.classList.value.includes("green"), false);

            // Check for timeouts (won't execute on a non-radio state)
            timeoutsList.filter(t1 => (t1.rocket === currRocket) && (indicator.includes(t1.name))).forEach((t1) => {
                let currElems = document.querySelectorAll(`[data-key="${"state." + t1.name + ".radio"}"]`);

                currElems.forEach((c1) => {
                    // Use functions for recalculating the expressions
                    const timeoutState = () => c1.classList.value.includes(indicatorStates[t1.state]);
                    const greenState = () => !c1.classList.value.includes("green");
                    const currSound = t1.name.toUpperCase() + "_Loss";

                    if (timeoutState()) {
                        // At a minimum, the regular sound should be playing regardless
                        updateSound(currSound, true, false);

                        setTimeout(() => {
                            /* If the timeout is still not resolved, set the sound to
                            * the quicker version.
                            */
                            if (timeoutState()) {
                                updateSound(currSound, true, true);
                            }
                            else {
                                // Set the alarm back to its normal state (if the timeout went away on time)
                                updateSound(currSound, !greenState, false);
                            }
                        }, t1.duration);
                    }
                    else {
                        // Same code as above, except it doesn't wait (when the state was never 'unfavourable')
                        updateSound(currSound, !greenState, false);
                    }
                })
            })
        }
    }

    // Activate a single alarm
    if (elem !== null) {
        stateToSound(elem);
    }
    else {
        // Check all states at the start
        const validStates = ["av.radio", "gse.radio", "gpsFix", "dualBoard"]
        validStates.map(key => {
            let currElems = document.querySelectorAll(`[data-key="state.${key}"]`);

            // Activate any required alarms
            currElems.forEach((c1) => {
                stateToSound(c1);
            })
        });
    }
}

// Check if the main Horizon page is selected
function isHorizonMain() {
    /* Before clicking on any header page, the former will be
     * true, afterwards, it will be the latter
    */
    return window.location.href.endsWith("rocket=horizon") ||
        window.location.href.endsWith("rocket=horizon#page-main");
}

// Block calls to enforce silence
let silence = false;

/* Plays alarm sounds in a queue, whose order matches the priority
 * (in descending order).
*/
function playAlarmSounds() {
    // Return if 1 second not up, yet
    if (silence) { return; }
    silence = true;

    for (let i = 0; i < soundsList_losses.length; ++i) {
        // Play the active sounds in succession (only if not already playing)
        if ((soundsList_losses[i].active) && (soundsList_losses[i].source.paused)) {
            soundsList_losses[i].source.play();
        }
    }

    // After 1 second, allow function calls
    setTimeout(() => {
        silence = false;
    }, 1000);
}

// Plays a non-alarm sound
function playOtherSound(sound) {
    // Look for the sound
    const soundNumber = soundsList_other.findIndex(
        file => file.source.src.includes(sound)
    );

    // Not found or already playing
    if ((soundNumber === -1) || (!soundsList_other[soundNumber].source.paused)) {
        return;
    }

    // Play if on the Horizon main page
    if (isHorizonMain()) {
        soundsList_other[soundNumber].source.play();
    }
}

function toggleMute() {
    // Toggle mute first, then update UI

    // Alarm sounds
    for (let i = 0; i < soundsList_losses.length; ++i) {
        soundsList_losses[i].source.muted = !soundsList_losses[i].source.muted;
    }

    // Other sounds (no source as these aren't in a queue)
    for (let i = 0; i < soundsList_other.length; ++i) {
        soundsList_other[i].source.muted = !soundsList_other[i].source.muted;
    }

    /* Icon represents current state.
     * In addition, the icons are free to use per https://creativecommons.org/licenses/by/4.0/,
     * modified by changing the colour to a Horizon-themed gradient
    */
    if (allUnmuted()) {
        document.getElementById("toggleIcon").src = "img/icons/sound-unmuted.svg";
        document.getElementById("toggleIcon").alt = "Sound unmuted";
    }
    else {
        document.getElementById("toggleIcon").src = "img/icons/sound-muted.svg";
        document.getElementById("toggleIcon").alt = "Sound muted";
    }
}

/* Update the given sound as to if it will play in the sound
 * queue. If long = true, the alarm will change to its extended version.
*/
function updateSound(sound, newValue, quicker) {
    const soundNumber = soundsList_losses.findIndex(
        file => file.source.src.includes(sound)
    );

    // If newValue is true, the sound should play when called
    if (soundNumber >= 0) {
        soundsList_losses[soundNumber].active = newValue;
    }

    /* Custom functions just for inside this one. Note that the suffix
     * is before the file extension, not after
    */
    function addQuicker() {
        // Filepath must not already contain the differentiating suffix
        if (!soundsList_losses[soundNumber].source.src.includes("_Quicker")) {
            soundsList_losses[soundNumber].source.src = soundsList_losses[soundNumber].source.src.slice(0, -4) + "_Quicker.mp3";
        }
    }
    function removeQuicker() {
        // Remove the suffix
        soundsList_losses[soundNumber].source.src.replaceAll("_Quicker", "");
    }

    quicker ? addQuicker() : removeQuicker();
    try {
        /* Don't play any sound if none are active (else that would delay any
         * future ones by an extra second). Likewise, don't do so unless the main
         * Horizon page is selected
        */
        if ((soundsList_losses.some(file => file.active)) && isHorizonMain()) {
            playAlarmSounds();
        }
    } catch (error) {
        /* Perform opposite operation, leading into an infinite loop
         * if the original sound did not exist neither with, nor without
         * "_Quicker"), which should not be the case here at this time
        */
        quicker ? removeQuicker() : addQuicker();
    }
}

// Reconnecting code
function scheduleReconnect() {
    reconnectTimeout = setTimeout(() => {
        API_socketConnect();
        reconnectInterval = Math.min(
            reconnectInterval * 2,
            maxReconnectInterval,
        );
    }, reconnectInterval);
}

// Animation/timing code
function startAnimating() {
    fpsInterval = 1000 / graphRenderRate;
    then = window.performance.now();
    animate();
}
function animate(newtime) {
    // Calculate time since last loop
    let now = newtime;
    let elapsed = now - then;

    // Rerender if enough time has elapsed
    if (elapsed > fpsInterval) {
        then = now - (elapsed % fpsInterval);

        // Rerender graphs
        if (typeof graphRequestRender === "function") {
            graphRequestRender();
        }

        // Increment time (so if we stop getting packets, time moves forward)
        timestampLocal = (Date.now() - timestampLocalLoad) / 1000;
        updateTime();
    }

    // Request next animation frame
    requestAnimationFrame(animate);
}
startAnimating();

function updateTime() {
    /// SYSTEM TIME
    // Rocket launch timer
    if (timestampApi != 0 && timers?.launchTimestamp != undefined) {
        let launchTime = 0;
        if (timers.launchTimestamp != 0) {
            launchTime = timestampApi - timers.launchTimestamp;
        }
        sendDataToRegistry({ launchTime: `T+${launchTime.toFixed(1)}` });
    }

    // Local time
    if (timestampLocal != undefined && timestampLocal != 0) {
        sendDataToRegistry({
            localTime: `${(timestampLocal + timestampApiConnect - timeDrift).toFixed(1)} s`,
        });
    }
}

// Logging code
function logMessage(message, logType = "", timestamp = "") {
    // Make sure log area exists
    const logArea = document.getElementById("errorLogBox");
    if (!logArea) {
        // console.error("Log area not found.");
        return;
    }

    // Calculate timestamp
    if (timestamp == "") {
        let timestamp = "?";
        if (timestampLocal != undefined && timestampApiConnect != undefined) {
            timestamp = (timestampLocal + timestampApiConnect - timeDrift).toFixed(1) + "s";
        }
    }

    // Handle different message types
    const messageTypes = {
        "error": {
            logName: "Error",
            textColor: "text-red-400",
            function: console.error
        },
        "warning": {
            logName: "Warning",
            textColor: "text-yellow-300",
            function: console.warn
        },
        "ws": {
            logName: "WebSocket",
            textColor: "text-emerald-300",
            function: console.debug
        },
        "debug": {
            logName: "Debug",
            textColor: "text-white-900",
            function: console.debug
        },
        "critical": {
            logName: "CRITICAL",
            textColor: "text-red-crit",
            function: console.error
        },
        "success": {
            logName: "Success",
            textColor: "text-green-300",
            function: console.debug
        },
    }

    if (type == "error") {
        logName = "Error";
        textColor = "text-red-400";
        console.error(timestamp, message);
    } else if (type == "warning") {
        logName = "Warning";
        textColor = "text-yellow-300";
        console.warn(timestamp, message);
    } else if (type == "ws") {
        logName = "WebSocket";
        textColor = "text-emerald-300";
        console.debug(timestamp, message);
    } else {
        logName = "Notice";
        textColr = "text-white";
        console.log(timestamp, message);
    }

    // Add message to log
    const line = document.createElement("span");
    line.classList.add("block", "m-0", textColor);
    line.textContent = `[${timestamp}] ${logName}: ${message}`;
    logArea.appendChild(line);

    // Limit lines
    const maxlines = 256;
    while (logArea.children.length > maxlines) {
        logArea.removeChild(logArea.firstChild);
    }

    // // Scroll to bottom of log
    // logArea.scrollTop = logArea.scrollHeight;
}

document.addEventListener("visibilitychange", function () {
    if (document.hidden) {
        // Clear timeouts when tabbed away from
        clearTimeout(reconnectTimeout);
    } else {
        // Attempt reconnecting again
        if (connected == false) {
            scheduleReconnect();
        }
    }
});

function API_socketConnect() {
    // Log connecting and readystate
    logMessage(`Connecting to ${ws_url} (${apiSocket.readyState})`, "ws");

    // Socket connected
    apiSocket.onopen = () => {
        connected = true;
        timestampApiConnect = undefined;
        if (logVerbose)
            console.log(`Successfully connected to server at: - ${api_url}`);
        logMessage("Successfully connected", "ws");
        clearTimeout(reconnectTimeout);
        reconnectInterval = initialReconnectInterval;
    };

    // Socket received message
    apiSocket.onmessage = API_OnMessage;

    // Socket error
    apiSocket.onerror = (error) => {
        connected = false;
        timestampApiConnect = undefined;
        logMessage(`Websocket error: ${error}`, "ws");
    };

    // Socket closed
    apiSocket.onclose = () => {
        connected = false;
        timestampApiConnect = undefined;

        // Log on browser console
        console.warn(
            "Socket closed",
            {
                wasClean: event.wasClean,
                code: event.code,
                reason: event.reason,
            },
            "Attempting to reconnect automatically",
        );

        // Log on page
        logMessage("Connection lost error, attempting to reconnect", "ws");

        // Attempt reconnecting
        scheduleReconnect();
    };

    // Monitor readystate every 10 seconds
    setInterval(() => {
        if (apiSocket)
            console.info("WebSocket readyState:", apiSocket.readyState);
    }, 10000);
}
API_socketConnect();

// Handle incoming data through the API socket
function API_OnMessage(event) {
    if (logIncomingMessages) console.log("Message from server:", event.data);

    let apiLatest, apiData;
    try {
        // Handle incoming data
        apiLatest = JSON.parse(event.data);

        // When detected Slogger Packets just skip the whole validation part and just upload packets avoids feeding in old data just to get template to work
        if (apiLatest.id == 40) {
            ///// ----- sLogger PACKETS ----- /////
            displaySloggerLogs(apiLatest.data.slogger);
            return;
        }


        // Flag data for errors
        checkErrorConditions(apiLatest.data);

        // Check if any data has gone offline
        // This should be constant throughout runtime,
        // But it's worth checking every packet at this stage to avoid a bug
        checkOfflineData(apiLatest.data)

        // Process data for display
        apiData = processDataForDisplay(apiLatest.data, apiLatest.id);
        sendDataToRegistry(apiData);

        // Legacy Legacy support
        if (typeof hmiUpdate === "function") {
            hmiUpdate(apiData);
        }

        // Handle different packet types
        if (apiData.id == 2) {
            ///// ----- SINGLE OPERATOR PACKETS ----- /////
            //

        } else if (apiData.id == 3 || apiData.id == 4) {
            ///// ----- AVIONICS PACKETS ----- /////
            // Display values
            if (typeof displayUpdateFlightState === "function") {
                displayUpdateFlightState(apiData);
            }

            // Graphs
            if (typeof graphUpdateAvionics === "function") {
                graphUpdateAvionics(apiData);
            }
            if (typeof graphUpdatePosition === "function") {
                graphUpdatePosition(apiData);
            }

            // Rocket visualisation
            if (apiData.id == 4) {
                if (typeof rocketUpdate === "function") {
                    rocketUpdate(apiData);
                }
            }
        } else if (apiData.id == 55) {
            ///// ----- GSE PACKETS ----- /////
            // Graphs
            if (typeof graphUpdateAuxData === "function") {
                graphUpdateAuxData(apiData);
            }
        } else if (apiData.id == 10) {
            ///// ----- PENDANT ----- /////
            if (typeof updatePendantState === "function") {
                updatePendantState(apiData);
            }
        } else if (apiData.id == 50) {
            ///// ----- NETWORK DIAGNOSTICS ----- /////
            if (typeof horizonDiagNavAlertProcessPacket === "function") {
                horizonDiagNavAlertProcessPacket(apiData);
            }

            if (typeof graphUpdateDiagnostics === "function") {
                graphUpdateDiagnostics(apiData);
            }
        }
    } catch (error) {
        console.error("Data processing error:", error);
    }
}

// Check data for error conditions
function checkErrorConditions(apiData) {
    const errorConditions = [
        {
            IDs: ["weight_rocket"], // Rocket weight
            discard: {
                min: -1,
                max: 128,
            },
        },
        {
            IDs: [
                "accelLowX",
                "accelLowY",
                "accelLowZ",
                "accelHighX",
                "accelHighY",
                "accelHighZ",
            ],
            discard: {
                min: -32,
                max: 32,
            },
        },
        {
            IDs: ["altitude"],
            discard: {
                min: -128,
                max: 8192,
            },
        },
        {
            IDs: ["velocity"],
            discard: {
                min: -128,
                max: 1024,
            },
        },
        {
            IDs: ["GPSLatitude", "GPSLongitude"],
            discard: {
                min: -18000,
                max: 18000,
            },
        },
        {
            IDs: ["gyroX", "gyroY", "gyroZ"],
            discard: {
                min: -295,
                max: 295,
            },
        },
        {
            IDs: ["temp_vent"],
            discard: {
                min: -200,
                max: 80,
            },
        },
        {
            IDs: ["mach_speed"],
            discard: {
                min: -1,
                max: 16,
            },
        },
        {
            IDs: ["qw", "qx", "qy", "qz"],
            discard: {
                min: -1,
                max: 1,
            },
        },
        {
            IDs: ["navigationStatus"],
            accept: ["NF", "DR", "G2", "G3", "D2", "D3", "RK", "TT"],
        },
        {
            IDs: ["flightState"],
            accept: [
                "PRE_FLIGHT_NO_FLIGHT_READY",
                "LAUNCH",
                "COAST",
                "APOGEE",
                "DESCENT",
                "LANDED",
                "OH_NO",
            ],
        },
        {
            IDs: ["gasBottleWeight1", "gasBottleWeight2"],
            error: {
                min: 15.1,
                max: 19,
            },
            errorMessage: "out of range",
            discard: {
                min: -1,
                max: 128,
            },
        },
        {
            IDs: [
                "temp_tank_top",
                "temp_tank_middle",
                "temp_tank_bottom",
            ],
            error: {
                max: 30,
            },
            errorMessage: " warming",
            discard: {
                min: -128,
                max: 128,
            },
        },
        {
            IDs: [
                "temp_pipe_n2o_gse",
            ],
            error: {
                max: 40,
            },
            errorMessage: " warming",
            discard: {
                min: -128,
                max: 128,
            },
        },
        {
            IDs: [
                "temp_vent",
            ],
            error: {
                max: 34.5,
            },
            discard: {
                min: -200,
                max: 128,
            },
        },
        {
            IDs: [
                "pressure_n2o_bottle",
                "pressure_n2o_tank",
                "pressure_o2_tank",
            ],
            error: {
                max: 64.5,
            },
            errorMessage: "flag raised",
            discard: {
                min: -1,
                max: 128,
            },
        },
    ];

    // Get error flags from the API and use as overrides
    const errorOverrides = [];
    if (apiData.errorFlags != undefined) {
        Object.entries(apiData.errorFlags).forEach(([key, value]) => {
            if (value === true) {
                errorOverrides.push(key);
            }
        });
    }

    // Iterate over all error conditions
    errorConditions.forEach((errorCondition) => {
        // Error conditions may apply equivalently to multiple data IDs
        errorCondition.IDs.forEach((id) => {
            // Make sure the ID is defined within the current packet
            if (
                Object.keys(apiData).indexOf(id) != -1 &&
                apiData[id] != undefined
            ) {
                const apiDataValue = apiData[id];
                const apiDataType = typeof apiDataValue;
                if (apiDataValue != undefined) {

                    // Define error key
                    const errorKey = `${id}Error`;
                    let isError = false;
                    let isErrorApi = errorOverrides.indexOf(errorKey) != -1;
                    let isDiscard = false;

                    // Check error ranges if the value is a number
                    if (apiDataType == "number") {
                        // Check against error ranges
                        if (errorCondition?.error) {
                            if (
                                errorCondition.error?.min &&
                                apiDataValue < errorCondition.error.min
                            ) {
                                isError = true;
                            }
                            if (
                                errorCondition.error?.max &&
                                apiDataValue > errorCondition.error.max
                            ) {
                                isError = true;
                            }
                        }

                        // Check against discard ranges (corrupted data)
                        if (errorCondition?.discard) {
                            if (
                                errorCondition.discard?.min &&
                                apiDataValue < errorCondition.discard.min
                            ) {
                                isDiscard = true;
                            }
                            if (
                                errorCondition.discard?.max &&
                                apiDataValue > errorCondition.discard.max
                            ) {
                                isDiscard = true;
                            }
                        }
                    } else if (apiDataType == "string") {
                        // Check strings against whitelist
                        if (
                            errorCondition?.accept &&
                            !errorCondition.accept.includes(apiDataValue)
                        ) {
                            isDiscard = true;
                        }
                    }

                    isError ||= isErrorApi;

                    if (isDiscard) {
                        // Check for discards
                        logMessage(
                            `Discarded ${id} (${apiData[id]})`,
                            "warning",
                        );
                        apiData[id] = apiDataType == "number" ? null : ""; // Flag invalid value
                    }

                    if (!isDiscard || isErrorApi) {
                        // Check errors against current system status
                        if (isError && errors.indexOf(errorKey) == -1) {
                            // If error, log error and raise flag
                            logMessage(
                                `${errorKey} ${errorCondition.errorMessage}`,
                                "error",
                            );
                            errors.push(errorKey);
                        } else if (!isError && errors.indexOf(errorKey) != -1) {
                            // If not error, remove from errors flags
                            logMessage(`${errorKey} resolved`);
                            errors.splice(errors.indexOf(errorKey), 1);
                        }
                    }
                }
            }
        });
    });
}

// Mark devices offline and manage their display change
function checkOfflineData(apiData) {
    const offlineSentinel = "offline"; // From gsedaq_metrics.py
    function isOffline(value) { return value === offlineSentinel; }

    // Top level check.
    // Recursion will be needed if you want to implement for other packets
    if (apiData == null) {
        console.warning("apiData passed as null to checkOfflineData");
    }

    for (const [key, value] of Object.entries(apiData)) {
        if (value == null) {
            metricOffline[key] = true;
        } else if (isOffline(value)) {
            metricOffline[key] = true;
        } else {
            metricOffline[key] = false;
        }
    }
}

// May not be required
const networkPackets = [];

function processDataForDisplay(apiData, apiId) {
    // Process data from the API for display
    const processedData = { ...apiData }; // Shallow copy
    processedData.id = apiId;

    if (processedData.state == undefined) {
        processedData.state = {};
    }
    if (processedData.meta == undefined) {
        processedData.meta = {};
    }
    /***
    This was made by Michael PP1 Hive 2026 team. I had to make changes to his code
    for customizing and seperating diagnostic page variables while it follows
    the same logic of Michael. I just sepearted the code into pieces. 
    - Mohammad
     */
    // if (apiId === 50) {
    //     // Get the table (return early if not loaded)
    //     let packetsTable = document.getElementById("packets");
    //     if (packetsTable === null) {
    //         return processedData;
    //     }

    //     // Update data if present, otherwise add it
    //     Object.entries(apiData).forEach(([device, deviceData]) => {
    //         let currRow = packetsTable.querySelector(`tr td div[data-key='${device}']`);
    //         if (currRow === null) {
    //             // Append 2 rows
    //             let topRow = packetsTable.insertRow(-1);
    //             let bottomRow = packetsTable.insertRow(-1);

    //             topRow.innerHTML = `
    //             <tr>
    //                 <td class="w-full flex gap-4 justify-start items-center">
    //                     <div
    //                         data-key="${device}"
    //                         data-type="state"
    //                         class="indicator-state mx-0 green"
    //                     ></div>
    //                     <span class="font-bold text-hive">${device}</span>
    //                 </td>
    //             </tr>
    //             `;

    //             // Set state to red if no pings coming through
    //             if ((deviceData.ping == null) || (deviceData.ping < 0)) {
    //                 topRow.querySelector(".indicator-state")?.classList.replace("green", "red");
    //             }
                
    //             bottomRow.innerHTML = `
    //             <tr>
    //                 <td style="border-bottom: 30px solid transparent;">
    //                     <label>
    //                         Packet Loss:<input
    //                             data-key="${device}.packet_loss"
    //                             data-precision="3"
    //                             readonly
    //                             autocomplete="off"
    //                             class="text-right"
    //                             size="4"
    //                             value='${deviceData.packet_loss != null ? deviceData.packet_loss*100 : 0}'
    //                         />%
    //                     </label>
    //                 </td>
    //                 <td style="border-bottom: 30px solid transparent;">
    //                     <label>
    //                         Ping:<input
    //                             data-key="${device}.ping"
    //                             data-precision="0"
    //                             readonly
    //                             autocomplete="off"
    //                             size="4"
    //                             value='${deviceData.ping != null ? deviceData.ping : -1}'
    //                         />
    //                     </label>
    //                 </td>
    //             </tr>
    //             `
    //             // Not required at this stage
    //             /* <td style="border-bottom: 30px solid transparent;">
    //                     <label>
    //                         Packets:<input
    //                             data-key=${device}.packet_count
    //                             data-precision="0"
    //                             readonly
    //                             autocomplete="off"
    //                             class="text-right"
    //                             size="11"
    //                             value = 0
    //                         />
    //                     </label>
    //                 </td>
    //             */
    //         }
    //         else {
    //             // Get the top row
    //             const index = currRow.closest("tr").rowIndex;
                
    //             // Update the state
    //             let topRow = packetsTable.rows[index].querySelector('td div');
    //             topRow.classList.value = `indicator-state mx-0 ${
    //                 ((deviceData.ping != null) && (deviceData.ping >= 0)) ? 'green' : 'red'
    //             }`;

    //             // Update the packet loss then ping
    //             let bottomRow = packetsTable.rows[index + 1].querySelectorAll('td label input');
    //             bottomRow[0].setAttribute('value', (deviceData.packet_loss != null) ? deviceData.packet_loss*100 : 0);
    //             bottomRow[1].setAttribute('value', (deviceData.ping != null) ? deviceData.ping : -1);
    //         }

    //         // The below may not be required
    //         // // Regardless, track packet count
    //         // let index = networkPackets.findIndex(item => item.name === device);
    //         // if (index >= 0) {
    //         //     // If the device in question exists, update count and offset
    //         //     networkPackets[index].count++;

    //         //     // Keep offset if no value was passed in (such as at the start)
    //         //     if (typeof device.packet_loss !== 'undefined') {
    //         //         networkPackets[index].offset = packet_loss;
    //         //     }
    //         // }
    //         // else {
    //         //     // Create a new record and update index
    //         //     networkPackets.push({name: device, count: 1, offset: 0});
                
    //         //     // index was -1, now need the last element
    //         //     index += networkPackets.length;
    //         // }

    //         // // Calculate packet count as the total number of packets minus the % loss
    //         // const actualPacketCount = Math.floor(networkPackets[index].count * ((100 - networkPackets[index].offset) / 100));
    //         // let inputValue = packetsTable.querySelector(`input[data-key='${device}.packet_count']`);
            
    //         // // Make sure the element exists
    //         // if (inputValue != null) {
    //         //     inputValue.value = actualPacketCount;
    //         // }
    //     });
    // }

    if (apiId === 50) {
        // Track packet counts per device and attach to processedData.
        // All HTML rendering is handled by graphUpdateDiagnostics() in GCS_Graphs.js.
        Object.keys(apiData).forEach(device => {
            if (typeof apiData[device] !== 'object' || apiData[device] === null) return;
            if (!('ping' in apiData[device])) return;

            processedData[device] = {
                ...apiData[device],
                ping: apiData[device].ping,
                packet_loss: (apiData[device].packet_loss * 100).toFixed(1),
                count: apiData[device].packet_count ?? 0,
            };
        });
    }

    if (apiData?.meta) {
        // Timestamp, synchronization and connection
        if (apiData.meta?.timestampS) {
            if (timestampApi) {
                timestampApi = Math.max(timestampApi, apiData.meta.timestampS);
            } else {
                timestampApi = apiData.meta.timestampS;
            }

            if (timestampApiConnect == undefined) {
                timestampApiConnect = timestampApi;
                timestampLocalLoad = Date.now();
            } else {
                // Code to synchronise local time with GSE time if it gets too far behind
                timeDrift =
                    timestampLocal - (timestampApi - timestampApiConnect);

                // Time drift
                // timeDrift > 0 means LOCAL is ahead of GSE
                // timeDrift < 0 means GSE is ahead of LOCAL
                // Ideally there's no time drift at all, but if there is it's used to update the time
                //console.log(timeDrift);
            }
        }

        // Packets
        if ([3, 4, 5].includes(apiId)) {
            if (apiData.meta?.totalPacketCountAv) {
                if (packetsAV1 == 0) {
                    packetsAV1offset = apiData.meta.totalPacketCountAv - 1;
                }
                processedData.meta.totalPacketCountAv =
                    apiData.meta.totalPacketCountAv - packetsAV1offset;
            }

            processedData.meta.radio = "av1";
            processedData.meta.av = {
                rssi: apiData.meta.rssi,
                snr: apiData.meta.snr,
                packets: ++packetsAV1,
                lostPackets: processedData.meta.totalPacketCountAv - packetsAV1,
            };
            processedData.state.av = { radio: 1 };
        } else if ([55].includes(apiId)) {
            processedData.meta.radio = "gse";
            processedData.state.gse = { radio: 1 };
        }
    }

    // Acceleration
    // Determine whether to use low or high precision values
    if (apiData.accelLowX != undefined && apiData.accelHighX != undefined) {
        processedData.accelX =
            Math.abs(apiData.accelHighX) < 17
                ? apiData.accelLowX
                : apiData.accelHighX;
    }
    if (apiData.accelLowY != undefined && apiData.accelHighY != undefined) {
        processedData.accelY =
            Math.abs(apiData.accelHighY) < 17
                ? apiData.accelLowY
                : apiData.accelHighY;
    }
    if (apiData.accelLowZ != undefined && apiData.accelHighZ != undefined) {
        processedData.accelZ =
            Math.abs(apiData.accelHighZ) < 17
                ? apiData.accelLowZ
                : apiData.accelHighZ;
    }

    // Altitude
    // Track previous altitudes
    if (apiData.altitude != undefined) {
        processedData.altitudeFeet = metresToFeet(apiData.altitude);

        altitudeHistory.push(apiData.altitude);
        if (altitudeHistory.length > 5) {
            altitudeHistory.shift();
        }
        if (altitudeHistory.length === 5) {
            // Calculate mean of last 5 altitudes, then determine deviation and threshold
            const altitudeMean =
                altitudeHistory.reduce((acc, val) => acc + val, 0) /
                altitudeHistory.length;
            const altitudeThreshold = Math.max(altitudeMean * 0.2, 200); // 20% difference or < 200 whichever is greater
            const altitudeDeviation = Math.abs(apiData.altitude - altitudeMean);

            // Calculate max altitude
            if (altitudeDeviation <= altitudeThreshold) {
                if (
                    altitudeMax == undefined ||
                    apiData.altitude > altitudeMax
                ) {
                    altitudeMax = apiData.altitude;
                }
            } else {
                logMessage(`Discard max altitude (${altitudeMax})`, "warning");
            }
        }
        if (altitudeMax != undefined && altitudeMax > 0) {
            processedData.altitudeMax = altitudeMax;
            processedData.altitudeMaxFeet = metresToFeet(altitudeMax);
        }

        // Parachute sound should play if we descend below a set altitude
        const PARACHUTE_ALTITUDE = 1200; // Ideally this would be in a place of unified truth

        // The new altitude must be below the threshold, unlike the old one
        const prevAltitude = metresToFeet(altitudeHistory.at(-2));
        const currAltitude = metresToFeet(altitudeHistory.at(-1));
        if ((currAltitude < PARACHUTE_ALTITUDE) && (prevAltitude >= PARACHUTE_ALTITUDE)) {
            playOtherSound("Parachute");
        }
    }

    // Feet
    if (apiData.velocity != undefined) {
        processedData.velocityFeet = metresToFeet(apiData.velocity);
    }

    // GPS position
    if (apiData.GPSLatitude != undefined) {
        processedData.GPSLatitude = gpsToDecimal(apiData.GPSLatitude);
    }
    if (apiData.GPSLongitude != undefined) {
        processedData.GPSLongitude = gpsToDecimal(apiData.GPSLongitude);
    }

    /* If the rocket is within 50m of the GCS, play a warning sound.
     * Use Pythagorean theorem, scaling up latitude and longitude, both
     * of which are required to be present in the packet.
     *
     * Requires matching the GCS coordinates to "LATITUDE": sinusoid() and/or
     * "LONGITUDE": sinusoid() in backend/device_emulator.py (or vice versa) during
     * testing, or else the rocket will appear to be 23000-24000m metres (23-24km)
     * away from the GCS.
    */
    if (apiData.GPSLatitude != undefined && apiData.GPSLongitude != undefined) {
        // Scaling constants
        const lat_kilometers = 110.87;
        const long_kilometers = 95.48;

        // (Decimal) Coordinates of the GCS
        const lat_GCS = 31.039581;
        const long_GCS = 103.526623;

        /* Distance to GCS in km (both latitude and longitude). Use the decimal
         * version of the coordinates as this is what the GCS coordinates are given
         * as.
        */
        const lat_distance = ((gpsToDecimal(apiData.GPSLatitude - lat_GCS)) * lat_kilometers) ** 2;
        const long_distance = ((gpsToDecimal(apiData.GPSLongitude - long_GCS)) * long_kilometers) ** 2;
        const final_distance = Math.sqrt(lat_distance + long_distance);

        // Rocket_Warn sound
        let currSound = soundsList_other[2];

        // 50m in km
        if (final_distance <= 50 / 1000) {
            // Sometimes the property might be equal to NaN, make sure no error is thrown
            if (currSound.source.duration === currSound.source.duration) {
                /* Volume rises in logarithmic fashion the longer the rocket stays within
                * 50m of the GCS (within the 1st iteration), full volume otherwise.
                */
                currSound.source.volume = currSound.loopCount > 0
                    ? 1 : (currSound.source.currentTime / currSound.source.duration) ** 1.5;
                console.log(currSound.loopCount);
                playOtherSound("Rocket_Warn");
            }
        }
        else {
            // Stop and reset number of iterations.
            currSound.source.pause();
            currSound.source.currentTime = 0;
            currSound.loopCount = 0;
        }
    }

    // Gas fill timer
    if ([10].includes(apiId) && apiData != null) {
        const systemActivated = apiData.SYS_ON;
        const gasFillSelected = apiData.FILL_SELECTED;
        const n20FillActivated = apiData.N2O_ACTIVE;

        if (systemActivated && gasFillSelected && n20FillActivated) {
            // Increase gas fill timer
            if (timers.gasTimestamp == 0) {
                timers.gasTimestamp = timestampApi;
            }
            timers.gasFillTimer =
                timers.gasTimestamp == 0
                    ? 0
                    : timestampApi - timers.gasTimestamp;
        } else {
            timers.gasTimestamp = 0;
            timers.gasFillTimerTotal += timers.gasFillTimer;
            timers.gasFillTimer = 0;
        }

        if (timers.gasFillTimer != undefined && timers.gasFillTimer != 0) {
            processedData.gasBottleTime = `${(timers.gasFillTimerTotal + timers.gasFillTimer).toFixed(2)}s`;
        }
    }

    // State flags
    // GPS fix (navigation state)
    if (apiData.navigationStatus != undefined) {
        if (["NF"].includes(apiData.navigationStatus)) {
            processedData.state.gpsFix = 3; // Red
        } else if (["DR", "TT"].includes(apiData.navigationStatus)) {
            processedData.state.gpsFix = 2; // Yellow
        } else if (
            ["D2", "D3", "G2", "G3", "RK"].includes(apiData.navigationStatus)
        ) {
            processedData.state.gpsFix = 1; // Green
        }
    }

    if (apiData.stateFlags != undefined) {
        // Dual board connectivity
        if (apiData.stateFlags.dualBoardConnectivityStateFlag != undefined) {
            processedData.state.dualBoard = apiData.stateFlags
                .dualBoardConnectivityStateFlag
                ? 1
                : 5; // green / error
        }
        // Recovery checks
        if (apiData.stateFlags.recoveryChecksCompleteAndFlightReady) {
            processedData.state.recoveryCheck = apiData.stateFlags
                .recoveryChecksCompleteAndFlightReady
                ? 1
                : 0;
        }
        // Payload
        if (apiData.stateFlags.payloadConnectionFlag) {
            processedData.state.payload = apiData.stateFlags
                .payloadConnectionFlag
                ? 1
                : 0;
        }
        // Camera controller
        if (apiData.stateFlags.cameraControllerConnectionFlag) {
            processedData.state.camera = apiData.stateFlags
                .cameraControllerConnectionFlag
                ? 1
                : 0;
        }
    }

    // Return processed data
    return processedData;
}

// UNIT CONVERSION FUNCTIONS
function metresToFeet(metres) {
    if (metres == undefined || isNaN(metres)) return undefined;
    return metres * 3.28084;
}

function feetToMetres(feet) {
    if (feet == undefined || isNaN(feet)) return undefined;
    return feet / 3.28084;
}

function gpsToDecimal(gps) {
    // Converts the compressed GPS value into a decimal degrees coordinate
    if (gps == undefined || isNaN(gps) || gps == 0) return 0;

    // Split string into parts
    let [intPart, decPart] = gps.toString().split('.');

    // Get sign (positive or negative)
    let sign = intPart >= 0 ? 1 : -1;

    // Equations only work on positive numbers (since rounding and modulus changes in negative)
    intPart = Math.abs(intPart);
    let degrees = parseInt(intPart / 100);
    let minutes = parseInt(intPart % 100);
    let seconds = 0;
    if (decPart != undefined) {
        seconds = parseFloat(decPart.slice(0, 2) + "." + decPart.slice(2));
    }

    // Convert to decimal
    return sign * (degrees + minutes / 60 + seconds / 3600);
}

/**
 * GCS Display code
 *
 * Responsible for updating the webpage based on the API
 */

// FUNCTIONS FOR UPDATING DISPLAY ITEMS
// Register elements to listen for API updates
const displayRegistry = {};
window.addEventListener("load", (event) => {
    document.querySelectorAll("[data-key]").forEach((elem) => {
        let key = elem.getAttribute("data-key"),
            prec = elem.getAttribute("data-precision"),
            type = elem.getAttribute("data-type");

        // Defaults
        let rego = { e: elem, t: "value" };
        if (prec != null) {
            rego.p = prec;
        }
        if (type != null) {
            rego.t = type;
        }

        /* Play sound if any state indicator is already problematic
         * (which at least in --experimental mode) will be the case).
         * Only that no specific element is in mind at this stage.
        */
        checkStateIndicator();

        // Register element
        if (key in displayRegistry) {
            displayRegistry[key].push(rego);
        } else {
            displayRegistry[key] = [rego];
        }
    });

    console.log(displayRegistry);
});

// Hotkeys for the navbar
window.addEventListener('keydown', (event) => {
    const styles = "h-full w-full flex flex-row items-center justify-center gap-2 whitespace-nowrap border-2 border-orange-900 px-2";
    const buttons = document.querySelectorAll('a.' + styles.replaceAll(" ", "."));

    // Only NaN would fail the test
    if (parseInt(event.key, 10) === parseInt(event.key, 10)) {
        // Get element by index from found elements list
        const index = parseInt(event.key, 10) - 1;

        if ((0 <= index) && (index < buttons.length)) {
            // Click the element (ignoring default browser behaviour)
            buttons[index].click();
            event.preventDefault();
        }
    }
});

const skippedKeys = [];
function sendDataToRegistry(apiData) {
    // Don't receive data until page has loaded
    if (Object.keys(displayRegistry).length === 0) {
        return;
    }

    // Flatten API data so that keys are in format a.b
    let flat = {};
    function flatten(prefix, obj) {
        if (prefix != "") {
            prefix = prefix + ".";
        }
        if (obj == null) {
            return;
        }
        Object.entries(obj).forEach(([key, value]) => {
            if (typeof value == "object") {
                flatten(prefix + key, value);
            } else {
                flat[prefix + key] = value;
            }
        });
    }
    flatten("", apiData);

    // TODO: Store last datapoint for every key
    //       and only update elements if it changes

    // Loop through flattened keys and update registered element
    Object.entries(flat).forEach(([key, value]) => {
        if (key in displayRegistry) {
            for (const reg of displayRegistry[key]) {
                if (metricOffline[key]) {
                    displaySetOffline(reg.e);
                    continue;
                }
                displaySetOnline(reg.e);
                let elem = reg.e,
                    prec = reg.p,
                    type = reg.t;
                switch (type) {
                    case "value":
                        displaySetValue(elem, value, prec);
                        break;
                    case "string":
                        displaySetString(elem, value);
                        break;
                    case "state":
                        displaySetState(elem, value);
                        break;
                }
            }
        } else if (skippedKeys.indexOf(key) == -1) {
            // Add skipped keys to a list, so we only warn about them once
            console.warn(`${key} not found in displayRegistry, skipping`);
            skippedKeys.push(key);
        }
    });
}

function displaySetValue(item, value, precision = 2, error = false) {
    // Updates a floating point value for a display item
    if (value != undefined && !Number.isNaN(value)) {
        if (logVerbose)
            console.debug(
                `new value %c${item}%c ${parseFloat(value).toFixed(precision)}`,
                "color:orange",
                "color:white",
            );

        // Use classes instead of IDs since IDs must be unique
        // and some items occur on multiple pages
        let elements = [item];
        if (typeof item == "string") {
            elements = document.querySelectorAll(`.${item}`);
        }
        if (elements && elements.length > 0) {
            elements.forEach((elem) => {
                // Update value
                elem.value = parseFloat(value).toFixed(precision);

                // Update error state
                if (error) {
                    elem.classList.add("error");
                } else {
                    elem.classList.remove("error");
                }
            });
        }
    }
}

function displaySetString(item, string) {
    // Updates the string in a display item
    if (string != undefined) {
        if (logVerbose)
            console.debug(
                `new string %c${item}%c ${string}`,
                "color:orange",
                "color:white",
            );

        // Update all instances of item
        let elements = [item];
        if (typeof item == "string") {
            elements = document.querySelectorAll(`.${item}`);
        }
        if (elements && elements.length > 0) {
            elements.forEach((elem) => {
                // Update string
                elem.value = string;
            });
        }
    }
}

function displaySetState(item, value) {
    // Updates the state of an indicator
    if (logVerbose)
        console.debug(
            `new state %c${item}%c ${value}`,
            "color:orange",
            "color:white",
        );

    // Update all instances of item
    let elements = [item];
    if (typeof item == "string") {
        elements = document.querySelectorAll(`.${item}`);
    }

    if (elements && elements.length > 0) {
        elements.forEach((elem) => {
            elem.classList.remove(...indicatorStates);
            // Convert true/false boolean values to on/error
            if (typeof value == "boolean") {
                value = value ? 1 : 3;
            }

            // Get indicator state from value (only then change the sound)
            if (value >= 0 && value < indicatorStates.length) {
                elem.classList.add(indicatorStates[value]);
            }

            // Check if sound needs to be played
            checkStateIndicator(elem);
        })
    }
}

/*
    The following functions are still called manually and should be integrated
    into the sendDataToRegistry() functionality
*/

function displaySetError(item, error) {
    // Adds/removed error class from element
    let elements = document.querySelectorAll(`.${item}`);
    if (elements && elements.length > 0) {
        elements.forEach((elem) => {
            if (error) {
                elem.classList.add("error");
            } else {
                elem.classList.remove("error");
            }
        });
    }
}

function displaySetOffline(elem) {
    const label = elem.closest("label");
    elem.value = "N/A"; // Has to be small
    elem.classList.add("offline");
    elem.classList.remove("error");
    if (label) label.classList.add("sensor-offline");
}

function displaySetOnline(elem) {
    const label = elem.closest("label");
    elem.classList.remove("offline");
    if (label) label.classList.remove("sensor-offline");
}

function displaySetActiveFlightState(item) {
    // Updates active flight state to a specific html element
    let elements = document.querySelectorAll(`.${item}`);

    // Remove error state
    let fsElements = document.querySelectorAll(`.indicator-flightstate`);
    if (fsElements && fsElements.length > 0) {
        fsElements.forEach((elem) => {
            elem.classList.remove("error");
        });
    }

    if (elements && elements.length > 0) {
        // Make sure we're actually updating this
        if (elements[0].classList.contains("active")) return;

        // The active element is different, update active item
        let active = document.querySelectorAll(`.active`);
        if (active && active.length > 0) {
            active.forEach((elem) => {
                elem.classList.remove("active");
            });
        }

        // Update active item
        elements.forEach((elem) => {
            elem.classList.add("active");
        });
    }

    // Launch timer
    if (item == "fs-state-preflight") {
        timers.launchTimestamp = 0;
    } else {
        if (
            timers.launchTimestamp == undefined ||
            timers.launchTimestamp == 0
        ) {
            timers.launchTimestamp = timestampApi;
        }
    }
}

function displaySetErrorFlightState() {
    // Add error state
    let elements = document.querySelectorAll(`.indicator-flightstate`);
    if (elements && elements.length > 0) {
        elements.forEach((elem) => {
            elem.classList.remove("active");
            elem.classList.add("error");
        });
    }
}

// FUNCTIONS FOR UPDATING MODULES
function displayUpdateFlightState(data) {
    /// MODULE FLIGHTSTATE
    if (data?.flightState) {
        displaySetError("fs-flightstate", false);

        let stateName = "";
        if (
            data.flightState == 0 ||
            data.flightState == "PRE_FLIGHT_NO_FLIGHT_READY"
        ) {
            // Preflight (not ready)
            stateName = "Pre-flight";
            displaySetActiveFlightState("fs-state-preflight");
        } else if (data.flightState == 1 || data.flightState == "LAUNCH") {
            // Launch
            stateName = "Launch";
            displaySetActiveFlightState("fs-state-launch");
        } else if (data.flightState == 2 || data.flightState == "COAST") {
            // Coast
            stateName = "Coast";
            displaySetActiveFlightState("fs-state-coast");
        } else if (data.flightState == 3 || data.flightState == "APOGEE") {
            // Apogee
            stateName = "Apogee";
            displaySetActiveFlightState("fs-state-apogee");

            // Play the apogee sound, whose file includes a parachute sound 2 seconds afterwards
            playOtherSound("Apogee");
        } else if (data.flightState == 4 || data.flightState == "DESCENT") {
            // Descent
            stateName = "Descent";
            displaySetActiveFlightState("fs-state-descent");
        } else if (data.flightState == 5 || data.flightState == "LANDED") {
            // Landed successfully
            stateName = "Landed";
            displaySetActiveFlightState("fs-state-landed");
        } else if (
            data.flightState == 6 ||
            data.flightState == 7 ||
            data.flightState == "OH_NO"
        ) {
            // Oh no oh no what the oh no :(
            stateName = "OH NO!";
            displaySetErrorFlightState();
            displaySetError("fs-flightstate", true);
        }

        displaySetString("fs-flightstate", stateName);
    }
}