"""
FRONTEND CONFIG

(use .flaskenv for runtime configuration)
"""

# SELECT CONFIG HERE
rocket = "Legacy"  # Options: "", "Atlas", "Legacy"


# DEFAULT CONFIGURATION
class Config(object):
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


# ROCKET SPECIFIC CONFIGURATIONS

# Legacy III
# Launched at IREC 2025
class LegacyConfig(Config):
    ROCKET_NAME = "Legacy III"
    PAGES = [
        {
            "name": "Main Interface",
            "icon": "icon-rocket",
            "id": "page-main"
        },
        {
            "name": "Launchpad",
            "icon": "icon-video-camera",
            "id": "page-live-launchpad"
        },
        {
            "name": "Rocket",
            "icon": "icon-video-camera",
            "id": "page-live-rocket"
        },
        {
            "name": "Both feeds",
            "icon": "icon-video-camera",
            "id": "page-live-all"
        },
        {
            "name": "Single Operator",
            "icon": "icon-gamepad",
            "id": "page-ops"
        },
        {
            "name": "GSE State",
            "icon": "icon-sitemap",
            "id": "page-hmi"
        }
    ]
    MODULE_LOGOS = "modules/legacy3_logos.html"
    MODULES = {
        "modules/legacy3_auxiliary_gse.html": {
            "pages": [
                ["page-main", 8, 4, 4, 8],
                ["page-live-launchpad", 8, 4, 4, 8]
            ]
        },
        "modules/legacy3_avionics_position.html": {
            "pages": [
                ["page-main", 0, 0, 4, 12],
                ["page-live-rocket", 0, 0, 4, 12]
            ]
        },
        "modules/legacy3_hmi.html": {
            "pages": [
                ["page-hmi", 0, 0, 12, 12]
            ]
        },
        "modules/legacy3_live_launchpad.html": {
            "pages": [
                ["page-live-launchpad", 0, 0, 8, 9],
                ["page-live-all", 0, 0, 6, 8]
            ]
        },
        "modules/legacy3_live_rocket.html": {
            "pages": [
                ["page-live-rocket", 4, 0, 8, 9],
                ["page-live-all", 6, 0, 6, 8]
            ]
        },
        "modules/legacy3_ops_auxcontrols.html": {
            "pages": [
                ["page-ops", 4, 6, 4, 6]
            ]
        },
        "modules/legacy3_ops_continuitycheck.html": {
            "pages": [
                ["page-ops", 0, 0, 4, 6]
            ]
        },
        "modules/legacy3_ops_poptest.html": {
            "pages": [
                ["page-ops", 0, 6, 4, 6]
            ]
        },
        "modules/legacy3_ops_systemflags.html": {
            "pages": [
                ["page-ops", 8, 0, 4, 12]
            ]
        },
        "modules/legacy3_rocket.html": {
            "pages": [
                ["page-main", 4, 0, 4, 9]
            ]
        },
        "modules/legacy3_timeline.html": {
            "pages": [
                ["page-main", 4, 9, 4, 3],
                ["page-live-launchpad", 0, 9, 8, 3],
                ["page-live-rocket", 4, 9, 8, 3],
                ["page-live-all", 2, 8, 8, 4]
            ]
        },
        "modules/module_errorlog.html": {
            "pages": [
                ["page-main", 8, 0, 4, 4],
                ["page-live-launchpad", 8, 0, 4, 4]
            ]
        }
    }

# Atlas
# Launched at AURC 2025


class AtlasConfig(Config):
    ROCKET_NAME = "Atlas"
    PAGES = [
        {
            "name": "Main Interface",
            "icon": "icon-rocket",
            "id": "page-main"
        },
    ]
    MODULE_LOGOS = "modules/atlas_logos.html"
    MODULES = {
        "modules/atlas_avionics.html": {
            "pages": [
                ["page-main", 0, 0, 4, 7]
            ]
        },
        "modules/atlas_indicators.html": {
            "pages": [
                ["page-main", 8, 0, 4, 2]
            ]
        },
        "modules/atlas_position.html": {
            "pages": [
                ["page-main", 0, 7, 4, 5]
            ]
        },
        "modules/atlas_payload.html": {
            "pages": [
                ["page-main", 8, 2, 4, 6]
            ]
        },
        "modules/atlas_rocket.html": {
            "pages": [
                ["page-main", 4, 0, 4, 9]
            ]
        },
        "modules/atlas_timeline.html": {
            "pages": [
                ["page-main", 4, 9, 4, 3]
            ]
        },
        "modules/module_errorlog.html": {
            "pages": [
                ["page-main", 8, 8, 4, 4]
            ]
        },
    }
