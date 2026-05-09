/**
 * GCS Rocket Viewer
 *
 * This script renders a 3D rocket model using Three.js, and updates its orientation in real-time
 * using quaternion data. Smooth interpolation is supported to improve visual stability during flight.
 *
 * Functions and constants should be prefixed with "rocket_" for clarity and namespace safety.
 */

import * as THREE from "/static/js/libraries/three.module.min.js";
import { GLTFLoader } from "/static/js/libraries/loaders/GLTFLoader.js";

const rotationSpeed = 15000; // Time (ms) for a full rotation

window.addEventListener("DOMContentLoaded", () => {
    const rockets = {
        legacy: {
            model: "/legacy/static/assets/rocket_legacy3.v2.glb",
            scale: 2.45,
        },
        atlas: {
            model: "/atlas/static/assets/rocket_atlas.glb",
            scale: 3.42,
        },
        horizon: {
            model: "horizon/static/assets/rocket_horizon.glb",
            scale: 3,
        },
    };

    for (const rocketName of Object.keys(rockets)) {
        const canvas = document.getElementById(rocketName + "Preview");
        if (canvas) {
            setupRocketPreview(canvas, rocketName, rockets[rocketName]);
        }
    }

    function setupRocketPreview(canvas, rocketName, rocket) {
        // Make sure rocket has a model
        if (rocket.model === "") {
            console.warn(`No model path provided for rocket: ${rocketName}`);
            return;
        }

        // Setup canvas and renderer
        const renderer = new THREE.WebGLRenderer({
            canvas,
            antialias: true, // Smooth edges
            alpha: true, // Transparent background
        });
        renderer.setPixelRatio(window.devicePixelRatio);
        renderer.setSize(
            canvas.parentElement.clientWidth,
            Math.min(canvas.parentElement.clientHeight, 512),
        );
        //renderer.gammaOutput = true;
        //renderer.gammaFactor = 2.2;

        // Setup scene and camera
        const scene = new THREE.Scene();

        const aspect =
            canvas.parentElement.clientWidth /
            Math.min(canvas.parentElement.clientHeight, 512);
        const viewSize = 10;
        const camera = new THREE.OrthographicCamera(
            (-aspect * viewSize) / 2, // left
            (aspect * viewSize) / 2, // right
            viewSize / 2, // top
            -viewSize / 2, // bottom
            0.1,
            1000,
        );
        camera.position.set(0, 0, 20);
        camera.lookAt(0, 0, 0);

        // Setup environment lighting
        // Newer versions of three.js require an environment map for lighting
        const environmentTexture = new THREE.CubeTextureLoader().setPath('/static/img/cubemap/').load(['px.png', 'nx.png', 'py.png', 'ny.png', 'pz.png', 'nz.png']);
        scene.environment = environmentTexture;
        //scene.background = environmentTexture;
        scene.environmentIntensity = 1;

        // Also define fixed lights (for aesthetic reasons)
        let skyColor = 0xB1E1FF;  // light blue
        let groundColor = 0xB97A20;  // brownish orange
        let lightIntensity = 100;
        let light = new THREE.HemisphereLight(skyColor, groundColor, lightIntensity);
        scene.add(light);

        let light2 = new THREE.PointLight(skyColor, 20);
        light2.position.set(10, 4, 2);
        scene.add(light2);

        let light3 = new THREE.PointLight(0xFFFFFF, 100);
        light3.position.set(10, 2.5, 0);
        scene.add(light3);

        let light4 = new THREE.PointLight(groundColor, 50);
        light4.position.set(-20, -4, 0);
        scene.add(light4);

        // Load rocket model
        new GLTFLoader().load(
            rocket.model,
            (gltf) => {
                const model = gltf.scene;
                model.scale.set(rocket.scale, rocket.scale, rocket.scale); // Resize for better visibility

                // Center the model at the origin for rotation
                const box = new THREE.Box3().setFromObject(model);
                const center = box.getCenter(new THREE.Vector3());
                model.position.sub(center);

                rocket.group = new THREE.Group();
                rocket.group.add(model);
                scene.add(rocket.group);

                // Dynamically position camera to fit model size
                const size = box.getSize(new THREE.Vector3()).length();
                camera.position.set(0, 0, size * 1.5);
                camera.lookAt(new THREE.Vector3(0, 0, 0));

                animate(); // Start render loop
            },
            (xhr) =>
                console.log(
                    `Loading: ${((xhr.loaded / xhr.total) * 100).toFixed(1)}%`,
                ),
            (err) => console.error("Error loading model:", err),
        );

        // === Main Render Loop ===
        function animate() {
            requestAnimationFrame(animate);

            const now = performance.now();
            const rotation =
                ((now % rotationSpeed) / rotationSpeed) * Math.PI * 2;
            rocket.group.rotation.y = rotation;

            renderer.render(scene, camera);
        }

        // === Responsive Canvas Resize ===
        window.addEventListener("resize", () => {
            renderer.setSize(
                canvas.parentElement.clientWidth,
                Math.min(canvas.parentElement.clientHeight, 512),
            );
            const aspect =
                canvas.parentElement.clientWidth /
                Math.min(canvas.parentElement.clientHeight, 512);
            camera.left = (-aspect * viewSize) / 2;
            camera.right = (aspect * viewSize) / 2;
            camera.top = viewSize / 2;
            camera.bottom = -viewSize / 2;
            camera.updateProjectionMatrix();
        });
    }
});
