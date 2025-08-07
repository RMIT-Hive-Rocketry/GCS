/**
 * GCS HMI code
 */

const color = ["#FF0000", "#00FF4D", "#FFF600"];
const colorBoolean = ["#FF0000", "#00FF4D"]; // for valves only (on/off)

function changecolor(objectid) {
    const elem = document.getElementById(objectid);
    if (elem != undefined) {
        const fill = elem.getAttribute("fill");
        let newFill;
        if (fill == undefined || fill == colorBoolean[1]) {
            newFill = colorBoolean[0];
        } else {
            newFill = colorBoolean[1];
        }
        elem.setAttribute("fill", newFill);
    }
}

function hmiUpdateValue(id, value) {
    if (value != undefined && !Number.isNaN(value)) {
        let elem = document.getElementById(id).firstElementChild;
        if (elem) {
            elem.innerHTML = value.toFixed(1);
            if (id == "HMI_N2O-1TEMP") {
                hmiUpdateTemperature("gauge_1_fill", value, "gauge_1_bar");
            } else if (id == "HMI_N2O-2TEMP") {
                hmiUpdateTemperature("gauge_2_fill", value, "gauge_2_bar");
            } else if (id == "HMI_O2TEMP") {
                hmiUpdateTemperature("gauge_3_fill", value, "gauge_3_bar");
            }
        }
    }
}

function hmiUpdateTemperature(id, value, id2) {
    const gauge = document.getElementById(id);
    const gaugesize = document.getElementById(id2);

    if (gauge) {
        if (value >= 15 && value <= 25) {
            gauge.setAttribute("fill", color[2]);
        } else if (value > 25) {
            gauge.setAttribute("fill", color[0]);
        } else if (value < 15) {
            gauge.setAttribute("fill", color[1]);
        }

        if (value >= 0 && value <= 36) {
            let height = 69 - (value / 36) * 69;
            gaugesize.setAttribute("height", height);
        } else if (value < 0) {
            gaugesize.setAttribute("height", 69);
        } else if (value > 36) {
            gaugesize.setAttribute("height", 0);
        }
    }
}

function hmiUpdateSolenoid(id, state) {
    if (state == undefined) return;
    if (typeof state != "boolean") return;

    // Get solenoid
    const solenoid = document.getElementById(id);
    if (solenoid == undefined) return;

    // Update colour
    solenoid.setAttribute("fill", colorBoolean[state ? 1 : 0]);
}
