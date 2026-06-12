# Functions for loading and validating rocket files from /frontend/rockets
from flask import Blueprint
from os import path as os_path, scandir as os_scandir
from inspect import getmembers, isclass
import importlib.util
import sys


class Rocket:
    flask_app = None

    def __init__(self):
        # Rocket package
        self.path = None
        self.name = None
        self.package = None

        # Flask parameters
        self.flask_app = None
        self.blueprint = None

        # Layout configurations
        self.configs = []

    def set_flask_app(self, _flask_app) -> None:
        self.flask_app = _flask_app

    def load_from_module(self, _module) -> None:
        # Import rocket as a python package
        package_name = _module.split("/")[-1]
        spec = importlib.util.spec_from_file_location(
            "rockets." + package_name, os_path.join(_module, "__init__.py")
        )
        rocket_package = importlib.util.module_from_spec(spec)
        sys.modules["rockets." + package_name] = rocket_package
        spec.loader.exec_module(rocket_package)

        self.path = _module
        self.name = package_name
        self.package = rocket_package

        # Load different configurations from package
        self.load_configs()

        # Generate layouts
        self.generate_config_layouts()

    def load_configs(self) -> None:
        # Load all config classes from module
        for name, obj in getmembers(self.package, isclass):
            if (
                name.startswith("Config")
                and obj.__module__ == self.package.__name__
                and (
                    obj.__name__ == "Config"
                    or obj.__bases__[0].__name__ == "Config"
                )
            ):
                # Instantiate and validate rocket config
                rocket_config = obj()  # object.__new__(obj)
                rocket_config.MODULE = self.name

                # Validate config then append to configs list
                self.validate_config(rocket_config)
                self.configs.append(rocket_config)

        # Print loaded configs
        self.print_rocket_configs()

    def validate_config(self, _config) -> None:
        # Validate rocket configuration
        grid_tuple_len = 2
        grid_size_range = (1, 64)
        position_tuple_len = 5

        # Test that required variables are defined
        assert isinstance(
            _config.ROCKET_NAME, str
        ), "ROCKET_NAME not defined correctly"
        assert isinstance(_config.GRID, tuple), "GRID not defined correctly"
        assert isinstance(
            _config.MODULES, list
        ), "MODULES not defined correctly"
        assert isinstance(_config.PAGES, list), "PAGES not defined correctly"
        assert isinstance(
            _config.MODULE_PAGES, dict
        ), "MODULE_PAGES not defined correctly"

        # Test that GRID is a valid size
        assert (
            len(_config.GRID) == grid_tuple_len
        ), "GRID must be a tuple containing two values"
        assert (
            _config.GRID[0] >= grid_size_range[0]
            and _config.GRID[0] <= grid_size_range[1]
        ), "GRID must have between 1 and 64 columns (inclusive)"
        assert (
            _config.GRID[1] >= grid_size_range[0]
            and _config.GRID[1] <= grid_size_range[1]
        ), "GRID must have between 1 and 64 rows (inclusive)"

        # Test that MODULES exist
        for m in _config.MODULES:
            assert os_path.exists(
                os_path.join(os_path.dirname(__file__), "rockets/" + m).strip()
            )

        # Test PAGES formatting
        for page in _config.PAGES:
            assert isinstance(page["name"], str)
            assert isinstance(page["icon"], str)
            assert isinstance(page["id"], str)

        # Test MODULE_PAGES formatting
        for key in _config.MODULE_PAGES:
            # Test modules are defined properly
            assert key in [
                m.split("/")[-1].replace(".html", "") for m in _config.MODULES
            ], ("Module " + key + " in MODULE_PAGES not in MODULES")
            assert isinstance(
                _config.MODULE_PAGES[key], list
            ), "MODULE_PAGES must be a list"

            # Test position format
            for pos in _config.MODULE_PAGES[key]:
                assert isinstance(pos, tuple), "Module position must be a tuple"
                assert (
                    len(pos) == position_tuple_len
                ), "Module position tuple must be length 5"
                assert isinstance(pos[0], str)
                assert isinstance(pos[1], int)
                assert isinstance(pos[2], int)
                assert isinstance(pos[3], int)
                assert isinstance(pos[4], int)
                assert (
                    pos[1] >= 0 and pos[1] < _config.GRID[0]
                ), "Module x out of bounds"
                assert (
                    pos[2] >= 0 and pos[2] < _config.GRID[1]
                ), "Module y out of bounds"
                assert (
                    pos[3] > 0 and pos[3] <= _config.GRID[0]
                ), "Module width invalid"
                assert (
                    pos[4] > 0 and pos[4] <= _config.GRID[1]
                ), "Module height invalid"
                assert (
                    pos[1] + pos[3] <= _config.GRID[0]
                ), "Module width out of bounds"
                assert (
                    pos[2] + pos[4] <= _config.GRID[1]
                ), "Module height out of bounds"
                assert pos[0] in [
                    n["id"] for n in _config.PAGES
                ], "Module page not found"

    def print_rocket_configs(self) -> None:
        # Print out loaded rocket information from configs
        print(
            f"Loaded 'rockets/{self.name}' with {len(self.configs)} config(s):"
        )
        for c in self.configs:
            self.print_config(c)

    def print_config(self, _config) -> None:
        # Print a single configuration
        print(
            f"  {type(_config).__name__}() \
                \n   - Rocket: {_config.ROCKET_NAME} \
                \n   - Grid: ({_config.GRID[0]}, {_config.GRID[1]}) \
                \n   - Pages: {len(_config.PAGES)} \
                \n   - Modules: {len(_config.MODULES)}"
        )

    def generate_blueprint(self) -> None:
        # Generate a flask blueprint for loading assets
        self.blueprint = Blueprint(
            self.name,
            self.package.__name__,
            url_prefix=f"/{self.name}",
            template_folder="modules",
            static_folder="static",
            static_url_path=f"/{self.name}/static",
        )
        # Register blueprint with flask
        self.flask_app.register_blueprint(self.blueprint)

    def generate_config_layouts(self) -> None:
        # Parse config and pre-generate modular layout information for CSS
        for config in self.configs:
            # Generate CSS selectors for pages
            config.CSS = (
                ", ".join(
                    ["#{0} .{0}".format(page["id"]) for page in config.PAGES]
                )
                + " {display: flex;}"
            )

            # Dynamically allocate grid size
            config.CSS += f"\n.grid-cols-{config.GRID[0]} {{grid-template-columns: repeat({config.GRID[0]}, minmax(0, 1fr));}}"
            config.CSS += f"\n.grid-rows-{config.GRID[1]} {{grid-template-rows: repeat({config.GRID[1]}, minmax(0, 1fr));}}"

            # For each module, check pages and positioning to generate CSS classes
            grid = set()
            for module in config.MODULES:
                module_id = module.split("/")[-1].split(".")[0]

                # Modules are hidden by default
                class_list = {"module", "hidden"}

                # For each module, update visibility and position for each page
                if module_id in config.MODULE_PAGES:
                    for page in config.MODULE_PAGES[module_id]:
                        if isinstance(page, tuple):
                            # Encode position and size in grid
                            cols = f"{page[0]}-c-{page[1]}-{page[3]}"
                            rows = f"{page[0]}-r-{page[2]}-{page[4]}"

                            # Add classes to grid
                            grid.add(f"#{page[0]} .{cols}")
                            grid.add(f"#{page[0]} .{rows}")

                            # Add classes to module
                            class_list.add(page[0])
                            class_list.add(cols)
                            class_list.add(rows)

                # Assign generated classes to module
                config.MODULE_CLASSES[module_id] = " ".join(class_list)

            # Add optimised grid to CSS
            for grid_class in grid:
                grid_type, grid_start, grid_span = grid_class.split("-")[-3:]
                config.CSS += "\n{} {{grid-{}: {} / span {};}} ".format(
                    grid_class,
                    "column" if grid_type == "c" else "row",
                    int(grid_start) + 1,
                    grid_span,
                )

            # Wrap CSS
            config.CSS = f"<style>{config.CSS}</style>"


