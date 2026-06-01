/**
 * GCS Data Visualiser
 *
 * Uses d3.js to plot data from the API in beautiful graphs
 *
 * Functions and constants should be prefixed with "graph_"
 */

/* global d3 */

import { metresToFeet, timestamp } from '/js/GCS_API.js'

const MAX_TIME = 20; // Seconds of graph shown, TODO: load config
const GRAPH_GAP_SIZE = 4; // Max time between data points where line is drawn
const GRAPH_TICKS_Y = 8;

// DEFINE CHARTS
const LINE_COLOURS = [
    "#FF0000",
    "#00FF00",
    "#0000FF",
    // "#FFFFFF", - not required at this stage
];
const DEFAULT_MARGINS = { top: 6, right: 10, bottom: 24, left: 50 };

const GRAPH_AV_ACCEL = {
    selector: "#graph-av-accel",
    ylabel: "Acceleration (g)",
    numLines: 3,
    data: [],
};
const GRAPH_AV_GYRO = {
    selector: "#graph-av-gyro",
    ylabel: "Rotation Rate (°/s)",
    numLines: 3,
    data: [],
};
const GRAPH_AV_VELOCITY = {
    selector: "#graph-av-velocity",
    ylabel: "Vertical Speed (m/s)",
    numLines: 1,
    limits: {
        yBottomMax: 0,
    },
    data: [],
};
const GRAPH_POS_ALT = {
    selector: "#graph-pos-alt",
    ylabel: "Altitude (ft)",
    numLines: 1,
    limits: {
        yBottomMax: 0,
    },
    data: [],
};
const GRAPH_AUX_TRANSDUCERS = {
    selector: "#graph-aux-transducers",
    ylabel: "Pressure (bar)",
    numLines: 3,
    limits: {
        yBottomMax: 0,
    },
    data: [],
};
const GRAPH_AUX_THERMOCOUPLES = {
    selector: "#graph-aux-thermocouples",
    ylabel: "Temperature (°C)",
    numLines: 3,
    limits: {
        yBottomMax: 0,
    },
    data: [],
};
const GRAPH_AUX_VENTTEMP = {
    selector: "#graph-aux-venttemp",
    ylabel: "Temperature (°C)",
    numLines: 1,
    limits: {
        yBottomMax: 0,
    },
    data: [],
};
const GRAPH_AUX_SUPPLY_TEMP = {
    selector: "#graph-aux-n2o-supply-temp",
    ylabel: "Temperature (°C)",
    numLines: 1,
    data: [],
};

const GRAPH_TEST_COLOURS = {
    selector: "#graph-test-colours",
    ylabel: "Sample metric",
    numLines: 3,
    data: [],
}

const symbolCircle = d3.symbol().type(d3.symbolCircle).size(10);

// Create and initialise line graphs
function graphCreateLine(chart) {
    // Select SVG
    chart.svg = d3.select(chart.selector);

    // Make sure chart exists
    if (chart.svg.node() == null) {
        return;
    }

    // Dynamic graph size initialisation
    const boundingRect = chart.svg.node().parentElement.getBoundingClientRect();
    chart.width = boundingRect.width;
    chart.height = boundingRect.height;
    chart.svg
        .attr("viewBox", `0 0 ${chart.width} ${chart.height}`)
        .attr("preserveAspectRatio", "xMidYMid meet");

    // Update graph margins and axes
    if (chart.margin === undefined) {
        chart.margin = DEFAULT_MARGINS;
    }

    /* If the 1st parameter is 0, this would throw -ve dimension errors.
     * This would happen if boundingRect gave 0-dimensions (such as in the
     * diagnostics graphs where the devices aren't hardcoded and hence).
    */
    chart.graphWidth = Math.abs(chart.width - chart.margin.left - chart.margin.right);
    chart.graphHeight = Math.abs(chart.height - chart.margin.top - chart.margin.bottom);

    chart.x = d3.scaleLinear().range([0, chart.graphWidth]);
    chart.y = d3.scaleLinear().range([chart.graphHeight, 0]);

    // Build graph
    chart.g = chart.svg
        .append("g")
        .attr(
            "transform",
            `translate(${chart.margin.left},${chart.margin.top})`,
        );

    // Create and style the x and y axis
    // x axis
    const xAxis = chart.g
        .append("g")
        .attr("transform", `translate(0,${chart.graphHeight})`)
        .call(
            d3
                .axisBottom(chart.x)
                .tickFormat((d) => (Number.isInteger(d) ? d : "")),
        );

    xAxis.selectAll(".domain")
        .attr("stroke", "#f79322")
        .attr("stroke-width", 1);

    xAxis.selectAll(".tick line")
        .attr("stroke", "#f79322");

    xAxis.selectAll(".tick text")
        .attr("fill", "white")
        .attr("font-size", "9px");

    // Y-axis
    chart.yAxis = chart.g.append("g").attr("class", "y-axis");
    chart.yAxis.selectAll(".tick text").attr("fill", "white").attr("font-size", "9px");
    chart.yAxis
        .call(
            d3
                .axisLeft(chart.y)
                .ticks(GRAPH_TICKS_Y)
                .tickFormat((d) => (Number.isInteger(d) ? d : "")),
        )
        .selectAll(".domain")
        .attr("stroke", "#f79322")
        .attr("stroke-width", 1);
    chart.yAxis.selectAll(".tick line").attr("stroke", "#f79322");

    // Y-axis Label
    chart.yAxisLabel = chart.svg
        .append("text")
        .attr("text-anchor", "middle")
        .attr("font-size", "90%")
        .attr("fill", "white")
        .attr("transform", "rotate(-90)")
        .attr("x", -Math.round(chart.graphHeight / 2))
        .attr("y", 15)
        .text(chart.ylabel || "Y LABEL");

    // Lines array to hold multiple line data sets
    chart.lines = [];
    for (let i = 0; i < chart.numLines; i++) {
        chart.lines.push({ data: [], color: LINE_COLOURS[i] });
    }

    // ResizeObserver (for dynamic graph resizing)
    const resizeObserver = new ResizeObserver((entries) => {
        for (const entry of entries) {
            const { width, height } = entry.contentRect;
            chart.width = width;
            chart.height = height;
            graphResize(chart); // Call resize handler
        }
    });
    resizeObserver.observe(chart.svg.node().parentElement);
}

