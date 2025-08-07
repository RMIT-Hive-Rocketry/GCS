"""
FRONTEND CONFIG

(use .flaskenv for runtime configuration)
"""
# SELECT CONFIG HERE
rocket = "Atlas" # Options: "", "Atlas", "Legacy"


# DEFAULT CONFIGURATION
class Config(object):
    ROCKET_NAME = ""
    PAGES = [
        {
            "name": "Main Interface",
            "icon": "icon-rocket",
            "id": "m-main"
        },
        {
            "name": "Single Operator",
            "icon": "icon-gamepad",
            "id": "m-ops"
        },
        {
            "name": "GSE State",
            "icon": "icon-sitemap",
            "id": "m-hmi"
        }
    ]
    MODULE_LOGOS = "modules/module_logos.html"
    MODULE_RADIO = "modules/module_radio.html"


# ROCKET SPECIFIC CONFIGURATIONS

# Atlas
# Used for AURC 2025
class AtlasConfig(Config):
    ROCKET_NAME = "Atlas"
    PAGES = [
        {
            "name": "Main Interface",
            "icon": "icon-rocket",
            "id": "m-main"
        },
    ]
    MODULE_LOGOS = "modules/atlas_logos.html"
    MODULES = []


# Legacy III
# Used for IREC 2025
class LegacyConfig(Config):
    ROCKET_NAME = "Legacy III"
    PAGES = [
        {
            "name": "Main Interface",
            "icon": "icon-rocket",
            "id": "m-main"
        },
        {
            "name": "Launchpad",
            "icon": "icon-video-camera",
            "id": "m-lf2"
        },
        {
            "name": "Rocket",
            "icon": "icon-video-camera",
            "id": "m-lf1"
        },
        {
            "name": "Both feeds",
            "icon": "icon-video-camera",
            "id": "m-lf3"
        },
        {
            "name": "Single Operator",
            "icon": "icon-gamepad",
            "id": "m-ops"
        },
        {
            "name": "GSE State",
            "icon": "icon-sitemap",
            "id": "m-hmi"
        }
    ]
    MODULE_LOGOS = "modules/legacy3_logos.html"
