"""
# HORIZON CONFIGURATION
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
            # Header / nav
            "horizon/modules/horizon_logos.html",
            "horizon/modules/horizon_nav.html",
            "horizon/modules/horizon_radio.html",
            # Overview page modules (mirrors Legacy III's main page for now)
            "horizon/modules/horizon_avionics.html",
            "horizon/modules/horizon_position.html",
            "horizon/modules/horizon_avionics_position.html",
            "horizon/modules/horizon_auxiliary_gse.html",
            "horizon/modules/horizon_errorlog.html",
            "horizon/modules/horizon_rocket.html",
            "horizon/modules/horizon_timeline.html",
        ]

        # Define pages for Horizon
        self.PAGES = [
            {"name": "Overview", "icon": "icon-rocket", "id": "page-main"},
            {"name": "Pre-flight", "icon": "icon-tasks", "id": "page-preflight"},
            {"name": "Control", "icon": "icon-gamepad", "id": "page-control"},
        ]

        # Module positioning on each page
        # Overview content area is 24 cols x 10 rows (y = 1..10), giving
        # us three 8-wide columns to mirror Legacy's three 4-wide columns.
        self.MODULE_PAGES = {
            "horizon_logos": [
                ("page-main", 0, 0, 12, 1),
                ("page-preflight", 0, 0, 12, 1),
                ("page-control", 0, 0, 12, 1),
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
            "horizon_avionics_position": [("page-main", 0, 1, 8, 10)],
            "horizon_rocket": [("page-main", 8, 1, 8, 7)],
            "horizon_timeline": [("page-main", 8, 8, 8, 3)],
            "horizon_errorlog": [("page-main", 16, 1, 8, 3)],
            "horizon_auxiliary_gse": [("page-main", 16, 4, 8, 7)],
        }
