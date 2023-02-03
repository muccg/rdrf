from django.db import models
from rdrf.models.definition.models import Registry


class VisualisationBaseDataConfig(models.Model):
    """
    base data for visualisations for a registry
    """

    code = models.CharField(max_length=80)

    states = (("E", "Empty"), ("D", "Data Loaded"))
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    state = models.CharField(max_length=1, choices=states)
    registry = models.ForeignKey(Registry, on_delete=models.CASCADE)
    config = models.JSONField()
    data = models.JSONField()


class VisualisationConfig(models.Model):
    dashboards = (("S", "Single Patient"), ("A", "All Patients"))
    codes = (
        ("proms_stats", "Proms Statistics"),
        ("cfc", "Combined Field Comparison"),
        ("cpr", "Changes in Patient Responses"),
        ("sgc", "Scale Group Comparison"),
        ("tl", "Traffic Lights Display"),
    )
    registry = models.ForeignKey(Registry, on_delete=models.CASCADE)
    base_data = models.ForeignKey(
        VisualisationBaseDataConfig, blank=True, null=True, on_delete=models.SET_NULL
    )
    dashboard = models.CharField(
        max_length=1, choices=dashboards
    )  # which dashboard this vis will be on
    code = models.CharField(
        max_length=80, choices=codes
    )  # used as a tag to run the correct vis
    title = models.CharField(max_length=80)
    config = models.JSONField(null=True)
    position = models.IntegerField(null=True, blank=True)
