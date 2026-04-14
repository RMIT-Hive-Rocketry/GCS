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
            "horizon/modules/horizon_sounds.html",
        ]

        # Define pages for Horizon
        self.PAGES = [
            {"name": "Overview", "icon": "icon-rocket", "id": "page-main"},
            {"name": "Pre-flight", "icon": "icon-tasks", "id": "page-preflight"},
            {"name": "Control", "icon": "icon-gamepad", "id": "page-control"},
            {"name": "Diagnostics", "icon": "icon-signal", "id": "page-diagnostics"},
        ]

        # Module positioning on each page
        # Header row (y=0): logos 0-7, nav 8-15, radio 16-23.
        # Overview content area is now 24 cols x 11 rows (y = 1..11).
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
                ("page-main", 8, 0, 8, 1),
                ("page-preflight", 8, 0, 8, 1),
                ("page-control", 8, 0, 8, 1),
                ("page-diagnostics", 8, 0, 8, 1),
            ],
            "horizon_overview": [("page-main", 0, 1, 24, 10)],
            "horizon_sounds": [
                ("page-main", 6, 0, 6, 1),
                ("page-preflight", 6, 0, 6, 1),
                ("page-control", 6, 0, 6, 1),
            ],
        }
