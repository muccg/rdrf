from rdrf.models import RegistryForm, Section, CommonDataElement
from rdrf.utils import de_camelcase
from explorer.views import Humaniser
from django.core.urlresolvers import reverse
from collections import OrderedDict
from rdrf.generalised_field_expressions import GeneralisedFieldExpressionParser
from django.core.exceptions import ValidationError
from registry.patients.models import Patient
from registry.patients.models import PatientAddress, AddressType
from dynamic_data import DynamicDataWrapper
from django.conf import settings
from registry.groups.models import WorkingGroup
from django.db import transaction
from datetime import datetime, date, time
import pycountry

import logging
logger = logging.getLogger("registry_log")


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
    "CDEPatientDateOfBirth": ("date_of_birth", None),
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


class QuestionType:
    CLINICAL_SINGLE = 1
    CLINICAL_MULTI = 2
    DEMOGRAPHIC = 3
    ADDRESS = 4
    CONSENT = 5


class QuestionnaireReverseMapper(object):

    """
    Save data back into original forms from the Questionnaire Response data
    """

    def __init__(self, registry, patient, questionnaire_data):
        self.patient = patient
        self.registry = registry
        self.questionnaire_data = questionnaire_data

    def save_patient_fields(self):
        working_groups = []
        for attr, value in self._get_demographic_data():
            if attr == 'working_groups':
                working_groups = value
                continue
            logger.debug(
                "setting patient demographic field: %s = %s" % (attr, value))
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
            # AddressTypeHome --> Home etc
            value = value.replace("AddressType", "")
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

        address.state = self._get_state(
            getcde(address_map, "State"), address.country)
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
            pycountry_states = list(
                pycountry.subdivisions.get(country_code=country_code))
            for state in pycountry_states:
                logger.debug("checking state code %s" % state.code.lower())
                if state.code.lower() == state_code.lower():
                    logger.debug("found state!: %s" % state.code)
                    return state.code

            logger.debug("could not find state - returning None")
        except Exception as ex:
            logger.debug("Error setting state: state = %s country code = %s error = %s" % (
                cde_value, country_code, ex))
            logger.error("could not find state code for for %s %s" %
                         (country_code, cde_value))

    def save_dynamic_fields(self):
        wrapper = DynamicDataWrapper(self.patient)
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
                orig_item_form, orig_item_section = self.parse_generated_section_code(
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
                original_form_name, original_section_code = self.parse_generated_section_code(
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
                                             & Q(registry=self.registry))]

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

        value = KEY_MAP[cde_code]

        if isinstance(value, Func):
            function_name = value.name
            return eval(function_name)
        else:
            return value

    def _get_demographic_data(self):
        return self._get_field_data(dynamic=False)

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
        mapper = QuestionnaireReverseMapper(
            self.registry, patient, questionnaire_data)

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

        # set custom consents here as these need access to the patients
        # registr(y|ies)
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
        # RDR-667 we don't need to preserve the approved QRs once patient
        # created
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
        if field_expression in KEY_MAP.keys():
            original_expression = field_expression
            field_expression = KEY_MAP[field_expression][
                0]  # the demographic field

        retrieval_function = self.gfe_parser.parse(field_expression)
        try:
            value = retrieval_function(self.patient_model, self.patient_data)
            value = self.humaniser.display_value2(
                form_model, section_model, cde_model, value)

            if isinstance(value, datetime) or isinstance(value, date):
                value = str(value)
            return value

        except Exception, ex:
            return "Error[!%s]" % ex

    @property
    def link(self):
        demographic_link = reverse("patient_edit", args=[self.registry_model.code,
                                                         self.patient_model.pk,
                                                         self.default_context_model.pk])
        return demographic_link

    @property
    def questions(self):
        """
        If data already filled in for patient
        grab and return as list of wrappers for view
        There are two special sections PatientData and PatientAddressData
        """
        l = []
        for question in self.questionnaire.questions:

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
                except Exception, ex:
                    logger.error("could not get target for %s %s: %s" % (question.section_code,
                                                                         question.cde_code,
                                                                         ex))
                    continue

            if field_name in KEY_MAP:
                field_name = question.cde_model.name


            if not question.is_multi:
                existing_answer = {"name": field_name,
                          "pos": str(question.pos),
                          "is_multi": False,
                          "answer": self._get_field_data(field_expression, question.form_model, question.section_model, question.cde_model)}
            else:
                existing_answer = {"name": field_name,
                                   "pos" : str(question.pos),
                                   "is_multi": True,
                                   "answers": self._get_existing_multisection_data(question.field_expression,
                                                                                   question.form_model,
                                                                                   question.section_model)}
                
                                                                         

            logger.debug("existing data = %s" % existing_answer)
            l.append(existing_answer)

        return l

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
        try:
            self.form_model = RegistryForm.objects.get(registry=self.registry_model,
                                                       name=form_name)
        except RegistryForm.DoesNotExist:
            raise Exception("xxx")

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
        except Exception, ex:
            logger.error("error getting target: %s" % ex)
            return "%s/%s/%s" % (self.form_name, self.section_model.display_name, self.cde_model.name)

    def _get_display_value(self, value):
        if not self.is_multi:
            return self.humaniser.display_value2(self.form_model, self.section_model, self.cde_model, value)
        else:
            return ",".join([self.humaniser.display_value2(self.form_model, self.section_model, self.cde_model, single_value)
                     for single_value in value])

    def _get_target(self):
        """
        Return the generalised field expression that data for this field should be put into.
        This step is necessary because we decided early on to present one questionnaire form
        comprised of selected questions from potentially many clinical forms.
        """

        # the generated section code in a questionnaire encodes the original form name and
        # original section code ... ugh
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




