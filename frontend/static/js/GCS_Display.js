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
        if (key in registry) {
            registry[key].push(rego);
        } else {
            registry[key] = [rego];
        }
    });

    console.log(registry);
});

function sendDataToRegistry(apiData) {
    //console.log(apiData);

    // Flatten API data so that keys are in format a.b
    let flat = {};
    function flatten(prefix, obj) {
        if (prefix != "") {
            prefix = prefix + ".";
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
        if (key in registry) {
            for (const reg of registry[key]) {
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
        if (verboseLogging)
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

function displaySetState(item, value, timeout = {}) {
    // Updates the state of an indicator
    if (verboseLogging)
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

            // Get indicator state from value
            if (value >= 0 && value < indicatorStates.length) {
                elem.classList.add(indicatorStates[value]);
            }

            if (timeout != undefined && Object.keys(timeout).length > 0) {
                Object.entries(timeout).forEach(([ms, state]) => {
                    clearTimeout(timeouts[[elem, ms]]);
                    timeouts[[elem, ms]] = setTimeout(() => {
                        displaySetState(elem, state); // timeout
                    }, parseInt(ms));
                });
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
