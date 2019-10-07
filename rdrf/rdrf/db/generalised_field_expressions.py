from django.conf import settings
from rdrf.services.io.reporting import report_field_functions
from registry.patients.models import Patient, PatientAddress
from rdrf.models.definition.models import ConsentSection, ConsentQuestion
from rdrf.models.definition.models import RegistryForm, Section, CommonDataElement
from rdrf.helpers.utils import get_cde_value
from collections import OrderedDict

import logging
import collections

logger = logging.getLogger(__name__)


class FieldExpressionError(Exception):
    pass


class GeneralisedFieldExpression(object):

    def __init__(self, registry_model):
        self.registry_model = registry_model
        self.valid = True

    def __call__(self, patient_model, mongo_data):
        try:
            return self.evaluate(patient_model, mongo_data)
        except Exception as ex:
            logger.error("Error evaluating %s for %s: %s" % (self.__class__.__name__,
                                                             getattr(patient_model, settings.LOG_PATIENT_FIELDNAME),
                                                             ex))
            return "??ERROR??"

    def evaluate(self, patient_model, mongo_data):
        raise NotImplementedError("subclass responsibility!")

    def set_value(self, patient_model, mongo_data, new_value, **kwargs):
        raise NotImplementedError("subclass responsibility!")


class ClearMultiSectionExpression(GeneralisedFieldExpression):
    # "$op/<FORMNAME>/<SECTIONCODE>/clear"

    def __init__(self, registry_model, form_model, section_model):
        self.registry_model = registry_model
        self.form_model = form_model
        if not section_model.allow_multiple:
            raise Exception(
                "Can't create a multisection expression from nonmultisection)")
        self.section_model = section_model

    def evaluate(self, patient_model, mongo_data):
        for form_dict in mongo_data["forms"]:
            if form_dict["name"] == self.form_model.name:
                for section_dict in form_dict["sections"]:
                    if section_dict["code"] == self.section_model.code and section_dict["allow_multiple"]:
                        # cdes key holds _items_
                        section_dict["cdes"] = []
                    else:
                        raise Exception(
                            "Can't clear items of a non-multisection as there aren't any!")

        return patient_model, mongo_data


class MultiSectionItemsExpression(GeneralisedFieldExpression):
    # "$op/<FORMNAME>/<SECTIONCODE/items"

    def __init__(self, registry_model, form_model, section_model):
        self.registry_model = registry_model
        self.form_model = form_model
        self.section_model = section_model
        if not self.section_model.allow_multiple:
            raise Exception(
                "items not defined for non multisection %s" %
                self.section_model.code)

    def evaluate(self, patient_model, mongo_data):
        # return items ( dictionaries of cde code --> values ) for each added multisection item
        if mongo_data is None:
            return []

        items = []

        for form_dict in mongo_data["forms"]:
            if form_dict["name"] == self.form_model.name:
                for section_dict in form_dict["sections"]:
                    if section_dict["code"] == self.section_model.code:
                        if not section_dict["allow_multiple"]:
                            raise Exception(
                                "section %s is not multiple in data" %
                                section_dict["code"])
                        else:
                            for cde_dict_list in section_dict["cdes"]:
                                cde_map = OrderedDict()
                                for cde_dict in cde_dict_list:
                                    cde_map[cde_dict["code"]] = cde_dict["value"]
                                items.append(cde_map)
        return items

    def set_value(self, patient_model, mongo_data, replacement_items, **kwargs):
        # mongo data must be _nested_

        if mongo_data is None:
            mongo_data = {"forms": [{"name": self.form_model.name,
                                     "sections": [{"code": self.section_model.code,
                                                   "allow_multiple": True,
                                                   "cdes": replacement_items}]}]}
            return patient_model, mongo_data

        else:

            form_exists = False
            section_exists = False
            for form_dict in mongo_data["forms"]:
                if form_dict["name"] == self.form_model.name:
                    form_exists = True
                    for section_dict in form_dict["sections"]:
                        if section_dict["code"] == self.section_model.code:
                            section_exists = True
                            section_dict["cdes"] = replacement_items
                            return patient_model, mongo_data
                    if not section_exists:
                        section_dict = {"code": self.section_model.code,
                                        "allow_multiple": True,
                                        "cdes": replacement_items}
                        form_dict["sections"].append(section_dict)
                        return patient_model, mongo_data
            if not form_exists:
                form_dict = {"name": self.form_model.name,
                             "sections": [{"code": self.section_model.code,
                                           "allow_multiple": True,
                                           "cdes": replacement_items}]
                             }
                mongo_data["forms"].append(form_dict)
                return patient_model, mongo_data


