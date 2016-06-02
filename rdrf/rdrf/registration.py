from django.core.exceptions import ValidationError
from registry.patients.models import Patient
from registry.patients.models import PatientAddress, AddressType
from dynamic_data import DynamicDataWrapper
import logging
from django.conf import settings
from registry.groups.models import WorkingGroup
from django.db import transaction
from datetime import datetime
import pycountry

logger = logging.getLogger(__name__)


class PatientCreatorState:
    READY = "READY"
    CREATED_OK = "PATIENT CREATED OK"
    FAILED_VALIDATION = "PATIENT NOT CREATED DUE TO VALIDATION ERRORS"
    FAILED = "PATIENT NOT CREATED"


class QuestionnaireReverseMapper(object):

    """
    Save data back into original forms from the Questionnaire Response data
    """

    def __init__(self, registry, patient, questionnaire_data):
        self.patient = patient
        self.registry = registry
        self.questionnaire_data = questionnaire_data
        self.context_model = None

    def save_patient_fields(self):
        working_groups = []
        for attr, value in self._get_demographic_data():
            if attr == 'working_groups':
                working_groups = value
                continue
            logger.debug("setting patient demographic field: %s = %s" % (attr, value))
            setattr(self.patient, attr, value)

        self.patient.save()
        self.patient.working_groups = working_groups
        self.patient.save()

    def _empty_address_data(self, address_map):
        for value in address_map.values():
            if value:
                return False
        return True

    def save_address_data(self):
        if "PatientDataAddressSection" in self.questionnaire_data:
            address_maps = self.questionnaire_data["PatientDataAddressSection"]
            for address_map in address_maps:
                address = self._create_address(address_map, self.patient)
                if address:
                    address.save()

    def _create_address(self, address_map, patient_model):
        logger.debug("creating address for %s" % address_map)
        # GeneratedQuestionnaireForbfr____PatientDataAddressSection____State

        if self._empty_address_data(address_map):
            return

        def getcde(address_map, code):
            for k in address_map:
                if k.endswith("___" + code):
                    logger.debug("getcde %s = %s" % (code, address_map[k]))
                    return address_map[k]

        def get_address_type(address_map):
            value = getcde(address_map, "AddressType")
            logger.debug("address type = %s" % value)
            value = value.replace("AddressType", "")  # AddressTypeHome --> Home etc
            try:
                address_type_obj = AddressType.objects.get(type=value)
            except:
                address_type_obj = AddressType.objects.get(type="Home")
            return address_type_obj

        address = PatientAddress()
        logger.debug("created address object")
        address.patient = patient_model
        logger.debug("set patient")

        address.address_type = get_address_type(address_map)
        logger.debug("set address type")

        address.address = getcde(address_map, "Address")
        logger.debug("set address")
        address.suburb = getcde(address_map, "SuburbTown")
        logger.debug("set suburb")

        address_postcode = getcde(address_map, "postcode")
        if address_postcode:
            address.postcode = getcde(address_map, "postcode")
        else:
            address.postcode = ""
        logger.debug("set postcode")

        address.country = self._get_country(getcde(address_map, "Country"))
        logger.debug("set country")

        address.state = self._get_state(getcde(address_map, "State"), address.country)
        logger.debug("set state")

        return address

    def _get_country(self, cde_value):
        # cde value for country already is country code not name AU etc
        return cde_value

    def _get_state(self, cde_value, country_code):
        try:
            logger.debug("_get_state cde_value = %s" % cde_value)
            logger.debug("_get_state country_code = %s" % country_code)
            state_code = "%s-%s" % (country_code.lower(), cde_value.lower())
            if "-" in cde_value:
                state_code = cde_value
            else:
                state_code = "%s-%s" % (country_code, state_code)

            logger.debug("state_code to check = %s" % state_code)
            pycountry_states = list(pycountry.subdivisions.get(country_code=country_code))
            for state in pycountry_states:
                logger.debug("checking state code %s" % state.code.lower())
                if state.code.lower() == state_code.lower():
                    logger.debug("found state!: %s" % state.code)
                    return state.code

            logger.debug("could not find state - returning None")
        except Exception as ex:
            logger.debug("Error setting state: state = %s country code = %s error = %s" % (
                cde_value, country_code, ex))
            logger.error("could not find state code for for %s %s" % (country_code, cde_value))

    def save_dynamic_fields(self):
        wrapper = DynamicDataWrapper(self.patient, rdrf_context_id=self.context_model.pk)
        wrapper.current_form_model = None
        dynamic_data_dict = {}
        form_names = set([])
        for reg_code, form_name, section_code, cde_code, value in self._get_dynamic_data():
            form_names.add(form_name)
            delimited_key = settings.FORM_SECTION_DELIMITER.join(
                [form_name, section_code, cde_code])
            dynamic_data_dict[delimited_key] = value

        for original_multiple_section, element_list in self._get_multiple_sections():
            if original_multiple_section in dynamic_data_dict:
                dynamic_data_dict[original_multiple_section].extend(element_list)
            else:
                dynamic_data_dict[original_multiple_section] = element_list

        self._update_timestamps(form_names, dynamic_data_dict)
        wrapper.save_dynamic_data(self.registry.code, "cdes", dynamic_data_dict, parse_all_forms=True)

    def _update_timestamps(self, form_names, dynamic_data_dict):
        # These timestamps are used by the form progress indicator in the
        # patient listing
        last_update_time = datetime.now()
        dynamic_data_dict["timestamp"] = last_update_time
        for form_name in form_names:
            dynamic_data_dict["%s_timestamp" % form_name] = last_update_time

    def _get_multiple_sections(self):
        for k in self.questionnaire_data:
            if settings.FORM_SECTION_DELIMITER not in k:
                if k not in self.registry.generic_sections:
                    data = self.questionnaire_data[k]
                    if isinstance(data, list):
                        if len(data) > 0:
                            yield self._parse_multisection_data(k, data)

    def _parse_multisection_data(self, generated_multisectionkey, item_dicts):
        # sorry !- this is hideous - Todo refactor how storing multisections work
        # questionnaire response multisection data looks like:

        # "GenQxyfooFoobarSection" : [ 	{ 	"GeneratedQuestionnaireForxy____GenQxyfooFoobarSection____CDEHeight" : 1, ..
        # to
        # "FoobarSection" : [ 	{ 	"foo____FoobarSection____CDEHeight" : 1
        original_form, original_multisection = self._parse_generated_section_code(
            generated_multisectionkey)
        new_items = []
        for item_dict in item_dicts:
            new_item_dict = {}
            for k in item_dict:
                logger.debug("k = %s" % k)
                if k is None:
                    continue
                if k == "DELETE":
                    logger.debug(
                        "skipping DELETE key: not applicable in questionnaire response ...")
                    continue
                value = item_dict[k]
                logger.debug("value = %s" % value)
                generated_item_form, generated_item_section, cde_code = k.split(
                    settings.FORM_SECTION_DELIMITER)
                orig_item_form, orig_item_section = self._parse_generated_section_code(
                    generated_item_section)
                new_item_key = settings.FORM_SECTION_DELIMITER.join(
                    [orig_item_form, orig_item_section, cde_code])
                new_item_dict[new_item_key] = value
            new_items.append(new_item_dict)

        return original_multisection, new_items

    def _get_field_data(self, dynamic=True):
        for k in self.questionnaire_data:
            logger.debug("getting key: %s" % k)

            if settings.FORM_SECTION_DELIMITER not in k:
                continue
            form_name, section_code, cde_code = self._get_key_components(k)
            is_a_dynamic_field = section_code not in self.registry.generic_sections

            if dynamic and is_a_dynamic_field:
                logger.debug("yielding dynamic %s" % k)
                generated_form_name, generated_section_code, cde_code = self._get_key_components(
                    k)
                original_form_name, original_section_code = self._parse_generated_section_code(
                    generated_section_code)

                yield self.registry.code, original_form_name, original_section_code, cde_code, self.questionnaire_data[k]

            if not dynamic and not is_a_dynamic_field:
                logger.debug("yield non-dynamic %s" % k)
                patient_attribute, converter = self._get_patient_attribute_and_converter(
                    cde_code)
                if converter is None:
                    yield patient_attribute, self.questionnaire_data[k]
                else:
                    yield patient_attribute, converter(self.questionnaire_data[k])

    def _get_patient_attribute_and_converter(self, cde_code):

        def get_working_group(working_group_name):
            from django.db.models import Q

            return [WorkingGroup.objects.get(Q(name__iexact=working_group_name.strip())
                        & Q(registry=self.registry) )]

        def set_next_of_kin_relationship(relationship_name):
            from registry.patients.models import NextOfKinRelationship
            try:
                rel, created = NextOfKinRelationship.objects.get_or_create(
                    relationship=relationship_name)
                if created:
                    rel.save()
                return rel
            except:
                return None

        key_map = {
            "CDEPatientGivenNames": ("given_names", None),
            "CDEPatientFamilyName": ("family_name", None),
            "CDEPatientSex": ("sex", None),
            "CDEPatientEmail": ("email", None),
            "PatientConsentPartOfRegistry": ("consent", None),
            "PatientConsentClinicalTrials": ("consent_clinical_trials", None),
            "PatientConsentSentInfo": ("consent_sent_information", None),
            "CDEPatientDateOfBirth": ("date_of_birth", None),
            "CDEPatientCentre": ("working_groups", get_working_group),
            "CDEPatientMobilePhone": ("mobile_phone", None),
            "CDEPatientHomePhone": ("home_phone", None),

            "CDEPatientNextOfKinFamilyName": ("next_of_kin_family_name", None),
            "CDEPatientNextOfKinGivenNames": ("next_of_kin_given_names", None),
            "CDEPatientNOKRelationship": ("next_of_kin_relationship", set_next_of_kin_relationship),
            "CDEPatientNextOfKinAddress": ("next_of_kin_address", None),
            "CDEPatientNextOfKinSuburb": ("next_of_kin_suburb", None),
            "CDEPatientNextOfKinCountry": ("next_of_kin_country", None),
            "CDEPatientNextOfKinState": ("next_of_kin_state", None),
            "CDEPatientNextOfKinPostCode": ("next_of_kin_postcode", None),
            "PatientConsentByGuardian": ("consent_provided_by_parent_guardian", None),
            # "CDEPatientNextOfKinHomePhone": ("next_of_kin_home_phone", None),
            # "CDEPatientNextOfKinMobilePhone": ("next_of_kin_mobile_phone", None),
            # "CDEPatientNextOfKinWorkPhone": ("next_of_kin_work_phone", None),
            "CDEPatientNextOfKinEmail": ("next_of_kin_email", None),
            # "CDEPatientNextOfKinParentPlace": ("next_of_kin_parent_place_of_birth", None),
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
                if generated_section_code == self.registry._generated_section_questionnaire_code(
                        form_model.name,
                        section_model.code):
                    return form_model.name, section_model.code
        return None, None


class PatientCreator(object):

    def __init__(self, registry, user):
        self.registry = registry
        self.user = user
        self.state = PatientCreatorState.READY
        self.error = None

    @transaction.atomic
    def create_patient(self, approval_form_data, questionnaire_response, questionnaire_data):
        before_creation = transaction.savepoint()
        patient = Patient()
        patient.consent = True
        from rdrf.contexts_api import RDRFContextManager
        cm = RDRFContextManager(self.registry)
        mapper = QuestionnaireReverseMapper(self.registry, patient, questionnaire_data)

        try:
            mapper.save_patient_fields()
        except Exception as ex:
            logger.error("Error saving patient fields: %s" % ex)
            self.error = ex
            self.state = PatientCreatorState.FAILED
            return

        try:
            patient.full_clean()
            logger.debug("patient creator patient fullclean")
            patient.save()
            patient.rdrf_registry = [self.registry]
            patient.save()
            context_model = cm.create_initial_context_for_new_patient(patient)
            mapper.context_model = context_model
            mapper.save_address_data()
        except ValidationError as verr:
            self.state = PatientCreatorState.FAILED_VALIDATION
            logger.error("Could not save patient %s: %s" % (patient, verr))
            self.error = verr
            transaction.savepoint_rollback(before_creation)
            return
        except Exception as ex:
            self.error = ex
            self.state = PatientCreatorState.FAILED
            transaction.savepoint_rollback(before_creation)
            return

        # set custom consents here as these need access to the patients registr(y|ies)
        try:
            logger.debug("creating custom consents")
            custom_consent_data = questionnaire_data["custom_consent_data"]
            logger.debug("custom_consent_data = %s" % custom_consent_data)
            self._create_custom_consents(patient, custom_consent_data)
        except Exception as ex:
            self.error = ex
            self.state = PatientCreatorState.FAILED
            transaction.savepoint_rollback(before_creation)
            return

        logger.info("created patient %s" % patient.pk)
        questionnaire_response.patient_id = patient.pk
        questionnaire_response.processed = True
        questionnaire_response.save()

        try:
            mapper.save_dynamic_fields()
        except Exception as ex:
            self.state = PatientCreatorState.FAILED
            logger.error("Error saving dynamic data in mongo: %s" % ex)
            try:
                self._remove_mongo_data(self.registry, patient)
                logger.info("removed dynamic data for %s for registry %s" %
                            (patient.pk, self.registry))
                transaction.savepoint_rollback(before_creation)
                return
            except Exception as ex:
                logger.error("could not remove dynamic data for patient %s: %s" %
                             (patient.pk, ex))
                transaction.savepoint_rollback(before_creation)
                return

        self.state = PatientCreatorState.CREATED_OK
        # RDR-667 we don't need to preserve the approved QRs once patient created
        transaction.savepoint_commit(before_creation)

        questionnaire_response.delete()

    def _remove_mongo_data(self, registry, patient):
        wrapper = DynamicDataWrapper(patient)
        wrapper.delete_patient_data(registry, patient)

    def _create_custom_consents(self, patient_model, custom_consent_dict):
        from rdrf.models import ConsentQuestion
        # dictionary looks like: ( only the "on"s will exist if false it won't have a key
        # 	"customconsent_9_1_3" : "on",

        for field_key in custom_consent_dict:
            logger.debug(field_key)
            value = custom_consent_dict[field_key]
            answer = value == "on"
            _, registry_pk, consent_section_pk, consent_question_pk = field_key.split("_")
            consent_question_model = ConsentQuestion.objects.get(pk=int(consent_question_pk))
            patient_model.set_consent(consent_question_model, answer)
