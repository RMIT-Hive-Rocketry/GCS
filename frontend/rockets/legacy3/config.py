from rockets.default.config import DefaultConfig


class LegacyConfig(DefaultConfig):
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