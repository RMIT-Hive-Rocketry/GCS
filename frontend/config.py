"""
FRONTEND CONFIG

(use .flaskenv for runtime configuration)
"""

# SELECT CONFIG HERE
rocket = "Atlas" # Options: "", "Atlas", "Legacy"





# ROCKET SPECIFIC CONFIGURATIONS

# Legacy III
# Launched at IREC 2025


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