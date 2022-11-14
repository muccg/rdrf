from django.db import models
from rdrf.models.definition.models import Registry


class VisualisationConfig(models.Model):
    dashboards = (("S", "Single Patient"), ("A", "All Patients"))
    codes = (
        ("tofc", "Types of Forms Completed"),
        ("pcf", "Patients Who Completed Forms"),
        ("fgc", "FieldGroupComparison"),
    )
    registry = models.ForeignKey(Registry, on_delete=models.CASCADE)
    dashboard = models.CharField(
        max_length=1, choices=dashboards
    )  # which dashboard this vis will be on
    code = models.CharField(
        max_length=80, choices=codes
    )  # used as a tag to run the correct vis
    title = models.CharField(max_length=80)
    config = models.JSONField()
