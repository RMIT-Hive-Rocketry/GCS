"""
# ATLAS CONFIGURATION
# Extends default configuration with Atlas modules and layout
"""

from rockets.default import Config


class ConfigAtlas(Config):
    def __init__(self):
        super().__init__()

        self.ROCKET_NAME = "Atlas"
        self.LOGO = "atlas/static/img/atlas-name.png"
        self.STYLESHEETS.extend(["atlas/static/css/atlas.css"])
        self.GRID = (12, 13)

        # Load Atlas modules
        self.MODULES.extend(
            [
                "atlas/modules/atlas_avionics.html",
                "atlas/modules/atlas_header.html",
                "atlas/modules/atlas_indicators.html",
                "atlas/modules/atlas_payload.html",
                "atlas/modules/atlas_position.html",
                "atlas/modules/atlas_rocket.html",
                "atlas/modules/atlas_timeline.html",
            ]
        )

        # Define pages for Atlas
        self.PAGES = [
            {"name": "Main Interface", "icon": "icon-rocket", "id": "page-main"},
        ]

        # Module positioning on each page
        self.MODULE_PAGES = {
            "atlas_avionics": [("page-main", 0, 1, 4, 7)],
            "atlas_header": [("page-main", 0, 0, 12, 1)],
            "atlas_indicators": [("page-main", 8, 1, 4, 2)],
            "atlas_payload": [("page-main", 8, 3, 4, 6)],
            "atlas_position": [("page-main", 0, 8, 4, 5)],
            "atlas_rocket": [("page-main", 4, 1, 4, 9)],
            "atlas_timeline": [("page-main", 4, 10, 4, 3)],
            "default_errorlog": [("page-main", 8, 9, 4, 4)],
            "default_radio": ["radio"],
        }
