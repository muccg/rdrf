from rdrf import report_field_functions
from registry.patients.models import Patient, PatientAddress
from rdrf.models import ConsentSection, ConsentQuestion
from rdrf.models import RegistryForm, Section, CommonDataElement
from rdrf.utils import get_cde_value
import logging

logger = logging.getLogger("registry_log")


class FieldExpressionError(Exception):
    pass


class GeneralisedFieldExpression(object):

    def __init__(self, registry_model):
        self.registry_model = registry_model
        self.valid = True

    def __call__(self, patient_model, mongo_data):
        try:
            return self.evaluate(patient_model, mongo_data)
        except Exception, ex:
            logger.error("Error evaluating %s for %s: %s" % (self.__class__.__name__,
                                                             patient_model.pk,
                                                             ex))
            return "??ERROR??"

    def evaluate(self, patient_model, mongo_data):
        raise NotImplementedError("subclass responsibility!")


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
        return getattr(patient_model, self.field)


class ConsentExpression(GeneralisedFieldExpression):

    def __init__(self, registry_model, consent_question_model, field):
        super(ConsentExpression, self).__init__(registry_model)
        self.consent_question_model = consent_question_model
        self.field = field

    def evaluate(self, patient_model, mongo_data):
        return patient_model.get_consent(self.consent_question_model, self.field)


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


class ClinicalFormExpression(GeneralisedFieldExpression):

    def __init__(self, registry_model, form_model, section_model, cde_model):
        self.registry_model = registry_model
        self.form_model = form_model
        self.section_model = section_model
        self.cde_model = cde_model

    def evaluate(self, patient_model, mongo_record):
        return get_cde_value(self.form_model, self.section_model, self.cde_model, mongo_record)


class GeneralisedFieldExpressionParser(object):

    def __init__(self, registry_model):
        self.registry_model = registry_model
        self.patient_fields = self._get_patient_fields()

    def _get_patient_fields(self):
        return set([field.name for field in Patient._meta.fields])

    def parse(self, field_expression):
        try:
            if field_expression.startswith("Consents/"):
                return self._parse_consent_expression(field_expression)
            elif field_expression.startswith("@"):
                return self._parse_report_function_expression(field_expression)
            elif field_expression.startswith("Demographics/Address/"):
                return self._parse_address_expression(field_expression)
            elif "/" in field_expression:
                return self._parse_clinical_form_expression(field_expression)
            elif field_expression in self.patient_fields:
                return self._parse_patient_fields_expression(field_expression)
            else:
                return BadColumnExpression()

        except Exception, ex:
            logger.error("Error parsing %s: %s" % (field_expression, ex))
            return BadColumnExpression()

    def _parse_patient_fields_expression(self, field_expression):
        return PatientFieldExpression(self.registry_model, field_expression)

    def _parse_consent_expression(self, consent_expression):
        """
        Consents/ConsentSectionCode/ConsentQuestionCode/field
        """
        try:
            _, consent_section_code, consent_code, consent_field = consent_expression.split(
                "/")
        except ValueError, ex:
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
            if callable(func) and hasattr(func, "report_function") and func.report_function:
                return ReportExpression(self.registry_model, func)
            else:
                raise FieldExpressionError(
                    "Unknown field expression: %s" % field_expression)
        except Exception, ex:
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
        Demographics/Address/Postal/State
        Demographics/Address/Postal/Country
        """
        from registry.patients.models import PatientAddress, AddressType
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
