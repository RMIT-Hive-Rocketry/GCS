# Frontend developer documentation

*Developer notes and documentation for working on the GCS frontend.*

## Libraries
We're using the following libraries for frontend:
- Tailwind v4.0.17
- D3.js v7.9.0
- Three.js v0.175.0

These libraries have been included as standalone JS so we don't have to rely on NPM or a CDN. 

Unless updating them is absolutely necessary, we will be using these specific versions throughout the capstone project. Updating in the middle of development can add a lot of work and cause weird glitches.

### Tailwind
**Tailwind v4.0.17 is used for stylesheets.**

The standalone version of Tailwind will be used so we don't have to rely on node.js. Download it from https://github.com/tailwindlabs/tailwindcss/releases/tag/v4.0.17, rename to *tailwindcss*, and place it INSIDE `/third_party/` for development. 

The `/frontend/scripts/` folder has a number of scripts for using Tailwind:

- *tailwind_dev.sh* will update tailwind.css in realtime, as you make changes to the html. Use this while developing the webpage.
- *tailwind_build.sh* will build an optimised and minified version of tailwind.css for production. This probably isn't necessary since it's a fairly small website, but we'll take any optimisations we can get.

### D3.js
**D3.js v7.9.0 is used for data visualisation.**

It lets us make pretty graphs

### Three.js
**Three.js v0.175.0 is used to render the 3D model of the rocket.**

Included with this is the **GLTFLoader.js** loader, which lets us load .gltf and .glb model files.