// Render static graph from CSV
// eslint-disable-next-line no-unused-vars
function _graphFromCSVStatic(csvData, chart) {
    chart.data = csvData;
    graphRender(chart);
}

// Simulate graph from CSV by progressively loading data
// eslint-disable-next-line no-unused-vars
function _graphFromCSVSimulated(csvData, chart) {
    // Initialise loop
    let index = 0;

    d3.interval(() => {
        if (index < csvData.length) {
            // Add new value to data
            chart.data.push(csvData[index]);

            // Render graph
            graphRender(chart);

            // Increment index
            index++;
        }
    }, 20);
}

// Resize graph
function graphResize(chart) {
    // Update SVG size
    chart.svg
        .attr("viewBox", `0 0 ${chart.width} ${chart.height}`)
        .attr("preserveAspectRatio", "xMidYMid meet");

    // Recalculate graph drawing area

    /* If the 1st parameter is 0, this would throw -ve dimension errors.
     * This would happen if boundingRect gave 0-dimensions (such as in the
     * diagnostics graphs where the devices aren't hardcoded and hence).
    */
    chart.graphWidth = Math.abs(chart.width - chart.margin.left - chart.margin.right);
    chart.graphHeight = Math.abs(chart.height - chart.margin.top - chart.margin.bottom);


    // Update axes
    chart.x.range([0, chart.graphWidth]);
    chart.g
        .select("g")
        .attr("transform", `translate(0,${chart.graphHeight})`)
        .call(
            d3
                .axisBottom(chart.x)
                .tickFormat((d) => (Number.isInteger(d) ? d : "")),
        );

    chart.y.range([chart.graphHeight, 0]);
    chart.yAxis.call(
        d3
            .axisLeft(chart.y)
            .ticks(GRAPH_TICKS_Y)
            .tickFormat((d) => (Number.isInteger(d) ? d : "")),
    );
    chart.yAxisLabel.attr(
        "x",
        -Math.round(chart.graphHeight / 2) - chart.margin.top,
    );

    // Re-render
    graphRender(chart);
}