class AddMultiSectionItemExpression(GeneralisedFieldExpression):
    # "$op/<FORMNAME>/<SECTIONCODE/add"

    def __init__(self, registry_model, form_model, section_model):
        self.registry_model = registry_model
        self.form_model = form_model
        if not section_model.allow_multiple:
            raise Exception(
                "Can't create a multisection expression from nonmultisection")
        else:
            self.section_model = section_model

    def set_value(self, patient_model, mongo_data, item_cde_map, **kwargs):
        # add new item which is a list of cde dicts
        item = []
        for cde_code in item_cde_map:
            value = item_cde_map[cde_code]
            cde_dict = {"code": cde_code,
                        "value": value}
            item.append(cde_dict)

        for form_dict in mongo_data["forms"]:
            if form_dict["name"] == self.form_model.name:
                for section_dict in form_dict["sections"]:
                    if section_dict["code"] == self.section_model.code:
                        if section_dict["allow_multiple"]:
                            section_dict["cdes"].append(item)
                        else:
                            raise Exception("cannot add an item to a non multisection!")
        return patient_model, mongo_data


class PokeFieldExpression(GeneralisedFieldExpression):
    # "[pick|poke]/<FORMNAME>/<SECTIONCODE/items/2/CDECODE"
    # returns the value of CDECODE in the 2nd item
    #

    def __init__(self, registry_model, field_expression):
        self.registry_model = registry_model
        self._parse_poke(field_expression)

    def _parse_poke(self, field_expression):
        # e.g. poke/<FORMNAME>/<SECTIONCODE>/2/<CDECODE>
        # means the value of the cde CDECODE in the second item of
        # FORMNAME, SECTIONCODE  - set_value will update
        _, form_name, section_code, item_num_string, cde_code = field_expression.split("/")
        self.item_number = int(item_num_string)
        self.form_model = RegistryForm.objects.get(registry=self.registry_model,
                                                   name=form_name)
        self.section_model = self._get_section_model(section_code)
        self.cde_model = self._get_cde_model(cde_code)

        if self.section_model not in self.form_model.section_models:
            raise Exception("section not in form")

        if self.cde_model not in self.section_model.cde_models:
            raise Exception("cde not in section")

    def _get_section_model(self, section_code):
        for section_model in self.form_model.section_models:
            if section_model.code == section_code:
                return section_model

    def _get_cde_model(self, cde_code):
        for cde_model in self.section_model.cde_models:
            if cde_model.code == cde_code:
                return cde_model

    def evaluate(self, patient_model, mongo_data):
        if mongo_data is not None:
            return self._iterate_through_forms(mongo_data)

        raise ValueError("cde not found")

    def _iterate_through_forms(self, mongo_data, **kwargs):
        is_setting = "value" in kwargs

        for form_dict in mongo_data["forms"]:
            if form_dict["name"] == self.form_model.name:
                if self.section_model.code not in [x["code"] for x in form_dict["sections"]]:
                    if is_setting:
                        section_dict = {"code": self.section_model.code,
                                        "allow_multiple": self.section_model.allow_multiple
                                        }

                        cde_dict = {"code": self.cde_model.code,
                                    "value": kwargs["value"]}

                        if self.section_model.allow_multiple:
                            item = [cde_dict]
                            items = [item]
                            section_dict["cdes"] = items
                        else:
                            section_dict["cdes"] = [cde_dict]
                        form_dict["sections"].append(section_dict)
                        return True

                for section_dict in form_dict["sections"]:
                    if section_dict["code"] == self.section_model.code:
                        if not section_dict["allow_multiple"]:
                            raise Exception("Can't get cde in item if not a multisection")
                        else:
                            if len(section_dict["cdes"]) == 0:
                                # if we're setting, create an item with one cde
                                if is_setting:
                                    cde_dict = {"code": self.cde_model.code,
                                                "value": kwargs["value"]}
                                    item = [cde_dict]
                                    items = [item]
                                    section_dict["cdes"] = items
                                    return True

                            for item_index, cde_dict_list in enumerate(section_dict["cdes"]):
                                num = item_index + 1
                                if num == self.item_number:
                                    if is_setting:
                                        if self.cde_model.code not in [
                                                x["code"] for x in cde_dict_list]:
                                            # missing cde dict in correct item
                                            cde_dict = {"code": self.cde_model.code,
                                                        "value": kwargs["value"]}
                                            cde_dict_list.append(cde_dict)
                                            return True

                                    for cde_dict in cde_dict_list:
                                        if cde_dict["code"] == self.cde_model.code:
                                            if is_setting:
                                                cde_dict["value"] = kwargs["value"]
                                                return True
                                            else:
                                                return cde_dict["value"]

        if is_setting:
            return False
        else:
            raise ValueError("can't retrieve value")

    def set_value(self, patient_model, mongo_data, new_value, **kwargs):

        if mongo_data is None:
            if self.item_number == 1:
                item = {"code": self.cde_model.code,
                        "value": new_value}

                items = [item]
                mongo_data = {"forms": [{"name": self.form_model.name,
                                         "sections": [{"code": self.section_model.code,
                                                       "allow_multiple": True,
                                                       "cdes": items}]}]}

            else:
                raise ValueError("Can't update item %s as there is no data" % self.item_number)

        else:
            # this updates the clinical data
            succeeded = self._iterate_through_forms(mongo_data, value=new_value)
            # if we couldn't poke the right item, fail
            if not succeeded:
                raise ValueError("can't update this cde")
            else:
                return patient_model, mongo_data


