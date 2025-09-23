#!/usr/bin/env python3
from flask import Flask, send_from_directory, abort, render_template
from os import path as os_path, scandir as os_scandir
from inspect import getmembers, isclass
import importlib.util
import sys

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
    '.css','.js',                   # CSS, JavaScript
    '.png','.jpg','.ico','.svg',    # Images
)

# Load rocket configs and assets from /rockets directory
ROCKETS = {}
def load_rockets():
    # Scan for rockets in rockets/ directory
    dir_rockets = os_path.join(os_path.dirname(__file__), "rockets")
    assert os_path.isdir(dir_rockets)

    # Find all rocket directories
    rocket_paths = [
        f.path for f in os_scandir(dir_rockets)
        if f.is_dir() and os_path.isfile(os_path.join(f.path, "__init__.py"))
    ]

    # Make sure default rocket exists
    assert len(rocket_paths) > 0
    assert "default" in [ path.split("/")[-1] for path in rocket_paths ]
    
    # Load rocket configurations
    for path in rocket_paths:

        # Import rocket package
        package_name = path.split("/")[-1]
        spec = importlib.util.spec_from_file_location(
            "rockets." + package_name, 
            os_path.join(path, "__init__.py")
        )
        rocket_package = importlib.util.module_from_spec(spec)
        sys.modules["rockets." + package_name] = rocket_package
        spec.loader.exec_module(rocket_package)

        # Keep track of rocket data
        ROCKETS[package_name] = {
            "path": path,
            "package": rocket_package,
            "configs": []
        }
        
        # Load all config classes from module
        for name, obj in getmembers(rocket_package, isclass):
            if name.startswith("Config") and obj.__module__ == rocket_package.__name__ \
            and (obj.__name__ == "Config" or obj.__bases__[0].__name__ == "Config"):
                # Instantiate and validate rocket config
                rocket_config = object.__new__(obj)
                rocket_config.MODULE = package_name
                validate_rocket_config(rocket_config)
                ROCKETS[package_name]["configs"].append(rocket_config)

        # Debug info
        print(f"Loaded 'rockets/{package_name}' with {len(ROCKETS[package_name]['configs'])} config(s):")
        for c in ROCKETS[package_name]['configs']:
            print(f"  {type(c).__name__}() \
                  \n   - Rocket: {c.ROCKET_NAME} \
                  \n   - Pages: {len(c.PAGES)} \
                  \n   - Modules: {len(c.MODULES)}")


# Validate rocket configurations
def validate_rocket_config(c):
    # Test that required variables are defined
    assert isinstance(c.ROCKET_NAME, str), "ROCKET_NAME not defined correctly"
    assert isinstance(c.MODULES, list), "MODULES not defined correctly"
    assert isinstance(c.PAGES, list), "PAGES not defined correctly"
    assert isinstance(c.MODULE_PAGES, dict), "MODULE_PAGES not defined correctly"

    # Test that MODULES exist
    for m in c.MODULES:
        assert os_path.exists(os_path.join(os_path.dirname(__file__), "rockets/" + m).strip())
    
    # Test PAGES formatting
    for page in c.PAGES:
        assert isinstance(page["name"], str)
        assert isinstance(page["icon"], str)
        assert isinstance(page["id"], str)

    # Test MODULE_PAGES formatting
    logos_count = 0
    radio_count = 0
    for key in c.MODULE_PAGES:
        # Test modules are defined properly
        assert key in [m.split("/")[-1].replace(".html","") for m in c.MODULES], "Module " + key + " in MODULE_PAGES not in MODULES"
        assert isinstance(c.MODULE_PAGES[key], list), "MODULE_PAGES must be a list"

        # Test position format
        for pos in c.MODULE_PAGES[key]:
            if pos not in ("radio", "logos"):
                assert isinstance(pos, tuple), "Module position must be a tuple"
                assert len(pos) == 5, "Module position tuple must be length 5"
                assert isinstance(pos[0], str)
                assert isinstance(pos[1], int)
                assert isinstance(pos[2], int)
                assert isinstance(pos[3], int)
                assert isinstance(pos[4], int)
                assert pos[1] >= 0 and pos[1] < 12, "Module x out of bounds"
                assert pos[2] >= 0 and pos[2] < 12, "Module y out of bounds"
                assert pos[3] > 0 and pos[3] <= 12, "Module width invalid"
                assert pos[4] > 0 and pos[4] <= 12, "Module height invalid"
                assert pos[1] + pos[3] <= 12, "Module width out of bounds"
                assert pos[2] + pos[4] <= 12, "Module height out of bounds"
                assert pos[0] in [n["id"] for n in c.PAGES], "Module page not found"
            elif pos == "logos":
                logos_count += 1
                assert logos_count <= 1, "More than one module in position 'logos'"
            elif pos == "radio":
                radio_count += 1
                assert radio_count <= 1, "More than one module in position 'radio'"


# Initialise flask app
def create_app():
    # Create flask app
    app = Flask(__name__)
    # app.config.from_object("frontend.config." + frontend.config.rocket + "Config")
    
    """
    Load static files and rocket configs
    """
    # Load static files
    DIR_STATIC = os_path.join(os_path.dirname(__file__), 'static')
    assert os_path.isdir(DIR_STATIC)

    # Load rockets
    load_rockets()
    app.config["rockets"] = ROCKETS
    # print(app.config["rockets"])

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

    """
    Static file loading
    """
    # Serve static files and HTML pages
    @app.route('/<path:filename>')
    def serve_html(filename):
        # Absolute filepath of request
        filepath = os_path.join(DIR_STATIC, filename)

        # Load files with valid extensions
        if filename.endswith(valid_file_extensions) and os_path.isfile(filepath):
            #app.logger.debug(f"Serving static file: {filename}")
            return send_from_directory(DIR_STATIC, filename)
        
        # Attempt to load filename as .html (so suffix isn't always required)
        elif os_path.isfile(filepath + ".html"):
            #app.logger.debug(f"Serving static file: {filename}.html")
            return send_from_directory(DIR_STATIC, filename + ".html")
        
        # 404 page not found
        else:
            #app.logger.warning(f"404 not found: {filename}")
            abort(404)

    """
    Debugging
    """
    # Debug rocket loading
    @app.route('/debug/rockets')
    def debug_rockets():
        return render_template("debug_rockets.html")
    
    # Debug modules
    # Shows all modules from loaded rockets
    @app.route('/debug/modules')
    def debug_modules():
        return render_template("debug_modules.html")

    return app