// Render graph
function graphRender(chart) {
    if (!window.graphsInitialised) {
        return;
    }

    if (
        chart &&
        chart?.g &&
        chart?.x &&
        chart?.lines &&
        typeof timestamp.local !== "undefined"
    ) {
        // Get timestamp of data
        const now = Math.max(
            d3.max(
                chart.lines.flatMap((line) => line.data),
                (d) => d.x,
            ),
            timestamp.local + timestamp.apiConnect - timestamp.drift,
        );

        /* Normally, line data is filtered to be in sync with the time,
         * but for the test colours graph we don't need any scrolling,
         * hence the graph should just be a static display (barring the
         * changes in colour made by the operator).
        */
        const windowStart = (chart !== GRAPH_TEST_COLOURS) ? (now - MAX_TIME) : 0;

        if (chart.lastRender !== now) {
            // Limit data to graph window
            chart.lines.forEach((line) => {
                line.data = line.data.filter(
                    (d) => d.x >= windowStart - GRAPH_GAP_SIZE,
                );
            });

            const allPoints = chart.lines.flatMap((line) => line.data);

            if (allPoints.length === 0) {
                return;
            }

            const yMinRaw = d3.min(allPoints, (d) => d.y);
            const yMaxRaw = d3.max(allPoints, (d) => d.y);

            if (!Number.isFinite(yMinRaw) || !Number.isFinite(yMaxRaw)) {
                return;
            }

            // Seemingly unused code, since yMin and yMax aren't used for anything
            /*
            let yMin = yMinRaw - 1;
            let yMax = yMaxRaw + 1;

            if (chart?.limits?.yBottomMax !== undefined) {
                yMin = Math.min(yMin, chart.limits.yBottomMax);
            }

            if (yMin === yMax) {
                yMin -= 1;
                yMax += 1;
            }
            */

            if (chart.lastRender !== now || chart.lastPointCount !== allPoints.length) {

                /* Update x and y domains (unless it's the test colour
                 * graph where no scrolling is required).
                */
                if (chart !== GRAPH_TEST_COLOURS) {
                    chart.x.domain([windowStart, now]);
                }

                chart.y.domain([
                    Math.min(
                        d3.min(allPoints, (d) => d.y) - 1,
                        chart?.limits?.yBottomMax !== undefined
                            ? chart?.limits?.yBottomMax
                            : Infinity,
                    ),
                    d3.max(allPoints, (d) => d.y) + 1,
                ]); // .nice();

                // Update rendering of X and Y domain
                chart.g
                    .select("g")
                    .transition()
                    .duration(0)
                    .call(
                        d3.axisBottom(chart.x)
                            .tickFormat((d) => (Number.isInteger(d) ? d : ""))
                    );

                chart.yAxis
                    .transition()
                    .duration(0)
                    .call(
                        d3
                            .axisLeft(chart.y)
                            .ticks(GRAPH_TICKS_Y)
                            .tickFormat((d) => (Number.isInteger(d) ? d : "")),
                    );

                // De-emphasize hidden non-integer axis values
                chart.yAxis
                    .selectAll(".tick")
                    .filter((d) => !Number.isInteger(d))
                    .select("line")
                    .style("stroke", "#ccc")
                    .style("stroke-width", 0.5);

                chart.yAxis
                    .selectAll(".tick")
                    .filter((d) => !Number.isInteger(d))
                    .select("text")
                    .style("display", "none");

                // Remove old lines and dots before rendering new ones
                chart.g.selectAll(".line-path").remove();
                chart.g.selectAll(".line-dot").remove();

                // Render each line with a different color
                chart.lines.forEach((lineData, index) => {
                    // Line rendering logic is a bit messy oops
                    // If two points are close together, we draw a line between them.
                    lineData.data.forEach((d, i, data) => {
                        d.prev = Math.abs(d.x - data[i - 1]?.x) <= GRAPH_GAP_SIZE;
                        d.next = Math.abs(d.x - data[i + 1]?.x) <= GRAPH_GAP_SIZE;

                        // If they're not close, we draw a point
                        if (d.x >= windowStart && d.x <= now) {
                            if (!d.prev && !d.next) {
                                chart.g
                                    .append("path")
                                    .attr("class", "line-dot")
                                    .attr("d", symbolCircle)
                                    .attr(
                                        "transform",
                                        `translate(${chart.x(d.x)},${chart.y(d.y)})`,
                                    )
                                    .attr(
                                        "fill",
                                        lineData.color || LINE_COLOURS[index],
                                    );
                            } else if (!d.next || !d.prev) {
                                chart.g
                                    .append("path")
                                    .attr("class", "line-dot")
                                    .attr("d", symbolCircle) // Make cross?
                                    .attr(
                                        "transform",
                                        `translate(${chart.x(d.x)},${chart.y(d.y)})`,
                                    )
                                    .attr(
                                        "fill",
                                        lineData.color || LINE_COLOURS[index],
                                    );
                            }
                        }
                    });

                    // Add path for each line
                    const line = d3
                        .line()
                        .x((d) => chart.x(d.x))
                        .y((d) => chart.y(d.y))
                        .defined((d) => {
                            return d.prev || d.next;
                        });

                    chart.g
                        .append("path")
                        .datum(
                            lineData.data.filter(
                                (d) => d.x >= windowStart && d.x <= now,
                            ),
                        )
                        .attr("class", "line-path")
                        .attr("fill", "none")
                        .attr("stroke", lineData.color || LINE_COLOURS[index]) // Cycle through colors
                        .attr("stroke-width", 1.5)
                        .attr("stroke-linecap", "round")
                        .attr("d", line);
                });

                // Update last render time
                chart.lastRender = now;
                chart.lastPointCount = allPoints.length;
            }
        } else {
            // console.log("graphRender: chart not ready", chart);
        }
    }
}

function graphRequestRender() {
    // Attempt to render all graphs
    graphRender(GRAPH_AV_ACCEL);
    graphRender(GRAPH_AV_GYRO);
    graphRender(GRAPH_AV_VELOCITY);

    graphRender(GRAPH_POS_ALT);

    graphRender(GRAPH_AUX_TRANSDUCERS);
    graphRender(GRAPH_AUX_THERMOCOUPLES);
    graphRender(GRAPH_AUX_VENTTEMP);
    graphRender(GRAPH_AUX_SUPPLY_TEMP);

    graphRender(GRAPH_TEST_COLOURS);

    // Diagnostics ping graphs
    graphRenderDiagnostics();
}

function graphAddValue(graph, line, timestamp, value) {
    // Adds a value to a graph in the right position
    // To make sure things are all valid and don't go out of order

    // Make sure graph is valid and has lines defined
    if (!graph?.lines || line < 0 || line >= graph.lines.length)
        return;

    // Ensure timestamp is a valid number
    if (timestamp === undefined || Number.isNaN(timestamp) || timestamp < 0)
        return;

    // Ensure value is a number
    if (value === undefined || Number.isNaN(value))
        return;

    // Add data to graph (sorted in chronological order)
    const data = graph.lines[line].data;
    const point = { x: timestamp, y: value };

    // Loop backwards from the end to find where to insert the data
    let index = data.length;
    while (index > 0 && data[index - 1].x > timestamp) {
        index--;
    }
    data.splice(index, 0, point);

    // graph.lines[line].data.push({ x: timestamp, y: value});
}

