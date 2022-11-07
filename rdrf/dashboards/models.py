from django.db import models
import pandas as pd
from typing import List
from rdrf.models.definition.models import Registry
from rdrf.models.definition.models import CommonDataElement
from registry.patients.models import Patient


class VisualisationConfig(models.Model):
    code = models.CharField(max_length=80)
    registry = models.ForeignKey(Registry, on_delete=models.CASCADE)
    config = models.JSONField()

    def get_cdes(self) -> List[CommonDataElement]:
        cdes = []
        cde_codes = self.config.get("fields", [])
        for cde_code in cde_codes:
            try:
                cde_model = CommonDataElement.objects.get(code=cde_code)
                cdes.append(cde_model)
            except CommonDataElement.DoesNotExist:
                pass
        return cdes

    def load_overall_data(self) -> pd.DataFrame:
        overall_fields = self.config.get("overall_fields", [])
        return get_data(self.registry, overall_fields)
