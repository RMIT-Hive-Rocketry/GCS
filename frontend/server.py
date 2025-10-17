#!/usr/bin/env python3
from frontend.rocket_loader import load_rockets
from flask import Flask, send_from_directory, abort, render_template
from os import path as os_path

# import logging
# import backend.includes_python.process_logging as slogger

"""
class SubprocessLogHandler(logging.Handler):
    def emit(self, record):
        msg = self.format(record)
        level = record.levelname.upper()
        if hasattr(slogger, level.lower()):
            getattr(slogger, level.lower())(msg)
        else:
            slogger.info(msg)  # fallback
"""

valid_file_extensions = (
    ".css",
    ".js",  # CSS, JavaScript
    ".png",
    ".jpg",
    ".ico",
    ".svg",  # Images
    ".glb",  # 3D models
)


# Initialise flask app
def create_app():
    # Create flask app
    app = Flask(
        __name__,
        template_folder=os_path.join(os_path.dirname(__file__), "."),
    )

    # Load static files
    DIR_STATIC = os_path.join(os_path.dirname(__file__), "static")
    assert os_path.isdir(DIR_STATIC)

    DIR_ROCKETS = os_path.join(os_path.dirname(__file__), "rockets")
    assert os_path.isdir(DIR_ROCKETS)

    # Load rocket assets and configurations from /rockets dir
    app.config["rockets"] = load_rockets(app, __name__)
    app.config["active"] = app.config["rockets"][2].configs[0]

    """
    Logging
    """
    """
    # Custom logging
    if logger != None:
        handler = SubprocessLogHandler()
        formatter = logging.Formatter('%(message)s')  # Keep raw message for slogger
        handler.setFormatter(formatter)

        app.logger.handlers.clear()
        app.logger.propagate = False
        app.logger.addHandler(handler)
        app.logger.setLevel(logging.DEBUG)
    """

    """
    Page rendering
    """

    # Render modular layout
    @app.route("/")
    def index():
        return render_template("/templates/layout.html", config=app.config)

    """
    Static file loading
    """

    # Serve static files and HTML pages
    @app.route("/<path:filename>")
    def serve_html(filename):
        # Make sure rocket assets are loaded from a different directory
        file_directory = DIR_STATIC
        if filename.startswith(tuple([r.name for r in app.config.get("rockets")])):
            file_directory = DIR_ROCKETS

        # Set filepath
        filepath = os_path.join(file_directory, filename)

        # Load files with valid extensions
        if filename.endswith(valid_file_extensions) and os_path.isfile(filepath):
            # app.logger.debug(f"Serving static file: {filename}")
            return send_from_directory(file_directory, filename)

        # Attempt to load filename as .html (so suffix isn't always required)
        elif os_path.isfile(filepath + ".html"):
            # app.logger.debug(f"Serving static file: {filename}.html")
            return send_from_directory(file_directory, filename + ".html")

        # 404 page not found
        else:
            # app.logger.warning(f"404 not found: {filename}")
            abort(404)

    """
    Debugging
    """

    # Debug rocket loading
    @app.route("/debug/rockets")
    def debug_rockets():
        return render_template("templates/debug_rockets.html")

    # Debug modules
    # Shows all modules from loaded rockets
    @app.route("/debug/modules")
    def debug_modules():
        return render_template("templates/debug_modules.html")

    return app
