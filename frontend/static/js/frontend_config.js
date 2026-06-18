/**
 * Javascript configuration for GCS frontend
 */

/* global d3 */


class Config {
    // GPS
    static gps = {
        // Scaling constants
        lat_scale_factor: 110.87,
        lon_scale_factor: 95.48,

        // Expected GCS coords (decimal)
        gcs_lat: 31.039581,
        gcs_lon: 103.526623,
    }

    // Websockets
    static ws = {
        url: `ws://${window.location.host.split(':')[0]}:1887`, // `ws://${_ws["host"]}:${_ws["port"]}`
        initial_reconnect_interval: 100, // Initial reconnection wait time
        max_reconnect_interval: 5000, // Maximum amount of time between reconnect attempts
    }

    // Logging
    static logging = {
        verbose: false,
        websocket: false, // Whether to log messages received from the websocket
        max_size_diagnostics: 40
    }

    // Display
    static display = {
        indicator_states: ['off', 'green', 'yellow', 'red', 'timeout', 'error'],
    }

    // Graphing
    static graphs = {
        max_time: 60,  // Seconds of graph shown for avionics graphs
        max_gap_size: 4,  // Max time between data points where line is drawn
        render_rate: 20,  // Frames per second that graphs are updates
        y_ticks: 8,
        line_colours: [
            "#FF0000",
            "#00FF00",
            "#0000FF",
            // "#FFFFFF", - not required at this stage
        ],
        default_margins: { top: 6, right: 10, bottom: 24, left: 50 },
        symbol_circle: d3.symbol().type(d3.symbolCircle).size(10),
        av: {
            accel: {
                selector: "#graph-av-accel",
                ylabel: "Acceleration (g)",
                numLines: 3,
                data: [],
            },
            gyro: {
                selector: "#graph-av-gyro",
                ylabel: "Rotation Rate (°/s)",
                numLines: 3,
                data: [],
            },
            velocity: {
                selector: "#graph-av-velocity",
                ylabel: "Vertical Speed (m/s)",
                numLines: 1,
                limits: {
                    yBottomMax: 0,
                    yBottomMin: 0,
                },
                data: [],
            },
        },
        pos: {
            alt: {
                selector: "#graph-pos-alt",
                ylabel: "Altitude (ft)",
                numLines: 1,
                limits: {
                    yBottomMax: 0,
                },
                data: [],
            }
        },
        gse: {
            transducers: {
                max_time: 20,
                selector: "#graph-aux-transducers",
                ylabel: "Pressure (bar)",
                numLines: 3,
                limits: {
                    yBottomMax: 0,
                },
                data: [],
            },
            thermocouples: {
                max_time: 20,
                selector: "#graph-aux-thermocouples",
                ylabel: "Temperature (°C)",
                numLines: 3,
                limits: {
                    yBottomMax: 0,
                },
                data: [],
            },
            vent_temp: {
                max_time: 20,
                selector: "#graph-aux-venttemp",
                ylabel: "Temperature (°C)",
                numLines: 1,
                limits: {
                    yBottomMax: 0,
                },
                data: [],
            },
            supply_temp: {
                max_time: 20,
                selector: "#graph-aux-n2o-supply-temp",
                ylabel: "Temperature (°C)",
                numLines: 1,
                data: [],
            },
        },
        test: {
            colours: {
                selector: "#graph-test-colours",
                ylabel: "Sample metric",
                numLines: 3,
                data: [],
            }
        }
    }

