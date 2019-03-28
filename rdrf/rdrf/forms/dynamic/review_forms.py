from rdrf.models.definition.review_models import REVIEW_ITEM_TYPES
from rdrf.models.definition.models import CommonDataElement

from django import forms
from django.utils.translation import ugettext as _

import logging


logger = logging.getLogger(__name__)


class ReviewFormGenerator:
    def __init__(self, review_item):
        self.review_item = review_item

    def create_form_class(self):
        form_class = type(self.form_class_name,
                          (self.base_class,),
                          self.form_class_dict)
        return form_class

    @property
    def form_class_name(self):
        return "ReviewForm"

    @property
    def base_class(self):
        return forms.Form

    def get_field_map(self):
        return {"dummy": forms.CharField(max_length=80)}

    def get_media_class(self):
        class Media:
            css = {'all': ('dmd_admin.css',)}
        return Media

    @property
    def form_class_dict(self):
        fields_map = self.get_field_map()
        media_class = self.get_media_class()
        form_class_dict = {"fields": fields_map,
                           "Media": media_class}
        return form_class_dict


class ConsentReviewFormGenerator(ReviewFormGenerator):
    def create_consent_field(self):
        consent_cde_code = self.review_item.target_code
        consent_cde_model = CommonDataElement.objects.get(code=consent_cde_code)
        field_label = _(consent_cde_model.name)


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
    # for each review "item" we create the form class to collect data for it
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


