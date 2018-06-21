from django.forms import BaseForm
from collections import OrderedDict
from rdrf.forms.dynamic.field_lookup import FieldFactory
from django.conf import settings
import logging
from rdrf.models.definition.models import CdePolicy

logger = logging.getLogger(__name__)


def create_form_class(owner_class_name):
    from rdrf.models.definition.models import CommonDataElement
    form_class_name = "CDEForm"
    cde_map = {}
    base_fields = {}

    for cde in CommonDataElement.objects.all().filter(owner=owner_class_name):
        cde_field = FieldFactory(cde).create_field()
        field_name = cde.code
        # e.g.  "CDE0023" --> the cde element corresponding to this code
        cde_map[field_name] = cde
        base_fields[field_name] = cde_field   # a django field object

    class Media:
        css = {
            'all': ('dmd_admin.css',)
        }

    form_class_dict = {"base_fields": base_fields,
                       "cde_map": cde_map,
                       'Media': Media}

    form_class = type(form_class_name, (BaseForm,), form_class_dict)
    return form_class


def get_cde_policy(registry, cde):
    try:
        return CdePolicy.objects.get(registry=registry, cde=cde)
    except CdePolicy.DoesNotExist:
        return None


def create_form_class_for_section(
        registry,
        registry_form,
        section,
        questionnaire_context=None,
        injected_model=None,
        injected_model_id=None,
        is_superuser=None,
        user_groups=None,
        patient_model=None):

    base_fields = OrderedDict()
    for cde in section.cde_models:
        cde_policy = get_cde_policy(registry, cde)
        if cde_policy and user_groups:
            if not cde_policy.is_allowed(user_groups.all(),
                                         patient_model,
                                         is_superuser=is_superuser):
                continue

        cde_field = FieldFactory(
            registry,
            registry_form,
            section,
            cde,
            questionnaire_context,
            injected_model=injected_model,
            injected_model_id=injected_model_id,
            is_superuser=is_superuser).create_field()

        cde_field.important = cde.important

        field_code_on_form = "%s%s%s%s%s" % (registry_form.name,
                                             settings.FORM_SECTION_DELIMITER,
                                             section.code,
                                             settings.FORM_SECTION_DELIMITER,
                                             cde.code)
        base_fields[field_code_on_form] = cde_field

    form_class_dict = {"base_fields": base_fields, "auto_id": True}

    return type("SectionForm", (BaseForm,), form_class_dict)


def create_form_class_for_consent_section(
        registry_model,
        consent_section_model,
        questionnaire_context=None,
        is_superuser=None):
    # This function is used by the _questionnaire_, to provide a form for filling in custom consent info
    # It differs from the "normal" form class creation function above which takes a RDRF Section model, in that it takes
    # a ConsentSection model ( which is NOT CDE based )
    from django.forms import BooleanField
    form_class_name = "CustomConsentSectionForm"
    base_fields = OrderedDict()

    def get_answer_dict_from_form_data(consent_section_model, form_cleaned_data):
        # This allows the custom validation rule to be applied
        from rdrf.models.definition.models import ConsentQuestion
        answer_dict = {}
        # NB customconsent_%s_%s_%s" % (registry_model.pk, consent_section_model.pk, self.pk)
        for field_key in form_cleaned_data:
            key_parts = field_key.split("_")
            question_pk = int(key_parts[3])
            consent_question_model = ConsentQuestion.objects.get(id=question_pk)
            question_code = consent_question_model.code
            answer_dict[question_code] = form_cleaned_data[field_key]
        return answer_dict

    for question_model in consent_section_model.questions.order_by("position"):
        field = BooleanField(
            label=question_model.questionnaire_label,
            required=False,
            help_text=question_model.instructions)
        field_key = question_model.field_key
        base_fields[field_key] = field

    def clean_method(self):
        """
        We override form.clean with this method
        From the Django BaseForm code:
        Hook for doing any extra form-wide cleaning after Field.clean() been
        called on every field. Any ValidationError raised by this method will
        not be associated with a particular field; it will have a special-case
        association with the field named '__all__'.
        """
        from django.core.exceptions import ValidationError
        # NB super class has : return self.cleaned_data
        answer_dict = get_answer_dict_from_form_data(consent_section_model, self.cleaned_data)

        if not consent_section_model.is_valid(answer_dict):
            raise ValidationError("%s is invalid" % consent_section_model.section_label)

        return self.cleaned_data

    form_class_dict = {"base_fields": base_fields, "auto_id": True}

    form_class_dict["clean"] = clean_method

    return type(form_class_name, (BaseForm,), form_class_dict)