function graphInit() {
    // Build D3 charts
    graphCreateLine(GRAPH_AV_ACCEL);
    graphCreateLine(GRAPH_AV_GYRO);
    graphCreateLine(GRAPH_AV_VELOCITY);
    graphCreateLine(GRAPH_POS_ALT);
    graphCreateLine(GRAPH_AUX_TRANSDUCERS);
    graphCreateLine(GRAPH_AUX_THERMOCOUPLES);
    graphCreateLine(GRAPH_AUX_VENTTEMP);
    graphCreateLine(GRAPH_AUX_SUPPLY_TEMP);
    graphCreateLine(GRAPH_TEST_COLOURS);

    // Update the test colours graph
    for (let i = 0; i < GRAPH_TEST_COLOURS.numLines; ++i) {
        graphAddValue(GRAPH_TEST_COLOURS, i, 0, 2 + i);
        graphAddValue(GRAPH_TEST_COLOURS, i, 1, 2 + i);
    }

    window.graphsInitialised = true;
    console.log("Graphs initialised");
}

if (document.readyState === "loading") {
    window.addEventListener("DOMContentLoaded", graphInit);
} else {
    graphInit();
}

// Update colours in real-time
["One", "Two", "Three", "Four"].forEach((c1, index) => {
    document.getElementById(`colour${c1}`)?.addEventListener('input', (event) => {
        LINE_COLOURS[index] = event.target.value;

        // Same code as above
        for (let i = 0; i < GRAPH_TEST_COLOURS.numLines; ++i) {
            graphAddValue(GRAPH_TEST_COLOURS, i, 0, 2 + i);
            graphAddValue(GRAPH_TEST_COLOURS, i, 1, 2 + i);
        }

        // Update the colours (even if no data is coming through)
        const graphsList = [GRAPH_AV_ACCEL, GRAPH_AV_GYRO, GRAPH_AV_VELOCITY, GRAPH_POS_ALT, GRAPH_AUX_TRANSDUCERS, GRAPH_AUX_THERMOCOUPLES, GRAPH_AUX_VENTTEMP, GRAPH_AUX_SUPPLY_TEMP, GRAPH_TEST_COLOURS];
        graphsList.forEach((g1) => {
            g1.lines.forEach((l1, index) => {
                l1.color = LINE_COLOURS[index];
            });
        });

        // Update the bottom borders (lineFour not required at this stage)
        const lineOne = ["test1", "accelX", "gyroX", "pressure_n2o_bottle", "temp_tank_top", "temp_pipe_n2o_gse", "gasBottleWeight1", "temp_vent", "altitudeFeet", "velocity"];
        const lineTwo = ["test2", "accelY", "gyroY", "pressure_n2o_tank", "temp_tank_middle", "gasBottleWeight2"];
        const lineThree = ["test3", "accelZ", "gyroZ", "pressure_o2_tank", "temp_tank_bottom"];

        [lineOne, lineTwo, lineThree].forEach((line, index) => {
            line.forEach((c1) => {
                const inputElement = document.querySelector(`input[data-key="${c1}"]`);
                if (inputElement != null) {
                    inputElement.style.borderBottomColor = LINE_COLOURS[index];
                }
            });
        });

        // Not tied to any graphs, but might as well also change these bottom borders
        ["pitch", "yaw", "roll"].forEach((a1, index) => {
            const inputElement = document.querySelector(`input[class*="rocket-${a1}"]`);
            if (inputElement != null) {
                inputElement.style.borderBottomColor = LINE_COLOURS[index];
            }
        });
    })
})

// Update modules
function graphUpdateAvionics(data) {
    // AVIONICS MODULE GRAPHS
    if (data?.id && data?.meta?.timestampS && data?.meta?.totalPacketCountAv) {
        const timestamp = data.meta.timestampS;

        // Acceleration
        graphAddValue(GRAPH_AV_ACCEL, 0, timestamp, data.accelX);
        graphAddValue(GRAPH_AV_ACCEL, 1, timestamp, data.accelY);
        graphAddValue(GRAPH_AV_ACCEL, 2, timestamp, data.accelZ);

        // Gyroscope
        graphAddValue(GRAPH_AV_GYRO, 0, timestamp, data.gyroX);
        graphAddValue(GRAPH_AV_GYRO, 1, timestamp, data.gyroY);
        graphAddValue(GRAPH_AV_GYRO, 2, timestamp, data.gyroZ);

        // Velocity
        graphAddValue(GRAPH_AV_VELOCITY, 0, timestamp, data.velocity);
    }
}

function graphUpdatePosition(data) {
    // POSITION MODULE GRAPHS
    if (data?.id && data?.meta?.timestampS && data?.meta?.totalPacketCountAv) {
        const timestamp = data.meta.timestampS;

        // Altitude
        graphAddValue(GRAPH_POS_ALT, 0, timestamp, metresToFeet(data.altitude));
    }
}

