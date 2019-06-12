from rdrf.models.definition.review_models import REVIEW_ITEM_TYPES
from rdrf.models.definition.models import RegistryForm
from rdrf.models.definition.models import Section
from rdrf.models.definition.models import CommonDataElement
from rdrf.models.definition.models import ConsentSection
from rdrf.models.definition.models import ConsentQuestion
from rdrf.forms.dynamic.field_lookup import FieldFactory
from rdrf.helpers.utils import mongo_key_from_models

from django import forms
from django.utils.translation import ugettext as _


import logging


logger = logging.getLogger(__name__)


class FieldTags:
    DATA_ENTRY = "data_entry"
    METADATA = "metadata"


CURRENT_STATUS_CHOICES = (("1", _("Currently Experiencing")),
                          ("2", _("Intermittently Experiencing")),
                          ("3", _("Resolved")),
                          ("4", _("Unknown")))

CONDITION_CHOICES = (("1", _("Yes")),
                     ("2", _("No")),
                     ("3", _("Unknown")))


class PseudoForm:
    def __init__(self, form_name):
        self.name = form_name


class BaseReviewForm(forms.Form):
    @property
    def data_entry_fields(self):
        for field in self._get_fields_by_tag(FieldTags.DATA_ENTRY):
            yield field

    @property
    def metadata_fields(self):
        for field in self._get_fields_by_tag(FieldTags.METADATA):
            yield field

    def _get_fields_by_tag(self, tag):
        # this allows us to partition the types of fields in groups
        # in the template
        # we've already tagged the field object
        # not sure why this is field.field and not field

        for field in self:
            if hasattr(field.field, "rdrf_tag"):
                if field.field.rdrf_tag == tag:
                    yield field


class ReviewFormGenerator:
    def __init__(self, review_item):
        self.review_item = review_item
        self.review = review_item.review
        self.registry_model = self.review.registry

    def create_form_class(self):
        class Mixin:
            registry_code = self.registry_model.code
            review_code = self.review.code
            review_item_code = self.review_item.code

        form_class = type(self.form_class_name,
                          (self.base_class, Mixin),
                          self.get_field_map())
        return form_class

    @property
    def form_class_name(self):
        return "ReviewForm"

    @property
    def base_class(self):
        return BaseReviewForm

    def get_field_map(self):
        field_map = {}
        metadata_fields = self.generate_metadata_fields()
        data_entry_fields = self.generate_data_entry_fields()
        field_map.update(metadata_fields)
        field_map.update(data_entry_fields)

        return field_map

    def generate_metadata_fields(self):
        # subclass
        return {}

    def generate_data_entry_fields(self):
        # subclass
        return {}

    def get_media_class(self):
        class Media:
            css = {'all': ('dmd_admin.css',)}
        return Media

    def generate_fields_from_section(self, form_model, section_model):
        if section_model is None:
            return {}
        d = {}
        for cde_model in section_model.cde_models:
            field_name, field = self.create_cde_field((form_model, section_model, cde_model))
            field.rdrf_tag = FieldTags.DATA_ENTRY
            logger.debug("added tag %s to field %s" % (FieldTags.DATA_ENTRY, field))

            d.update({field_name: field})
        return d

    def generate_field_from_cde(self, cde_model):
        field = forms.CharField(max_length=80,
                                required=False)
        field.label = _(cde_model.name)
        field_name = cde_model.code
        return field_name, field

    def generate_current_status_field(self):
        field = forms.CharField(max_length=1,
                                widget=forms.Select(choices=CURRENT_STATUS_CHOICES),
                                initial="4")
        field.label = _("What is the current status of this condition?")
        field.help_text = _("Please indicate the current status of this medical condition in your child/adult.")
        field_name = "metadata_current_status"
        field.rdrf_tag = FieldTags.METADATA
        return field_name, field

    def generate_condition_changed_field(self):
        field = forms.CharField(max_length=1,
                                widget=forms.Select(choices=CONDITION_CHOICES,
                                                    attrs={'class': 'condition'}),
                                initial="3")
        field.label = _("Has your child/adult's condition changed since your report?")
        field_name = "metadata_condition_changed"
        field.rdrf_tag = FieldTags.METADATA
        return field_name, field

    def create_cde_field(self, spec):
        if isinstance(spec, tuple):
            form_model, section_model, cde_model = spec
            field_label = cde_model.name
            field_name = mongo_key_from_models(form_model, section_model, cde_model)
        elif isinstance(spec, dict):
            field_dict = spec
            field_name = field_dict["name"]
            field_label = field_dict["label"]
            target_dict = field_dict["target"]

            form_name = target_dict["form"]
            form_model = RegistryForm.objects.get(registry=self.registry_model,
                                                  name=form_name)
            cde_code = target_dict["cde"]
            cde_model = CommonDataElement.objects.get(code=cde_code)

            section_code = target_dict["section"]
            section_model = Section.objects.get(code=section_code)
        else:
            raise Exception("unknown spec: %s" % spec)

        cde_model.is_required = False

        field_factory = FieldFactory(self.registry_model,
                                     form_model,
                                     section_model,
                                     cde_model)

        field = field_factory.create_field()
        field.rdrf_tag = FieldTags.DATA_ENTRY

        field.label = field_label

        return field_name, field


