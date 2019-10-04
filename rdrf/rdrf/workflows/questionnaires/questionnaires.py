from rdrf.models.definition.models import RegistryForm, Section, CommonDataElement
from explorer.views import Humaniser
from django.urls import reverse
from collections import OrderedDict
from rdrf.db.generalised_field_expressions import GeneralisedFieldExpressionParser
from django.core.exceptions import ValidationError
from registry.patients.models import Patient
from registry.patients.models import PatientAddress, AddressType
from rdrf.db.dynamic_data import DynamicDataWrapper
from django.conf import settings
from registry.groups.models import WorkingGroup
from datetime import date
from datetime import datetime
import pycountry

import logging
logger = logging.getLogger(__name__)

CONSENTS_SECTION = "custom_consent_data"


class Func(object):

    def __init__(self, func_name):
        self.name = func_name


class TargetCDE(object):

    def __init__(self, display_name, field_expression):
        self.display_name = display_name
        self.field_expression = field_expression


# Map special patient data section cdes to patient attributes
KEY_MAP = {
    "CDEPatientGivenNames": ("given_names", None),
    "CDEPatientFamilyName": ("family_name", None),
    "CDEPatientSex": ("sex", None),
    "CDEPatientEmail": ("email", None),
    "PatientConsentPartOfRegistry": ("consent", None),
    "PatientConsentClinicalTrials": ("consent_clinical_trials", None),
    "PatientConsentSentInfo": ("consent_sent_information", None),
    "CDEPatientDateOfBirth": ("date_of_birth", Func("get_patient_date_of_birth")),
    "CDEPatientCentre": ("working_groups", Func("get_working_group")),
    "CDEPatientMobilePhone": ("mobile_phone", None),
    "CDEPatientHomePhone": ("home_phone", None),

    "CDEPatientNextOfKinFamilyName": ("next_of_kin_family_name", None),
    "CDEPatientNextOfKinGivenNames": ("next_of_kin_given_names", None),
    "CDEPatientNOKRelationship": ("next_of_kin_relationship", Func("set_next_of_kin_relationship")),
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
        self.default_context_model = None
        # questionnaire handling works only for registry which use default context

    def set_context(self):
        if self.patient is not None:
            patient_contexts = self.patient.context_models
            if len(patient_contexts) == 1:
                self.default_context_model = patient_contexts[0]
            elif len(patient_contexts) == 0:
                from rdrf.db.contexts_api import RDRFContextManager
                self.patient.save()
                manager = RDRFContextManager(self.registry)
                default_context = manager.get_or_create_default_context(self.patient)
                self.default_context_model = default_context
        else:
            self.default_context_model = None  # ???

    def save_patient_fields(self):
        working_groups = []
        for attr, value in self._get_demographic_data():
            if attr == 'working_groups':
                working_groups = value
                continue
            setattr(self.patient, attr, value)

        self.patient.save()
        self.patient.working_groups = working_groups
        self.patient.save()

    def _empty_address_data(self, address_map):
        for value in list(address_map.values()):
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
        # GeneratedQuestionnaireForbfr____PatientDataAddressSection____State

        if self._empty_address_data(address_map):
            return

        def getcde(address_map, code):
            for k in address_map:
                if k.endswith("___" + code):
                    return address_map[k]

        def get_address_type(address_map):
            value = getcde(address_map, "AddressType")
            # AddressTypeHome --> Home etc
            value = value.replace("AddressType", "")
            try:
                address_type_obj = AddressType.objects.get(type=value)
            except BaseException:
                address_type_obj = AddressType.objects.get(type="Home")
            return address_type_obj

        address = PatientAddress()
        address.patient = patient_model
        address.address_type = get_address_type(address_map)
        address.address = getcde(address_map, "Address")
        address.suburb = getcde(address_map, "SuburbTown")
        address_postcode = getcde(address_map, "postcode")
        if address_postcode:
            address.postcode = getcde(address_map, "postcode")
        else:
            address.postcode = ""
        address.country = self._get_country(getcde(address_map, "Country"))
        try:
            address.state = self._get_state(
                getcde(address_map, "State"), address.country)

        except Exception as ex:
            logger.error("Error setting state: %s" % ex)

        return address

    def _get_country(self, cde_value):
        # cde value for country already is country code not name AU etc
        return cde_value

    def _get_state(self, cde_value, country_code):
        try:
            state_code = "%s-%s" % (country_code.lower(), cde_value.lower())
            if "-" in cde_value:
                state_code = cde_value
            else:
                state_code = "%s-%s" % (country_code, state_code)

            pycountry_states = list(
                pycountry.subdivisions.get(country_code=country_code))
            for state in pycountry_states:
                if state.code.lower() == state_code.lower():
                    return state.code

        except Exception:
            logger.error("could not find state code for for %s %s" %
                         (country_code, cde_value))

    def save_dynamic_fields(self):
        default_context_model = self.patient.default_context(self.registry)
        wrapper = DynamicDataWrapper(self.patient, rdrf_context_id=default_context_model.pk)
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
                dynamic_data_dict[
                    original_multiple_section].extend(element_list)
            else:
                dynamic_data_dict[original_multiple_section] = element_list

        self._update_timestamps(form_names, dynamic_data_dict)
        wrapper.save_dynamic_data(
            self.registry.code, "cdes", dynamic_data_dict, parse_all_forms=True)

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
        original_form, original_multisection = self.parse_generated_section_code(
            generated_multisectionkey)
        new_items = []
        for item_dict in item_dicts:
            new_item_dict = {}
            for k in item_dict:
                if k is None:
                    continue
                if k == "DELETE":
                    continue
                value = item_dict[k]
                generated_item_form, generated_item_section, cde_code = k.split(
                    settings.FORM_SECTION_DELIMITER)
                orig_item_form, orig_item_section = self.parse_generated_section_code(
                    generated_item_section)
                new_item_key = settings.FORM_SECTION_DELIMITER.join(
                    [orig_item_form, orig_item_section, cde_code])
                new_item_dict[new_item_key] = value
            new_items.append(new_item_dict)

        return original_multisection, new_items

    def _get_field_data(self, dynamic=True):
        for k in self.questionnaire_data:
            if settings.FORM_SECTION_DELIMITER not in k:
                continue
            form_name, section_code, cde_code = self._get_key_components(k)
            is_a_dynamic_field = section_code not in self.registry.generic_sections

            if dynamic and is_a_dynamic_field:
                generated_form_name, generated_section_code, cde_code = self._get_key_components(
                    k)
                original_form_name, original_section_code = self.parse_generated_section_code(
                    generated_section_code)
                reg_code = self.registry.code
                q_data = self.questionnaire_data[k]
                yield reg_code, original_form_name, original_section_code, cde_code, q_data

            if not dynamic and not is_a_dynamic_field:
                patient_attribute, converter = self._get_patient_attribute_and_converter(
                    cde_code)
                if converter is None:
                    yield patient_attribute, self.questionnaire_data[k]
                else:
                    yield patient_attribute, converter(self.questionnaire_data[k])

    def _get_patient_attribute_and_converter(self, cde_code):

        def get_working_group(working_group_name):
            from django.db.models import Q

            return [WorkingGroup.objects.get(Q(name__iexact=working_group_name.strip()) & Q(registry=self.registry))]

        def set_next_of_kin_relationship(relationship_name):
            from registry.patients.models import NextOfKinRelationship
            try:
                rel, created = NextOfKinRelationship.objects.get_or_create(
                    relationship=relationship_name)
                if created:
                    rel.save()
                return rel
            except BaseException:
                return None

        value = KEY_MAP[cde_code]

        if isinstance(value[1], Func):
            function_name = value[1].name
            if function_name == "get_working_group":
                converter = get_working_group
            elif function_name == "set_next_of_kin_relationship":
                converter = set_next_of_kin_relationship
            elif function_name == "get_patient_date_of_birth":
                converter = self._get_date_of_birth
            return value[0], converter
        else:
            return value

    def _get_demographic_data(self):
        return self._get_field_data(dynamic=False)

    def _get_date_of_birth(self, questionnaire_value):
        from rdrf.helpers.utils import parse_iso_datetime
        try:
            # the time field was causing a problem
            return parse_iso_datetime(questionnaire_value).date()
        except ValueError:
            raise ValueError("Invalid date of birth: %s" % questionnaire_value)

    def _get_dynamic_data(self):
        return self._get_field_data()

    def _get_key_components(self, delimited_key):
        return delimited_key.split(settings.FORM_SECTION_DELIMITER)

    def parse_generated_section_code(self, generated_section_code):
        """
        GenQbfrGeneralFormbfrsec01
        :param generated_section_code:
        :return:
        """
        for form_model in self.registry.forms:
            for section_model in form_model.section_models:
                if generated_section_code == self.registry._generated_section_questionnaire_code(
                        form_model.name, section_model.code):
                    return form_model.name, section_model.code
        return None, None


class PatientCreatorError(Exception):
    pass


class PatientCreator(object):

    def __init__(self, registry, user):
        self.registry = registry
        self.user = user

    def create_patient(self, approval_form_data, questionnaire_response, questionnaire_data):
        log_prefix = "PatientCreator on QR %s" % questionnaire_response.pk

        class MyLogger(object):

            def __init__(self, logger, log_prefix):
                self.logger = logger
                self.log_prefix = log_prefix

            def error(self, msg):
                self.logger.error(self.log_prefix + ": " + msg)

            def info(self, msg):
                self.logger.info(self.log_prefix + ": " + msg)

        mylogger = MyLogger(logger, log_prefix)

        patient = Patient()
        patient.consent = True
        mapper = QuestionnaireReverseMapper(
            self.registry, patient, questionnaire_data)

        try:
            mapper.save_patient_fields()
        except Exception as ex:
            mylogger.error("Error saving patient fields: %s" % ex)
            raise PatientCreatorError("%s" % ex)

        try:
            patient.full_clean()
            patient.save()
            patient.rdrf_registry.set([self.registry])
            patient.save()
            mapper.save_address_data()
            mapper.set_context()  # ensure context setup properly before we save any data to Mongfo
        except ValidationError as verr:
            mylogger.error("Could not save patient %s: %s" % (patient, verr))
            raise PatientCreatorError("Validation Error: %s" % verr)

        except Exception as ex:
            mylogger.error("Unhandled error: %s" % ex)
            raise PatientCreatorError("Unhandled error: %s" % ex)

        try:
            custom_consent_data = questionnaire_data["custom_consent_data"]
            self._create_custom_consents(patient, custom_consent_data)
        except Exception as ex:
            mylogger.error("Error setting consents: %s" % ex)
            raise PatientCreatorError("Error setting consents: %s" % ex)

        try:
            mapper.save_dynamic_fields()
        except Exception as ex:
            logger.error("Error saving dynamic data in clinical database: %s" % ex)
            raise PatientCreatorError("Error saving clinical data: %s" % ex)

        try:
            questionnaire_response.patient_id = patient.pk
            questionnaire_response.processed = True
            questionnaire_response.save()
        except Exception as ex:
            logger.error("couldn't set qr to processed: %s" % ex)
            raise PatientCreatorError("Error setting qr to processed: %s" % ex)

        mylogger.info("Created patient (%s)" % (patient.pk))
        return patient

    def _create_custom_consents(self, patient_model, custom_consent_dict):
        from rdrf.models.definition.models import ConsentQuestion
        # dictionary looks like: ( only the "on"s will exist if false it won't have a key
        # 	"customconsent_9_1_3" : "on",

        for field_key in custom_consent_dict:
            value = custom_consent_dict[field_key]
            answer = value == "on"
            _, registry_pk, consent_section_pk, consent_question_pk = field_key.split(
                "_")
            consent_question_model = ConsentQuestion.objects.get(
                pk=int(consent_question_pk))
            patient_model.set_consent(consent_question_model, answer)


class _ExistingDataWrapper(object):
    """
    return to qr view to show data already saved on a patient
    """

    def __init__(self, registry_model, patient_model, questionnaire):
        self.registry_model = registry_model
        self.humaniser = Humaniser(self.registry_model)
        self.patient_model = patient_model
        self.patient_data = self.patient_model.get_dynamic_data(
            self.registry_model)

        self.questionnaire = questionnaire
        self.gfe_parser = GeneralisedFieldExpressionParser(self.registry_model)
        self.default_context_model = patient_model.default_context(
            registry_model)
        self.name = "%s" % self.patient_model

    def _get_field_data(self, field_expression, form_model, section_model, cde_model):
        if field_expression in list(KEY_MAP.keys()):
            field_expression = KEY_MAP[field_expression][
                0]  # the demographic field

        retrieval_function = self.gfe_parser.parse(field_expression)
        try:
            value = retrieval_function(self.patient_model, self.patient_data)
            if field_expression == "working_groups":
                return self._get_working_groups_display_value(value)
            value = self.humaniser.display_value2(
                form_model, section_model, cde_model, value)

            if isinstance(value, datetime) or isinstance(value, date):
                value = str(value)
            return value

        except Exception as ex:
            return "Error[!%s]" % ex

    def _get_working_groups_display_value(self, working_group_models):
        return ",".join(sorted([wg.name for wg in working_group_models]))

    @property
    def link(self):
        demographic_link = reverse("patient_edit", args=[self.registry_model.code,
                                                         self.patient_model.pk])
        return demographic_link

    @property
    def questions(self):
        """
        If data already filled in for patient
        grab and return as list of wrappers for view
        There are two special sections PatientData and PatientAddressData
        """
        lst = []
        for question in self.questionnaire.questions:
            if isinstance(question, _ConsentQuestion):
                existing_answer = {"name": question.name,
                                   "pos": str(question.pos),
                                   "is_multi": False,
                                   "answer": self._get_consent_answer(question)
                                   }
                lst.append(existing_answer)
                continue

            if question.section_code == "PatientData":
                field_name = self._get_patient_data_field_name(
                    question.cde_code)
                field_expression = question.cde_code
            elif question.section_code == 'PatientAddressSection':
                field_name = self._get_patient_address_field_name(
                    question.cde_code)
                field_expression = "address field expression"
            else:
                try:
                    field_name = question.target.display_name
                    field_expression = question.target.field_expression
                except Exception as ex:
                    logger.error("could not get target for %s %s: %s" % (question.section_code,
                                                                         question.cde_code,
                                                                         ex))
                    continue

            if field_name in KEY_MAP:
                field_name = question.cde_model.name

            if not question.is_multi:
                existing_answer = {
                    "name": field_name,
                    "pos": str(
                        question.pos),
                    "is_multi": False,
                    "answer": self._get_field_data(
                        field_expression,
                        question.form_model,
                        question.section_model,
                        question.cde_model)}
            else:
                if not question.is_address:
                    existing_answer = {
                        "name": field_name,
                        "pos": str(
                            question.pos),
                        "is_multi": True,
                        "answers": self._get_existing_multisection_data(
                            question.field_expression,
                            question.form_model,
                            question.section_model)}
                else:
                    existing_answer = {
                        "name": field_name, "pos": str(
                            question.pos), "is_multi": True, "answers": self._get_address_labels(
                            question.field_expression)}

            lst.append(existing_answer)

        return lst

    def _get_consent_answer(self, consent_question):
        from registry.patients.models import ConsentValue
        try:
            consent_value_model = ConsentValue.objects.get(
                patient=self.patient_model,
                consent_question=consent_question.consent_question_model)
            if consent_value_model.answer:
                return "Yes"
        except ConsentValue.DoesNotExist:
            return "No"

        return "No"

    def _get_address_labels(self, addresses_expression):

        def address_label(address):
            try:
                atype = address.address_type.description
            except Exception as ex:
                atype = "%s" % ex

            return "%s: %s %s %s %s %s" % (atype,
                                           address.address,
                                           address.suburb,
                                           address.state,
                                           address.postcode,
                                           address.country)

        retriever = self.gfe_parser.parse(addresses_expression)
        address_objects = retriever.evaluate(
            self.patient_model, self.patient_data)
        return [address_label(address) for address in address_objects]

    def _get_existing_multisection_data(self, field_expression, form_model, section_model):
        items_retriever = self.gfe_parser.parse(field_expression)
        display_items = []
        raw_items = items_retriever(self.patient_model, self.patient_data)

        for item in raw_items:
            display_fields = []
            for cde_code in item:
                cde_model = CommonDataElement.objects.get(code=cde_code)
                display_name = cde_model.name
                raw_value = item[cde_code]
                display_value = self.humaniser.display_value2(form_model,
                                                              section_model,
                                                              cde_model,
                                                              raw_value)
                display_field = "%s=%s" % (display_name, display_value)
                display_fields.append(display_field)

            item_field = ",".join(display_fields)
            display_items.append(item_field)

        # list of items displayed as key value pairs
        return display_items

    def _get_patient_data_field_name(self, cde_code):
        return cde_code

    def _get_patient_address_field_name(self, cde_code):
        return cde_code


class _ConsentQuestion(object):
    # Mongo record looks like this on questionnaire:
    # question
    # "customconsent_%s_%s_%s" %
    # (registry_model.pk, consent_section_model.pk, self.pk)
    # "custom_consent_data" : {
    # "customconsent_2_2_3" : "on",
    # "customconsent_2_2_6" : "on",
    # "customconsent_2_2_5" : "on",
    # "customconsent_2_2_4" : "on",
    # "customconsent_2_1_1" : "on",
    # "customconsent_2_1_2" : "on"

    def __init__(self, registry_model, key, raw_value):
        self.is_multi = False
        self.is_address = False
        self.valid = False
        self.registry_model = registry_model
        self.pos = 0
        self.key = key
        self.consent_section_model = None
        self.consent_question_model = None
        self.raw_value = raw_value
        self.answer = None
        self.name = None
        self.src_id = None
        self.dest_id = None

        self._parse()
        self.target = self._get_target()

    def _get_target(self):
        class ConsentTarget:

            def __init__(self):
                self.field_expression = None

        target = ConsentTarget()
        # Consents/ConsentSectionCode/ConsentQuestionCode/field

        target.field_expression = "Consents/%s/%s/answer" % (self.consent_section_model.code,
                                                             self.consent_question_model.code)
        return target

    def _parse(self):
        try:
            _, registry_id, consent_section_pk, consent_question_pk = self.key.split(
                "_")
        except ValueError:
            logger.error("invalid consent question key %s" % self.key)
            return

        from rdrf.models.definition.models import ConsentSection, ConsentQuestion
        try:
            self.consent_section_model = ConsentSection.objects.get(
                pk=int(consent_section_pk))
        except ConsentSection.DoesNotExist:
            logger.error("Could not find consent section with pk %s" %
                         consent_section_pk)
            return
        try:
            self.consent_question_model = ConsentQuestion.objects.get(
                pk=int(consent_question_pk))
        except ConsentQuestion.DoesNotExist:
            logger.error("Could not find consent question with pk %s" %
                         consent_question_pk)
            return

        if self.raw_value == "on":
            self.answer = "Yes"
        else:
            self.answer = "No"
        self.value = self.answer == "Yes"

        self.name = self.consent_question_model.question_label
        self.src_id = self.key

        self.valid = True


class _Question(object):
    """
    Read only view of entered questionnaire data
    """

    def __init__(self, registry_model, questionnaire, form_name, section_code, cde_code, value):
        self.registry_model = registry_model
        self.questionnaire = questionnaire
        self.humaniser = Humaniser(self.registry_model)
        self.form_name = form_name
        self.pos = 0
        self.question_type = None
        self.form_model = RegistryForm.objects.get(registry=self.registry_model,
                                                   name=form_name)
        self.section_model = Section.objects.get(code=section_code)
        self.cde_model = CommonDataElement.objects.get(code=cde_code)
        self.section_code = section_code
        self.cde_code = cde_code
        # raw value to be stored in Mongo ( or a list of values if from a
        # multisection)
        self.value = value

        self.target = self._get_target()

        # used on form:
        self.name = self._get_name()
        self.is_address = self.section_code == "PatientDataAddressSection"
        # or list of answers if cde in multisection
        self.answer = self._get_display_value(value)
        self.dest_id = "foo"
        self.src_id = self._construct_id()

    def _construct_id(self):
        return "id__%s__%s__%s" % (self.form_name,
                                   self.section_code,
                                   self.cde_code)

    @property
    def field_expression(self):
        if self.cde_code not in KEY_MAP:
            # not a special field - a "normal" clinical field
            return "%s/%s/%s" % (self.form_name,
                                 self.section_code,
                                 self.cde_code)
        else:
            return "TODO"

    def __str__(self):
        return "Q[%s] %s = %s" % (self.pos, self.name, self.answer)

    @property
    def is_multi(self):
        return self.section_model.allow_multiple

    def _get_name(self):
        # return a short name for the GUI - use the target display name not the generated
        # questionnaire name
        try:
            return self.target.display_name
        except Exception as ex:
            logger.error("error getting target: %s" % ex)
            return "%s/%s/%s" % (self.form_name,
                                 self.section_model.display_name,
                                 self.cde_model.name)

    def _get_display_value(self, value):
        if not self.is_multi:
            return self.humaniser.display_value2(
                self.form_model, self.section_model, self.cde_model, value)
        else:
            if not self.is_address:
                display = self.humaniser.display_value2
                return ",".join([display(self.form_model,
                                         self.section_model,
                                         self.cde_model,
                                         single_value) for single_value in value])
            else:
                return ",".join([x for x in value])

    def _get_target(self):
        """
        Return the generalised field expression that data for this field should be put into.
        This step is necessary because we decided early on to present one questionnaire form
        comprised of selected questions from potentially many clinical forms.
        """

        # the generated section code in a questionnaire encodes the original form name and
        # original section code ... ugh

        if self.cde_code in KEY_MAP:
            demographic_field = KEY_MAP[self.cde_code][0]
            target_expression = demographic_field
            target_display_name = CommonDataElement.objects.get(code=self.cde_code).name
            return TargetCDE(target_display_name, target_expression)

        t = self.questionnaire.questionnaire_reverse_mapper.parse_generated_section_code(
            self.section_code)

        original_form_name = t[0]
        original_section_code = t[1]

        target_display_name = self._get_target_display_name(
            original_form_name, original_section_code, self.cde_code)

        target_expression = "%s/%s/%s" % (original_form_name,
                                          original_section_code,
                                          self.cde_code)

        return TargetCDE(target_display_name, target_expression)

    def _get_target_display_name(self, target_form_name, target_section_code, target_cde_code):
        try:
            target_form_model = RegistryForm.objects.get(registry=self.registry_model,
                                                         name=target_form_name)
        except RegistryForm.DoesNotExist:
            target_form_model = None

        try:
            target_section_model = Section.objects.get(
                code=target_section_code)
        except Section.DoesNotExist:
            target_section_model = None

        try:
            target_cde_model = CommonDataElement.objects.get(
                code=target_cde_code)
        except CommonDataElement.DoesNotExist:
            target_cde_model = None

        if None in [target_form_model, target_section_model, target_cde_model]:
            return "%s/%s/%s" % (target_form_name,
                                 target_section_code,
                                 target_cde_code)
        else:
            return "%s/%s/%s" % (target_form_model.name,
                                 target_section_model.display_name,
                                 target_cde_model.name)


class _Multisection(object):

    def __init__(self, registry_model, questionnaire, form_name, section_code):
        self.pos = None
        self.is_address = section_code == "PatientDataAddressSection"
        self.registry_model = registry_model
        self.humaniser = Humaniser(registry_model)
        self.questionnaire = questionnaire
        self.form_name = form_name
        self.section_code = section_code
        self.target = self._get_target()
        self.src_id = "test"
        self.is_multi = True
        self.items = []

    def _get_target(self):
        if self.is_address:
            self.form_model = None
            self.section_model = None
            return TargetCDE("Addresses", "Demographics/Addresses")

        t = self.questionnaire.questionnaire_reverse_mapper.parse_generated_section_code(
            self.section_code)

        original_form_name = t[0]
        original_section_code = t[1]
        self.form_model = RegistryForm.objects.get(name=original_form_name,
                                                   registry=self.registry_model)
        self.section_model = Section.objects.get(
            code=original_section_code)
        original_display_name = "%s/%s" % (self.form_model.name,
                                           self.section_model.display_name)

        multisection_expression = "$ms/%s/%s/items" % (original_form_name,
                                                       original_section_code)
        target = TargetCDE(original_display_name,
                           multisection_expression)
        return target

    @property
    def field_expression(self):
        return self.target.field_expression

    @property
    def name(self):
        return self.target.display_name

    @property
    def value(self):
        # Eg Multisection like this with two items:
        #
        # ITEM 1:
        # DRUG_NAME Neurophen
        # DRUG_DOSE 22
        #
        # ITEM 2:
        # DRUG_NAME Aspirin
        # DRUG_DOSE 10
        # returns list of (ordered)maps as value
        # [{"DRUG_NAME": "Neurophen", "DRUG_DOSE": 22}, ..]

        return [item.value_map for item in self.items]


class _MultiSectionItem(object):

    def __init__(
            self,
            registry_model,
            target_form_model,
            target_section_model,
            value_map,
            is_address=False):
        self.registry_model = registry_model
        self.form_model = target_form_model
        self.section_model = target_section_model
        self.humaniser = Humaniser(registry_model)
        self.value_map = value_map
        self.is_address = is_address

    @property
    def answer(self):
        fields = []
        for cde_code in self.value_map:
            cde_model = CommonDataElement.objects.get(code=cde_code)
            display_name = cde_model.name
            raw_value = self.value_map[cde_code]
            if not self.is_address:
                display_value = self.humaniser.display_value2(self.form_model,
                                                              self.section_model,
                                                              cde_model,
                                                              raw_value)
            else:
                if cde_code == "AddressType":
                    display_value = raw_value.replace("AddressType", "")
                else:
                    display_value = raw_value

            fields.append("%s=%s" % (display_name, display_value))

        csv = ",".join(fields)
        return csv


class Questionnaire(object):
    """
    A questionnaire is a single public web form
    whose questions derive from several clinical\
    forms and where the wording of questions is potentially
    different.
    Curators "APPROVE" questionnaires causes either:
    A) Creation of a new patient is created from the data
    B) Update of an existing patient's data

    This class wraps data entered for a questionnaire to allow A and B easily
    from the view.
    """

    def __init__(self, registry_model, questionnaire_response_model):
        self.registry_model = registry_model
        self.questionnaire_response_model = questionnaire_response_model
        self.data = self.questionnaire_response_model.data

        self.questionnaire_reverse_mapper = QuestionnaireReverseMapper(self.registry_model,
                                                                       None,
                                                                       self.data)
        # self.patient_creator = PatientCreator()

    @property
    def questions(self):
        lst = []
        n = 0

        for consent_question in self._get_consents():
            consent_question.pos = n
            lst.append(consent_question)
            n += 1

        for form_dict in self.data["forms"]:
            for section_dict in form_dict["sections"]:
                if not section_dict["allow_multiple"]:
                    for cde_dict in section_dict["cdes"]:
                        question = _Question(self.registry_model,
                                             self,
                                             form_dict["name"],
                                             section_dict["code"],
                                             cde_dict["code"],
                                             cde_dict["value"])

                        n += 1
                        question.pos = n
                        lst.append(question)

                else:
                    # unit of selection is the entire section ..
                    n += 1
                    multisection = _Multisection(self.registry_model,
                                                 self,
                                                 form_dict["name"],
                                                 section_dict["code"])

                    for item in section_dict["cdes"]:
                        value_map = OrderedDict()
                        # each item is a list of cde dicts
                        for cde_dict in item:
                            value_map[cde_dict["code"]] = cde_dict["value"]

                        multisection_item = _MultiSectionItem(self.registry_model,
                                                              multisection.form_model,
                                                              multisection.section_model,
                                                              value_map,
                                                              multisection.is_address)
                        multisection.items.append(multisection_item)

                    multisection.pos = n
                    lst.append(multisection)

        return self._correct_ordering(lst)

    def _correct_ordering(self, questions):
        correct_ordering = ["Centre",
                            "Family Name",
                            "Given Names",
                            "Date of Birth",
                            "Sex",
                            "Home Phone",
                            "Mobile Phone",
                            "Email",
                            "Parent/Guardian Family Name",
                            "Parent/Guardian Given Names",
                            "Parent/Guardian Relationship",
                            "Parent/Guardian Email",
                            "Parent/Guardian Address",
                            "Parent/Guardian Suburb"
                            "Parent/Guardian State"
                            "Parent/Guardian Country"]

        consent_block = []
        for question in list(questions):
            if question.name.startswith("Consent"):
                consent_block.append(question)
                questions.remove(question)

        demographics_block = []
        for name in correct_ordering:
            for question in list(questions):
                if question.name == name:
                    demographics_block.append(question)
                    questions.remove(question)

        new_ordering = consent_block + demographics_block + questions
        return new_ordering

    def _get_consents(self):
        # Clinical record looks like in questionnaire - ( NB not in Patients ...):
        # for patients , the consent data stored in django models
        # question
        # "customconsent_%s_%s_%s" % (registry_model.pk, consent_section_model.pk, self.pk)
        # "custom_consent_data" : {
        # "customconsent_2_2_3" : "on",
        # "customconsent_2_2_6" : "on",
        # "customconsent_2_2_5" : "on",
        # "customconsent_2_2_4" : "on",
        # "customconsent_2_1_1" : "on",
        # "customconsent_2_1_2" : "on"

        consents = []

        if CONSENTS_SECTION in self.data:
            consent_block = self.data[CONSENTS_SECTION]
            for key in consent_block:
                _, x, y, z = key.split("_")
                raw_value = consent_block[key]
                consent_question = _ConsentQuestion(self.registry_model,
                                                    key,
                                                    raw_value)

                consents.append(consent_question)

        return consents

    def existing_data(self, patient_model):
        return _ExistingDataWrapper(self.registry_model,
                                    patient_model,
                                    self,
                                    )

    def update_patient(self, patient_model, selected_questions):
        # NB. here that the _original_ target form needs to be updated ( the source of the question )
        # NOT the dynamically generated questionnaire form's version ...
        errors = []

        non_multi_updates = [(q.target.field_expression, q.value)
                             for q in selected_questions if not q.is_multi]

        single_errors = patient_model.update_field_expressions(
            self.registry_model, non_multi_updates)

        errors.extend(single_errors)
        multisection_questions = [q for q in selected_questions if q.is_multi]

        def correct_structure(ordered_dicts):
            # multisection expects different structure to what was being persisted:
            # what this function receives:
            # a list of (ordered) dictionaries like:
            # [ {"DrugName": "Aspirin", "DrugDose": 23},
            #   {"DrugName": "Neurophen","DrugDose": 100}]
            # ( i.e. 2 section items in the multisection )
            # The structure actually used in the clinical forms is:
            # in the multisection record would be:
            # cdes: [  [ {"code": "DrugName", "value": "Aspirin"}, {"code": "DrugDose",
            # "value" : 23 } ],  [ {"code" "DrugName", "value": "Neurophen"},
            # {"code": "DrugDose", "value": 100}]]

            items = []
            for ordered_dict in ordered_dicts:
                item = []
                for cde_code, cde_value in ordered_dict.items():
                    cde_dict = {}
                    cde_dict["code"] = cde_code
                    cde_dict["value"] = cde_value
                    item.append(cde_dict)
                items.append(item)
            return items

        for q in multisection_questions:
            try:
                if not q.field_expression.startswith("Demographics/"):
                    items = correct_structure(q.value)
                else:
                    items = q.value
                patient_model.evaluate_field_expression(self.registry_model,
                                                        q.field_expression,
                                                        value=items)
            except Exception as ex:
                msg = "Error setting field expression %s: %s" % (
                    q.field_expression, ex)
                errors.append(msg)

        try:
            patient_model.save()
        except Exception as ex:
            msg = "Error saving patient for questionnaire update: %s" % ex
            errors.append(msg)

        num_errors = len(errors)

        if num_errors == 0:
            logger.info(
                "Questionnaire update of Patient %s succeeded without error." %
                getattr(patient_model, settings.LOG_PATIENT_FIELDNAME))
        else:
            logger.warning("Questionnaire update of Patient %s had %s errors: " % (
                getattr(patient_model, settings.LOG_PATIENT_FIELDNAME), num_errors))
            for msg in errors:
                logger.error("Questionnaire update error: %s" % msg)

        return errors