class BadColumnExpression(GeneralisedFieldExpression):
    # used when a column parse fails

    def __init__(self):
        pass

    def evaluate(self, patient_model, mongo_data):
        return "??COLUMNERROR??"


class PatientFieldExpression(GeneralisedFieldExpression):

    def __init__(self, registry_model, field):
        self.registry_model = registry_model
        self.field = field

    def evaluate(self, patient_model, mongo_data):
        if self.field == "next_of_kin_relationship":
            return patient_model.next_of_kin_relationship.relationship
        elif self.field == "working_groups":
            return [wg for wg in patient_model.working_groups.all()]

        return getattr(patient_model, self.field)

    def set_value(self, patient_model, mongo_data, new_value, **kwargs):
        if self.field == "next_of_kin_relationship":
            self._set_next_of_kin_relationship(patient_model, new_value)
        elif self.field == "working_groups":
            from registry.groups.models import WorkingGroup
            if isinstance(new_value, str):
                try:
                    working_group = WorkingGroup.objects.get(registry=self.registry_model,
                                                             name=new_value)
                    patient_model.working_groups.set([working_group])
                    patient_model.save()
                except WorkingGroup.DoesNotExist:
                    logger.error("Working group %s does not exist" % new_value)
                    from django.conf import settings
                    raise Exception("can't update working group on %s" % getattr(patient_model, settings.LOG_PATIENT_FIELDNAME))
            elif isinstance(new_value, WorkingGroup):
                patient_model.working_groups.set([new_value])
                patient_model.save()
            else:
                logger.error("can't update working group to %s" % new_value)
                raise Exception("can't update working group on %s" % getattr(patient_model, settings.LOG_PATIENT_FIELDNAME))

        else:
            setattr(patient_model, self.field, new_value)
        return patient_model, mongo_data

    def _set_next_of_kin_relationship(self, patient_model, new_value):
        from registry.patients.models import NextOfKinRelationship
        try:
            nok_rel = NextOfKinRelationship.objects.get(relationship=new_value)
        except NextOfKinRelationship.DoesNotExist:
            nok_rel = NextOfKinRelationship()
            nok_rel.relationship = new_value
            nok_rel.save()
        patient_model.next_of_kin_relationship = nok_rel


