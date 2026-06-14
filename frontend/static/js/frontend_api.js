/**
 * GCS API
 *
 * Receives data from the API and loads it into memory to be accessed by other javascript modules.
 *
 * Functions and constants should be prefixed with "api_"
 */

/* global hmiUpdate, rocketUpdate, updatePendantState */

import { Config as cfg } from '/js/frontend_config.js';
import { displaySloggerLogs, displayUpdateFlightState, playOtherSound, sendDataToRegistry, soundGetOther, timers, timestamp, updateMetricOffline, updateTimestamp } from '/js/frontend_display.js';
import { graphUpdateAuxData, graphUpdateAvionics, updateNetworkDiagnostics2, graphUpdatePosition } from '/js/frontend_graphs.js';
import { updateNetworkDiagnostics } from '/js/frontend_network_diagnostics.js';
import { gpsToDecimal, logMessage, metresToFeet } from '/js/frontend_utils.js';

// Global display values
const errors = []
const altitudeHistory = []
let altitudeMax
let packetsAV1 = 0
let packetsAV1offset = 0

// Handle incoming messages through the API
function API_OnMessage(event_data) {
    let apiLatest, apiData
    const pid = cfg.api.packet_id
    try {
        // Handle incoming data
        apiLatest = JSON.parse(event_data)

        // When detected Slogger Packets just skip the whole validation part and just upload packets avoids feeding in old data just to get template to work
        if (apiLatest.id === pid.logging) {
            // Slogger
            displaySloggerLogs(apiLatest.data.slogger)
            return
        }

        // Flag data for errors
        checkErrorConditions(apiLatest.data)

        // Check if any data has gone offline
        // This should be constant throughout runtime,
        // But it's worth checking every packet at this stage to avoid a bug
        checkOfflineData(apiLatest.data)

        // Process data for display
        // console.log(apiLatest.data, apiLatest.id);
        apiData = processDataForDisplay(apiLatest.data, apiLatest.id)
        sendDataToRegistry(apiData)

        // Legacy Legacy support
        if (typeof hmiUpdate === 'function') {
            hmiUpdate(apiData)
        }

        // Handle different packet types
        if (apiData.id === pid.avionics || apiData.id === pid.avionics_rocket) {
            // Avionics packets
            // Display values
            displayUpdateFlightState(apiData)

            // Graphs
            graphUpdateAvionics(apiData)
            graphUpdatePosition(apiData)

            // Rocket visualisation
            if (apiData.id === pid.avionics_rocket) {
                if (typeof rocketUpdate === 'function') {
                    rocketUpdate(apiData)
                }
            }
        }
        else if (apiData.id === pid.pendant) {
            // Control pendant
            if (typeof updatePendantState === 'function') {
                updatePendantState(apiData)
            }
        }
        else if (apiData.id === pid.network) {
            // Network diagnostics
            updateNetworkDiagnostics(apiData)
            updateNetworkDiagnostics2(apiData)
        }
        else if (apiData.id === pid.gse) {
            // GSE packets
            graphUpdateAuxData(apiData)
        }
    }
    catch (error) {
        console.error('Data processing error:', error)
    }
}

