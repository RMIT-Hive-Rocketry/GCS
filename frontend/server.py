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

    # Serve main layout
    @app.route('/')
    def index():
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
