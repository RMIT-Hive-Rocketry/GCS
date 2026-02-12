# Frontend developer documentation

_Developer notes and documentation for working on the GCS frontend._

## Interface items

Certain elements on the page can be made to update when data is received. Previously, this was done by hardcoding into JavaScript which DOM elements would be updated (and how), but it's recently been changed with the inclusion of a registry.

### Registry

A registry is generated on page load to store all the elements that are live updated with data. All registry information relevant for updating elements is stored directly in the HTML, to reduce redundancy and make it easier for someone to edit the behaviour of the interface.

The registry is created by scanning for all HTML elements with the `data-key=""` field, then checking which type (or rather, function) they have on the page as stored in the `data-type=""` field.

The key refers to the name of the variable that updates that HTML element, for instance the element `<input data-key="localTime" data-type="string" readonly>` would have its value updated whenever localTime is received from the data stream, and it would be updated as a string type.

Further optional fields may be added to augment the behaviour. All fields and respective behaviour is in the table below.

| Name             | Values                                         | Description                                                                                                                                    |
| ---------------- | ---------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `data-key`\*     | Any alphanumeric string delineated by '.'      | Refers to a key in the incoming data stream                                                                                                    |
| `data-type`\*    | "value", "string", "state"                     | Changes how incoming data is handled by the element                                                                                            |
| `data-precision` | Positive integer                               | Number of decimal places to render "value" data type with.                                                                                     |
| `data-timeout`   | JSON dictionary in format of `{time_ms:state}` | Denotes timeout behaviour for the "state" data type. For each entry in the dictionary, a timer is started which sets a new state upon timeout. |

\*Required.

### Data types

| Type     | Description                                                                  |
| -------- | ---------------------------------------------------------------------------- |
| "value"  | Numerical value, most common type of data to be shown on a page.             |
| "string" | Text string, for displaying text or specific number formatting.              |
| "state"  | State indicator, small lights which change colour depending on system state. |

## Libraries

We're using the following libraries for frontend:

- Tailwind v4.0.17
- D3.js v7.9.0
- Three.js v0.175.0

These libraries have been included as standalone JS so we don't have to rely on NPM or a CDN.

These are likely to be updated before IREC 2026, probably in March after our first test launch.

### Tailwind

**Tailwind v4.0.17 is used for stylesheets.**

The standalone version of Tailwind will be used so we don't have to rely on node.js. Download it from https://github.com/tailwindlabs/tailwindcss/releases/tag/v4.0.17, rename to _tailwindcss_, and place it INSIDE `/third_party/` for development.

The `/frontend/scripts/` folder has a number of scripts for using Tailwind:

- _tailwind_dev.sh_ will update tailwind.css in realtime, as you make changes to the html. Use this while developing the webpage.
- _tailwind_build.sh_ will build an optimised and minified version of tailwind.css for production. This probably isn't necessary since it's a fairly small website, but we'll take any optimisations we can get.

### D3.js

**D3.js v7.9.0 is used for data visualisation.**

It lets us make pretty graphs

### Three.js

**Three.js v0.175.0 is used to render the 3D model of the rocket.**

Included with this is the **GLTFLoader.js** loader, which lets us load .gltf and .glb model files.

---

[Home](../README.md)
