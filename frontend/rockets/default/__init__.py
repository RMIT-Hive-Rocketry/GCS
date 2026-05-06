"""
BASE CONFIGURATION
Inherited by all rockets
Defines default modules, pages, and layout
"""


# DEFAULT ROCKET CONFIGURATION
class Config:
    def __init__(self):
        self.ROCKET_NAME = "ROCKET SELECTOR"
        self.LOGO = ""
        self.GRID = (1, 1)

        # List of modules used by the rocket
        # PATH = "default/modules/"
        self.MODULES = [
            "default/modules/rocket_selector.html",
        ]

        # List of pages in the interface
        # These appear in the navbar at the top of the page
        # Page ID values are used for module layouts
        self.PAGES = [
            {
                "name": "Main Interface",
                "icon": "icon-rocket",
                "id": "page-main",
            },
        ]

        # Module positioning on each page
        # Format: { module_name: [ (page_id, x, y, width, height), ... ] }
        # Can also be "logos" or "radio" to place in fixed positions
        self.MODULE_PAGES = {
            "rocket_selector": [
                # Take up entire page
                ("page-main", 0, 0, 1, 1)
            ],
        }

        self.MODULE_CLASSES = {}

    ## Methods
    def print_modules(this):
        for module in this.MODULES:
            print(module)