// Check data for error conditions
function checkErrorConditions(apiData) {
    // Get error flags from the API and use as overrides
    const errorOverrides = []
    if (apiData.errorFlags !== undefined) {
        Object.entries(apiData.errorFlags).forEach(([key, value]) => {
            if (value === true) {
                errorOverrides.push(key)
            }
        })
    }

    // Iterate over all error conditions
    cfg.api.error_conditions.forEach((errorCondition) => {
        // Error conditions may apply equivalently to multiple data IDs
        errorCondition.ids.forEach((id) => {
            // Make sure the ID is defined within the current packet
            if (
                Object.keys(apiData).includes(id)
                && apiData[id] !== undefined
            ) {
                const apiDataValue = apiData[id]
                const apiDataType = typeof apiDataValue
                if (apiDataValue !== undefined) {
                    // Define error key
                    const errorKey = `${id}Error`
                    let isError = false
                    const isErrorApi = errorOverrides.includes(errorKey)
                    let isDiscard = false

                    // Check error ranges if the value is a number
                    if (apiDataType === 'number') {
                        // Check against error ranges
                        if (errorCondition?.error) {
                            if (
                                errorCondition.error?.min
                                && apiDataValue < errorCondition.error.min
                            ) {
                                isError = true
                            }
                            if (
                                errorCondition.error?.max
                                && apiDataValue > errorCondition.error.max
                            ) {
                                isError = true
                            }
                        }

                        // Check against discard ranges (corrupted data)
                        if (errorCondition?.discard) {
                            if (
                                errorCondition.discard?.min
                                && apiDataValue < errorCondition.discard.min
                            ) {
                                isDiscard = true
                            }
                            if (
                                errorCondition.discard?.max
                                && apiDataValue > errorCondition.discard.max
                            ) {
                                isDiscard = true
                            }
                        }
                    }
                    else if (apiDataType === 'string') {
                        // Check strings against whitelist
                        if (
                            errorCondition?.accept
                            && !errorCondition.accept.includes(apiDataValue)
                        ) {
                            isDiscard = true
                        }
                    }

                    isError ||= isErrorApi

                    if (isDiscard) {
                        // Check for discards
                        logMessage(
                            `Discarded ${id} (${apiData[id]})`,
                            'warning',
                        )
                        apiData[id] = apiDataType === 'number' ? null : '' // Flag invalid value
                    }

                    if (!isDiscard || isErrorApi) {
                        // Check errors against current system status
                        if (isError && !errors.includes(errorKey)) {
                            // If error, log error and raise flag
                            logMessage(
                                `${errorKey} ${errorCondition.error_message}`,
                                'error',
                            )
                            errors.push(errorKey)
                        }
                        else if (!isError && errors.includes(errorKey)) {
                            // If not error, remove from errors flags
                            logMessage(`${errorKey} resolved`)
                            errors.splice(errors.indexOf(errorKey), 1)
                        }
                    }
                }
            }
        })
    })
}

// Mark devices offline and manage their display change
function checkOfflineData(apiData) {
    const offlineSentinel = 'offline' // From gsedaq_metrics.py
    function isOffline(value) { return value === offlineSentinel }

    // Top level check.
    // Recursion will be needed if you want to implement for other packets
    if (apiData == null) {
        console.warning('apiData passed as null to checkOfflineData')
    }

    for (const [key, value] of Object.entries(apiData)) {
        if (value == null) {
            updateMetricOffline(key, true);
        }
        else if (isOffline(value)) {
            updateMetricOffline(key, true)
        }
        else {
            updateMetricOffline(key, false)
        }
    }
}

