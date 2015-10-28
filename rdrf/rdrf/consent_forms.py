from django import forms
from rdrf.models import Registry
from rdrf.models import ConsentSection
from rdrf.models import ConsentQuestion
from registry.patients.models import Patient
from django.utils.datastructures import SortedDict

import logging

logger = logging.getLogger("registry_log")


def _get_consent_field_models(consent_field):
    logger.debug("getting consent field models for %s" % consent_field)
    _, reg_pk, sec_pk, q_pk = consent_field.split("_")

    registry_model = Registry.objects.get(pk=reg_pk)
    consent_section_model = ConsentSection.objects.get(pk=sec_pk)
    consent_question_model = ConsentQuestion.objects.get(pk=q_pk)

    return registry_model, consent_section_model, consent_question_model


class BaseConsentForm(forms.BaseForm):
        def __init__(self, *args, **kwargs):
            self.patient_model = kwargs["patient_model"]
            del kwargs["patient_model"]
            self.registry_model = kwargs['registry_model']
            del kwargs['registry_model']
            super(BaseConsentForm, self).__init__(*args, **kwargs)

        def _get_consent_section(self, consent_section_model):
            # return something like this for custom consents
            # consent = ("Consent", [
            #     "consent",
            #     "consent_clinical_trials",
            #     "consent_sent_information",
            # ])

            questions = []

            for field in self.fields:
                if field.startswith("customconsent_"):
                    parts = field.split("_")
                    reg_pk = int(parts[1])
                    if reg_pk == self.registry_model.pk:
                        consent_section_pk = int(parts[2])
                        if consent_section_pk == consent_section_model.pk:
                            consent_section_model = ConsentSection.objects.get(
                                pk=consent_section_pk)
                            questions.append(field)
            return (
                "%s %s" %
                (self.registry_model.code.upper(),
                 consent_section_model.section_label),
                questions)

        def get_consent_sections(self):
            section_tuples = []
            for consent_section_model in self.registry_model.consent_sections.all().order_by("code"):
                if consent_section_model.applicable_to(self.patient_model):
                    section_tuples.append(
                        self._get_consent_section(consent_section_model))
            return section_tuples


class CustomConsentFormGenerator(object):

    def __init__(self, registry_model, patient_model=None):
        self.registry_model = registry_model
        self.patient_model = patient_model  # None if add form
        self.fields = {}

    def create_form(self):
        form_dict = {"base_fields": self._create_custom_consent_fields()}
        form_class = type("PatientConsentForm", (BaseConsentForm,), form_dict)
        form_instance = form_class(patient_model=self.patient_model, registry_model=self.registry_model)
        return form_instance

    def _create_custom_consent_fields(self):
        fields = SortedDict()
        for consent_section_model in self.registry_model.consent_sections.all():
            logger.debug("consent section model = %s" % consent_section_model)
            if consent_section_model.applicable_to(self.patient_model):
                for consent_question_model in consent_section_model.questions.all().order_by("position"):
                    consent_field = consent_question_model.create_field()
                    field_key = consent_question_model.field_key
                    fields[field_key] = consent_field
                    logger.debug("added consent field %s = %s" % (field_key, consent_field))

        logger.debug("custom consent fields = %s" % fields)
        return fields