/**
 * GCS API
 *
 * Receives data from the API and loads it into memory to be accessed by other javascript modules.
 *
 * Functions and constants should be prefixed with "api_"
 */

/* global hmiUpdate, rocketUpdate, updatePendantState */

import { processPacket } from '/js/GCS_DiagnosticsNavAlert.js';
import { displaySloggerLogs, displayUpdateFlightState, playOtherSound, sendDataToRegistry, soundGetOther, updateMetricOffline } from '/js/gcs_display.js';
import { graphRequestRender, graphUpdateAuxData, graphUpdateAvionics, graphUpdateDiagnostics, graphUpdatePosition } from '/js/GCS_Graphs.js';
import { gpsToDecimal, logMessage, metresToFeet, timers, timestamp } from '/js/gcs_utils.js';

// const ws_url = `ws://${_ws["host"]}:${_ws["port"]}`

const graph_render_rate = 20 // FPS for rendering graphs


// WebSocket API connection
let then, fpsInterval

// Logging
const errors = []

// Global display values
let altitudeMax
const altitudeHistory = []
let packetsAV1 = 0
let packetsAV1offset = 0

// Animation/timing code
function startAnimating() {
    fpsInterval = 1000 / graph_render_rate
    then = window.performance.now()
    animate()
}
function animate(newtime) {
    // Calculate time since last loop
    const now = newtime
    const elapsed = now - then

    // Rerender if enough time has elapsed
    if (elapsed > fpsInterval) {
        then = now - (elapsed % fpsInterval)

        // Rerender graphs
        graphRequestRender()

        // Increment time (so if we stop getting packets, time moves forward)
        timestamp.local = (Date.now() - timestamp.localLoad) / 1000
        updateTime()
    }

    // Request next animation frame
    requestAnimationFrame(animate)
}
startAnimating()

function updateTime() {
    /// SYSTEM TIME
    // Rocket launch timer
    if (timestamp.api !== 0 && timers?.launchTimestamp !== undefined) {
        let launchTime = 0
        if (timers.launchTimestamp !== 0) {
            launchTime = timestamp.api - timers.launchTimestamp
        }
        sendDataToRegistry({ launchTime: `T+${launchTime.toFixed(1)}` })
    }

    // Local time
    if (timestamp.local !== undefined && timestamp.local !== 0) {
        sendDataToRegistry({
            localTime: `${(timestamp.local + timestamp.apiConnect - timestamp.drift).toFixed(1)} s`,
        })
    }
}

