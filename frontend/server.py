#!/usr/bin/env python3
from flask import Flask, send_from_directory, abort, render_template
import os
import frontend.config
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

# Initialise flask app
def create_app():
    # App configuration
    app = Flask(__name__)
    app.config.from_object("frontend.config." + frontend.config.rocket + "Config")
    static_dir = os.path.join(os.path.dirname(__file__), 'static')
    file_extensions = (
        '.css','.js',                   # CSS, JavaScript
        '.png','.jpg','.ico','.svg',    # Images
    )


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


    # Render modular layout
    @app.route('/')
    def index():
        # Parse app.config and pre-process modular layout information for CSS
        # Generate CSS selectors for pages
        app.config["CSS"] = ", ".join(["#{0} .{0}".format(page["id"]) for page in app.config["PAGES"]]) + " {display: flex;}";
    
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
            app.config["MODULES"][module]["classes"] = ' '.join(class_list)

        # Add optimised grid to CSS
        for grid_class in grid:
            grid_type, grid_start, grid_span = grid_class.split("-")[-3:]
            app.config["CSS"] += "\n{} {{grid-{}: {} / span {};}} ".format(
                grid_class,
                "column" if grid_type == "c" else "row",
                int(grid_start)+1,
                grid_span
            )
        
        # Render the page
        return render_template("layout.html", config=app.config)


    # Serve static files and HTML pages
    @app.route('/<path:filename>')
    def serve_html(filename):
        # Absolute filepath of request
        filepath = os.path.join(static_dir, filename)

        # Load files with valid extensions
        if filename.endswith(file_extensions) and os.path.isfile(filepath):
            #app.logger.debug(f"Serving static file: {filename}")
            return send_from_directory(static_dir, filename)
        
        # Attempt to load filename as .html (so suffix isn't always required)
        elif os.path.isfile(filepath + ".html"):
            #app.logger.debug(f"Serving static file: {filename}.html")
            return send_from_directory(static_dir, filename + ".html")
        
        # 404 page not found
        else:
            #app.logger.warning(f"404 not found: {filename}")
            abort(404)


    # Debugging
    @app.route('/debug/api')
    def debug_api():
        return render_template("debug_api.html")
    @app.route('/debug/modules')
    def debug_modules():
        return render_template("debug_modules.html")

    return app