function graphUpdateAuxData(data) {
    // AUXILIARY DATA MODULE GRAPHS

    // TODO Based on launch configuration, some values will be "offline"
    // Clearly label those graphs as offline instead of leaving them blank

    if (data?.id) {
        const timestamp = data.meta.timestampS;

        // Transducers
        graphAddValue(GRAPH_AUX_TRANSDUCERS, 0, timestamp, data.pressure_n2o_bottle);
        graphAddValue(GRAPH_AUX_TRANSDUCERS, 1, timestamp, data.pressure_n2o_tank);
        graphAddValue(GRAPH_AUX_TRANSDUCERS, 2, timestamp, data.pressure_o2_tank);

        // Supply Temp
        graphAddValue(
            GRAPH_AUX_SUPPLY_TEMP,
            0,
            timestamp,
            data.temp_pipe_n2o_gse,
        );

        // Vent temperature
        graphAddValue(GRAPH_AUX_VENTTEMP, 0, timestamp, data.temp_vent);

        graphAddValue(
            GRAPH_AUX_THERMOCOUPLES,
            0,
            timestamp,
            data.temp_tank_top,
        );
        graphAddValue(
            GRAPH_AUX_THERMOCOUPLES,
            1,
            timestamp,
            data.temp_tank_middle,
        );
        graphAddValue(
            GRAPH_AUX_THERMOCOUPLES,
            2,
            timestamp,
            data.temp_tank_bottom,
        );
    }
}
// ================================================================
// DIAGNOSTICS — Full redesign
// Manages: device list cards, ping graphs, status boxes, bottom bar
// Called by GCS_API.js when packet ID 50 arrives
// ================================================================

const diagGraphs = {}; // d_id → graph object (with pingValues[])
const DIAG_GSE_DEVICES = ["GSE ESP32", "Vulcan ESP32", "WiFi Bridge @ GSE"];
const DIAG_LAN_DEVICES = ["TP-Link", "TP-Link Router", "GCS Raspberry Pi", "GC-1", "GC-2", "WiFi Bridge @ GCS"];
const DIAG_RENDER_LATENCY_SECONDS = 1.8;
function diagNowSeconds() {
    return performance.now() / 1000;
}
function diagClampGraphPing(value) {
    return Math.max(1, Math.min(498, value));
}

// Returns a CSS-safe ID string from a device name
function diagSafeId(d_id) {
    return d_id.replace(/[^a-z0-9]/gi, "-").toLowerCase();
}

// ── Left panel: create/update a device card ──────────────────────
function diagUpdateDeviceCard(d_id, d_data) {
    const safeId = diagSafeId(d_id);
    const listEl = document.getElementById("diag-device-list");
    if (!listEl)
        return;

    let card = document.getElementById(`diag-card-${safeId}`);
    if (!card) {
        card = document.createElement("div");
        card.id = `diag-card-${safeId}`;
        card.className = "flex flex-col px-3 py-2 rounded-xl gap-1 shrink-0";
        listEl.appendChild(card);
    }

    const lossText = d_data.packet_loss != null ? `${d_data.packet_loss}%` : "--";
    const pingText = d_data.connected ? `${d_data.ping.toPrecision(3)} ms` : "-- ms";
    const pktsText = d_data.packet_count ?? "--";

    card.style.background =
        d_data.connected
            ? "linear-gradient(180deg, rgba(12,12,16,0.9), rgba(4,4,8,0.9))"
            : "linear-gradient(180deg, rgba(80,0,0,0.35), rgba(20,0,0,0.85))";

    card.style.border =
        `1px solid ${d_data.connected ? "rgba(255,45,105,0.65)" : "rgba(220,38,38,0.55)"}`;

    card.style.boxShadow =
        d_data.connected
            ? "0 0 8px rgba(255,45,105,0.15)"
            : "0 0 12px rgba(239,68,68,0.35)";

    card.innerHTML = `
        <div class="flex items-center gap-2 mb-1">
            <div style="
                width:10px; height:10px; border-radius:50%; flex-shrink:0;
                background:${d_data.connected ? "#4ade80" : "#ef4444"};
                box-shadow:0 0 6px ${d_data.connected ? "#4ade80" : "#ef4444"};
            "></div>
            <span class="font-bold" style="color:var(--color-horizon-yellow,#f59e0b); font-size:0.95rem;">${d_id}</span>
        </div>
        <div style="
            display:grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
            margin-top: 4px;
        ">
            <div style="display:flex; flex-direction:column; gap:2px;">
                <span style="font-size:0.65rem; color:rgba(255,255,255,0.45);">Packet Loss</span>
                <span style="font-size:0.9rem; color:rgba(255,255,255,0.85);">${lossText}</span>
            </div>

            <div style="display:flex; flex-direction:column; gap:2px;">
                <span style="font-size:0.65rem; color:rgba(255,255,255,0.45);">Ping</span>
                <span style="font-size:0.9rem; color:rgba(255,255,255,0.85);">${pingText}</span>
            </div>

            <div style="display:flex; flex-direction:column; gap:2px;">
                <span style="font-size:0.65rem; color:rgba(255,255,255,0.45);">Updates</span>
                <span style="font-size:0.9rem; color:rgba(255,255,255,0.85);">${pktsText}</span>
            </div>
        </div>
    `;
}

