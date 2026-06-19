#!/usr/bin/env python3

from frontend.rocket_loader import load_rockets
from flask import (
    Flask,
    Response,
    send_from_directory,
    abort,
    render_template,
    request,
)
from os import path as os_path
import backend.includes_python.process_logging as slogger
from config import config

valid_file_extensions = (
    ".css",
    ".js",  # CSS, JavaScript
    ".png",
    ".jpg",
    ".ico",
    ".svg",  # Images
    ".glb",  # 3D models
    ".mp3",  # Sounds
)


# Initialise flask app
def create_app() -> Flask:
    # Create flask app
    app = Flask(
        __name__,
        template_folder=os_path.join(os_path.dirname(__file__), "."),
    )

    # Configure paths for static and rocket files
    dir_static = os_path.join(os_path.dirname(__file__), "static")
    dir_rockets = os_path.join(os_path.dirname(__file__), "rockets")

    # Load rocket assets and configurations from /rockets dir
    app.config["rockets"] = load_rockets(app)
    app.config["default"] = app.config["rockets"][0].configs[0]

    # Load additional configuration from config.ini
    frontend_config = config.get_config()["frontend"]
    websocket = {
        "host": frontend_config.get("ws_host"),
        "port": frontend_config.get("ws_port"),
    }

    """
    Page rendering
    """

    # Render modular layout
    @app.route("/")
    def index() -> str:
        # Get active rocket config default
        active = app.config.get("default")
        name = ""

        # Check for config override via URL parameter
        rocket = request.args.get("rocket", "default")
        rocket_configs = app.config.get("rockets")
        if rocket is not None and rocket_configs is not None:
            for rc in rocket_configs:
                if rc.name == rocket:
                    active = rc.configs[0]
                    name = rc.name
                    break

        return render_template(
            "/templates/layout.html",
            config=app.config,
            active=active,
            name=name,
            websocket=websocket,
        )

    """
    Static file loading
    """

    # Serve static files and HTML pages
    @app.route("/<path:filename>")
    def serve_html(filename) -> Response:
        # Make sure rocket assets are loaded from a different directory
        file_directory = dir_static
        rocket_configs = app.config.get("rockets")
        if rocket_configs is not None and filename.startswith(
            tuple([rc.name for rc in rocket_configs])
        ):
            file_directory = dir_rockets

        # Set filepath
        filepath = os_path.join(file_directory, filename)

        # Load files with valid extensions
        if filename.endswith(valid_file_extensions) and os_path.isfile(
            filepath
        ):
            slogger.debug(f"Serving static file: {filename}")
            return send_from_directory(file_directory, filename)

        # Attempt to load filename as .html (so suffix isn't always required)
        if os_path.isfile(filepath + ".html"):
            slogger.debug(f"Serving static webpage: {filename}.html")
            return send_from_directory(file_directory, filename + ".html")

        # 404 page not found
        slogger.warning(f"404 not found: {filename}")
        abort(404)
        return None

    """
    Debugging
    """

    # Debug rocket loading
    @app.route("/debug/rockets")
    def debug_rockets() -> str:
        return render_template(
            "templates/debug_rockets.html",
            websocket=websocket,
        )

    # Debug modules
    # Shows all modules from loaded rockets
    @app.route("/debug/modules")
    def debug_modules() -> str:
        return render_template(
            "templates/debug_modules.html",
            websocket=websocket,
        )

    # Debug control pendant
    # Shows all modules from loaded rockets
    @app.route("/debug/pendant")
    def debug_pendant() -> str:
        return render_template(
            "templates/debug_pendant.html",
            websocket=websocket,
        )

    return app
