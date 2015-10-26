from django.forms import Form

import logging

logger = logging.getLogger("registry_log")

class CustomConsentsFormGenerator(object):
    def __init__(self, registry_model, patient_model=None):
        self.registry_model = registry_model
        self.patient_model = patient_model  # None if add form

    def create_form(self):
        PASS

    # PASTED FROM PatientForm initially
    def _get_consent_field_models(self, consent_field):
        logger.debug("getting consent field models for %s" % consent_field)
        _, reg_pk, sec_pk, q_pk = consent_field.split("_")

        registry_model = Registry.objects.get(pk=reg_pk)
        consent_section_model = ConsentSection.objects.get(pk=sec_pk)
        consent_question_model = ConsentQuestion.objects.get(pk=q_pk)

        return registry_model, consent_section_model, consent_question_model

    def _add_custom_consent_fields(self, patient_model):
        if patient_model is None:
            registries = [self.registry_model]
        else:
            registries = patient_model.rdrf_registry.all()

        for registry_model in registries:
            for consent_section_model in registry_model.consent_sections.all():
                if consent_section_model.applicable_to(patient_model):
                    for consent_question_model in consent_section_model.questions.all().order_by(
                            "position"):
                        consent_field = consent_question_model.create_field()
                        field_key = consent_question_model.field_key
                        self.fields[field_key] = consent_field
                        logger.debug("added consent field %s = %s" % (field_key, consent_field))

    def get_all_consent_section_info(self, patient_model, registry_code):
        section_tuples = []
        registry_model = Registry.objects.get(code=registry_code)

        for consent_section_model in registry_model.consent_sections.all().order_by("code"):
            if consent_section_model.applicable_to(patient_model):
                section_tuples.append(
                    self.get_consent_section_info(registry_model, consent_section_model))
        return section_tuples

    def get_consent_section_info(self, registry_model, consent_section_model):
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
                if reg_pk == registry_model.pk:
                    consent_section_pk = int(parts[2])
                    if consent_section_pk == consent_section_model.pk:
                        consent_section_model = ConsentSection.objects.get(
                            pk=consent_section_pk)
                        questions.append(field)

        return (
            "%s %s" %
            (registry_model.code.upper(),
             consent_section_model.section_label),
            questions)






