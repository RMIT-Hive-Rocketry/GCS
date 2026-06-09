"""
# HORIZON CONFIGURATION
"""

from rockets.default import Config


class ConfigHorizon(Config):
    def __init__(self):
        super().__init__()

        self.ROCKET_NAME: str = "Horizon"
        self.LOGO: str = "horizon/static/img/logo-horizon-gradient.png"
        self.STYLESHEETS: list = ["horizon/static/css/horizon.css"]
        self.GRID: tuple = (24, 12)

        # Load Horizon modules
        self.MODULES: list = [
            # Header / nav (including sounds)
            "horizon/modules/horizon_logos.html",
            "horizon/modules/horizon_nav.html",
            "horizon/modules/horizon_radio.html",
            # Main page modules (mirrors Legacy III's main page for now)
            "horizon/modules/horizon_avionics.html",
            "horizon/modules/horizon_position.html",
            "horizon/modules/horizon_avionics_position.html",
            "horizon/modules/horizon_auxiliary_gse.html",
            "horizon/modules/horizon_errorlog.html",
            "horizon/modules/horizon_rocket.html",
            "horizon/modules/horizon_timeline.html",
            # HMI modules
            "horizon/modules/horizon_pendant.html",
            "horizon/modules/horizon_gse_hmi.html",
            # Diagnostics modules
            "horizon/modules/horizon_diagnostics_packets.html",
            "horizon/modules/horizon_diagnostics_graphs.html",
            "horizon/modules/horizon_diagnostics_summary.html",
            # "horizon/modules/horizon_diagnostics_bottom.html",
            # Settings page
            "horizon/modules/horizon_settings_audio.html",
            "horizon/modules/horizon_settings_graph_colours.html",
        ]

        # Define pages for Horizon
        self.PAGES: list = [
            {"name": "Overview", "icon": "icon-rocket", "id": "page-main"},
            {"name": "Pre-flight", "icon": "icon-gamepad", "id": "page-control"},
            {"name": "Diagnostics", "icon": "icon-signal", "id": "page-diagnostics"},
            {"name": "Settings", "icon": "icon-tasks", "id": "page-preflight"},
        ]

        # Module positioning on each page
        # Header row (y=0): logos 0-7, nav 8-15, radio 16-23.
        # Overview content area is now 24 cols x 11 rows (y = 1..11).
        self.MODULE_PAGES: dict = {
            # Header / nav (including sounds)
            "horizon_logos": [
                ("page-main", 0, 0, 8, 1),
                ("page-preflight", 0, 0, 8, 1),
                ("page-control", 0, 0, 8, 1),
            ],
            "horizon_nav": [
                ("page-main", 8, 0, 8, 1),
                ("page-preflight", 8, 0, 8, 1),
                ("page-control", 8, 0, 8, 1),
            ],
            "horizon_radio": [
                ("page-main", 16, 0, 8, 1),
                ("page-preflight", 16, 0, 8, 1),
                ("page-control", 16, 0, 8, 1),
            ],
            # Main page modules (mirrors Legacy III's main page for now)
            "horizon_avionics_position": [("page-main", 0, 1, 8, 11)],
            "horizon_rocket": [("page-main", 8, 1, 8, 8)],
            "horizon_timeline": [("page-main", 8, 9, 8, 3)],
            "horizon_errorlog": [("page-main", 16, 1, 8, 3)],
            "horizon_auxiliary_gse": [("page-main", 16, 4, 8, 8)],
            # Settings page
            "horizon_settings_audio": [("page-preflight", 0, 1, 12, 11)],
            "horizon_settings_graph_colours": [
                ("page-preflight", 12, 1, 12, 11)
            ],
            # Control page: GSE HMI on the left (14 cols), pendant on the right (10 cols)
            "horizon_gse_hmi": [("page-control", 0, 1, 14, 11)],
            "horizon_pendant": [("page-control", 14, 1, 10, 11)],
            # Diagnostics modules
            # Content area: rows 1-10 (10 rows tall)
            # Bottom bar:   row 11  (1 row tall, full width)
            "horizon_diagnostics_packets": [("page-diagnostics", 0, 1, 5, 11)],
            "horizon_diagnostics_graphs": [("page-diagnostics", 5, 1, 15, 11)],
            "horizon_diagnostics_summary": [("page-diagnostics", 20, 1, 4, 11)],
        }
