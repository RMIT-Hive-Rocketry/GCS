/*
Utility code and functions for use by the GCS
*/

// Logging code
function logMessage(message, logType = '', timestamp = '') {
    // Make sure log area exists
    const logArea = document.getElementById('errorLogBox')
    if (!logArea) {
        // console.error("Log area not found.");
        return
    }

    // Calculate timestamp
    if (timestamp.local !== undefined && timestamp.apiConnect !== undefined) {
        timestamp
            = `${(timestamp.local + timestamp.apiConnect - timestamp.drift).toFixed(1)}s`
    } else {
        timestamp = '?';
    }

    // Handle different message types
    const messageTypes = {
        error: {
            logName: 'Error',
            textColor: 'text-red-400',
            function: console.error,
        },
        warning: {
            logName: 'Warning',
            textColor: 'text-yellow-300',
            function: console.warn,
        },
        ws: {
            logName: 'WebSocket',
            textColor: 'text-emerald-300',
            function: console.debug,
        },
        debug: {
            logName: 'Debug',
            textColor: 'text-white-900',
            function: console.debug,
        },
        critical: {
            logName: 'CRITICAL',
            textColor: 'text-red-crit',
            function: console.error,
        },
        success: {
            logName: 'Success',
            textColor: 'text-green-300',
            function: console.debug,
        },
    }

    let logName, textColor
    if (Object.keys(messageTypes).includes(logType)) {
        logName = messageTypes[logType].logName
        textColor = messageTypes[logType].textColor
        messageTypes[logType].function(timestamp, message)
    }
    else {
        logName = 'Notice'
        textColor = 'text-white'
        console.log(timestamp, message)
    }

    // Add message to log
    const line = document.createElement('span')
    line.classList.add('block', 'm-0', textColor)
    line.textContent = `[${timestamp}] ${logName}: ${message}`
    logArea.appendChild(line)

    // Limit lines
    const maxlines = 256
    while (logArea.children.length > maxlines) {
        logArea.removeChild(logArea.firstChild)
    }

    // // Scroll to bottom of log
    // logArea.scrollTop = logArea.scrollHeight;
}


// Converting between metres and feet
function metresToFeet(metres) {
    if (metres === undefined || Number.isNaN(metres))
        return undefined
    return metres * 3.28084
}


function feetToMetres(feet) {
    if (feet === undefined || Number.isNaN(feet))
        return undefined
    return feet / 3.28084
}

// Convert a compressed GPS value (which we get from a specific system?) into standard decimal coordinates
function gpsToDecimal(gps) {
    if (gps === undefined || Number.isNaN(gps) || gps === 0)
        return 0

    // Split string into parts
    let [intPart, decPart] = gps.toString().split('.')

    // Get sign (positive or negative)
    const sign = intPart >= 0 ? 1 : -1

    // Equations only work on positive numbers (since rounding and modulus changes in negative)
    intPart = Math.abs(intPart)
    const degrees = Number.parseInt(intPart / 100)
    const minutes = Number.parseInt(intPart % 100)
    let seconds = 0
    if (decPart !== undefined) {
        seconds = Number.parseFloat(`${decPart.slice(0, 2)}.${decPart.slice(2)}`)
    }

    // Convert to decimal
    return sign * (degrees + minutes / 60 + seconds / 3600)
}

export { feetToMetres, gpsToDecimal, logMessage, metresToFeet };
