from rdrf.models.definition.review_models import REVIEW_ITEM_TYPES
from rdrf.models.definition.models import CommonDataElement
from rdrf.models.definition.models import ConsentSection
from rdrf.models.definition.models import ConsentQuestion

from django import forms
from django.utils.translation import ugettext as _

import logging


logger = logging.getLogger(__name__)



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
        return forms.Form

    def get_field_map(self):
        field_name = "%sField" % self.__class__.__name__
        field = forms.CharField(max_length=80, help_text="test")
        field.label = "testlabel"
        return {field_name: field}

    def get_media_class(self):
        class Media:
            css = {'all': ('dmd_admin.css',)}
        return Media


class ConsentReviewFormGenerator(ReviewFormGenerator):
    def _create_consent_field(self):
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
        

    def get_field_map(self):
        field_name, field = self._create_consent_field()
        return {field_name: field}


class DemographicsReviewFormGenerator(ReviewFormGenerator):
    pass


class SectionMonitorReviewFormGenerator(ReviewFormGenerator):
    pass


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
    REVIEW_ITEM_TYPES.VERIFICATION: VerificationReviewFormGenerator
}


def create_review_forms(review_model):
    logger.debug("review_model = %s" % review_model.name)
    # for each review "item" we create the form _class_ to collect data for it
    # the resulting set of forms is sent to a wizard
    forms_list = []
    logger.debug("creating review form classes ...")

    for review_item in review_model.items.all().order_by("position"):
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


