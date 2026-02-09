/**
 * GCS Display
 *
 * Responsible for updating the webpage based on the API
 *
 * Functions and constants should be prefixed with "display"
 */

// FUNCTIONS FOR UPDATING DISPLAY ITEMS
var verboseLogging = false;
const indicatorStates = ["off", "green", "yellow", "red", "timeout", "error"];
const timeouts = {};

// Register elements to listen for API updates
const registry = {};
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

        // Register element
        if (key in registry) {
            registry[key].push(rego);
        } else {
            registry[key] = [rego];
        }
    });

    console.log(registry);
});

function displayUpdateRegistry(apiData) {
    // Flatten API data so that keys are in format data.a.b
    let flat = {};
    function flatten(prefix, obj) {
        Object.entries(obj).forEach(([key, value]) => {
            if (typeof value == "object") {
                flatten(prefix + "." + key, value);
            } else {
                flat[prefix + "." + key] = value;
            }
        });
    }
    flatten("data", apiData);

    // Loop through flattened keys and update registered element
    Object.entries(flat).forEach(([key, value]) => {
        if (key in registry) {
            for (const reg of registry[key]) {
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
                }
            }
        }
    });
}

function displaySetValue(item, value, precision = 2, error = false) {
    // Updates a floating point value for a display item
    if (value != undefined && !Number.isNaN(value)) {
        if (verboseLogging)
            console.debug(
                `new value %c${item}%c ${parseFloat(value).toFixed(precision)}`,
                "color:orange",
                "color:white"
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
        if (verboseLogging)
            console.debug(
                `new string %c${item}%c ${string}`,
                "color:orange",
                "color:white"
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

function displaySetState(item, value) {
    // Updates the state of an indicator
    if (verboseLogging)
        console.debug(
            `new state %c${item}%c ${value}`,
            "color:orange",
            "color:white"
        );

    // Update all instances of item
    let elements = document.querySelectorAll(`.${item}`);
    if (elements && elements.length > 0) {
        elements.forEach((elem) => {
            elem.classList.remove(...indicatorStates);

            // Convert true/false boolean values to on/error
            if (typeof value == "boolean") {
                value = value ? 1 : 3;
            }

            // Get indicator state from value
            if (value >= 0 && value < indicatorStates.length) {
                elem.classList.add(indicatorStates[value]);
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
function displayUpdateTime() {
    /// SYSTEM TIME
    if (timestampApi != 0) {
        // Rocket launch time
        // TODO: Find somewhere nicer to put this in the code, this is so jank
        if (timers?.launchTimestamp != undefined) {
            const launchTime =
                timers.launchTimestamp == 0
                    ? 0
                    : timestampApi - timers.launchTimestamp;
            displaySetString("fs-launch-time", `T+${launchTime.toFixed(1)}`);
        }
    }
    if (timestampLocal != undefined && timestampLocal != 0) {
        displaySetString(
            "fs-time-local",
            `${(timestampLocal + timestampApiConnect - timeDrift).toFixed(1)}s`
        );
    }
}

function displayUpdateAuxData(data) {
    /// MODULE AUXDATA
    // Transducers (Bar)
    if (data?.transducer1) {
        // N2O in pressure
        if (typeof hmiUpdateValue === "function")
            hmiUpdateValue("hmi-pressure-1", data.transducer1);
    }
    if (data?.transducer2) {
        // N2O out pressure
        if (typeof hmiUpdateValue === "function")
            hmiUpdateValue("hmi-pressure-2", data.transducer2);
    }
    if (data?.transducer3) {
        // O2 pressure
        if (typeof hmiUpdateValue === "function")
            hmiUpdateValue("hmi-pressure-3", data.transducer3);
    }

    // Thermocouples (degrees Celsius)
    if (data?.thermocouple1) {
        // n2o (int) temperature
        if (typeof hmiUpdateValue === "function")
            hmiUpdateValue("HMI_N2O-INTTEMP", data.thermocouple1);
    }
    if (data?.thermocouple2) {
        // n2o #1 pressure
        if (typeof hmiUpdateValue === "function")
            hmiUpdateValue("HMI_N2O-1TEMP", data.thermocouple2);
    }
    if (data?.thermocouple3) {
        // n2o #2 pressure
        if (typeof hmiUpdateValue === "function")
            hmiUpdateValue("HMI_N2O-2TEMP", data.thermocouple3);
    }
    if (data?.thermocouple4) {
        // o2 pressure
        if (typeof hmiUpdateValue === "function")
            hmiUpdateValue("HMI_O2TEMP", data.thermocouple4);
    }

    // Gas fill timer
    if (timers.gasFillTimer != undefined && timers.gasFillTimer != 0) {
        displaySetString(
            "aux-gasbottle-time",
            `${(timers.gasFillTimerTotal + timers.gasFillTimer).toFixed(2)}s`
        );
    }

    // Solenoids
    /*
    if (data?.stateFlags) {
        hmiUpdateSolenoid("solenoidsV5", data.stateFlags.n20FillActivated);
        hmiUpdateSolenoid("solenoidsV6", data.stateFlags.o2FillActivated);
        hmiUpdateSolenoid("solenoidsV7", data.stateFlags.manualPurgeActivated); // Normally open
    }
    */
}

function displayUpdateAvionics(data) {
    /// MODULE AVIONICS
    // Indicators
    if (data?.navigationStatus) {
        // Nav state
        if (["NF"].includes(data.navigationStatus)) {
            // Red
            displaySetState("av-state-gpsfix", 3);
        } else if (["DR", "TT"].includes(data.navigationStatus)) {
            // Yellow
            displaySetState("av-state-gpsfix", 2);
        } else if (
            ["D2", "D3", "G2", "G3", "RK"].includes(data.navigationStatus)
        ) {
            // Green
            displaySetState("av-state-gpsfix", 1);
        }
    }

    if (data?.stateFlags) {
        if (data.stateFlags?.dualBoardConnectivityStateFlag) {
            displaySetState(
                "av-state-dualboard",
                data.stateFlags.dualBoardConnectivityStateFlag ? 1 : 5 // green / error
            );
        }
    }
}

function displayUpdateSystemFlags(data) {
    // green : off
    if (data?.stateFlags) {
        if (data.stateFlags?.dualBoardConnectivityStateFlag) {
            displaySetState(
                "sysflags-state-dualboard",
                data.stateFlags.dualBoardConnectivityStateFlag ? 1 : 0
            );
        }
        if (data.stateFlags?.recoveryChecksCompleteAndFlightReady) {
            displaySetState(
                "sysflags-state-recovery",
                data.stateFlags.recoveryChecksCompleteAndFlightReady ? 1 : 0
            );
        }
        if (data.stateFlags?.payloadConnectionFlag) {
            displaySetState(
                "sysflags-state-payload",
                data.stateFlags.payloadConnectionFlag ? 1 : 0
            );
        }
        if (data.stateFlags?.cameraControllerConnectionFlag) {
            displaySetState(
                "sysflags-state-camera",
                data.stateFlags.cameraControllerConnectionFlag ? 1 : 0
            );
        }
    }
}

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

function displayUpdateRadio(data) {
    /// MODULE RADIO
    if (data?.meta?.radio) {
        if (data.meta.radio == "av1") {
            // AVIONICS DATA
            // Connection indicators
            displaySetState("radio-av-state", 1); // green

            if (timeouts != undefined) {
                // Show idle timeout error after 3 seconds
                clearTimeout(timeouts?.radioAv1Idle);
                timeouts.radioAv1Idle = setTimeout(() => {
                    displaySetState("radio-av-state", 4); // timeout
                }, 3000);

                // Show error after 10 seconds
                clearTimeout(timeouts?.radioAv1Error);
                timeouts.radioAv1Error = setTimeout(() => {
                    displaySetState("radio-av-state", 5); // error
                }, 10000);
            }

            if (data?.meta?.packets) {
                // Lost packets calculation
                let lostPackets =
                    data.meta.totalPacketCountAv - data.meta.packets;
            }
        } else if (data.meta.radio == "gse") {
            // GSE DATA
            // Connection indicators
            displaySetState("radio-gse-state", 1);

            if (timeouts != undefined) {
                // Show idle timeout error after 3 seconds
                clearTimeout(timeouts?.radioGseIdle);
                timeouts.radioGseIdle = setTimeout(() => {
                    displaySetState("radio-gse-state", 4); // timeout
                }, 3000);

                // Show error after 10 seconds
                clearTimeout(timeouts?.radioGseError);
                timeouts.radioGseError = setTimeout(() => {
                    displaySetState("radio-gse-state", 5); // error
                }, 10000);
            }

            if (data?.meta?.packets) {
                // Lost packets calculation
                let lostPackets =
                    data.meta.totalPacketCountGse - data.meta.packets;
            }
        }
    }
}
