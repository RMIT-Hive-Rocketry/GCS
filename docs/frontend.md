# Frontend developer documentation

_Developer notes and documentation for working on the GCS frontend._

## Libraries

We're using the following libraries for frontend:

- Tailwind v4.0.17
- D3.js v7.9.0
- Three.js v0.175.0

These libraries have been included as standalone JS so we don't have to rely on NPM or a CDN.

Unless updating them is absolutely necessary, we will be using these specific versions throughout the capstone project. Updating in the middle of development can add a lot of work and cause weird glitches.

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

## Interface items

### Display item keys and IDs

> These are out of date, and were documented during development of the GCS-2025 system.
>
> TODO: Incorporate this into the API standardisation, which makes all keys and values consistently handled across the entire system, instead of having to do a bunch of processing/handling on each interface

### Module tables

These are the item IDs for updating values with JavaScript:

(Tables have been removed due to being outdated. Please put new tables here when you get a chance.)

---

[Home](../README.md)