class ConsentExpression(GeneralisedFieldExpression):

    def __init__(self, registry_model, consent_question_model, field):
        super(ConsentExpression, self).__init__(registry_model)
        self.consent_question_model = consent_question_model
        self.field = field

    def evaluate(self, patient_model, mongo_data):
        return patient_model.get_consent(self.consent_question_model, self.field)

    def set_value(self, patient_model, mongo_data, new_value, **kwargs):
        # must be answer field , True False for new_value
        # ignores applicability?!
        if self.field not in ["answer", "last_update", "first_save"]:
            raise ValueError("Unknown consent field: %s" % self.field)

        from registry.patients.models import ConsentValue
        try:
            consent_value_model = ConsentValue.objects.get(
                patient=patient_model, consent_question=self.consent_question_model)
            # allow answer, first_save, last_update now
            setattr(consent_value_model, self.field, new_value)
            consent_value_model.save()
        except ConsentValue.DoesNotExist:
            consent_value_model = ConsentValue()
            consent_value_model.patient = patient_model
            consent_value_model.consent_question = self.consent_question_model
            consent_value_model.answer = new_value
            consent_value_model.save()
        return patient_model, mongo_data


class ReportExpression(GeneralisedFieldExpression):

    def __init__(self, registry_model, func):
        self.registry_model = registry_model
        self.func = func

    def evaluate(self, patient_model, mongo_data):
        return self.func(patient_model)


class AddressExpression(GeneralisedFieldExpression):

    def __init__(self, registry_model, address_type_model, field):
        self.registry_model = registry_model
        self.address_type_model = address_type_model
        self.field = field

    def evaluate(self, patient_model, mongo_data):

        try:
            address_model = PatientAddress.objects.get(patient=patient_model,
                                                       address_type=self.address_type_model)
        except PatientAddress.DoesNotExist:
            return None

        return getattr(address_model, self.field.lower())


class AddressesExpression(GeneralisedFieldExpression):
    # Demographics/Addresses

    def __init__(self, registry_model):
        self.registry_model = registry_model

    def evaluate(self, patient_model, mongo_data):
        return [
            address_object for address_object in PatientAddress.objects.filter(
                patient=patient_model)]

    def set_value(self, patient_model, mongo_record, address_maps, **kwargs):
        # address = models.TextField()
        # suburb = models.CharField(max_length=100, verbose_name="Suburb/Town")
        # state = models.CharField(max_length=50, verbose_name="State/Province/Territory")
        # postcode = models.CharField(max_length=50)
        # country = models.CharField(max_length=100)

        # addresses = [OrderedDict([(u'State', u'AU-NSW'), (u'AddressType', u'AddressTypeHome'), (u'Address', u'11 Green Street'),
        # (u'postcode', u'2042'), (u'SuburbTown', u'Newtown'),
        # (u'Country', u'AU')]), OrderedDict([(u'State', u'AU-NSW'),
        # (u'AddressType', u'AddressTypePostal'), (u'Address', u'23 Station Street'), (u'postcode', u'2000'), (u'SuburbTown', u'Sydney'), (u'Country', u'AU')])]

        # delete existing addresses ...
        from registry.patients.models import PatientAddress
        for patient_address in PatientAddress.objects.filter(patient=patient_model):
            patient_address.delete()

        for address_map in address_maps:
            patient_address = PatientAddress(patient=patient_model)
            address_type = address_map.get("AddressType", "AddressTypeHome")
            address_type_object = self._get_address_type(address_type)
            patient_address.address_type = address_type_object
            patient_address.address = address_map.get("Address", "")
            patient_address.suburb = address_map.get("SuburbTown", "")
            patient_address.postcode = address_map.get("postcode", "")
            patient_address.state = address_map.get("State", "")
            patient_address.country = address_map.get("Country", "")
            patient_address.save()

        return patient_model, mongo_record

    def _get_address_type(self, address_type):
        if address_type.startswith("AddressType"):
            address_type = address_type.replace("AddressType", "")
        from registry.patients.models import AddressType
        for x in AddressType.objects.all():
            if address_type.lower() in x.description.lower():
                return x

        types = [a for a in AddressType.objects.all().order_by("description")]
        if len(types) > 0:
            return types[0]


