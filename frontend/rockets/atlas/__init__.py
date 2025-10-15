"""
# ATLAS CONFIGURATION
# Extends default configuration with Atlas modules and layout
"""

from rockets.default import Config


class ConfigAtlas(Config):
    ROCKET_NAME = "Atlas"

    # Load Atlas modules
    MODULES = list(Config.MODULES)
    MODULES.extend(
        [
            "atlas/modules/atlas_avionics.html",
            "atlas/modules/atlas_indicators.html",
            "atlas/modules/atlas_logos.html",
            "atlas/modules/atlas_payload.html",
            "atlas/modules/atlas_position.html",
            "atlas/modules/atlas_rocket.html",
            "atlas/modules/atlas_timeline.html",
        ]
    )

    # Define pages for Atlas
    PAGES = [
        {"name": "Main Interface", "icon": "icon-rocket", "id": "page-main"},
    ]

    # Module positioning on each page
    MODULE_PAGES = {
        "atlas_avionics": [("page-main", 0, 0, 4, 7)],
        "atlas_indicators": [("page-main", 8, 0, 4, 2)],
        "atlas_logos": ["logos"],
        "atlas_payload": [("page-main", 8, 2, 4, 6)],
        "atlas_position": [("page-main", 0, 7, 4, 5)],
        "atlas_rocket": [("page-main", 4, 0, 4, 9)],
        "atlas_timeline": [("page-main", 4, 9, 4, 3)],
        "default_errorlog": [("page-main", 8, 8, 4, 4)],
        "default_radio": ["radio"],
    }