// ── Middle panel: create a graph card if it doesn't exist ────────
function diagEnsureGraph(d_id) {
    // Check if graph exists
    if (diagGraphs[d_id])
        return;

    //
    const container = document.getElementById("diag-graphs-container");
    if (!container)
        return;

    const safeId = diagSafeId(d_id);
    const svgId = `diag-graph-${safeId}`;
    if (document.getElementById(svgId))
        return;

    const panel = document.createElement("div");
    panel.id = `diag-panel-${safeId}`;
    panel.className = "flex flex-col rounded-xl overflow-hidden";
    panel.style.cssText =
        "background:linear-gradient(180deg, rgba(20,0,8,0.95), rgba(5,0,3,0.95)); border:1px solid rgba(255,45,105,0.75); box-shadow:0 0 12px rgba(255,45,105,0.22);";

    panel.innerHTML = `
        <div class="flex items-center justify-between px-2 pt-1 shrink-0">
            <span class="text-xs font-semibold"
                  style="color:var(--color-horizon-yellow,#f59e0b);">${d_id}</span>
            <span id="diag-badge-${safeId}"
                  style="font-size:0.6rem; padding:1px 5px; border-radius:3px;
                         background:#ef4444; color:white; font-weight:700;">
                OFFLINE
            </span>
        </div>
        <div class="grow relative min-h-0">
            <svg id="${svgId}" class="w-full h-full absolute inset-0"
                 width="0" height="0"></svg>
        </div>
        <div id="diag-stats-${safeId}"
             class="px-2 pb-1 shrink-0 flex gap-1 justify-center"
             style="font-size:0.6rem; color:rgba(255,255,255,0.45);">
            <span>Avg: -- ms</span><span>|</span>
            <span>Min: -- ms</span><span>|</span>
            <span>Max: -- ms</span>
        </div>
    `;
    container.appendChild(panel);

    const graph = {
        selector: `#${svgId}`,
        ylabel: "ms",
        numLines: 1,
        lineColor: "#000000",
        limits: { yBottomMax: 0, yTopMin: 500, },
        data: [],
        margin: { top: 4, right: 6, bottom: 20, left: 36 },
        pingValues: [], // for avg/min/max tracking
    };

    diagGraphs[d_id] = graph;

    // Add threshold background layers after graph initialises
    // Delay so the browser paints the panel before we measure its dimensions
    setTimeout(() => {

        graphCreateLine(graph);

        if (!graph.g)
            return;

        // Remove existing layers if re-created
        graph.g.selectAll(".diag-threshold-layer").remove();

        // GREEN 0-100
        graph.g.append("rect")
            .attr("class", "diag-threshold-layer")
            .attr("x", 0)
            .attr("y", 0)
            .attr("width", graph.graphWidth)
            .attr("height", graph.graphHeight)
            .attr("fill", "rgba(34,197,94,0.12)");

        // YELLOW 100-200
        graph.g.append("rect")
            .attr("class", "diag-threshold-layer")
            .attr("x", 0)
            .attr("width", graph.graphWidth)
            .attr("fill", "rgba(250,204,21,0.12)");

        // RED 200-500
        graph.g.append("rect")
            .attr("class", "diag-threshold-layer")
            .attr("x", 0)
            .attr("width", graph.graphWidth)
            .attr("fill", "rgba(239,68,68,0.14)");

        // Force diagnostics graph lines black
        graph.lines.forEach(line => {
            line.color = "#000000";
        });
    }, 200);

}

// ── Middle panel: update badge, graph line, and stats ────────────
function diagUpdateGraph(d_id, d_data, timestamp) {
    const safeId = diagSafeId(d_id);
    const graph = diagGraphs[d_id];

    // Badge
    const badge = document.getElementById(`diag-badge-${safeId}`);
    if (badge) {
        badge.textContent = d_data.connected ? "ONLINE" : "OFFLINE";
        badge.style.background = d_data.connected ? "#4ade80" : "#ef4444";
        badge.style.color = d_data.connected ? "black" : "white";
    }

    // Graph data + stats
    if (graph) {
        graphAddValue(graph, 0, timestamp, d_data.ping);

        // Update diagnostics threshold layer positions
        if (graph?.g && graph?.graphHeight) {
            const greenTop = graph.y(100);
            const yellowTop = graph.y(200);
            const bottom = graph.y(1);
            const top = graph.y(500);

            const layers = graph.g.selectAll(".diag-threshold-layer");

            // GREEN: 1–100ms
            d3.select(layers.nodes()[0])
                .attr("y", greenTop)
                .attr("height", bottom - greenTop);

            // YELLOW: 101–200ms
            d3.select(layers.nodes()[1])
                .attr("y", yellowTop)
                .attr("height", greenTop - yellowTop);

            // RED: 200–500ms
            d3.select(layers.nodes()[2])
                .attr("y", top)
                .attr("height", yellowTop - top);
        }

        // This keeps disconnected values from affecting average/min/max stats.
        // Ping 0 is a special graph marker, so it is also excluded from stats.
        if (d_data.connected) {
            graph.pingValues.push(d_data.ping);
            if (graph.pingValues.length > 300)
                graph.pingValues.shift();
        }

        const statsEl = document.getElementById(`diag-stats-${safeId}`);

        if (statsEl) {
            if (graph.pingValues.length > 0) {
                const avg = graph.pingValues.reduce((a, b) => a + b, 0) / graph.pingValues.length;
                const min = Math.min(...graph.pingValues);
                const max = Math.max(...graph.pingValues);

                statsEl.innerHTML = `
                    <span>Avg: ${avg.toFixed(1)} ms</span><span>|</span>
                    <span>Min: ${min.toFixed(0)} ms</span><span>|</span>
                    <span>Max: ${max.toFixed(0)} ms</span>
                `;
            } else {
                statsEl.innerHTML =
                    "<span>Avg: -- ms</span><span>|</span><span>Min: -- ms</span><span>|</span><span>Max: -- ms</span>";
            }
        }
    } else {
        const statsEl = document.getElementById(`diag-stats-${safeId}`);
        if (statsEl) {
            statsEl.innerHTML =
                "<span>Avg: -- ms</span><span>|</span><span>Min: -- ms</span><span>|</span><span>Max: -- ms</span>";
        }
    }
}

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
// ── Bottom bar: update summary counts ────────────────────────────
function diagUpdateBottomBar(totalDevices, onlineCount) {
    const offlineCount = totalDevices - onlineCount;
    const allOnline = offlineCount === 0 && totalDevices > 0;

    const elAll = document.getElementById("diag-bottom-all-online");
    const elOffline = document.getElementById("diag-bottom-offline");
    const elOnline = document.getElementById("diag-bottom-online");

    if (elAll) {
        elAll.textContent = allOnline ? "Yes" : "No";
        elAll.style.background = allOnline ? "#16a34a" : "#dc2626";
    }
    if (elOffline) {
        elOffline.textContent = offlineCount;
        elOffline.style.background = offlineCount > 0 ? "#dc2626" : "#16a34a";
    }
    if (elOnline) {
        elOnline.textContent = onlineCount;
        elOnline.style.background = onlineCount > 0 ? "#16a34a" : "rgba(255,255,255,0.1)";
    }
}

