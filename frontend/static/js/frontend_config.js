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
}

export { Config };