"""
BASE CONFIGURATION
Inherited by all rockets
Defines default modules, pages, and layout
"""


# DEFAULT ROCKET CONFIGURATION
class Config(object):
    def __init__(self):
        self.ROCKET_NAME = "Default"

        # List of modules used by the rocket
        # PATH = "default/modules/"
        self.MODULES = [
            "default/modules/default_avionics.html",
            "default/modules/default_camera.html",
            "default/modules/default_errorlog.html",
            "default/modules/default_example.html",
            "default/modules/default_gse.html",
            "default/modules/default_logos.html",
            "default/modules/default_position.html",
            "default/modules/default_radio.html",
            "default/modules/default_timeline.html",
        ]

        # List of pages in the interface
        # These appear in the navbar at the top of the page
        # Page ID values are used for module layouts
        self.PAGES = [
            {"name": "Main Interface", "icon": "icon-rocket", "id": "page-main"},
        ]

        # Module positioning on each page
        # Format: { module_name: [ (page_id, x, y, width, height), ... ] }
        # Can also be "logos" or "radio" to place in fixed positions
        self.MODULE_PAGES = {
            "default_example": [
                # Take up entire 12x12 grid on main page
                ("page-main", 0, 0, 12, 12)
            ],
            "default_logos": [
                # Logos position (top left)
                "logos"
            ],
            "default_radio": [
                # Radio position (top right)
                "radio"
            ],
        }

        self.MODULE_CLASSES = {}
        self.MODULE_RADIO = ""
        self.MODULE_LOGOS = ""

    ## Methods
    def print_modules(this):
        for module in this.MODULES:
            print(module)
