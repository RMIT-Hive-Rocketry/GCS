/**
 * Javascript configuration for GCS frontend
 */

class Config {
    // Logging
    static logging = {
        verbose: false,
        websocket: false, // Whether to log messages received from the websocket
        max_size_diagnostics: 40
    }

    // Websockets
    static ws = {
        url: `ws://${window.location.host.split(':')[0]}:1887`, // `ws://${_ws["host"]}:${_ws["port"]}`
        initial_reconnect_interval: 100, // Initial reconnection wait time
        max_reconnect_interval: 5000, // Maximum amount of time between reconnect attempts
    }

    // Graphing
    static graphs = {
        max_time: 20,  // Seconds of graph shown
        max_gap_size: 4,  // Max time between data points where line is drawn
        y_ticks: 8
    }

    // Sounds
    static sounds = {
        parachute_altitude: 1200
    }

    // API configuration
    static api = {
        packet_id: {
            pendant: 10,
            diagnostics: 50,
        },
        error_conditions: [
            {
                ids: ['weight_rocket'], // Rocket weight
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
                discard: {
                    min: -295,
                    max: 295,
                },
            },
            {
                ids: ['temp_vent'],
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
                    'temp_tank_top',
                    'temp_tank_middle',
                    'temp_tank_bottom',
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
                    'temp_pipe_n2o_gse',
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
                    'temp_vent',
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
                    'pressure_n2o_bottle',
                    'pressure_n2o_tank',
                    'pressure_o2_tank',
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
}

export { Config };
