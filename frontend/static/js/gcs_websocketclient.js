
/**
 * WebSocketClient
 * Keeps track of all the websocket connection handling
 */

import { API_OnMessage } from '/js/gcs_api.js';
import { logMessage, logVerbose, timestamp } from '/js/gcs_utils.js';

class WebSocketClient {
    // Constants
    static ws_url = `ws://${window.location.host.split(':')[0]}:1887`
    static max_reconnect_interval = 5000 // Maximum amount of time between reconnect attempts
    static initial_reconnect_interval = 100 // Initial reconnection wait time
    static log_messages = false; // Whether to log messages received from the websocket

    // Keep track of websocket client state
    static is_connected = false;
    static api_socket = new WebSocket(this.ws_url);
    static reconnect_interval = this.initial_reconnect_interval;
    static reconnect_timeout

    // Functions for connecting
    static connect() {
        // Log connecting and readystate
        logMessage(`Connecting to ${this.ws_url} (${this.api_socket.readyState})`, 'ws')


        // Socket connected
        this.api_socket.onopen = () => {
            // Connected
            this.is_connected = true;
            timestamp.apiConnect = undefined;

            // Log connection
            if (logVerbose) {
                console.log(`Successfully connected to websocket at: - ${WebSocketClient.ws_url}`)
            }
            logMessage('Successfully connected', 'ws')

            // Reset connection timeouts
            clearTimeout(this.reconnect_timeout)
            this.reconnect_interval = this.initial_reconnect_interval
        }


        // Socket received message
        this.api_socket.onmessage = (event) => {
            // Connected
            this.is_connected = true;

            // Log message
            if (this.log_messages) {
                console.log('Received message data', event.data);
            }

            // Send event data to API
            API_OnMessage(event.data);
        }


        // Socket error
        this.api_socket.onerror = (error) => {
            // Disconnected
            this.is_connected = false;
            timestamp.apiConnect = undefined;

            // Log error
            logMessage(`Connection error: ${error}`, 'ws')
        }


        // Socket closed
        this.api_socket.onclose = () => {
            // Disconnected
            this.is_connected = false;
            timestamp.apiConnect = undefined;

            // Log on browser console
            console.warn(
                'Socket closed',
                {
                    wasClean: event.wasClean,
                    code: event.code,
                    reason: event.reason,
                },
                'Attempting to reconnect automatically',
            )

            // Log on page
            logMessage('Connection lost, attempting to reconnect', 'ws')

            // Attempt reconnecting
            this.scheduleReconnect()
        }


        // Monitor readystate every 10 seconds
        setInterval(() => {
            if (this.api_socket) {
                console.info(`WebSocket readyState: ${this.api_socket.readyState}`)
            }
        }, 10000)
    }

    // Function for automatically reconnecting after a timeout
    static scheduleReconnect() {
        this.reconnect_timeout = setTimeout(() => {
            this.connect()
            this.reconnect_interval = Math.min(
                this.reconnect_interval * 2,
                this.max_reconnect_interval,
            )
        }, this.reconnect_interval)
    }
}

export { WebSocketClient }