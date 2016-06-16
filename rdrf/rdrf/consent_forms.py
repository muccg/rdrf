from collections import OrderedDict
from django import forms
from rdrf.models import Registry
from rdrf.models import ConsentSection
from rdrf.models import ConsentQuestion
from registry.patients.models import Patient

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
            "%s %s" %
            (self.registry_model.code.upper(),
             consent_section_model.section_label),
            questions)

    def _get_consent_field_models(self, consent_field):
        logger.debug("getting consent field models for %s" % consent_field)
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
            logger.debug("saving consent field %s ( value to save = %s)" %
                         (consent_field, self.custom_consents[consent_field]))
            registry_model, consent_section_model, consent_question_model = self._get_consent_field_models(
                consent_field)

            if registry_model in patient_registries:
                logger.debug("saving consents for %s %s" %
                             (registry_model, consent_section_model))
                # are we still applicable?! - maybe some field on patient changed which
                # means not so any longer?
                if consent_section_model.applicable_to(self.patient_model):
                    logger.debug("%s is applicable to %s" %
                                 (consent_section_model, self.patient_model))
                    cv = self.patient_model.set_consent(
                        consent_question_model, self.custom_consents[consent_field], commit)
                    logger.debug("set consent value ok : cv = %s" % cv)
                else:
                    logger.debug("%s is not applicable to model %s" %
                                 (consent_section_model, self.patient_model))

            else:
                logger.debug("patient not in %s ?? no consents added here" % registry_model)

    def clean(self):
        logger.debug("in %s clean" % self.__class__.__name__)
        self.custom_consents = {}
        cleaneddata = self.cleaned_data

        for k in cleaneddata:
            logger.debug("cleaned field %s = %s" % (k, cleaneddata[k]))

        for k in cleaneddata:
            if k.startswith("customconsent_"):
                self.custom_consents[k] = cleaneddata[k]

        for k in self.custom_consents:
            del cleaneddata[k]
            logger.debug("removed custom consent %s" % k)

        self._validate_custom_consents()

        return super(BaseConsentForm, self).clean()

    def _validate_custom_consents(self):
        logger.debug("custom consents = %s" % self.custom_consents)
        data = {}
        for field_key in self.custom_consents:
            logger.debug("field key = %s" % field_key)
            parts = field_key.split("_")
            reg_pk = int(parts[1])
            registry_model = Registry.objects.get(id=reg_pk)
            logger.debug("reg = %s" % registry_model)
            if registry_model not in data:
                data[registry_model] = {}

            consent_section_pk = int(parts[2])
            consent_section_model = ConsentSection.objects.get(id=int(consent_section_pk))
            logger.debug("section model = %s" % consent_section_model)

            if consent_section_model not in data[registry_model]:
                data[registry_model][consent_section_model] = {}

            consent_question_pk = int(parts[3])
            consent_question_model = ConsentQuestion.objects.get(id=consent_question_pk)
            logger.debug("consent question = %s" % consent_question_model)
            answer = self.custom_consents[field_key]
            logger.debug("answer = %s" % answer)

            data[registry_model][consent_section_model][consent_question_model.code] = answer

        validation_errors = []

        for registry_model in data:
            for consent_section_model in data[registry_model]:

                answer_dict = data[registry_model][consent_section_model]
                if not consent_section_model.is_valid(answer_dict):
                    error_message = "Consent Section '%s %s' is not valid" % (
                        registry_model.code.upper(), consent_section_model.section_label)
                    validation_errors.append(error_message)
                else:
                    logger.debug("Consent section %s is valid!" %
                                 consent_section_model.section_label)

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
        form_instance = form_class(post_data, patient_model=self.patient_model, registry_model=self.registry_model)
        return form_instance

    def _create_custom_consent_fields(self):
        fields = OrderedDict()
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
