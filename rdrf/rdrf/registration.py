from django.core.exceptions import ValidationError
from registry.patients.models import Patient
from dynamic_data import DynamicDataWrapper
from rdrf.utils import get_code, get_form_section_code
import logging
import string

logger = logging.getLogger("registry_log")

class PatientCreatorState:
    READY = "READY"
    CREATED_OK = "PATIENT CREATED OK"
    FAILED_VALIDATION = "PATIENT NOT CREATED DUE TO VALIDATION ERRORS"
    FAILED = "PATIENT NOT CREATED"

class PatientCreator(object):
    def __init__(self, registry, user):
        self.registry = registry
        self.user = user
        self.state = PatientCreatorState.READY
        self.error = None

    def _create_cde_name(self, model_field_name):
        # Patient model
        # model_field_name looks like given_names
        # given_names --> CDEPatientGivenNames

        return "CDEPatient%s" % string.capwords(model_field_name.replace("_"," ")).replace(" ","")

    def _questionnaire_key(self,questionnaire_data, cde_code):
        from django.conf import settings
        for delimited_key in questionnaire_data:
            code = get_code(delimited_key)
            if code == cde_code:
                return delimited_key

        return None

    def _set_patient_field(self, patient, field_name, cde_value):
        if field_name == 'state':
            self._set_patient_state(patient, cde_value)
        else:
            setattr(patient, field_name, cde_value)

    def _set_patient_state(self, patient, cde_value):
        from registry.patients.models import State
        try:
            state_model = State.objects.get(short_name=cde_value)
            patient.state = state_model
        except State.DoesNotExist, ex:
            logger.error("Cannot set patient state to %s: %s" % (cde_value, ex))
            raise Exception("State %s doesn't exist" % cde_value)


    def create_patient(self, approval_form_data, questionnaire_response, questionnaire_data):
        patient = Patient()
        patient.consent = True
        model_cdes = [] # cdes which describe fields on the patient model

        for field_name in patient._meta.get_all_field_names():
            cde_name = self._create_cde_name(field_name)
            logger.debug("checking field %s on Patient model - cde name = %s" % (field_name, cde_name))
            questionnaire_cde_key = self._questionnaire_key(questionnaire_data, cde_name)

            if questionnaire_cde_key is not None:
                cde_value = questionnaire_data[questionnaire_cde_key]
                try:
                    self._set_patient_field(patient, field_name, cde_value)
                    logger.info("creating patient: %s to %s from %s" % (field_name, cde_value , cde_name))

                except Exception,ex:
                    logger.error("error setting patient field: %s to %s from %s: %s" % (field_name, cde_value , cde_name, ex))
                    self.state = PatientCreatorState.FAILED
                    self.error = ex
                    return

                model_cdes.append(cde_name)
            else:
                logger.debug("%s not in questionnaire data")

        try:
            working_group_id = int(approval_form_data['working_group'])
            self._set_patient_working_group(patient, working_group_id)
            patient.full_clean()
            patient.save()
            patient.rdrf_registry = [self.registry,]
        except ValidationError, verr:
            self.state = PatientCreatorState.FAILED_VALIDATION
            logger.error("Could not save patient %s: %s" % (patient, verr))
            self.error = verr
            return
        except Exception, ex:
            self.error = ex
            self.state = PatientCreatorState.FAILED
            return


        logger.info("created patient %s" % patient.pk)
        questionnaire_response.patient_id = patient.pk
        questionnaire_response.processed = True
        questionnaire_response.save()

        other_cdes = [ (k, questionnaire_data[k]) for k in questionnaire_data if "CDE" in k and k not in model_cdes ]
        logger.info("other cdes = %s" % other_cdes)

        self._create_patient_cdes(patient,other_cdes)
        self.state = PatientCreatorState.CREATED_OK

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



