// ── Main entry point: called by GCS_API.js when packet 50 arrives ─
function graphUpdateDiagnostics(apiData) {
    const timestamp = diagNowSeconds();

    let onlineCount = 0; let totalCount = 0;
    let gseOnline = true;
    let lanOnline = true;
    let hasGseDevice = false;
    let hasLanDevice = false;

    Object.entries(apiData).forEach(([d_id, d_data]) => {
        if (d_id === "id" || d_id === "state" || d_id === "meta")
            return;
        if (typeof d_data !== "object" || d_data === null)
            return;

        if (d_data.ping === undefined) {
            d_data.ping = -1;
            d_data.connected = false;
        }

        if (DIAG_GSE_DEVICES.includes(d_id)) {
            hasGseDevice = true;

            if (!d_data.connected) {
                gseOnline = false;
            }
        } else if (DIAG_LAN_DEVICES.includes(d_id)) {
            hasLanDevice = true;

            if (!d_data.connected) {
                lanOnline = false;
            }
        }

        totalCount++;
        if (d_data.connected)
            onlineCount++;

        // Left panel
        diagUpdateDeviceCard(d_id, d_data);

        // Middle panel
        if (diagGraphs[d_id] === undefined) {
            diagEnsureGraph(d_id);
        }
        diagUpdateGraph(d_id, d_data, timestamp);

        // if (DIAG_LAN_DEVICES.includes(d_id) && alive) {
        //     lanWorstPing =
        //         lanWorstPing == null
        //             ? ping
        //             : Math.max(lanWorstPing, ping);
        // }
    });


    // Right panel
    diagSetSummaryOnlineBox("diag-summary-gse", hasGseDevice && gseOnline);
    diagSetSummaryOnlineBox("diag-summary-lan", hasLanDevice && lanOnline);

    const avIndicator = document.querySelector('[data-key="state.av.radio"][data-type="state"]');

    if (avIndicator) {
        const avOnline = avIndicator.classList.contains("green");

        diagSetSummaryOnlineBox("diag-summary-av", avOnline);
        diagSetAvIndicator(avOnline);
    }

    // Bottom bar
    diagUpdateBottomBar(totalCount, onlineCount);

    // Last updated
    const lastUpdated = document.getElementById("diag-last-updated");
    if (lastUpdated) {
        const now = new Date();
        lastUpdated.textContent = `Last updated: ${now.toLocaleTimeString("en-AU")} AEST`;
    }
}

// Renders all diagnostics ping graphs every animation frame
function graphRenderDiagnostics() {
    Object.values(diagGraphs).forEach((graph) => {
        diagRenderGraph(graph);
    });
}