// Handle incoming messages through the API
function API_OnMessage(event_data) {
    let apiLatest, apiData
    try {
        // Handle incoming data
        apiLatest = JSON.parse(event_data)

        // When detected Slogger Packets just skip the whole validation part and just upload packets avoids feeding in old data just to get template to work
        if (apiLatest.id === 40) {
            /// // ----- sLogger PACKETS ----- /////
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
        if (apiData.id === 3 || apiData.id === 4) {
            /// // ----- AVIONICS PACKETS ----- /////
            // Display values
            displayUpdateFlightState(apiData)

            // Graphs
            graphUpdateAvionics(apiData)
            graphUpdatePosition(apiData)

            // Rocket visualisation
            if (apiData.id === 4) {
                if (typeof rocketUpdate === 'function') {
                    rocketUpdate(apiData)
                }
            }
        }
        else if (apiData.id === 10) {
            /// // ----- PENDANT ----- /////
            if (typeof updatePendantState === 'function') {
                updatePendantState(apiData)
            }
        }
        else if (apiData.id === 50) {
            /// // ----- NETWORK DIAGNOSTICS ----- /////
            processPacket(apiData)
            graphUpdateDiagnostics(apiData)
        }
        else if (apiData.id === 55) {
            /// // ----- GSE PACKETS ----- /////
            // Graphs
            graphUpdateAuxData(apiData)
        }
    }
    catch (error) {
        console.error('Data processing error:', error)
    }
}

// Check data for error conditions
function checkErrorConditions(apiData) {
    const errorConditions = [
        {
            IDs: ['weight_rocket'], // Rocket weight
            discard: {
                min: -1,
                max: 128,
            },
        },
        {
            IDs: [
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
            IDs: ['altitude'],
            discard: {
                min: -128,
                max: 8192,
            },
        },
        {
            IDs: ['velocity'],
            discard: {
                min: -128,
                max: 1024,
            },
        },
        {
            IDs: ['GPSLatitude', 'GPSLongitude'],
            discard: {
                min: -18000,
                max: 18000,
            },
        },
        {
            IDs: ['gyroX', 'gyroY', 'gyroZ'],
            discard: {
                min: -295,
                max: 295,
            },
        },
        {
            IDs: ['temp_vent'],
            discard: {
                min: -200,
                max: 80,
            },
        },
        {
            IDs: ['mach_speed'],
            discard: {
                min: -1,
                max: 16,
            },
        },
        {
            IDs: ['qw', 'qx', 'qy', 'qz'],
            discard: {
                min: -1,
                max: 1,
            },
        },
        {
            IDs: ['navigationStatus'],
            accept: ['NF', 'DR', 'G2', 'G3', 'D2', 'D3', 'RK', 'TT'],
        },
        {
            IDs: ['flightState'],
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
            IDs: ['gasBottleWeight1', 'gasBottleWeight2'],
            error: {
                min: 15.1,
                max: 19,
            },
            errorMessage: 'out of range',
            discard: {
                min: -1,
                max: 128,
            },
        },
        {
            IDs: [
                'temp_tank_top',
                'temp_tank_middle',
                'temp_tank_bottom',
            ],
            error: {
                max: 30,
            },
            errorMessage: ' warming',
            discard: {
                min: -128,
                max: 128,
            },
        },
        {
            IDs: [
                'temp_pipe_n2o_gse',
            ],
            error: {
                max: 40,
            },
            errorMessage: ' warming',
            discard: {
                min: -128,
                max: 128,
            },
        },
        {
            IDs: [
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
            IDs: [
                'pressure_n2o_bottle',
                'pressure_n2o_tank',
                'pressure_o2_tank',
            ],
            error: {
                max: 64.5,
            },
            errorMessage: 'flag raised',
            discard: {
                min: -1,
                max: 128,
            },
        },
    ]

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
    errorConditions.forEach((errorCondition) => {
        // Error conditions may apply equivalently to multiple data IDs
        errorCondition.IDs.forEach((id) => {
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
                                `${errorKey} ${errorCondition.errorMessage}`,
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
    /***
    This was made by Michael PP1 Hive 2026 team. I had to make changes to his code
    for customizing and seperating diagnostic page variables while it follows
    the same logic of Michael. I just sepearted the code into pieces. 
    - Mohammad
     */
    // if (apiId === 50) {
    //     // Get the table (return early if not loaded)
    //     let packetsTable = document.getElementById("packets");
    //     if (packetsTable === null) {
    //         return processedData;
    //     }

    //     // Update data if present, otherwise add it
    //     Object.entries(apiData).forEach(([device, deviceData]) => {
    //         let currRow = packetsTable.querySelector(`tr td div[data-key='${device}']`);
    //         if (currRow === null) {
    //             // Append 2 rows
    //             let topRow = packetsTable.insertRow(-1);
    //             let bottomRow = packetsTable.insertRow(-1);

    //             topRow.innerHTML = `
    //             <tr>
    //                 <td class="w-full flex gap-4 justify-start items-center">
    //                     <div
    //                         data-key="${device}"
    //                         data-type="state"
    //                         class="indicator-state mx-0 green"
    //                     ></div>
    //                     <span class="font-bold text-hive">${device}</span>
    //                 </td>
    //             </tr>
    //             `;

    //             // Set state to red if no pings coming through
    //             if ((deviceData.ping == null) || (deviceData.ping < 0)) {
    //                 topRow.querySelector(".indicator-state")?.classList.replace("green", "red");
    //             }
                
    //             bottomRow.innerHTML = `
    //             <tr>
    //                 <td style="border-bottom: 30px solid transparent;">
    //                     <label>
    //                         Packet Loss:<input
    //                             data-key="${device}.packet_loss"
    //                             data-precision="3"
    //                             readonly
    //                             autocomplete="off"
    //                             class="text-right"
    //                             size="4"
    //                             value='${deviceData.packet_loss != null ? deviceData.packet_loss*100 : 0}'
    //                         />%
    //                     </label>
    //                 </td>
    //                 <td style="border-bottom: 30px solid transparent;">
    //                     <label>
    //                         Ping:<input
    //                             data-key="${device}.ping"
    //                             data-precision="0"
    //                             readonly
    //                             autocomplete="off"
    //                             size="4"
    //                             value='${deviceData.ping != null ? deviceData.ping : -1}'
    //                         />
    //                     </label>
    //                 </td>
    //             </tr>
    //             `
    //             // Not required at this stage
    //             /* <td style="border-bottom: 30px solid transparent;">
    //                     <label>
    //                         Packets:<input
    //                             data-key=${device}.packet_count
    //                             data-precision="0"
    //                             readonly
    //                             autocomplete="off"
    //                             class="text-right"
    //                             size="11"
    //                             value = 0
    //                         />
    //                     </label>
    //                 </td>
    //             */
    //         }
    //         else {
    //             // Get the top row
    //             const index = currRow.closest("tr").rowIndex;
                
    //             // Update the state
    //             let topRow = packetsTable.rows[index].querySelector('td div');
    //             topRow.classList.value = `indicator-state mx-0 ${
    //                 ((deviceData.ping != null) && (deviceData.ping >= 0)) ? 'green' : 'red'
    //             }`;

    //             // Update the packet loss then ping
    //             let bottomRow = packetsTable.rows[index + 1].querySelectorAll('td label input');
    //             bottomRow[0].setAttribute('value', (deviceData.packet_loss != null) ? deviceData.packet_loss*100 : 0);
    //             bottomRow[1].setAttribute('value', (deviceData.ping != null) ? deviceData.ping : -1);
    //         }

    //         // The below may not be required
    //         // // Regardless, track packet count
    //         // let index = networkPackets.findIndex(item => item.name === device);
    //         // if (index >= 0) {
    //         //     // If the device in question exists, update count and offset
    //         //     networkPackets[index].count++;

    //         //     // Keep offset if no value was passed in (such as at the start)
    //         //     if (typeof device.packet_loss !== 'undefined') {
    //         //         networkPackets[index].offset = packet_loss;
    //         //     }
    //         // }
    //         // else {
    //         //     // Create a new record and update index
    //         //     networkPackets.push({name: device, count: 1, offset: 0});
                
    //         //     // index was -1, now need the last element
    //         //     index += networkPackets.length;
    //         // }

    //         // // Calculate packet count as the total number of packets minus the % loss
    //         // const actualPacketCount = Math.floor(networkPackets[index].count * ((100 - networkPackets[index].offset) / 100));
    //         // let inputValue = packetsTable.querySelector(`input[data-key='${device}.packet_count']`);
            
    //         // // Make sure the element exists
    //         // if (inputValue != null) {
    //         //     inputValue.value = actualPacketCount;
    //         // }
    //     });
    // }

    if (apiId === 50) {
        // Track packet counts per device and attach to processedData.
        // All HTML rendering is handled by graphUpdateDiagnostics() in GCS_Graphs.js.
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
            if (timestamp.api) {
                timestamp.api = Math.max(timestamp.api, apiData.meta.timestampS)
            }
            else {
                timestamp.api = apiData.meta.timestampS
            }

            if (timestamp.apiConnect === undefined) {
                timestamp.apiConnect = timestamp.api
                timestamp.localLoad = Date.now()
            }
            else {
                // Code to synchronise local time with GSE time if it gets too far behind
                timestamp.drift
                    = timestamp.local - (timestamp.api - timestamp.apiConnect)

                // Time drift
                // timestamp.drift > 0 means LOCAL is ahead of GSE
                // timestamp.drift < 0 means GSE is ahead of LOCAL
                // Ideally there's no time drift at all, but if there is it's used to update the time
                // console.log(timestamp.drift);
            }
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
        const PARACHUTE_ALTITUDE = 1200 // Ideally this would be in a place of unified truth

        // The new altitude must be below the threshold, unlike the old one
        const prevAltitude = metresToFeet(altitudeHistory.at(-2))
        const currAltitude = metresToFeet(altitudeHistory.at(-1))
        if ((currAltitude < PARACHUTE_ALTITUDE) && (prevAltitude >= PARACHUTE_ALTITUDE)) {
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
        // Scaling constants
        const lat_kilometers = 110.87
        const long_kilometers = 95.48

        // (Decimal) Coordinates of the GCS
        const lat_GCS = 31.039581
        const long_GCS = 103.526623

        /* Distance to GCS in km (both latitude and longitude). Use the decimal
             * version of the coordinates as this is what the GCS coordinates are given
             * as.
            */
        const lat_distance = ((gpsToDecimal(apiData.GPSLatitude - lat_GCS)) * lat_kilometers) ** 2
        const long_distance = ((gpsToDecimal(apiData.GPSLongitude - long_GCS)) * long_kilometers) ** 2
        const final_distance = Math.sqrt(lat_distance + long_distance)

        // Rocket_Warn sound
        const currSound = soundGetOther(2)

        // 50m in km
        if (final_distance <= 50 / 1000) {
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