def load_rockets(flask_app) -> list:
    # Load the frontend directory
    frontend_dir = os_path.dirname(__file__)
    if frontend_dir not in sys.path:
        sys.path.insert(0, frontend_dir)

    # Loads all rockets in the /rockets directory
    rockets = []

    # Get /rockets directory
    rockets_dir = os_path.join(os_path.dirname(__file__), "rockets")
    assert os_path.isdir(rockets_dir)

    # Find and load rocket modules in directory
    for module in get_rocket_modules(rockets_dir):
        # Load rockets and generate blueprints
        rocket = Rocket()
        rocket.set_flask_app(flask_app)
        rocket.load_from_module(module)
        rocket.generate_blueprint()

        # Append loaded rocket to list
        rockets.append(rocket)

    # Return array of loaded rockets
    return rockets


def get_rocket_modules(_dir) -> list:
    # Find all rocket modules in directory
    rocket_modules = [
        f.path
        for f in os_scandir(_dir)
        if f.is_dir() and os_path.isfile(os_path.join(f.path, "__init__.py"))
    ]

    # Check that default rocket exists (since other rockets extend it)
    assert len(rocket_modules) > 0
    assert "default" in [path.split("/")[-1] for path in rocket_modules]

    # Return rocket modules
    return rocket_modules