function diagRenderGraph(graph) {
    if (!graph || !graph.g || !graph.x || !graph.y || !graph.lines)
        return;

    const allPoints = graph.lines.flatMap((line) => line.data);
    if (allPoints.length === 0)
        return;

    const renderNow = diagNowSeconds();
    const now = renderNow - DIAG_RENDER_LATENCY_SECONDS;

    if (!Number.isFinite(now))
        return;

    const windowStart = now - MAX_TIME;

    graph.lines.forEach((line) => {
        line.data = line.data.filter(
            (d) => d.x >= windowStart - GRAPH_GAP_SIZE,
        );
    });

    graph.x.domain([windowStart, now]);
    graph.y.domain([0, 500]);

    graph.g
        .select("g")
        .transition()
        .duration(0)
        .call(d3.axisBottom(graph.x).tickFormat((d) => `${Math.round(d)}`));

    graph.g.select("g").selectAll(".tick text").attr("fill", "white").attr("font-size", "9px");

    graph.yAxis
        .transition()
        .duration(0)
        .call(
            d3.axisLeft(graph.y)
                .tickValues([0, 100, 200, 300, 400, 500])
                .tickFormat((d) => `${d}`)
        );

    graph.yAxis.selectAll(".tick text")
        .attr("fill", "white")
        .attr("font-size", "9px");

    const greenTop = graph.y(100);
    const yellowTop = graph.y(200);
    const bottom = graph.y(0);
    const top = graph.y(500);

    const layers = graph.g.selectAll(".diag-threshold-layer");

    d3.select(layers.nodes()[0])
        .attr("x", 0)
        .attr("width", graph.graphWidth)
        .attr("y", greenTop)
        .attr("height", bottom - greenTop);

    d3.select(layers.nodes()[1])
        .attr("x", 0)
        .attr("width", graph.graphWidth)
        .attr("y", yellowTop)
        .attr("height", greenTop - yellowTop);

    d3.select(layers.nodes()[2])
        .attr("x", 0)
        .attr("width", graph.graphWidth)
        .attr("y", top)
        .attr("height", yellowTop - top);

    graph.g.selectAll(".line-path").remove();
    graph.g.selectAll(".line-dot").remove();

    graph.lines.forEach((lineData) => {
        const visibleData = lineData.data.filter(
            (d) => d.x >= windowStart && d.x <= now
        );

        // Build a single continuous blue step-line segment.
        // Offline points (-1) do NOT break the line
        const normalSegments = [];
        const currentSegment = [];
        let lastValidY = null;

        // Look for the most recent valid (online) point before the window
        // so we can seed lastValidY and start the line at the window edge.
        const lastOnlineBeforeWindow = [...lineData.data]
            .reverse()
            .find((d) => d.x < windowStart && d.y >= 0);

        if (lastOnlineBeforeWindow) {
            lastValidY = lastOnlineBeforeWindow.y;
            currentSegment.push({ x: windowStart, y: lastValidY });
        }

        visibleData.forEach((d) => {
            if (d.y >= 0) {
                // Normal online point — update last known valid ping.
                lastValidY = d.y;
                currentSegment.push(d);
            } else {
                // Offline point — hold the last valid ping so the line
                // stays visible through the red offline block.
                if (lastValidY !== null) {
                    currentSegment.push({ x: d.x, y: lastValidY });
                }
                // If we have never seen a valid ping yet there is nothing
                // to draw, so we simply skip until the first online point.
            }
        });

        // Always extend the segment to the current render time so the
        // line reaches the right edge of the graph.
        if (currentSegment.length > 0) {
            const lastPoint = currentSegment[currentSegment.length - 1];
            if (lastPoint.x < now) {
                currentSegment.push({ x: now, y: lastPoint.y });
            }
            normalSegments.push(currentSegment);
        }

        const stepLine = d3
            .line()
            .x((d) => graph.x(d.x))
            .y((d) => graph.y(diagClampGraphPing(d.y)))
            .curve(d3.curveStepAfter);

        const stepPath = graph.g.selectAll(".diag-step-line")
            .data(normalSegments);

        stepPath
            .enter()
            .append("path")
            .attr("class", "diag-step-line")
            .attr("fill", "none")
            .attr("stroke", "#22d3ee")
            .attr("stroke-width", 2.5)
            .attr("stroke-opacity", 0.95)
            .attr("stroke-linecap", "round")
            .attr("stroke-linejoin", "round")
            .merge(stepPath)
            .attr("d", stepLine);

        stepPath.exit().remove();

        // Red vertical bars use ONLY disconnected ping values.
        const offlineSpans = [];

        let offlineStart = null;

        visibleData.forEach((d) => {
            // THIS CODE NEEDS TO BE UPDATED WITH .CONNECTED NOT PING
            if (d.y < 0 && offlineStart === null) {
                offlineStart = d.x;
            }

            if (d.y >= 0 && offlineStart !== null) {
                offlineSpans.push({
                    start: offlineStart,
                    end: d.x,
                });

                offlineStart = null;
            }
        });

        if (offlineStart !== null) {
            offlineSpans.push({
                start: offlineStart,
                end: now,
            });
        }

        const disconnectBars = graph.g.selectAll(".diag-disconnect-bar")
            .data(offlineSpans, (d) => `${d.start}-${d.end}`);

        disconnectBars
            .enter()
            .append("rect")
            .attr("class", "diag-disconnect-bar")
            .attr("fill", "#ef4444")
            .attr("fill-opacity", 1.2)
            .merge(disconnectBars)
            .attr("x", (d) => graph.x(d.start))
            .attr("y", graph.y(500))
            .attr("width", (d) => Math.max(2, graph.x(d.end) - graph.x(d.start)))
            .attr("height", graph.y(1) - graph.y(500));

        disconnectBars.exit().remove();
    });
}

export { diagSetAvIndicator, diagSetStatusBox, diagSetSummaryOnlineBox, graphRequestRender, graphUpdateAuxData, graphUpdateAvionics, graphUpdateDiagnostics, graphUpdatePosition }
