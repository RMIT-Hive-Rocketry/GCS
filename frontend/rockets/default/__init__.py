"""
BASE CONFIGURATION
Inherited by all rockets
Defines default modules, pages, and layout
"""


# DEFAULT ROCKET CONFIGURATION
class Config:
    def __init__(self) -> None:
        self.ROCKET_NAME: str = "ROCKET SELECTOR"
        self.LOGO: str = ""
        self.STYLESHEETS: list = []
        self.GRID: tuple = (1, 1)

        # List of modules used by the rocket
        # PATH = "default/modules/"
        self.MODULES: list = [
            "default/modules/rocket_selector.html",
        ]

        # List of pages in the interface
        # These appear in the navbar at the top of the page
        # Page ID values are used for module layouts
        self.PAGES: list = [
            {
                "name": "Main Interface",
                "icon": "icon-rocket",
                "id": "page-main",
            },
        ]

        # Module positioning on each page
        # Format: { module_name: [ (page_id, x, y, width, height), ... ] }
        # Can also be "logos" or "radio" to place in fixed positions
        self.MODULE_PAGES: dict = {
            "rocket_selector": [
                # Take up entire page
                ("page-main", 0, 0, 1, 1)
            ],
        }

        self.MODULE_CLASSES: dict = {}

    @staticmethod
    def print_modules() -> None:
        for module in Config.MODULES:
            print(module)
