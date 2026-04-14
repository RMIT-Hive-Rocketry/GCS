"""
# HORIZON CONFIGURATION
# Testing new layouts for Horizon
"""

from rockets.default import Config


class ConfigHorizon(Config):
    def __init__(self):
        super().__init__()

        self.ROCKET_NAME = "Horizon"
        self.LOGO = "horizon/static/img/logo-horizon-gradient.png"
        self.STYLESHEETS = ["horizon/static/css/horizon.css"]
        self.GRID = (24, 12)

        # Load Horizon modules
        self.MODULES = [
            "horizon/modules/horizon_logos.html",
            "horizon/modules/horizon_nav.html",
            "horizon/modules/horizon_overview.html",
            "horizon/modules/horizon_radio.html",
            "horizon/modules/horizon_sounds.html",
        ]

        # Define pages for Horizon
        self.PAGES = [
            {"name": "Overview", "icon": "icon-rocket", "id": "page-main"},
            {
                "name": "Pre-flight",
                "icon": "icon-tasks",
                "id": "page-preflight",
            },
            {"name": "Control", "icon": "icon-gamepad", "id": "page-control"},
        ]

        # Module positioning on each page
        self.MODULE_PAGES = {
            "horizon_logos": [
                ("page-main", 0, 0, 6, 1),
                ("page-preflight", 0, 0, 6, 1),
                ("page-control", 0, 0, 6, 1),
            ],
            "horizon_radio": [
                ("page-main", 12, 0, 12, 1),
                ("page-preflight", 12, 0, 12, 1),
                ("page-control", 12, 0, 12, 1),
            ],
            "horizon_nav": [
                ("page-main", 0, 11, 24, 1),
                ("page-preflight", 0, 11, 24, 1),
                ("page-control", 0, 11, 24, 1),
            ],
            "horizon_overview": [("page-main", 0, 1, 24, 10)],
            "horizon_sounds": [
                ("page-main", 6, 0, 6, 1),
                ("page-preflight", 6, 0, 6, 1),
                ("page-control", 6, 0, 6, 1),
            ],
        }
