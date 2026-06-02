
/**
 * WebSocketClient
 * Keeps track of all the websocket connection handling
 */

import { API_OnMessage } from '/js/frontend_api.js';
import { Config as cfg } from '/js/frontend_config.js';
import { timestamp } from '/js/frontend_display.js';
import { logMessage } from '/js/frontend_utils.js';

class WebSocketClient {
    // Keep track of websocket client state
    static is_connected = false;
    static api_socket = new WebSocket(cfg.ws.url);
    static reconnect_interval = cfg.ws.initial_reconnect_interval;
    static reconnect_timeout

    // Functions for connecting
    static connect() {
        // Log connecting and readystate
        logMessage(`Connecting to ${cfg.ws.url} (${this.api_socket.readyState})`, 'ws')

        // Socket connected
        this.api_socket.onopen = () => {
            // Connected
            this.is_connected = true;
            timestamp.apiConnect = undefined;

            // Log connection
            if (cfg.logging.verbose) {
                console.log(`Successfully connected to websocket at: - ${cfg.ws.url}`)
            }
            logMessage('Successfully connected', 'ws')

            // Reset connection timeouts
            clearTimeout(this.reconnect_timeout)
            this.reconnect_interval = cfg.ws.initial_reconnect_interval
        }


        // Socket received message
        this.api_socket.onmessage = (event) => {
            // Connected
            this.is_connected = true;

            // Log message
            if (cfg.logging.websocket) {
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
                cfg.ws.max_reconnect_interval,
            )
        }, this.reconnect_interval)
    }
}

export { WebSocketClient }