"""
# LEGACY III CONFIGURATION
"""

from rockets.default import Config


class ConfigLegacy3(Config):
    def __init__(self):
        super().__init__()

        self.ROCKET_NAME = "Legacy III"
        self.LOGO = "legacy/static/img/logo-legacy3.svg"
        self.STYLESHEETS.extend(["legacy/static/css/legacy3.css"])
        self.GRID = (12,13)

        # Inherit default modules and add legacy ones
        self.MODULES.extend(
            [
                "legacy/modules/legacy3_auxiliary_gse.html",
                "legacy/modules/legacy3_avionics_position.html",
                "legacy/modules/legacy3_avionics.html",
                "legacy/modules/legacy3_header.html",
                "legacy/modules/legacy3_hmi.html",
                "legacy/modules/legacy3_live_launchpad.html",
                "legacy/modules/legacy3_live_rocket.html",
                "legacy/modules/legacy3_logos.html",
                "legacy/modules/legacy3_ops_auxcontrols.html",
                "legacy/modules/legacy3_ops_continuitycheck.html",
                "legacy/modules/legacy3_ops_poptest.html",
                "legacy/modules/legacy3_ops_systemflags.html",
                "legacy/modules/legacy3_position.html",
                "legacy/modules/legacy3_rocket.html",
                "legacy/modules/legacy3_timeline.html",
            ]
        )

        # Define pages for Legacy III
        self.PAGES = [
            {"name": "Main Interface", "icon": "icon-rocket", "id": "page-main"},
            {
                "name": "Launchpad",
                "icon": "icon-video-camera",
                "id": "page-live-launchpad",
            },
            {"name": "Rocket", "icon": "icon-video-camera", "id": "page-live-rocket"},
            {"name": "Both feeds", "icon": "icon-video-camera", "id": "page-live-all"},
            {"name": "Single Operator", "icon": "icon-gamepad", "id": "page-ops"},
            {"name": "GSE State", "icon": "icon-sitemap", "id": "page-hmi"},
        ]

        # Define module placements on each page
        self.MODULE_PAGES = {
            "legacy3_auxiliary_gse": [
                ("page-main", 8, 5, 4, 8),
                ("page-live-launchpad", 8, 5, 4, 8),
            ],
            "legacy3_avionics_position": [
                ("page-main", 0, 1, 4, 12),
                ("page-live-rocket", 0, 1, 4, 12),
            ],
            "legacy3_header": [
                ("page-main", 0, 0, 12, 1),
                ("page-live-launchpad", 0, 0, 12, 1),
                ("page-live-rocket", 0, 0, 12, 1),
                ("page-live-all", 0, 0, 12, 1),
                ("page-ops", 0, 0, 12, 1),
                ("page-hmi", 0, 0, 12, 1),
            ],
            "legacy3_hmi": [("page-hmi", 0, 1, 12, 12)],
            "legacy3_live_launchpad": [
                ("page-live-launchpad", 0, 1, 8, 9),
                ("page-live-all", 0, 1, 6, 8),
            ],
            "legacy3_live_rocket": [
                ("page-live-rocket", 4, 1, 8, 9),
                ("page-live-all", 6, 1, 6, 8),
            ],
            "legacy3_logos": ["logos"],
            "legacy3_ops_auxcontrols": [("page-ops", 4, 7, 4, 6)],
            "legacy3_ops_continuitycheck": [("page-ops", 0, 1, 4, 6)],
            "legacy3_ops_poptest": [("page-ops", 0, 7, 4, 6)],
            "legacy3_ops_systemflags": [("page-ops", 8, 1, 4, 12)],
            "legacy3_rocket": [("page-main", 4, 1, 4, 9)],
            "legacy3_timeline": [
                ("page-main", 4, 10, 4, 3),
                ("page-live-launchpad", 0, 10, 8, 3),
                ("page-live-rocket", 4, 10, 8, 3),
                ("page-live-all", 2, 9, 8, 4),
            ],
            "default_errorlog": [
                ("page-main", 8, 1, 4, 4),
                ("page-live-launchpad", 8, 1, 4, 4),
            ],
            "default_radio": ["radio"],
        }
