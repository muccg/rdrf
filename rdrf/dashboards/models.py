from django.db import models
import pandas as pd
from rdrf.models.definition.models import Registry
from rdrf.models.definition.models import CommonDataElement
from registry.patients.models import Patient
from typing import List


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

    def load_patient_data(self, patient: Patient) -> pd.DataFrame:
        cde_models = self.get_cdes()
        responses = []
        data_records = get_baseline_and_followups(self.registry, patient)
        responses = [
            get_responses(data_record, cde_models) for data_record in data_records
        ]
        return convert_responses_to_dataframe(responses)
