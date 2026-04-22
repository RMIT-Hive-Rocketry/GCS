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

// API connection
const api_url = window.location.host.split(":")[0];
const ws_url = `ws://${api_url}:1887`;
const apiSocket = new WebSocket(ws_url);
var reconnectInterval = initialReconnectInterval;
var reconnectTimeout;
var connected = false;
var then, now, fpsInterval;

// Logging
const logVerbose = false;
const logIncomingMessages = false;
const errors = [];
const timeouts = {};

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

// Generate the sounds
const filenames = ["AV_Loss", "GSE_Loss", "Dual_Board_Loss", "GPS_Fix_Loss"];
const soundsList = filenames.map(src => {
    // Create the audio object that will return upon ending
    const audioObject = new Audio("sounds/" + src + ".mp3");
    audioObject.addEventListener('ended', () => {
        audioObject.pause();
        audioObject.currentTime = 0;
    });

    /* Active means whether the sound should be playing
     * but the mute status is stored inside source
    */
    return { source: audioObject, active: false };
});

// Check if all sounds are unmuted
function allUnmuted() {
    return soundsList.every(item => !item.source.mute);
}

function toggleMute() {
    // Toggle mute first, then update UI
    for (let i = 0; i < soundsList.length; ++i) {
        soundsList[i].source.mute = !soundsList[i].source.mute;
    }

    /* Icon represents current state.
     * In addition, the icons are free to use per https://creativecommons.org/licenses/by/4.0/,
     * modified by changing the colour to a Horizon-themed gradient (and converting to PNG so that
     * they are easier to use as buttons). The SVGs remain in this repository if the icons need
     * to be changed in the future.
    */
    if (allUnmuted()) {
        document.getElementById("toggleIcon").src = "img/icons/sound-unmuted.png";
        document.getElementById("toggleIcon").alt = "Sound unmuted";
    }
    else {
        document.getElementById("toggleIcon").src = "img/icons/sound-muted.png";
        document.getElementById("toggleIcon").alt = "Sound muted";
    }
}

/* Plays sounds in a particular (relative) order, determined by the
 * order in which their names (rather, something close to that) appear
 * in the filenames array closer to the top.
*/
function playSounds() {
    for (let i = 0; i < soundsList.length; ++i) {
        // Play the active sounds in succession
        if (soundsList[i].active) {
            soundsList[i].source.play();
        }
    }

    // 1 second silence after all alarms finished
    const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));
    async function silence() { await sleep(1000); }
    silence();
}

// Play/manual reset in one go
function updateSound(sound, newValue) {
    const soundNumber = soundsList.findIndex(
        file => file.source.src.includes(sound)
    );
    
    // If newValue is true, the sound should play when called
    if (soundNumber >= 0) {
        soundsList[soundNumber].active = newValue;
    }

    /* Don't play any sound if none are active (else
     * that would delay any future ones by an extra second).
    */
    if (soundsList.some(user => user.active)) {
        playSounds();
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
            localTime: `${(timestampLocal + timestampApiConnect - timeDrift).toFixed(1)}s`,
        });
    }
}

