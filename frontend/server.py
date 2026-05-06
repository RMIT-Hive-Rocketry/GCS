#!/usr/bin/env python3
from frontend.rocket_loader import load_rockets
from flask import (
    Flask,
    send_from_directory,
    abort,
    render_template,
    request,
)
from os import path as os_path
import backend.includes_python.process_logging as slogger
import config.config as config


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

# Initialise flask app
def create_app():
    # App configuration
    app = Flask(__name__)
    app.config.from_object(
        "frontend.config." + frontend.config.rocket + "Config"
    )
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    file_extensions = (
        ".css",
        ".js",  # CSS, JavaScript
        ".png",
        ".jpg",
        ".ico",
        ".svg",  # Images
    )

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
    Logging
    """
    """
    # Custom logging
    if slogger != None:
        handler = SubprocessLogHandler()
        formatter = logging.Formatter('%(message)s')  # Keep raw message for slogger
        handler.setFormatter(formatter)
        
        app.logger.handlers.clear()
        app.logger.propagate = False
        app.logger.addHandler(handler)
        app.logger.setLevel(logging.DEBUG)
    """

    # Render modular layout
    @app.route("/")
    def index():
        # Get active rocket config default
        active = app.config.get("default")
        name = ""

        # Check for config override via URL parameter
        rocket = request.args.get("rocket", "default")
        if rocket != None:
            for r in app.config.get("rockets"):
                if r.name == rocket:
                    active = r.configs[0]
                    name = r.name
                    break

        return render_template(
            "/templates/layout.html",
            config=app.config,
            active=active,
            name=name,
            websocket=websocket,
        )

        # Generate positional classes for modules
        grid = set()
        for module in app.config["MODULES"]:
            # All modules are hidden by default
            class_list = {"module", "hidden"}

            # For each module, update visibility and position for each page
            for page in app.config["MODULES"][module]["pages"]:
                # Encode position and size in grid
                cols = "{}-c-{}-{}".format(page[0], page[1], page[3])
                rows = "{}-r-{}-{}".format(page[0], page[2], page[4])

                # Add classes to grid
                grid.add("#{} .{}".format(page[0], cols))
                grid.add("#{} .{}".format(page[0], rows))

                # Add classes to module
                class_list.add(page[0])
                class_list.add(cols)
                class_list.add(rows)

            # Assign generated classes to module
            app.config["MODULES"][module]["classes"] = " ".join(class_list)

        # Add optimised grid to CSS
        for grid_class in grid:
            grid_type, grid_start, grid_span = grid_class.split("-")[-3:]
            app.config["CSS"] += "\n{} {{grid-{}: {} / span {};}} ".format(
                grid_class,
                "column" if grid_type == "c" else "row",
                int(grid_start) + 1,
                grid_span,
            )

        # Render the page
        return render_template("layout.html", config=app.config)

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
        if filename.endswith(file_extensions) and os.path.isfile(filepath):
            slogger.debug(f"Serving static file: {filename}")
            return send_from_directory(static_dir, filename)

        # Attempt to load filename as .html (so suffix isn't always required)
        if os_path.isfile(filepath + ".html"):
            slogger.debug(f"Serving static webpage: {filename}.html")
            return send_from_directory(file_directory, filename + ".html")

        # 404 page not found
        slogger.warning(f"404 not found: {filename}")
        abort(404)
        return None

    # Debugging
    @app.route("/debug/api")
    def debug_api():
        return render_template("debug_api.html")

    # Debug rocket loading
    @app.route("/debug/rockets")
    def debug_rockets():
        return render_template(
            "templates/debug_rockets.html",
            websocket=websocket,
        )

    # Debug modules
    # Shows all modules from loaded rockets
    @app.route("/debug/modules")
    def debug_modules():
        return render_template(
            "templates/debug_modules.html",
            websocket=websocket,
        )

    # Debug control pendant
    # Shows all modules from loaded rockets
    @app.route("/debug/pendant")
    def debug_pendant():
        return render_template(
            "templates/debug_pendant.html",
            websocket=websocket,
        )

    return app
