from django.db import models
from rdrf.models.definition.models import Registry


class VisualisationConfig(models.Model):
    dashboards = (("S", "Single Patient"), ("A", "All Patients"))
    codes = (
        ("tof", "Types of Forms Completed"),
        ("pc", "Patients Who Completed Forms"),
    )
    registry = models.ForeignKey(Registry, on_delete=models.CASCADE)
    dashboard = models.CharField(
        max_length=1, choices=dashboards
    )  # which dashboard this vis will be on
    code = models.CharField(max_length=80)  # used as a tag to run the correct vis
    config = models.JSONField()
