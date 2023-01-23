# flake8: noqa
from django.apps import AppConfig


class DashboardsConfig(AppConfig):
    name = "dashboards"
    verbose_name = "Visualisation Dashboards"

    def ready(self):
        from dashboards.models import VisualisationBaseDataConfig
        from dashboards.models import VisualisationConfig
