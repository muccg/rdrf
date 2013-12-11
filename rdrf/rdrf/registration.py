from registry.patients.models import Patient
from dynamic_data import DynamicDataWrapper
import logging
import string

logger = logging.getLogger("registry_log")

class PatientCreator(object):
    def __init__(self, registry):
        self.registry = registry

    def _create_cde_name(self, model_field_name):
        # Patient model
        # model_field_name looks like given_names
        # given_names --> CDEPatientGivenNames

        return "CDEPatient%s" % string.capwords(model_field_name.replace("_"," ")).replace(" ","")

    def create_patient(self, questionnaire_data):
        patient = Patient()
        patient.consent = True

        model_cdes = [] # cdes which describe fields on the patient model

        for field_name in patient.instance.fields:
            cde_name = self._create_cde_name(field_name)
            logger.debug("checking field %s on Patient model - cde name = %s" % (field_name, cde_name))
            if questionnaire_data.has_key(cde_name):
                cde_value = questionnaire_data[cde_name]
                setattr(patient, field_name, cde_value)
                logger.debug("setting patient.%s to %s from %s" % (field_name, cde_value , cde_name))
                model_cdes.append(cde_name)

        try:
            patient.save()
        except Exception:
            return False

        other_cdes = [ (k, questionnaire_data[k]) for k in questionnaire_data if "CDE" in k and k not in model_cdes ]

        self._create_patient_cdes(patient,other_cdes)

    def _create_dynamic_data(self, cde_pair_values):
        d = {}
        for k, value in cde_pair_values:
            d[k] = value
        return d

    def _create_patient_cdes(self, patient, other_cdes):
        wrapper = DynamicDataWrapper(patient)
        wrapper.save_dynamic_data(self.registry.code,'cdes',self._create_dynamic_data(other_cdes))


















