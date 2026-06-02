/*
This is the main javascript program for the GCS frontend, and runs the core program loop.
All other functionality is implemented in different files and imported into this program.
*/

// Note for JS developers:
// variables    =   snake_case
// functions    =   camelCase
// classes      =   PascalCase

/// IMPORTS
import { WebSocketClient } from '/js/gcs_websocketclient.js'

/// CONFIGURATION


/// START WEBSOCKET
WebSocketClient.connect();


/// EVENT LISTENERS
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        // Clear timeouts when tabbed away from
        clearTimeout(WebSocketClient.reconnect_timeout);
    }
    else {
        // Attempt reconnecting again
        if (WebSocketClient.is_connected === false) {
            WebSocketClient.scheduleReconnect();
        }
    }
})