class ConsentReviewFormGenerator(ReviewFormGenerator):
    def _create_consent_field(self):
        if self.review_item.target_code:
            consent_section_code, consent_question_code = self.review_item.target_code.split("/")
            consent_section_model = ConsentSection.objects.get(code=consent_section_code,
                                                               registry=self.registry_model)
            consent_question_model = ConsentQuestion.objects.get(code=consent_question_code,
                                                                 section=consent_section_model)
            field_label = _(consent_question_model.question_label)
            field_name = consent_question_model.field_key
            field = forms.BooleanField(required=False)
            field.label = self._remove_leading_number(field_label)
            return field_name, field

    def _remove_leading_number(self, label):
        import re
        pattern = re.compile(r'^(\d+\.?\w*)(.*)$')
        m = pattern.match(label)
        if m:
            return m.group(2).strip()
        else:
            return label

    def generate_data_entry_fields(self):
        field_name, field = self._create_consent_field()
        field.rdrf_tag = FieldTags.DATA_ENTRY
        return {field_name: field}

    def generate_metadata_fields(self):
        d = {}
        condition_changed_field_name, condition_changed_field = self.generate_condition_changed_field()
        d[condition_changed_field_name] = condition_changed_field
        return d


class DemographicsReviewFormGenerator(ReviewFormGenerator):
    def generate_data_entry_fields(self):
        form_model = PseudoForm("Demographics")
        section_field_map = self.generate_fields_from_section(form_model, self.review_item.section)
        logger.debug("section_field_map = %s" % section_field_map)
        return section_field_map

    def generate_metadata_fields(self):
        d = {}
        condition_changed_field_name, condition_changed_field = self.generate_condition_changed_field()
        d[condition_changed_field_name] = condition_changed_field
        return d


class SectionMonitorReviewFormGenerator(ReviewFormGenerator):
    def generate_data_entry_fields(self):
        form_model = self.review_item.form
        section_model = self.review_item.section
        section_field_map = self.generate_fields_from_section(form_model,
                                                              section_model)
        return section_field_map

    def generate_metadata_fields(self):
        d = {}
        current_status_field_name, current_status_field = self.generate_current_status_field()
        d[current_status_field_name] = current_status_field
        condition_changed_field_name, condition_changed_field = self.generate_condition_changed_field()
        d[condition_changed_field_name] = condition_changed_field

        return d


class MultiTargetReviewFormGenerator(ReviewFormGenerator):
    def generate_data_entry_fields(self):
        logger.debug("Multitarget")
        d = {}
        metadata = self.review_item.load_metadata()
        logger.debug("metadata = %s" % metadata)
        logger.debug("number of fields = %s" % len(metadata))

        for field_dict in metadata:
            field_name, field_object = self.create_cde_field(field_dict)
            d[field_name] = field_object
            logger.debug("created field for multitarget %s %s" % (field_name, field_object))

        logger.debug("d = %s" % d)

        return d

    def generate_metadata_fields(self):
        d = {}
        condition_changed_field_name, condition_changed_field = self.generate_condition_changed_field()
        d[condition_changed_field_name] = condition_changed_field

        return d


class MultisectionAddReviewFormGenerator(ReviewFormGenerator):
    pass


class VerificationReviewFormGenerator(ReviewFormGenerator):
    pass


class DummyFormClass(forms.Form):
    name = forms.CharField(max_length=20)
    age = forms.IntegerField()


GENERATOR_MAP = {
    REVIEW_ITEM_TYPES.CONSENT_FIELD: ConsentReviewFormGenerator,
    REVIEW_ITEM_TYPES.DEMOGRAPHICS_FIELD: DemographicsReviewFormGenerator,
    REVIEW_ITEM_TYPES.SECTION_CHANGE: SectionMonitorReviewFormGenerator,
    REVIEW_ITEM_TYPES.MULTISECTION_ITEM: MultisectionAddReviewFormGenerator,
    REVIEW_ITEM_TYPES.VERIFICATION: VerificationReviewFormGenerator,
    REVIEW_ITEM_TYPES.MULTI_TARGET: MultiTargetReviewFormGenerator
}


def create_review_forms(patient_review_model):
    review_model = patient_review_model.review
    logger.debug("review_model = %s" % review_model.name)
    # for each review "item" we create the form _class_ to collect data for it
    # the resulting set of forms is sent to a wizard
    forms_list = []
    logger.debug("creating review form classes ...")

    for review_item in review_model.items.all().order_by("position"):
        if review_item.is_applicable_to(patient_review_model):
            logger.debug("creating review form class for %s" % review_item.name)
            generator_class = GENERATOR_MAP.get(review_item.item_type, None)
            if generator_class is None:
                forms_list.append(DummyFormClass)
            else:
                generator = generator_class(review_item)
                review_form_class = generator.create_form_class()
                forms_list.append(review_form_class)

    logger.debug("forms list = %s" % forms_list)
    return forms_list
