from django.core.exceptions import ValidationError
from registry.patients.models import Patient
from dynamic_data import DynamicDataWrapper
from rdrf.utils import get_code, get_form_section_code
import logging
import string
from django.conf import settings
from registry.groups.models import WorkingGroup

logger = logging.getLogger("registry_log")

class PatientCreatorState:
    READY = "READY"
    CREATED_OK = "PATIENT CREATED OK"
    FAILED_VALIDATION = "PATIENT NOT CREATED DUE TO VALIDATION ERRORS"
    FAILED = "PATIENT NOT CREATED"


class QuestionnaireReverseMapper(object):
    def __init__(self, registry, patient , questionnaire_data):
        self.patient = patient
        self.registry = registry
        self.questionnaire_data = questionnaire_data

    def save_patient_fields(self):
        for attr, value in self._get_demographic_data():
            setattr(self.patient, attr, value)

    def save_dynamic_fields(self):
        wrapper = DynamicDataWrapper(self.patient)
        dynamic_data_dict = {}
        for reg_code, form_name, section_code, cde_code, value in self._get_dynamic_data():
            delimited_key = settings.FORM_SECTION_DELIMITER.join([form_name, section_code, cde_code])
            dynamic_data_dict[delimited_key] = value

        wrapper.save_dynamic_data(self.registry.code, 'cdes', dynamic_data_dict)


    def _get_field_data(self, dynamic=True):
        for k in self.questionnaire_data:
            logger.debug("getting key: %s" % k)
            if settings.FORM_SECTION_DELIMITER not in k:
                continue
            form_name, section_code, cde_code = self._get_key_components(k)
            is_a_dynamic_field = section_code not in [ self.registry._get_consent_section(), self.registry._get_patient_info_section() ]

            if dynamic and is_a_dynamic_field:
                logger.debug("yielding dynamic %s" % k)
                generated_form_name, generated_section_code, cde_code = self._get_key_components(k)
                original_form_name, original_section_code = self._parse_generated_section_code(generated_section_code)

                yield  self.registry.code, original_form_name, original_section_code, cde_code,  self.questionnaire_data[k]

            if not dynamic and not is_a_dynamic_field:
                logger.debug("yield non-dynamic %s" % k)
                patient_attribute, converter  = self._get_patient_attribute_and_converter(cde_code)
                if converter is None:
                    yield  patient_attribute, self.questionnaire_data[k]
                else:
                    yield patient_attribute, converter(self.questionnaire_data[k])

    def _get_patient_attribute_and_converter(self, cde_code):

        def get_working_group(working_group_id):
            return WorkingGroup.objects.get(pk=working_group_id)

        key_map = {
            "CDEPatientGivenNames": ("given_names", None),
            "CDEPatientFamilyName": ("family_name", None),
            "CDEPatientSex": ("sex", None),
            "CDEPatientEmail": ("email", None),
            "PatientConsentPartOfRegistry" : ("consent", None),
            "PatientConsentClinicalTrials": ("consent_clinical_trials", None),
            "PatientConsentSentInfo" : ("consent_sent_information", None),
            "CDEPatientDateOfBirth" : ("date_of_birth", None),
            "CDEPatientCentre" : ("working_group", get_working_group),
            "CDEPatientMobilePhone" : ("mobile_phone", None),
            "CDEPatientHomePhone": ("home_phone", None),


        }

        return key_map[cde_code]


    def _get_demographic_data(self):
        return self._get_field_data(dynamic=False)

    def _get_dynamic_data(self):
        return self._get_field_data()


    def _get_key_components(self, delimited_key):
        return delimited_key.split(settings.FORM_SECTION_DELIMITER)

    def _parse_generated_section_code(self, generated_section_code):
        """
        GenQbfrGeneralFormbfrsec01
        :param generated_section_code:
        :return:
        """
        for form_model in self.registry.forms:
            for section_model in form_model.section_models:
                if generated_section_code == self.registry._generated_section_questionnaire_code(form_model.name, section_model.code):
                    return form_model.name, section_model.code
        return None, None


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
        mapper = QuestionnaireReverseMapper(self.registry, patient, questionnaire_data)


        try:
            mapper.save_patient_fields()
        except Exception, ex:
            logger.error("Error saving patient fields: %s" % ex)
            self.state = PatientCreatorState.FAILED
            return


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

        try:
            mapper.save_dynamic_fields()
        except Exception, ex:
            self.state = PatientCreatorState.FAILED
            logger.error("Error saving dynamic data in mongo: %s" % ex)
            try:
                self._remove_mongo_data(self.registry, patient)
                logger.info("removed dynamic data for %s for registry %s" % (patient.pk, self.registry))
                return
            except Exception, ex:
                logger.error("could not remove dynamic data for patient %s: %s" % (patient.pk, ex))
                return

        self.state = PatientCreatorState.CREATED_OK

    def _remove_mongo_data(self, registry, patient):
        wrapper = DynamicDataWrapper(patient)
        wrapper.delete_patient_data(registry, patient)