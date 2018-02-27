from collections import OrderedDict
from django import forms
from rdrf.models.definition.models import Registry
from rdrf.models.definition.models import ConsentSection
from rdrf.models.definition.models import ConsentQuestion
from django.utils.translation import ugettext as _

import logging

logger = logging.getLogger(__name__)


class BaseConsentForm(forms.BaseForm):

    def __init__(self, *args, **kwargs):
        self.custom_consents = []
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
            "%s" %
            (
                _(consent_section_model.section_label)),
            questions)

    def _get_consent_field_models(self, consent_field):
        _, reg_pk, sec_pk, q_pk = consent_field.split("_")
        registry_model = Registry.objects.get(pk=reg_pk)
        consent_section_model = ConsentSection.objects.get(pk=sec_pk)
        consent_question_model = ConsentQuestion.objects.get(pk=q_pk)

        return registry_model, consent_section_model, consent_question_model

    def get_consent_sections(self):
        section_tuples = []
        for consent_section_model in self.registry_model.consent_sections.all().order_by("code"):
            if consent_section_model.applicable_to(self.patient_model):
                section_tuples.append(
                    self._get_consent_section(consent_section_model))
        return section_tuples

    def save(self, commit=True):
        try:
            patient_registries = [r for r in self.patient_model.rdrf_registry.all()]
        except ValueError:
            # If patient just created line above was erroring
            patient_registries = []

        for consent_field in self.custom_consents:
            registry_model, consent_section_model, consent_question_model = self._get_consent_field_models(
                consent_field)

            if registry_model in patient_registries:
                # are we still applicable?! - maybe some field on patient changed which
                # means not so any longer?
                if consent_section_model.applicable_to(self.patient_model):
                    self.patient_model.set_consent(consent_question_model,
                                                   self.custom_consents[consent_field],
                                                   commit)

    def clean(self):
        self.custom_consents = {}
        cleaneddata = self.cleaned_data

        for k in cleaneddata:
            if k.startswith("customconsent_"):
                self.custom_consents[k] = cleaneddata[k]

        for k in self.custom_consents:
            del cleaneddata[k]

        self._validate_custom_consents()

        return super(BaseConsentForm, self).clean()

    def _validate_custom_consents(self):
        data = {}
        for field_key in self.custom_consents:
            parts = field_key.split("_")
            reg_pk = int(parts[1])
            registry_model = Registry.objects.get(id=reg_pk)
            if registry_model not in data:
                data[registry_model] = {}

            consent_section_pk = int(parts[2])
            consent_section_model = ConsentSection.objects.get(id=int(consent_section_pk))

            if consent_section_model not in data[registry_model]:
                data[registry_model][consent_section_model] = {}

            consent_question_pk = int(parts[3])
            consent_question_model = ConsentQuestion.objects.get(id=consent_question_pk)
            answer = self.custom_consents[field_key]

            data[registry_model][consent_section_model][consent_question_model.code] = answer

        validation_errors = []

        for registry_model in data:
            for consent_section_model in data[registry_model]:

                answer_dict = data[registry_model][consent_section_model]
                if not consent_section_model.is_valid(answer_dict):
                    error_message = "Consent Section '%s %s' is not valid" % (
                        registry_model.code.upper(), consent_section_model.section_label)
                    validation_errors.append(error_message)

        if len(validation_errors) > 0:
            raise forms.ValidationError("Consent Error(s): %s" % ",".join(validation_errors))


class CustomConsentFormGenerator(object):

    def __init__(self, registry_model, patient_model=None):
        self.registry_model = registry_model
        self.patient_model = patient_model  # None if add form
        self.fields = {}

    def create_form(self, post_data={}):
        form_dict = {"base_fields": self._create_custom_consent_fields()}
        form_class = type("PatientConsentForm", (BaseConsentForm,), form_dict)
        form_instance = form_class(
            post_data,
            patient_model=self.patient_model,
            registry_model=self.registry_model)
        return form_instance

    def _create_custom_consent_fields(self):
        fields = OrderedDict()
        for consent_section_model in self.registry_model.consent_sections.all():
            if consent_section_model.applicable_to(self.patient_model):
                for consent_question_model in consent_section_model.questions.all().order_by("position"):
                    consent_field = consent_question_model.create_field()
                    field_key = consent_question_model.field_key
                    fields[field_key] = consent_field

        return fields
