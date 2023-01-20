# flake8: noqa
from django.apps import AppConfig


class DashboardsConfig(AppConfig):
    name = "dashboards"
    verbose_name = "Visualisation Dashboards"

    def ready(self):
        import dashboards.models.VisualisationBaseDataConfig
        import dashboards.models.VisualisationConfig