class ClinicalFormExpression(GeneralisedFieldExpression):

    def __init__(self, registry_model, form_model, section_model, cde_model):
        self.registry_model = registry_model
        self.form_model = form_model
        self.section_model = section_model
        self.cde_model = cde_model

    def evaluate(self, patient_model, mongo_record):
        return get_cde_value(self.form_model, self.section_model, self.cde_model, mongo_record)

    def set_value(self, patient_model, mongo_record, new_value, **kwargs):
        from datetime import datetime
        from rdrf.db.contexts_api import RDRFContextManager
        context_id = kwargs.get("context_id", None)
        if context_id is None:
            context_manager = RDRFContextManager(self.registry_model)
            default_context_model = context_manager.get_or_create_default_context(
                patient_model)
            context_id = default_context_model.pk

        if not self.section_model.allow_multiple:
            if mongo_record is None:
                # create a new blank record
                section_dict = {
                    "code": self.section_model.code,
                    "cdes": [{"code": self.cde_model.code,
                              "value": new_value}],
                    "allow_multiple": False}

                form_timestamp_key = "%s_timestamp" % self.form_model.name
                form_timestamp_value = datetime.now()

                form_dict = {"name": self.form_model.name,
                             form_timestamp_key: form_timestamp_value,
                             "sections": [section_dict]}

                mongo_record = {"forms": [form_dict],
                                "django_id": patient_model.pk,
                                "django_model": "Patient",
                                "context_id": context_id}
                return patient_model, mongo_record
            else:
                form_exists = False
                section_exists = False
                cde_exists = False
                forms = mongo_record["forms"]

                for form_dict in forms:
                    if form_dict["name"] == self.form_model.name:
                        form_exists = True
                        for section_dict in form_dict["sections"]:
                            if section_dict["code"] == self.section_model.code:
                                section_exists = True
                                for cde_dict in section_dict["cdes"]:
                                    if cde_dict["code"] == self.cde_model.code:
                                        cde_exists = True
                                        cde_dict["value"] = new_value
                                if not cde_exists:
                                    cde_dict = {"code": self.cde_model.code,
                                                "value": new_value}
                                    section_dict["cdes"].append(cde_dict)
                        if not section_exists:
                            section_dict = {"code": self.section_model.code,
                                            "allow_multiple": False,
                                            "cdes": [{"code": self.cde_model.code,
                                                      "value": new_value}]}
                            form_dict["sections"].append(section_dict)
                if not form_exists:
                    form_timestamp_key = "%s_timestamp"
                    form_timestamp_value = datetime.now()
                    form_dict = {"name": self.form_model.name,

                                 "sections": [{"code": self.section_model.code,
                                               "allow_multiple": False,
                                               "cdes": [{"code": self.cde_model.code,
                                                         "value": new_value}]}],
                                 form_timestamp_key: form_timestamp_value}
                    mongo_record["forms"].append(form_dict)

                return patient_model, mongo_record

        else:
            # todo - NB multisection items are being replaced as a whole
            # in the questionnaire
            return patient_model, mongo_record