class _MultiSectionItem(object):

    def __init__(self, registry_model, target_form_model, target_section_model, value_map):
        self.registry_model = registry_model
        self.form_model = target_form_model
        self.section_model = target_section_model
        self.humaniser = Humaniser(registry_model)
        self.value_map = value_map

    @property
    def answer(self):
        fields = []
        for cde_code in self.value_map:
            cde_model = CommonDataElement.objects.get(code=cde_code)
            display_name = cde_model.name
            raw_value = self.value_map[cde_code]
            display_value = self.humaniser.display_value2(self.form_model,
                                                          self.section_model,
                                                          cde_model,
                                                          raw_value)

            
            fields.append("%s=%s" % (display_name, display_value))
        
        csv = ",".join(fields)
        logger.debug("answer for multisection item: %s" % csv)
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
        self.registry_model=registry_model
        self.questionnaire_response_model=questionnaire_response_model
        self.data=self.questionnaire_response_model.data

        self.questionnaire_reverse_mapper=QuestionnaireReverseMapper(self.registry_model,
                                                                       None,
                                                                       self.data)
        # self.patient_creator = PatientCreator()

    def _generated_secton_code(self, original_form_name, original_section_code):
        return self.registry_model._generated_section_questionnaire_code(form_name, section_code)

    @property
    def questions(self):
        l=[]
        n=0

        for form_dict in self.data["forms"]:
            logger.debug("adding questions for %s" % form_dict["name"])
            for section_dict in form_dict["sections"]:
                if section_dict["code"] == "PatientDataAddressSection":
                    continue
                if not section_dict["allow_multiple"]:
                    logger.debug("adding section %s" % section_dict["code"])
                    for cde_dict in section_dict["cdes"]:
                        question=_Question(self.registry_model,
                                             self,
                                             form_dict["name"],
                                             section_dict["code"],
                                             cde_dict["code"],
                                             cde_dict["value"])

                        n += 1
                        question.pos=n
                        l.append(question)
                        logger.debug("question %s added" % question)

                else:
                    logger.debug(
                        "adding multisection question for section %s" % section_dict["code"])
                    # unit of selection is the entire section ..
                    n += 1
                    multisection= _Multisection(self.registry_model,
                                                 self,
                                                 form_dict["name"],
                                                 section_dict["code"])

                    for item in section_dict["cdes"]:
                        logger.debug("getting item %s" % item)
                        value_map = OrderedDict()
                        # each item is a list of cde dicts
                        for cde_dict in item:
                            value_map[cde_dict["code"]] = cde_dict["value"]

                        logger.debug("value_map = %s" % value_map)
                        
                        multisection_item = _MultiSectionItem(self.registry_model,
                                                              multisection.form_model,
                                                              multisection.section_model,
                                                              value_map)
                        multisection.items.append(multisection_item)

                    multisection.pos=n
                    l.append(multisection)
                    logger.debug("multisection %s added" % multisection.name)



        logger.debug("questions total = %s" % len(l))
        return l

    def existing_data(self, patient_model):
        return _ExistingDataWrapper(self.registry_model,
                                    patient_model,
                                    self,
                                    )

    def update_patient(self, patient_model, selected_questions):
        # begin transaction ... etc
        # NB. here that the _original_ target form needs to be updated ( the source of the question )
        # NOT the dynamically generated questionnaire form's version ...
        non_multi_updates=[(q.target.field_expression, q.value)
                            for q in selected_questions if not q.is_multi]
        patient_model.update_field_expressions(
            self.registry_model, non_multi_updates)

        multisection_questions = [q for q in selected_questions if q.is_multi]
        for q in multisection_questions:
            logger.debug("about to evaluate field expression %s" % q.field_expression)
            
            patient_model.evaluate_field_expression(self.registry_model,
                                                    q.field_expression,
                                                    value=q.value)

        patient_model.save()
        
            
        
