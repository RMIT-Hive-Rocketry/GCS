/* eslint-disable no-unused-vars */
/**
 * GCS Testing
 *
 * Contains a number of functions for testing different features
 *
 * Functions and constants should be prefixed with "testing_"
 */

import { API_OnMessage } from '/js/frontend_api.js'

const TESTING_API = [
    {
        id: 3,
        data: {
            meta: {
                rssi: -15.454711,
                snr: 0.37879905,
                timestampS: 24.453794,
                totalPacketCountAv: "1420",
                totalPacketCountGse: "946",
            },
            flightState: "PRE_FLIGHT_NO_FLIGHT_READY",
            stateFlags: {
                dualBoardConnectivityStateFlag: false,
                recoveryChecksCompleteAndFlightReady: false,
                GPSFixFlag: false,
                payloadConnectionFlag: true,
                cameraControllerConnectionFlag: true,
            },
            accelLowX: 15.462402,
            accelLowY: -4.169922,
            accelLowZ: -11.291992,
            accelHighX: 30.924805,
            accelHighY: -8.339844,
            accelHighZ: -22.583984,
            gyroX: 236.76625,
            gyroY: -63.84875,
            gyroZ: -172.90875,
            altitude: 548.1366,
            velocity: 346.6535,
            apogeePrimaryTestComplete: false,
            apogeeSecondaryTestComplete: false,
            apogeePrimaryTestResults: false,
            apogeeSecondaryTestResults: false,
            mainPrimaryTestComplete: false,
            mainSecondaryTestComplete: false,
            mainPrimaryTestResults: false,
            mainSecondaryTestResults: false,
            broadcastFlag: false,
            mach_number: 1.0250354996644375,
        },
    },
    {
        id: 4,
        data: {
            meta: {
                rssi: -14.7131,
                snr: 0.442897,
                timestampS: 24.412556,
                totalPacketCountAv: "1418",
                totalPacketCountGse: "944",
            },
            flightState: "PRE_FLIGHT_NO_FLIGHT_READY",
            stateFlags: {
                dualBoardConnectivityStateFlag: false,
                recoveryChecksCompleteAndFlightReady: false,
                GPSFixFlag: false,
                payloadConnectionFlag: true,
                cameraControllerConnectionFlag: true,
            },
            GPSLatitude: 15.598267,
            GPSLongitude: 145.00623,
            navigationStatus: "NA",
            qw: 0.77705765,
            qx: -0.4887131,
            qy: -0.66137505,
            qz: 0.333873,
        },
    },
    {
        id: 5,
        data: {
            meta: {
                rssi: -14.7131,
                snr: 0.442897,
                timestampS: 24.42302,
                totalPacketCountAv: "1419",
                totalPacketCountGse: "944",
            },
            flightState: "PRE_FLIGHT_NO_FLIGHT_READY",
            stateFlags: {
                dualBoardConnectivityStateFlag: false,
                recoveryChecksCompleteAndFlightReady: false,
                GPSFixFlag: false,
                payloadConnectionFlag: true,
                cameraControllerConnectionFlag: true,
            },
        },
    },
    {
        id: 6,
        data: {
            meta: {
                rssi: -14.7131,
                snr: 0.442897,
                timestampS: 24.433107,
                totalPacketCountAv: "1419",
                totalPacketCountGse: "945",
            },
            stateFlags: {
                manualPurgeActivated: false,
                o2FillActivated: false,
                selectorSwitchNeutralPosition: false,
                n20FillActivated: false,
                ignitionFired: false,
                ignitionSelected: false,
                gasFillSelected: false,
                systemActivated: false,
            },
            bottle_pressure: 1.0717549,
            tank_pressure: 23.961843,
            n2o_temp: 28.156767,
            thermocouple2: 10.335935,
            thermocouple3: 21.843233,
            thermocouple4: 39.664066,
            errorFlags: {
                ignitionError: false,
                relay3Error: false,
                relay2Error: false,
                relay1Error: false,
                thermocouple4Error: false,
                thermocouple3Error: false,
                thermocouple2Error: false,
                thermocouple1Error: false,
                loadCell4Error: false,
                loadCell3Error: false,
                loadCell2Error: false,
                loadCell1Error: false,
                transducer4Error: false,
                transducer3Error: false,
                transducer2Error: false,
                transducer1Error: false,
            },
        },
    },
    {
        id: 7,
        data: {
            meta: {
                rssi: -14.7131,
                snr: 0.442897,
                timestampS: 24.443491,
                totalPacketCountAv: "1419",
                totalPacketCountGse: "946",
            },
            stateFlags: {
                manualPurgeActivated: false,
                o2FillActivated: false,
                selectorSwitchNeutralPosition: false,
                n20FillActivated: false,
                ignitionFired: false,
                ignitionSelected: false,
                gasFillSelected: false,
                systemActivated: false,
            },
            ventTemp: 16.623802,
            windSpeed: 15.180423,
            gasBottleWeight1: 12,
            gasBottleWeight2: 16,
            rocket_weight: 16.623802,
            analogVoltageInput2: 0,
            additionalCurrentInput1: 0,
            additionalCurrentInput2: 0,
            errorFlags: {
                ignitionError: false,
                relay3Error: false,
                relay2Error: false,
                relay1Error: false,
                thermocouple4Error: false,
                thermocouple3Error: false,
                thermocouple2Error: false,
                thermocouple1Error: false,
                loadCell4Error: false,
                loadCell3Error: false,
                loadCell2Error: false,
                loadCell1Error: false,
                transducer4Error: false,
                transducer3Error: false,
                transducer2Error: false,
                transducer1Error: false,
            },
        },
    },
];

/// DISPLAY
function _testing_updateAllDisplayValues() {
    /* TESTING_DISPLAY_STATES.forEach((item, i) => {
        displaySetState(item, i);
    });
    TESTING_DISPLAY_ITEMS.forEach((item, i) => {
        displaySetValue(item, i);
    }); */
}

/// API
function _testing_mockApi() {
    TESTING_API.forEach((mockPacket) => {
        API_OnMessage({ data: JSON.stringify(mockPacket) });
    });
}

/// GRAPHS

/// ROCKET

// TEST DATA