class GeneralisedFieldExpressionParser(object):

    def __init__(self, registry_model):
        self.registry_model = registry_model
        self.patient_fields = self._get_patient_fields()

    def _get_patient_fields(self):
        s = set([field.name for field in Patient._meta.fields])
        s.add("working_groups")
        return s

    def parse(self, field_expression):
        try:
            if field_expression.startswith("Consents/"):
                return self._parse_consent_expression(field_expression)
            elif field_expression.startswith("poke/"):
                return self._parse_poke_expression(field_expression)
            elif field_expression.startswith("@"):
                return self._parse_report_function_expression(field_expression)
            elif field_expression.startswith("$ms"):
                return self._parse_ms_expression(field_expression)
            elif field_expression.startswith("Demographics/Address/"):
                return self._parse_address_expression(field_expression)
            elif field_expression == "Demographics/Addresses":
                return AddressesExpression(self.registry_model)
            elif "/" in field_expression:
                return self._parse_clinical_form_expression(field_expression)
            elif field_expression in self.patient_fields:
                return self._parse_patient_fields_expression(field_expression)
            else:
                return BadColumnExpression()

        except Exception as ex:
            logger.error("Error parsing %s: %s" % (field_expression, ex))
            return BadColumnExpression()

    def _parse_poke_expression(self, field_expression):
        return PokeFieldExpression(self.registry_model, field_expression)

    def _parse_patient_fields_expression(self, field_expression):
        return PatientFieldExpression(self.registry_model, field_expression)

    def _parse_ms_expression(self, field_expression):
        try:
            if field_expression.startswith("pick/") or field_expression.startswith("poke/"):
                return self._parse_poke_expression(field_expression)

            ms_designator, form_name, multisection_code, action_code = field_expression.split(
                "/")
        except ValueError:
            raise FieldExpressionError("Cannot parse multisection expression")

        try:
            form_model = RegistryForm.objects.get(name=form_name,
                                                  registry=self.registry_model)
        except RegistryForm.DoesNotExist:
            raise FieldExpressionError("Cannot find form %s" % form_name)

        try:
            section_model = Section.objects.get(code=multisection_code)
        except Section.DoesNotExist:
            raise FieldExpressionError("Cannot find section %s" % multisection_code)

        if action_code == "clear":
            return ClearMultiSectionExpression(self.registry_model,
                                               form_model,
                                               section_model)
        elif action_code == "add":
            return AddMultiSectionItemExpression(self.registry_model,
                                                 form_model,
                                                 section_model)
        elif action_code == "items":
            return MultiSectionItemsExpression(self.registry_model,
                                               form_model,
                                               section_model)
        else:
            raise FieldExpressionError("ms expression not understood: %s" % field_expression)

    def _parse_consent_expression(self, consent_expression):
        """
        Consents/ConsentSectionCode/ConsentQuestionCode/field
        """
        try:
            _, consent_section_code, consent_code, consent_field = consent_expression.split(
                "/")
        except ValueError as ex:
            raise FieldExpressionError(
                "couldn't split consent %s %s" % (consent_expression, ex))

        if consent_field not in ["answer", "last_update", "first_save"]:
            raise FieldExpressionError("consent field not recognised")

        try:
            consent_section_model = ConsentSection.objects.get(code=consent_section_code,
                                                               registry=self.registry_model)
        except ConsentSection.DoesNotExist:
            raise FieldExpressionError("consent section does not exist")

        try:
            consent_question_model = ConsentQuestion.objects.get(code=consent_code,
                                                                 section=consent_section_model)
        except ConsentQuestion.DoesNotExist:
            raise FieldExpressionError("consent question does not exist")

        return ConsentExpression(self.registry_model,
                                 consent_question_model,
                                 consent_field)

    def _parse_report_function_expression(self, field_expression):
        """
        @some_function_name
        """
        try:
            func = getattr(report_field_functions, field_expression[1:])
            if isinstance(func, collections.Callable) and hasattr(
                    func, "report_function") and func.report_function:
                return ReportExpression(self.registry_model, func)
            else:
                raise FieldExpressionError(
                    "Unknown field expression: %s" % field_expression)
        except Exception as ex:
            raise FieldExpressionError(
                "report field expression error: %s" % ex)

    def _parse_address_expression(self, address_expression):
        """
        Demographics/Address/Home/Address
        Demographics/Address/Home/Suburb
        Demographics/Address/Home/State
        Demographics/Address/Home/State
        Demographics/Address/Home/Country
        Demographics/Address/Postal/Address
        Demographics/Address/Postal/Suburb
        Demographics/Address/Postal/State
        Demographics/Address/Postal/Country
        """
        from registry.patients.models import AddressType
        try:
            _, _, address_type, field = address_expression.split("/")
        except ValueError:
            raise FieldExpressionError(
                "can't parse address expression: %s" % address_expression)

        if address_type not in ["Home", "Postal"]:
            raise FieldExpressionError(
                "Unknown address type: %s" % address_type)
        if field not in ["Address", "Suburb", "State", "Country", "Postcode"]:
            raise FieldExpressionError("Unknown address field: %s" % field)

        try:
            address_type_model = AddressType.objects.get(type=address_type)
        except AddressType.DoesNotExist:
            raise FieldExpressionError(
                "Address type does not exist: %s" % address_type)

        return AddressExpression(self.registry_model, address_type_model, field)

    def _parse_clinical_form_expression(self, field_expression):
        """
        ClinicalFormName/SectionCode/CDECode
        """
        form_name, section_code, cde_code = field_expression.split("/")
        form_model = RegistryForm.objects.get(
            name=form_name, registry=self.registry_model)
        section_model = Section.objects.get(code=section_code)
        cde_model = CommonDataElement.objects.get(code=cde_code)

        return ClinicalFormExpression(self.registry_model,
                                      form_model,
                                      section_model,
                                      cde_model)
