"""
DEFAULT FRONTEND CONFIGURATION
"""

# DEFAULT CONFIGURATION
class DefaultConfig(object):
    ROCKET_NAME = ""
    
    # List of pages in the interface
    # These appear in the navbar at the top of the page
    # Page ID values are used for module layouts
    PAGES = [
        {
            "name": "Main Interface",
            "icon": "icon-rocket",
            "id": "page-main"
        },
    ]

    # The logos and radio modules are hard-coded
    # Since they sit outside the grid, at the top of the page
    MODULE_LOGOS = "modules/module_logos.html"
    MODULE_RADIO = "modules/module_radio.html"

    # Remaining modules are defined here
    # Module path is used, then an array of pages
    MODULES = {
        "modules/module_example.html": {
            "pages": [
                # These indicate where the module appears in each page
                # Encoding: [page id, x, y, width, height]
                ["page-main", 0, 0, 12, 12]
            ]
        }
    }