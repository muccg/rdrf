from registry.patients.models import Patient
from dynamic_data import DynamicDataWrapper
import logging
import string

logger = logging.getLogger("registry_log")

class PatientCreator(object):
    def __init__(self, registry, user):
        self.registry = registry
        self.user = user

    def _create_cde_name(self, model_field_name):
        # Patient model
        # model_field_name looks like given_names
        # given_names --> CDEPatientGivenNames

        return "CDEPatient%s" % string.capwords(model_field_name.replace("_"," ")).replace(" ","")

    def create_patient(self, questionnaire_data, questionnaire_response):
        patient = Patient()
        patient.consent = True
        logger.debug("questionnaire data = %s" % questionnaire_data)

        model_cdes = [] # cdes which describe fields on the patient model
        for field_name in patient._meta.get_all_field_names():
            cde_name = self._create_cde_name(field_name)
            logger.debug("checking field %s on Patient model - cde name = %s" % (field_name, cde_name))
            if questionnaire_data.has_key(cde_name):

                cde_value = questionnaire_data[cde_name]
                setattr(patient, field_name, cde_value)
                logger.debug("set patient.%s to %s from %s" % (field_name, cde_value , cde_name))
                model_cdes.append(cde_name)

        working_group_id = int(questionnaire_data['working_group'])

        self._set_patient_working_group(patient, working_group_id)
        self._set_patient_dob(patient,questionnaire_data)

        from registry.patients.models import State
        patient.state = State.objects.all()[0] #todo fix state
        patient.postcode = "6112" #todo fix postcode

        patient.save()
        logger.debug("created patient %s" % patient.pk)
        questionnaire_response.patient_id = patient.pk
        questionnaire_response.processed = True
        questionnaire_response.save()


        other_cdes = [ (k, questionnaire_data[k]) for k in questionnaire_data if "CDE" in k and k not in model_cdes ]
        logger.debug("other cdes = %s" % other_cdes)
        self._create_patient_cdes(patient,other_cdes)

    def _set_patient_dob(self, patient, data):
        day = data.get("CDEPatientDateOfBirth_day",None)
        month = data.get("CDEPatientDateOfBirth_month", None)
        year = data.get("CDEPatientDateOfBirth_year", None)
        if all([day,month,year]):
            from datetime import datetime

            patient.date_of_birth = datetime(int(year),int(month), int(day))



    def _set_patient_working_group(self, patient,id):
        from registry.groups.models import WorkingGroup
        patient.working_group = WorkingGroup.objects.get(pk=id)


    def _create_dynamic_data_dictionary(self, cde_pair_values):
        d = {}
        for k, value in cde_pair_values:
            d[k] = value
        return d

    def _create_patient_cdes(self, patient, other_cdes):
        wrapper = DynamicDataWrapper(patient)
        wrapper.save_dynamic_data(self.registry.code,'cdes',self._create_dynamic_data_dictionary(other_cdes))



