// Logging code
function logMessage(message, type = "") {
    // Make sure log area exists
    const logArea = document.getElementById("errorLogBox");
    if (!logArea) {
        // console.error("Log area not found.");
        return;
    }

    // Calculate timestamp
    let timestamp = "?";
    if (timestampLocal != undefined && timestampApiConnect != undefined) {
        timestamp =
            (timestampLocal + timestampApiConnect - timeDrift).toFixed(1) + "s";
    }

    // Handle different message types
    let logName = "Notice";
    let textColor = "text-white";

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
        console.log(timestamp, message);
    }

    // Add message to log
    const line = document.createElement("span");
    line.classList.add("block", "m-0", textColor);
    line.textContent = `[${timestamp}] ${logName}: ${message}`;
    logArea.appendChild(line);

    // Limit lines
    const maxlines = 16;
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

        // Flag data for errors
        checkErrorConditions(apiLatest.data);

        // Process data for display
        apiData = processDataForDisplay(apiLatest.data, apiLatest.id);
        sendDataToRegistry(apiData);

        // Legacy Legacy support
        if (typeof hmiUpdate === "function") {
            hmiUpdate(apiData);
        }

        // Handle different packet types
        if (apiData.id == 3 || apiData.id == 4) {
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
        } else if (apiData.id == 6 || apiData.id == 7) {
            ///// ----- GSE PACKETS ----- /////
            // Graphs
            if (typeof graphUpdateAuxData === "function") {
                graphUpdateAuxData(apiData);
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
            IDs: ["analogVoltageInput1"], // Rocket weight
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
            IDs: ["internalTemp"],
            discard: {
                min: -1,
                max: 128,
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
                "thermocouple1",
                "thermocouple2",
                "thermocouple3",
                "thermocouple4",
            ],
            error: {
                max: 34.5,
            },
            errorMessage: "flag raised",
            discard: {
                min: -128,
                max: 128,
            },
        },
        {
            IDs: ["transducer1", "transducer2", "transducer3"],
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
        } else if ([6, 7].includes(apiId)) {
            if (apiData.meta?.totalPacketCountGse) {
                if (packetsGSE == 0) {
                    packetsGSEoffset = apiData.meta.totalPacketCountGse - 1;
                }
                processedData.meta.totalPacketCountGse =
                    apiData.meta.totalPacketCountGse - packetsGSEoffset;
            }

            processedData.meta.radio = "gse";
            processedData.meta.gse = {
                rssi: apiData.meta.rssi,
                snr: apiData.meta.snr,
                packets: ++packetsGSE,
                lostPackets:
                    processedData.meta.totalPacketCountGse - packetsGSE,
            };
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

    // Gas fill timer
    if ([6, 7].includes(apiId) && apiData?.stateFlags) {
        const systemActivated = apiData.stateFlags?.systemActivated;
        const gasFillSelected = apiData.stateFlags?.gasFillSelected;
        const n20FillActivated = apiData.stateFlags?.n20FillActivated;

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
            type = elem.getAttribute("data-type"),
            timeout = elem.getAttribute("data-timeout");

        // Defaults
        let rego = { e: elem, t: "value" };
        if (prec != null) {
            rego.p = prec;
        }
        if (type != null) {
            rego.t = type;
        }
        if (timeout != null) {
            console.log(timeout);
            rego.to = JSON.parse(timeout);
        }

        // Register element
        if (key in displayRegistry) {
            displayRegistry[key].push(rego);
        } else {
            displayRegistry[key] = [rego];
        }
    });

    console.log(displayRegistry);
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
                let elem = reg.e,
                    prec = reg.p,
                    type = reg.t,
                    timeout = reg.to;
                switch (type) {
                    case "value":
                        displaySetValue(elem, value, prec);
                        break;
                    case "string":
                        displaySetString(elem, value);
                        break;
                    case "state":
                        displaySetState(elem, value, timeout);
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

function displaySetState(item, value, timeout = {}) {
    const indicatorStates = ["off", "green", "yellow", "red", "timeout", "error"];

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

            // Complex way to get the required indicator
            let indicator = elem.attributes[0].textContent;
            let sound = "";

            /* All sounds come from https://www.youtube.com/watch?v=EWnhSCFCYto
             * except the last one (https://www.youtube.com/watch?v=W5Z-d1Zx02o)
            */
            if (indicator.includes("av.radio")) {
                sound = "AV_Loss";
            }
            else if (indicator.includes("gse.radio")) {
                sound = "GSE_Loss";
            }
            else if (indicator.includes("gpxFix")) {
                sound = "GPS_Fix_Loss";
            }
            else if (indicator.includes("dualBoard")) {
                sound = "Dual_Board_Loss";
            }

            // Should only execute with one of the above values
            if (sound !== "") {
                /* Can be changed, but at this stage only green is a good state,
                 * where the sound resets (otherwise continues playing). Also,
                 * elem.classList.value is the styling itself (use this so that
                 * in case the interested state/s exist elsewhere in the string)
                */
                updateSound(sound, elem.classList.value.includes("green"));

                if (timeout != undefined && Object.keys(timeout).length > 0) {
                    Object.entries(timeout).forEach(([ms, state]) => {
                        clearTimeout(timeouts[[elem, ms]]);
                        timeouts[[elem, ms]] = setTimeout(() => {
                            displaySetState(elem, state); // timeout
                        }, parseInt(ms));
                    });
                }
            }
        });
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
            stateName = "Pre-flight (not ready)";
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