    // API configuration
    static api = {
        packet_id: {
            avionics: 3,
            avionics_rocket: 4,
            pendant: 10,
            logging: 40,
            network: 50,
            gse: 55,
        },
        error_conditions: [
            {
                ids: ['rocket_weight'], // Rocket weight
                discard: {
                    min: -1,
                    max: 128,
                },
            },
            {
                ids: [
                    'accelLowX',
                    'accelLowY',
                    'accelLowZ',
                    'accelHighX',
                    'accelHighY',
                    'accelHighZ',
                ],
                discard: {
                    min: -32,
                    max: 32,
                },
            },
            {
                ids: ['altitude'],
                discard: {
                    min: -128,
                    max: 8192,
                },
            },
            {
                ids: ['velocity'],
                discard: {
                    min: -128,
                    max: 1024,
                },
            },
            {
                ids: ['GPSLatitude', 'GPSLongitude'],
                discard: {
                    min: -18000,
                    max: 18000,
                },
            },
            {
                ids: ['gyroX', 'gyroY', 'gyroZ'],
            },
            {
                ids: ['vent_temp'],
                discard: {
                    min: -200,
                    max: 80,
                },
            },
            {
                ids: ['mach_speed'],
                discard: {
                    min: -1,
                    max: 16,
                },
            },
            {
                ids: ['qw', 'qx', 'qy', 'qz'],
                discard: {
                    min: -1,
                    max: 1,
                },
            },
            {
                ids: ['navigationStatus'],
                accept: ['NF', 'DR', 'G2', 'G3', 'D2', 'D3', 'RK', 'TT'],
            },
            {
                ids: ['flightState'],
                accept: [
                    'PRE_FLIGHT_NO_FLIGHT_READY',
                    'LAUNCH',
                    'COAST',
                    'APOGEE',
                    'DESCENT',
                    'LANDED',
                    'OH_NO',
                ],
            },
            {
                ids: ['gasBottleWeight1', 'gasBottleWeight2'],
                error: {
                    min: 15.1,
                    max: 19,
                },
                error_message: 'out of range',
                discard: {
                    min: -1,
                    max: 128,
                },
            },
            {
                ids: [
                    'rtd_top',
                    'rtd_middle',
                    'rtd_bottom',
                ],
                error: {
                    max: 30,
                },
                error_message: ' warming',
                discard: {
                    min: -128,
                    max: 128,
                },
            },
            {
                ids: [
                    'n2o_temp',
                ],
                error: {
                    max: 40,
                },
                error_message: ' warming',
                discard: {
                    min: -128,
                    max: 128,
                },
            },
            {
                ids: [
                    'vent_temp',
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
                ids: [
                    'bottle_pressure',
                    'tank_pressure',
                    'o2_pressure',
                ],
                error: {
                    max: 64.5,
                },
                error_message: 'flag raised',
                discard: {
                    min: -1,
                    max: 128,
                },
            },
        ]
    }

    // Sounds
    static audio = {
        // Altitude in metres for when to play parachute sound
        parachute_altitude: 1200,
        // Radius in metres from GCS for overhead warning (rocket coming down)
        overhead_warn_radius: 50,
        /*
        Combine all timeouts into one array of objects (only for radios)
        so we can program sound alarms in a queue, with past rockets included
        for legacy support (replaces data-timeout attribute).
        */
        timeouts: {
            "Legacy3": [
                { name: 'av', duration: 3000, state: 4 },
                { name: 'av', duration: 10000, state: 5 },
                { name: 'gse', duration: 3000, state: 4 },
                { name: 'gse', duration: 10000, state: 5 },
            ],
            "Atlas": [
                { name: 'av', duration: 3000, state: 4 },
                { name: 'av', duration: 10000, state: 5 },
                { name: 'gse', duration: 3000, state: 4 },
                { name: 'gse', duration: 10000, state: 5 },
            ],
            "Horizon": [
                { name: 'av', duration: 5000, state: 4 },
                { name: 'gse', duration: 5000, state: 4 },
            ]
        },
    }

    // Network diagnostics
    static network = {
        devices: {
            control: [
                // "TP-Link Router",
                "GC-1",
                "GC-2",
                // "WiFi Bridge Control"
            ],
            gse: [
                "Launchpad Cam",
                "LabJack",
                "QuantumX DAQ",
                "DAQ 4-Channel",
                "Vulcan ESP32",
                // "WiFi Bridge GSE"
            ],
        },
        render_rate_s: 1.8,
    }
}

export { Config };
