"""
FRONTEND CONFIG

Use .flaskenv for runtime configuration
Change FrontendConfig variable to use that config
"""


# Select rocket here
# Options: "", "Atlas", "Legacy"
rocket = "Atlas"


# Default configuration
class Config(object):
    ROCKET_NAME = ""
    PAGES = [
        {
            "name": "Main Interface",
            "icon": "icon-rocket",
            "id": "m-main"
        },
        {
            "name": "Live - Launchpad",
            "icon": "icon-video-camera",
            "id": "m-lf2"
        },
        {
            "name": "Live - Rocket",
            "icon": "icon-video-camera",
            "id": "m-lf1"
        },
        {
            "name": "Live - All Feeds",
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
    MODULE_LOGOS = "modules/module_logos.html"
    MODULE_RADIO = "modules/module_radio.html"


# Rocket specific configurations
class AtlasConfig(Config):
    ROCKET_NAME = "Atlas"
    PAGES = [
        {
            "name": "Main Interface",
            "icon": "icon-rocket",
            "id": "m-main"
        },
        {
            "name": "Live - Launchpad",
            "icon": "icon-video-camera",
            "id": "m-lf2"
        },
        {
            "name": "Live - Rocket",
            "icon": "icon-video-camera",
            "id": "m-lf1"
        },
        {
            "name": "Live - All Feeds",
            "icon": "icon-video-camera",
            "id": "m-lf3"
        },
    ]
    MODULE_LOGOS = "modules/atlas_logos.html"
    MODULES = []


class LegacyConfig(Config):
    ROCKET_NAME = "Legacy III"
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
    MODULE_LOGOS = "modules/legacy3_logos.html"
