from rdrf.models.definition.review_models import ReviewItemTypes
from rdrf.models.definition.models import RegistryForm
from rdrf.models.definition.models import Section
from rdrf.models.definition.models import CommonDataElement
from rdrf.models.definition.models import ConsentSection
from rdrf.models.definition.models import ConsentQuestion
from rdrf.forms.dynamic.field_lookup import FieldFactory
from rdrf.helpers.utils import mongo_key_from_models
from rdrf.helpers.utils import get_normal_fields

from django import forms
from django.utils.translation import ugettext as _


import logging


logger = logging.getLogger(__name__)


class FieldTags:
    DATA_ENTRY = "data_entry"
    METADATA = "metadata"
    VERIFICATION = "verification"


CONDITION_CHOICES = (("1", _("Yes")),
                     ("2", _("No")),
                     ("3", _("Unknown")))

VERIFICATION_CHOICES = (("V", "Verified"),
                        ("N", "Not Verified"),
                        ("U", "Unknown"),
                        ('C', 'Corrected'))


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

    @property
    def verification_fields(self):
        for field in self._get_fields_by_tag(FieldTags.VERIFICATION):
            yield field

    @property
    def fields_with_verifications(self):
        ver_fields = {field.name: field for field in self.verification_fields}

        class Wrapper:
            def __init__(self, field, ver_field):
                self.field = field
                self.ver_field = ver_field
        wrappers = []
        for field in self.data_entry_fields:
            ver_name = "ver/%s" % field.name
            ver_field = ver_fields.get(ver_name, None)
            if ver_field is not None:
                wrappers.append(Wrapper(field, ver_field))
            else:
                raise Exception("no ver")
        return wrappers

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
            review_item_type = self.review_item.item_type

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

    def generate_fields_from_section(self, form_model, section_model, include_verification=False):
        if section_model is None:
            return {}
        d = {}
        for cde_model in get_normal_fields(section_model):
            field_name, field = self.create_cde_field((form_model, section_model, cde_model))
            field.rdrf_tag = FieldTags.DATA_ENTRY
            if include_verification:
                ver_field_name, ver_field = self.generate_verification_field(field_name)
                d[ver_field_name] = ver_field

            d.update({field_name: field})
        return d

    def generate_field_from_cde(self, cde_model):
        field = forms.CharField(max_length=80,
                                required=False)
        field.label = _(cde_model.name)
        field_name = cde_model.code
        return field_name, field

    def generate_verification_field(self, target_field_name):
        # item = 0 for non multisection target
        # item = 0,1,2 for multisection target
        field = forms.CharField(max_length=1,
                                widget=forms.Select(choices=VERIFICATION_CHOICES),
                                initial="U")
        field.label = ""  # field will sit next to the "real" field
        field_name = "ver/%s" % target_field_name
        field.rdrf_tag = FieldTags.VERIFICATION
        return field_name, field

    def generate_condition_changed_field(self):
        field = forms.CharField(max_length=1,
                                widget=forms.RadioSelect(choices=CONDITION_CHOICES,
                                                         attrs={'class': 'condition'}),
                                initial="3")
        field.label = _("Has your child/adult's condition changed since your report?")
        field_name = "metadata_condition_changed"
        field.rdrf_tag = FieldTags.METADATA
        return field_name, field

    def _deduce_section(self, form_model, cde_model):
        # this assumes unique cde codes..
        for section_model in form_model.section_models:
            if cde_model.code in [x.code for x in section_model.cde_models]:
                return section_model

    def create_cde_field(self, spec):
        if isinstance(spec, tuple):
            form_model, section_model, cde_model = spec
            field_label = cde_model.name
            if section_model is None:
                section_model = self._deduce_section(form_model, cde_model)
                if section_model is None:
                    raise Exception("cannot deduce section for %s %s" % (form_model.name,
                                                                         cde_model.code))
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
        condition_changed_field_name, condition_changed_field = self.generate_condition_changed_field()
        d[condition_changed_field_name] = condition_changed_field

        return d


class MultiTargetReviewFormGenerator(ReviewFormGenerator):
    def generate_data_entry_fields(self):
        d = {}
        metadata = self.review_item.load_metadata()

        for field_dict in metadata:
            field_name, field_object = self.create_cde_field(field_dict)
            d[field_name] = field_object

        return d

    def generate_metadata_fields(self):
        d = {}
        condition_changed_field_name, condition_changed_field = self.generate_condition_changed_field()
        d[condition_changed_field_name] = condition_changed_field

        return d


class MultisectionAddReviewFormGenerator(ReviewFormGenerator):
    pass


class VerificationReviewFormGenerator(ReviewFormGenerator):
    def generate_data_entry_fields(self):
        d = {}
        form_model = self.review_item.form
        section_model = self.review_item.section
        if form_model is None and section_model is None:
            return self._ad_hoc_data_entry_fields(self.review_item.target_metadata)

        if self.review_item.fields:
            cde_models = self._get_cdes(self.review_item.fields)  # subset of fields from the section
        else:
            cde_models = section_model.cde_models   # assume all

        for cde_model in cde_models:
            if cde_model.calculation:
                continue
            cde_field_name, cde_field_obj = self.create_cde_field((form_model, section_model, cde_model))
            d[cde_field_name] = cde_field_obj
            target = cde_field_name
            ver_field_name, ver_field_obj = self.generate_verification_field(target)
            d[ver_field_name] = ver_field_obj
        return d

    def _ad_hoc_data_entry_fields(self, target_metadata):
        return {}

    def _get_cdes(self, cde_codes_csv):
        cde_codes = [s.strip() for s in cde_codes_csv.split(",")]
        return [CommonDataElement.objects.get(code=cde_code) for cde_code in cde_codes]


class DummyFormClass(forms.Form):
    name = forms.CharField(max_length=20)
    age = forms.IntegerField()


GENERATOR_MAP = {
    ReviewItemTypes.CONSENT_FIELD: ConsentReviewFormGenerator,
    ReviewItemTypes.DEMOGRAPHICS_FIELD: DemographicsReviewFormGenerator,
    ReviewItemTypes.SECTION_CHANGE: SectionMonitorReviewFormGenerator,
    ReviewItemTypes.MULTISECTION_ITEM: MultisectionAddReviewFormGenerator,
    ReviewItemTypes.VERIFICATION: VerificationReviewFormGenerator,
    ReviewItemTypes.MULTI_TARGET: MultiTargetReviewFormGenerator
}


def create_review_forms(patient_review_model):
    review_model = patient_review_model.review
    # for each review "item" we create the form _class_ to collect data for it
    # the resulting set of forms is sent to a wizard
    forms_list = []

    for review_item in review_model.items.all().order_by("position"):
        if review_item.is_applicable_to(patient_review_model):
            generator_class = GENERATOR_MAP.get(review_item.item_type, None)
            if generator_class is None:
                forms_list.append(DummyFormClass)
            else:
                generator = generator_class(review_item)
                review_form_class = generator.create_form_class()
                forms_list.append(review_form_class)

    return forms_list