function processDataForDisplay(apiData, apiId) {
    // Process data from the API for display
    const processedData = { ...apiData } // Shallow copy
    processedData.id = apiId

    if (processedData.state === undefined) {
        processedData.state = {}
    }
    if (processedData.meta === undefined) {
        processedData.meta = {}
    }

    if (apiId === cfg.api.packet_id.network) {
        // Track packet counts per device and attach to processedData.
        // All HTML rendering is handled by updateNetworkDiagnostics2() in frontend_graphs.js.
        Object.keys(apiData).forEach((device) => {
            if (typeof apiData[device] !== 'object' || apiData[device] === null)
                return
            if (!('ping' in apiData[device]))
                return

            processedData[device] = {
                ...apiData[device],
                ping: apiData[device].ping,
                packet_loss: (apiData[device].packet_loss * 100).toFixed(1),
                count: apiData[device].packet_count ?? 0,
            }
        })
    }

    if (apiData?.meta) {
        // Timestamp, synchronization and connection
        if (apiData.meta?.timestampS) {
            updateTimestamp(apiData.meta?.timestampS)
        }

        // Packets
        if ([3, 4, 5].includes(apiId)) {
            if (apiData.meta?.totalPacketCountAv) {
                if (packetsAV1 === 0) {
                    packetsAV1offset = apiData.meta.totalPacketCountAv - 1
                }
                processedData.meta.totalPacketCountAv
                    = apiData.meta.totalPacketCountAv - packetsAV1offset
            }

            processedData.meta.radio = 'av1'
            processedData.meta.av = {
                rssi: apiData.meta.rssi,
                snr: apiData.meta.snr,
                packets: ++packetsAV1,
                lostPackets: processedData.meta.totalPacketCountAv - packetsAV1,
            }
            processedData.state.av = { radio: 1 }
        }
        else if ([55].includes(apiId)) {
            processedData.meta.radio = 'gse'
            processedData.state.gse = { radio: 1 }
        }
    }

    // Acceleration
    // Determine whether to use low or high precision values
    if (apiData.accelLowX !== undefined && apiData.accelHighX !== undefined) {
        processedData.accelX
            = Math.abs(apiData.accelHighX) < 17
                ? apiData.accelLowX
                : apiData.accelHighX
    }
    if (apiData.accelLowY !== undefined && apiData.accelHighY !== undefined) {
        processedData.accelY
            = Math.abs(apiData.accelHighY) < 17
                ? apiData.accelLowY
                : apiData.accelHighY
    }
    if (apiData.accelLowZ !== undefined && apiData.accelHighZ !== undefined) {
        processedData.accelZ
            = Math.abs(apiData.accelHighZ) < 17
                ? apiData.accelLowZ
                : apiData.accelHighZ
    }

    // Altitude
    // Track previous altitudes
    if (apiData.altitude !== undefined) {
        processedData.altitudeFeet = metresToFeet(apiData.altitude)

        altitudeHistory.push(apiData.altitude)
        if (altitudeHistory.length > 5) {
            altitudeHistory.shift()
        }
        if (altitudeHistory.length === 5) {
            // Calculate mean of last 5 altitudes, then determine deviation and threshold
            const altitudeMean
                = altitudeHistory.reduce((acc, val) => acc + val, 0)
                / altitudeHistory.length
            const altitudeThreshold = Math.max(altitudeMean * 0.2, 200) // 20% difference or < 200 whichever is greater
            const altitudeDeviation = Math.abs(apiData.altitude - altitudeMean)

            // Calculate max altitude
            if (altitudeDeviation <= altitudeThreshold) {
                if (
                    altitudeMax === undefined
                    || apiData.altitude > altitudeMax
                ) {
                    altitudeMax = apiData.altitude
                }
            }
            else {
                logMessage(`Discard max altitude (${altitudeMax})`, 'warning')
            }
        }
        if (altitudeMax !== undefined && altitudeMax > 0) {
            processedData.altitudeMax = altitudeMax
            processedData.altitudeMaxFeet = metresToFeet(altitudeMax)
        }

        // Parachute sound should play if we descend below a set altitude
        // The new altitude must be below the threshold, unlike the old one
        const prevAltitude = metresToFeet(altitudeHistory.at(-2))
        const currAltitude = metresToFeet(altitudeHistory.at(-1))
        if ((currAltitude < cfg.audio.parachute_altitude) && (prevAltitude >= cfg.audio.parachute_altitude)) {
            playOtherSound('Parachute')
        }
    }

    // Feet
    if (apiData.velocity !== undefined) {
        processedData.velocityFeet = metresToFeet(apiData.velocity)
    }

    // GPS position
    if (apiData.GPSLatitude !== undefined) {
        processedData.GPSLatitude = gpsToDecimal(apiData.GPSLatitude)
    }
    if (apiData.GPSLongitude !== undefined) {
        processedData.GPSLongitude = gpsToDecimal(apiData.GPSLongitude)
    }

    /* If the rocket is within 50m of the GCS, play a warning sound.
       * Use Pythagorean theorem, scaling up latitude and longitude, both
       * of which are required to be present in the packet.
       *
       * Requires matching the GCS coordinates to "LATITUDE": sinusoid() and/or
       * "LONGITUDE": sinusoid() in backend/device_emulator.py (or vice versa) during
       * testing, or else the rocket will appear to be very far from the GCS
      */
    if (apiData.GPSLatitude !== undefined && apiData.GPSLongitude !== undefined) {
        // Distance to GCS in km (both latitude and longitude)
        const lat_distance = ((gpsToDecimal(apiData.GPSLatitude - cfg.gps.gcs_lat)) * cfg.gps.lat_scale_factor)
        const lon_distance = ((gpsToDecimal(apiData.GPSLongitude - cfg.gps.gcs_lon)) * cfg.gps.lon_scale_factor)
        const final_distance = Math.sqrt(lat_distance ** 2 + lon_distance ** 2)

        // Rocket_Warn sound
        const currSound = soundGetOther(2)

        // 50m in km
        if (final_distance <= cfg.audio.overhead_warn_radius / 1000) {
            // Sometimes the property might be equal to NaN, make sure no error is thrown
            if (!Number.isNaN(currSound.source.duration)) {
                /* Volume rises in logarithmic fashion the longer the rocket stays within
                        * 50m of the GCS (within the 1st iteration), full volume otherwise.
                        */
                currSound.source.volume = currSound.loopCount > 0
                    ? 1
                    : (currSound.source.currentTime / currSound.source.duration) ** 1.5
                console.log(currSound.loopCount)
                playOtherSound('Rocket_Warn')
            }
        }
        else {
            // Stop and reset number of iterations.
            currSound.source.pause()
            currSound.source.currentTime = 0
            currSound.loopCount = 0
        }
    }

    // Gas fill timer
    if ([10].includes(apiId) && apiData != null) {
        const systemActivated = apiData.SYS_ON
        const gasFillSelected = apiData.FILL_SELECTED
        const n20FillActivated = apiData.N2O_ACTIVE

        if (systemActivated && gasFillSelected && n20FillActivated) {
            // Increase gas fill timer
            if (timers.gasTimestamp === 0) {
                timers.gasTimestamp = timestamp.api
            }
            timers.gasFillTimer
                = timers.gasTimestamp === 0
                    ? 0
                    : timestamp.api - timers.gasTimestamp
        }
        else {
            timers.gasTimestamp = 0
            timers.gasFillTimerTotal += timers.gasFillTimer
            timers.gasFillTimer = 0
        }

        if (timers.gasFillTimer !== undefined && timers.gasFillTimer !== 0) {
            processedData.gasBottleTime = `${(timers.gasFillTimerTotal + timers.gasFillTimer).toFixed(2)}s`
        }
    }

    // State flags
    // GPS fix (navigation state)
    if (apiData.navigationStatus !== undefined) {
        if (['NF'].includes(apiData.navigationStatus)) {
            processedData.state.gpsFix = 3 // Red
        }
        else if (['DR', 'TT'].includes(apiData.navigationStatus)) {
            processedData.state.gpsFix = 2 // Yellow
        }
        else if (
            ['D2', 'D3', 'G2', 'G3', 'RK'].includes(apiData.navigationStatus)
        ) {
            processedData.state.gpsFix = 1 // Green
        }
    }

    if (apiData.stateFlags !== undefined) {
        // Dual board connectivity
        if (apiData.stateFlags.dualBoardConnectivityStateFlag !== undefined) {
            processedData.state.dualBoard = apiData.stateFlags
                .dualBoardConnectivityStateFlag
                ? 1
                : 5 // green / error
        }
        // Recovery checks
        if (apiData.stateFlags.recoveryChecksCompleteAndFlightReady) {
            processedData.state.recoveryCheck = apiData.stateFlags
                .recoveryChecksCompleteAndFlightReady
                ? 1
                : 0
        }
        // Payload
        if (apiData.stateFlags.payloadConnectionFlag) {
            processedData.state.payload = apiData.stateFlags
                .payloadConnectionFlag
                ? 1
                : 0
        }
        // Camera controller
        if (apiData.stateFlags.cameraControllerConnectionFlag) {
            processedData.state.camera = apiData.stateFlags
                .cameraControllerConnectionFlag
                ? 1
                : 0
        }
    }

    // Return processed data
    return processedData
}

export { API_OnMessage };
