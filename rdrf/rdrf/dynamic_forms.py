from django.forms import BaseForm
from django.utils.datastructures import SortedDict
from field_lookup import FieldFactory
from django.conf import settings
import logging
from rdrf.models import CdePolicy

logger = logging.getLogger("registry_log")


def create_form_class(owner_class_name):
    from models import CommonDataElement
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
    from models import CommonDataElement
    form_class_name = "SectionForm"
    base_fields = SortedDict()

    for s in section.elements.split(","):
        try:
            cde = CommonDataElement.objects.get(code=s.strip())
            cde_policy = get_cde_policy(registry, cde)
            if cde_policy and user_groups:
                if not cde_policy.is_allowed(user_groups.all(), patient_model):
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
            field_code_on_form = "%s%s%s%s%s" % (registry_form.name,
                                                 settings.FORM_SECTION_DELIMITER,
                                                 section.code,
                                                 settings.FORM_SECTION_DELIMITER,
                                                 cde.code)
            base_fields[field_code_on_form] = cde_field
        except CommonDataElement.DoesNotExist:
            continue

    form_class_dict = {"base_fields": base_fields, "auto_id": True}

    return type(form_class_name, (BaseForm,), form_class_dict)


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
    base_fields = SortedDict()

    def get_answer_dict_from_form_data(consent_section_model, form_cleaned_data):
        # This allows the custom validation rule to be applied
        from rdrf.models import ConsentQuestion
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

        logger.debug("in clean method of custom consent form")
        # NB super class has : return self.cleaned_data

        answer_dict = get_answer_dict_from_form_data(consent_section_model, self.cleaned_data)

        if not consent_section_model.is_valid(answer_dict):
            logger.debug("*********** CUSTOM CONSENT VALIDATION ERROR!  %s" %
                         consent_section_model.section_label)
            raise ValidationError("%s is invalid" % consent_section_model.section_label)

        logger.debug("All good: cleaned data = %s" % self.cleaned_data)

        return self.cleaned_data

    form_class_dict = {"base_fields": base_fields, "auto_id": True}

    form_class_dict["clean"] = clean_method

    return type(form_class_name, (BaseForm,), form_class_dict)


class MongoReportingFieldSelectionGenerator(object):
    """
    Generates a form used to indicate which fields in
    Mongo are included in a report ( yes/no for each viewable form field)
    """
    def __init__(self, user, registry_model):
        self.user = user
        self.registry_model = registry_model
        self.field_dict = SortedDict()

    def generate_form(self):
        for form_model in self.registry_model.forms:
            if self.user.can_view(form_model) and not form_model.is_questionnaire:
                for section_model in form_model.section_models:
                    for cde_model in section_model.cde_models:
                        field_key, field = self._create_checkbox_field(form_model, section_model, cde_model)
                        self.field_dict[field_key] = field
        return self._create_form_instance()

    def _create_checkbox_field(self, form_model, section_model, cde_model):
        from django.forms.fields import BooleanField
        field_key = "id_%s_%s_%s" % (form_model.pk, section_model.pk, cde_model.pk)
        return (field_key, BooleanField(label=cde_model.name,
                                        required=False,
                                        help_text="Check if you would like this field to appear in the report"))

    def _create_form_instance(self):
        class MongoSelectionForm(BaseForm):

            def save(myself):
                models = []
                # return triples of form_model, section_model, cde_model
                for field in self.fields:
                    models.append(self_get_models(field))
                return models

            def _get_models(self, field_key):
                from rdrf.models import RegistryForm, Section, CommonDataElement
                form_pk, section_pk, cde_pk = field_key.split("_")
                form_model = RegistryForm.objects.get(pk=int(form_pk))
                section_model = Section.objects.get(pk=int(section_pk))
                cde_model = CommonDataElement.objects.get(pk=int(cde_pk))
                return form_model, section_model, cde_model

        form_class_dict = {"base_fields": self.field_dict}
        klass = type("MongoForm", (MongoSelectionForm,), form_class_dict)
        return klass()







