/**
 * GCS Display code
 *
 * Responsible for updating the webpage based on the API
 */

import { Config as cfg } from '/js/frontend_config.js';
import { graphRequestRender } from '/js/frontend_graphs.js'
import { logMessage } from '/js/frontend_utils.js'

const indicatorStates = ['off', 'green', 'yellow', 'red', 'timeout', 'error']
const metricOffline = {} // key -> boolean
const graph_render_rate = 20 // FPS for rendering graphs

let then, fpsInterval

const timestamp = {
    localLoad: Date.now(), // Timestamp upon page load (refreshed with API to keep time-alignment)
    local: 0, // Local timekeeping (for page to keep updating even if API stops sending signals)
    api: 0, // Timestamp sent by the API
    apiConnect: undefined, // First API timestamp sent upon connection with API
    drift: undefined, // Time desync calculation
}
const timers = {
    gasFillTimer: 0,
    gasFillTimerTotal: 0,
    gasTimestamp: 0,
    launchTimestamp: 0,
}


function updateTimestamp(new_timestamp) {
    if (timestamp.api) {
        timestamp.api = Math.max(timestamp.api, new_timestamp)
    }
    else {
        timestamp.api = new_timestamp
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

function updateMetricOffline(key, is_offline) {
    metricOffline[key] = is_offline;
}

function getMetricOffline(key) {
    return metricOffline[key];
}

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

// Generate the loss sounds (1st 2 have a quicker version - see cfg.audio.timeouts)
// Note: Horizon doesn't have 2 Australis boards (which is Dual_Board_Loss)
const filenames_losses = ['GSE_Loss', 'AV_Loss', 'GPS_Fix_Loss']
const soundsList_losses = filenames_losses.map((src) => {
    // Create the audio object that will return upon ending
    const audioObject = new Audio(`sounds/${src}.mp3`)

    // Mute sound by default
    audioObject.muted = true

    // Self-return after playing
    audioObject.addEventListener('ended', () => {
        audioObject.pause()
        audioObject.currentTime = 0
    })

    /* Active means whether the sound should be playing
       * but the mute status is stored inside source
      */
    return { source: audioObject, active: false }
})

// Other non-alarm sounds (uncomment the below when done).
/* TODO: Add "Rocket_Hit" to this list when the application can detect the rocket imminently
 * about to hit someone on the head, using playOtherSound(). At this stage, though, same as Rocket_Warn
 *
 * To put this sound into Combined_Sounds, add it to the end of the corresponding track/
 * segment in the attached Audacity project (static/sounds), continuing the pattern
 * of 0.5 seconds between each sound.
*/
const filenames_other = ['Apogee', 'Parachute', 'Rocket_Warn']
const soundsList_other = filenames_other.map((src) => {
    // Create the audio object that will return upon ending
    const audioObject = new Audio(`sounds/${src}.mp3`)

    // Mute sound by default
    audioObject.muted = true

    /* This time there is no queue so no active, but keep
       * track of how many times a sound has been looping for
       * (if required). Can't just put this in the return
       * statement, otherwise loopCount won't be tied to the object.
      */
    const returnValue = { source: audioObject, loopCount: 0 }

    // Loop in case required, else self-return after playing
    audioObject.addEventListener('ended', () => {
        if (src === 'Rocket_Warn') {
            audioObject.currentTime = 0
            audioObject.play()
            returnValue.loopCount++
        }
        else {
            audioObject.pause()
            audioObject.currentTime = 0
        }
    })

    return returnValue;
})

function soundGetOther(source) {
    return soundsList_other[source];
}


// FUNCTIONS FOR UPDATING DISPLAY ITEMS
// Register elements to listen for API updates
const displayRegistry = {}
window.addEventListener('load', () => {
    document.querySelectorAll('[data-key]').forEach((elem) => {
        const key = elem.getAttribute('data-key')
        const prec = elem.getAttribute('data-precision')
        const type = elem.getAttribute('data-type')

        // Defaults
        const rego = { e: elem, t: 'value' }
        if (prec != null) {
            rego.p = prec
        }
        if (type != null) {
            rego.t = type
        }

        /* Play sound if any state indicator is already problematic
             * (which at least in --experimental mode) will be the case).
             * Only that no specific element is in mind at this stage.
            */
        checkStateIndicator()

        // Register element
        if (key in displayRegistry) {
            displayRegistry[key].push(rego)
        }
        else {
            displayRegistry[key] = [rego]
        }
    })

    console.log(displayRegistry)
})

// Hotkeys for the navbar
window.addEventListener('keydown', (event) => {
    const styles = 'h-full w-full flex flex-row items-center justify-center gap-2 whitespace-nowrap border-2 border-orange-900 px-2'
    const buttons = document.querySelectorAll(`a.${styles.replaceAll(' ', '.')}`)

    // Only NaN would fail the test
    if (!Number.isNaN(Number.parseInt(event.key, 10))) {
        // Get element by index from found elements list
        const index = Number.parseInt(event.key, 10) - 1

        if ((index >= 0) && (index < buttons.length)) {
            // Click the element (ignoring default browser behaviour)
            buttons[index].click()
            event.preventDefault()
        }
    }
})

// ── Right panel: flip a status box green/red ─────────────────────
function diagSetStatusBox(id, pingValue) {
    const el = document.getElementById(id);
    if (!el)
        return;

    // No data / offline
    if (pingValue == null || pingValue < 0) {
        el.textContent = "DOWN";
        el.style.backgroundColor = "var(--color-red-500,#ef4444)";
        el.style.borderColor = "var(--color-red-800,#991b1b)";
        el.style.color = "white";
        return;
    }

    // Green
    if (pingValue <= 100) {
        el.textContent = "GOOD";
        el.style.backgroundColor = "var(--color-green-400,#4ade80)";
        el.style.borderColor = "var(--color-green-700,#15803d)";
        el.style.color = "black";
        return;
    }

    // Yellow
    if (pingValue <= 200) {
        el.textContent = "WARN";
        el.style.backgroundColor = "var(--color-yellow-400,#facc15)";
        el.style.borderColor = "var(--color-yellow-700,#a16207)";
        el.style.color = "black";
        return;
    }

    // Red
    el.textContent = "BAD";
    el.style.backgroundColor = "var(--color-red-500,#ef4444)";
    el.style.borderColor = "var(--color-red-800,#991b1b)";
    el.style.color = "white";
}

function diagSetSummaryOnlineBox(id, online) {
    const el = document.getElementById(id);
    if (!el)
        return;

    el.textContent = online ? "GOOD" : "DOWN";
    el.style.backgroundColor = online ? "#4ade80" : "#ef4444";
    el.style.borderColor = online ? "#15803d" : "#991b1b";
    el.style.color = online ? "black" : "white";
}

function diagSetAvIndicator(online) {
    const el = document.getElementById("diag-av-indicator");
    if (!el)
        return;

    el.style.background = online ? "#4ade80" : "#ef4444";
    el.style.boxShadow = online
        ? "0 0 6px #4ade80"
        : "0 0 6px #ef4444";
}

// Check if all sounds (alarms and otherwise) are unmuted
function allUnmuted() {
    return soundsList_losses.every(item => !item.source.muted)
        && soundsList_other.every(item => !item.source.muted)
}

// Call at the start and whenever a state updates
function checkStateIndicator(elem = null) {
    // Select rocket for below
    let currRocket = ''
    if (window.location.href.includes('rocket=legacy')) {
        currRocket = 'Legacy3'
    }
    else if (window.location.href.includes('rocket=atlas')) {
        currRocket = 'Atlas'
    }
    else if (window.location.href.includes('rocket=horizon')) {
        currRocket = 'Horizon'
    }

    function stateToSound(e1) {
        let sound = ''
        const indicator = e1.attributes[0].textContent

        /* See horizon_settings_audio.html for sound sources. Also set the corresponding
             * summary light for the 1st 2 states if the function exists.
            */
        if (indicator.includes('av.radio')) {
            sound = 'AV_Loss'

            const avOnline = e1.classList.value.includes('green')
            diagSetSummaryOnlineBox('diag-summary-av', avOnline)
            diagSetAvIndicator(avOnline);
        }
        else if (indicator.includes('gse.radio')) {
            sound = 'GSE_Loss'

            const alive = ['vulcan-esp32', 'wifi-bridge-gse'].every((device) => {
                const ping = document.querySelector(`[data-key="${device}.ping"]`)
                return ping && ping.getAttribute('value') >= 0
            })

            diagSetStatusBox('diag-summary-gse', alive && e1.classList.value.includes('green'))

            // // Track summary status, unless alive has already been set false
            // let alive = true;
            // if ((["Vulcan ESP32", "WiFi Bridge @ GSE"].includes(deviceName)) && alive) {
            //     // GSE: Check if the GSE radio indicator and the above pings are > 0
            //     const gseIndicator = document.querySelector('[data-key="state.gse.radio"][data-type="state"]');
            //     if (gseIndicator) {
            //         alive = gseIndicator.classList.contains("green") && (ping >= 0);
            //         diagSetStatusBox("diag-summary-gse", alive);
            //     }
            // }
        }
        else if (indicator.includes('gpsFix')) {
            sound = 'GPS_Fix_Loss'
        }
        // Currently moved out of scope
        // else if (indicator.includes("dualBoard")) {
        //     sound = "Dual_Board_Loss";
        // }

        // Should only execute with one of the above values
        if (sound !== '') {
            /* Can be changed, but at this stage only green is a good state,
                  * where the sound resets (otherwise continues playing). Also,
                  * elem.classList.value is the styling itself (use this so that
                  * in case the interested state/s exist elsewhere in the string)
                  */
            updateSound(sound, !e1.classList.value.includes('green'), false)

            // Check for timeouts (won't execute on a non-radio state)
            cfg.audio.timeouts[currRocket].filter(t1 => (indicator.includes(t1.name))).forEach((t1) => {
                const currElems = document.querySelectorAll(`[data-key="${`state.${t1.name}.radio`}"]`)

                currElems.forEach((c1) => {
                    // Use functions for recalculating the expressions
                    const timeoutState = () => c1.classList.value.includes(indicatorStates[t1.state])
                    const greenState = () => !c1.classList.value.includes('green')
                    const currSound = `${t1.name.toUpperCase()}_Loss`

                    if (timeoutState()) {
                        // At a minimum, the regular sound should be playing regardless
                        updateSound(currSound, true, false)

                        setTimeout(() => {
                            /* If the timeout is still not resolved, set the sound to
                                          * the quicker version.
                                          */
                            if (timeoutState()) {
                                updateSound(currSound, true, true)
                            }
                            else {
                                // Set the alarm back to its normal state (if the timeout went away on time)
                                updateSound(currSound, !greenState, false)
                            }
                        }, t1.duration)
                    }
                    else {
                        // Same code as above, except it doesn't wait (when the state was never 'unfavourable')
                        updateSound(currSound, !greenState, false)
                    }
                })
            })
        }
    }

    // Activate a single alarm
    if (elem !== null) {
        stateToSound(elem)
    }
    else {
        // Check all states at the start
        const validStates = ['av.radio', 'gse.radio', 'gpsFix', 'dualBoard']
        validStates.forEach((key) => {
            const currElems = document.querySelectorAll(`[data-key="state.${key}"]`)

            // Activate any required alarms
            currElems.forEach((c1) => {
                stateToSound(c1)
            })
        })
    }
}

// Check if the main Horizon page is selected
function isHorizonMain() {
    /* Before clicking on any header page, the former will be
       * true, afterwards, it will be the latter
      */
    return window.location.href.endsWith('rocket=horizon')
        || window.location.href.endsWith('rocket=horizon#page-main')
}

// Block calls to enforce silence
let silence = false

/* Plays alarm sounds in a queue, whose order matches the priority
 * (in descending order).
*/
function playAlarmSounds() {
    // Return if 1 second not up, yet
    if (silence) { return }
    silence = true

    for (let i = 0; i < soundsList_losses.length; ++i) {
        // Play the active sounds in succession (only if not already playing)
        if ((soundsList_losses[i].active) && (soundsList_losses[i].source.paused)) {
            soundsList_losses[i].source.play()
        }
    }

    // After 1 second, allow function calls
    setTimeout(() => {
        silence = false
    }, 1000)
}

// Plays a non-alarm sound
function playOtherSound(sound) {
    // Look for the sound
    const soundNumber = soundsList_other.findIndex(
        file => file.source.src.includes(sound),
    )

    // Not found or already playing
    if ((soundNumber === -1) || (!soundsList_other[soundNumber].source.paused)) {
        return
    }

    // Play if on the Horizon main page
    if (isHorizonMain()) {
        soundsList_other[soundNumber].source.play()
    }
}

function toggleMute() {
    // Toggle mute first, then update UI

    // Alarm sounds
    for (let i = 0; i < soundsList_losses.length; ++i) {
        soundsList_losses[i].source.muted = !soundsList_losses[i].source.muted
    }

    // Other sounds (no source as these aren't in a queue)
    for (let i = 0; i < soundsList_other.length; ++i) {
        soundsList_other[i].source.muted = !soundsList_other[i].source.muted
    }

    /* Icon represents current state.
       * In addition, the icons are free to use per https://creativecommons.org/licenses/by/4.0/,
       * modified by changing the colour to a Horizon-themed gradient
      */
    if (allUnmuted()) {
        document.getElementById('toggleIcon').src = 'img/icons/sound-unmuted.svg'
        document.getElementById('toggleIcon').alt = 'Sound unmuted'
    }
    else {
        document.getElementById('toggleIcon').src = 'img/icons/sound-muted.svg'
        document.getElementById('toggleIcon').alt = 'Sound muted'
    }
}
window.toggleMute = toggleMute;

/* Update the given sound as to if it will play in the sound
 * queue. If long = true, the alarm will change to its extended version.
*/
function updateSound(sound, newValue, quicker) {
    const soundNumber = soundsList_losses.findIndex(
        file => file.source.src.includes(sound),
    )

    // If newValue is true, the sound should play when called
    if (soundNumber >= 0) {
        soundsList_losses[soundNumber].active = newValue
    }

    /* Custom functions just for inside this one. Note that the suffix
       * is before the file extension, not after
      */
    function addQuicker() {
        // Filepath must not already contain the differentiating suffix
        if (!soundsList_losses[soundNumber].source.src.includes('_Quicker')) {
            soundsList_losses[soundNumber].source.src = `${soundsList_losses[soundNumber].source.src.slice(0, -4)}_Quicker.mp3`
        }
    }
    function removeQuicker() {
        // Remove the suffix
        soundsList_losses[soundNumber].source.src.replaceAll('_Quicker', '')
    }

    quicker ? addQuicker() : removeQuicker()
    try {
        /* Don't play any sound if none are active (else that would delay any
             * future ones by an extra second). Likewise, don't do so unless the main
             * Horizon page is selected
            */
        if ((soundsList_losses.some(file => file.active)) && isHorizonMain()) {
            playAlarmSounds()
        }
    }
    catch {
        /* Perform opposite operation, leading into an infinite loop
             * if the original sound did not exist neither with, nor without
             * "_Quicker"), which should not be the case here at this time
            */
        quicker ? removeQuicker() : addQuicker()
    }
}


function displaySetValue(item, value, precision = 2, error = false) {
    // Updates a floating point value for a display item
    if (value !== undefined && !Number.isNaN(value)) {
        if (cfg.logging.verbose) {
            console.debug(
                `new value %c${item}%c ${Number.parseFloat(value).toFixed(precision)}`,
                'color:orange',
                'color:white',
            )
        }

        // Use classes instead of IDs since IDs must be unique
        // and some items occur on multiple pages
        let elements = [item]
        if (typeof item == 'string') {
            elements = document.querySelectorAll(`.${item}`)
        }
        if (elements && elements.length > 0) {
            elements.forEach((elem) => {
                // Update value
                elem.value = Number.parseFloat(value).toFixed(precision)

                // Update error state
                if (error) {
                    elem.classList.add('error')
                }
                else {
                    elem.classList.remove('error')
                }
            })
        }
    }
}

function displaySetString(item, string) {
    // Updates the string in a display item
    if (string !== undefined) {
        if (cfg.logging.verbose) {
            console.debug(
                `new string %c${item}%c ${string}`,
                'color:orange',
                'color:white',
            )
        }

        // Update all instances of item
        let elements = [item]
        if (typeof item == 'string') {
            elements = document.querySelectorAll(`.${item}`)
        }
        if (elements && elements.length > 0) {
            elements.forEach((elem) => {
                // Update string
                elem.value = string
            })
        }
    }
}

function displaySetState(item, value) {
    // Updates the state of an indicator
    if (cfg.logging.verbose) {
        console.debug(
            `new state %c${item}%c ${value}`,
            'color:orange',
            'color:white',
        )
    }

    // Update all instances of item
    let elements = [item]
    if (typeof item == 'string') {
        elements = document.querySelectorAll(`.${item}`)
    }

    if (elements && elements.length > 0) {
        elements.forEach((elem) => {
            elem.classList.remove(...indicatorStates)
            // Convert true/false boolean values to on/error
            if (typeof value == 'boolean') {
                value = value ? 1 : 3
            }

            // Get indicator state from value (only then change the sound)
            if (value >= 0 && value < indicatorStates.length) {
                elem.classList.add(indicatorStates[value])
            }

            // Check if sound needs to be played
            checkStateIndicator(elem)
        })
    }
}

/*
    The following functions are still called manually and should be integrated
    into the sendDataToRegistry() functionality
*/

function displaySetError(item, error) {
    // Adds/removed error class from element
    const elements = document.querySelectorAll(`.${item}`)
    if (elements && elements.length > 0) {
        elements.forEach((elem) => {
            if (error) {
                elem.classList.add('error')
            }
            else {
                elem.classList.remove('error')
            }
        })
    }
}

function displaySetOffline(elem) {
    const label = elem.closest('label')
    elem.value = 'N/A' // Has to be small
    elem.classList.add('offline')
    elem.classList.remove('error')
    if (label)
        label.classList.add('sensor-offline')
}

function displaySetOnline(elem) {
    const label = elem.closest('label')
    elem.classList.remove('offline')
    if (label)
        label.classList.remove('sensor-offline')
}

function displaySetActiveFlightState(item) {
    // Updates active flight state to a specific html element
    const elements = document.querySelectorAll(`.${item}`)

    // Remove error state
    const fsElements = document.querySelectorAll(`.indicator-flightstate`)
    if (fsElements && fsElements.length > 0) {
        fsElements.forEach((elem) => {
            elem.classList.remove('error')
        })
    }

    if (elements && elements.length > 0) {
        // Make sure we're actually updating this
        if (elements[0].classList.contains('active'))
            return

        // The active element is different, update active item
        const active = document.querySelectorAll(`.active`)
        if (active && active.length > 0) {
            active.forEach((elem) => {
                elem.classList.remove('active')
            })
        }

        // Update active item
        elements.forEach((elem) => {
            elem.classList.add('active')
        })
    }

    // Launch timer
    if (item === 'fs-state-preflight') {
        timers.launchTimestamp = 0
    }
    else {
        if (
            timers.launchTimestamp === undefined
            || timers.launchTimestamp === 0
        ) {
            timers.launchTimestamp = timestamp.api
        }
    }
}

function displaySetErrorFlightState() {
    // Add error state
    const elements = document.querySelectorAll(`.indicator-flightstate`)
    if (elements && elements.length > 0) {
        elements.forEach((elem) => {
            elem.classList.remove('active')
            elem.classList.add('error')
        })
    }
}

// FUNCTIONS FOR UPDATING MODULES
function displayUpdateFlightState(data) {
    /// MODULE FLIGHTSTATE
    if (data?.flightState) {
        displaySetError('fs-flightstate', false)

        let stateName = ''
        if (
            data.flightState === 0
            || data.flightState === 'PRE_FLIGHT_NO_FLIGHT_READY'
        ) {
            // Preflight (not ready)
            stateName = 'Pre-flight'
            displaySetActiveFlightState('fs-state-preflight')
        }
        else if (data.flightState === 1 || data.flightState === 'LAUNCH') {
            // Launch
            stateName = 'Launch'
            displaySetActiveFlightState('fs-state-launch')
        }
        else if (data.flightState === 2 || data.flightState === 'COAST') {
            // Coast
            stateName = 'Coast'
            displaySetActiveFlightState('fs-state-coast')
        }
        else if (data.flightState === 3 || data.flightState === 'APOGEE') {
            // Apogee
            stateName = 'Apogee'
            displaySetActiveFlightState('fs-state-apogee')

            // Play the apogee sound, whose file includes a parachute sound 2 seconds afterwards
            playOtherSound('Apogee')
        }
        else if (data.flightState === 4 || data.flightState === 'DESCENT') {
            // Descent
            stateName = 'Descent'
            displaySetActiveFlightState('fs-state-descent')
        }
        else if (data.flightState === 5 || data.flightState === 'LANDED') {
            // Landed successfully
            stateName = 'Landed'
            displaySetActiveFlightState('fs-state-landed')
        }
        else if (
            data.flightState === 6
            || data.flightState === 7
            || data.flightState === 'OH_NO'
        ) {
            // Oh no oh no what the oh no :(
            stateName = 'OH NO!'
            displaySetErrorFlightState()
            displaySetError('fs-flightstate', true)
        }

        displaySetString('fs-flightstate', stateName)
    }
}

function displaySloggerLogs(apiData) {
    apiData.forEach((log) => {
        logMessage(log.message, log.level.toLowerCase(), log.timestamp)
    })
}

const skippedKeys = []
function sendDataToRegistry(apiData) {
    // Don't receive data until page has loaded
    if (Object.keys(displayRegistry).length === 0) {
        return
    }

    // Flatten API data so that keys are in format a.b
    const flat = {}
    function flatten(prefix, obj) {
        if (prefix !== '') {
            prefix = `${prefix}.`
        }
        if (obj == null) {
            return
        }
        Object.entries(obj).forEach(([key, value]) => {
            if (typeof value == 'object') {
                flatten(prefix + key, value)
            }
            else {
                flat[prefix + key] = value
            }
        })
    }
    flatten('', apiData)

    // TODO: Store last datapoint for every key
    //       and only update elements if it changes

    // Loop through flattened keys and update registered element
    Object.entries(flat).forEach(([key, value]) => {
        if (key in displayRegistry) {
            for (const reg of displayRegistry[key]) {
                if (getMetricOffline(key)) {
                    displaySetOffline(reg.e)
                    continue
                }
                displaySetOnline(reg.e)
                const elem = reg.e
                const prec = reg.p
                const type = reg.t
                switch (type) {
                    case 'value':
                        displaySetValue(elem, value, prec)
                        break
                    case 'string':
                        displaySetString(elem, value)
                        break
                    case 'state':
                        displaySetState(elem, value)
                        break
                }
            }
        }
        else if (!skippedKeys.includes(key)) {
            // Add skipped keys to a list, so we only warn about them once
            console.warn(`${key} not found in displayRegistry, skipping`)
            skippedKeys.push(key)
        }
    })
}

export { diagSetAvIndicator, diagSetSummaryOnlineBox, displaySetActiveFlightState, displaySetError, displaySetErrorFlightState, displaySetOffline, displaySetOnline, displaySetState, displaySetString, displaySetValue, displaySloggerLogs, displayUpdateFlightState, getMetricOffline, playOtherSound, sendDataToRegistry, soundGetOther, timers, timestamp, toggleMute, updateMetricOffline, updateTimestamp };
