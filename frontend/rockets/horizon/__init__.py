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
        self.STYLESHEETS = []
        self.GRID = (24, 12)

        # Load Horizon modules
        self.MODULES = ["horizon/modules/horizon_logos.html"]

        # Define pages for Horizon
        self.PAGES = [
            {"name": "Main Interface", "icon": "icon-rocket", "id": "page-main"},
        ]

        # Module positioning on each page
        self.MODULE_PAGES = {}
