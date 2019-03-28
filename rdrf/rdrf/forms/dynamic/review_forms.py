from rdrf.models.definition.review_models import REVIEW_ITEM_TYPES
from django.forms import BaseForm
from django.utils.translation import ugettext as _


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
        return BaseForm

    def get_field_map(self):
        return {}

    def get_media_class(self):
        class Media:
            css = {'all': ('dmd_admin.css',)}
        return Media

    @property
    def form_class_dict(self):
        fields_map = self.get_field_map()
        media_class = self.get_media_class()
        form_class_dict = {"base_fields": fields_map,
                           "Media": media_class}
        return form_class_dict

class TestFormGenerator(ReviewFormGenerator):
    pass
    


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


GENERATOR_MAP = {
    REVIEW_ITEM_TYPES.CONSENT_FIELD: ConsentReviewFormGenerator,
    REVIEW_ITEM_TYPES.DEMOGRAPHICS_FIELD: DemographicsReviewFormGenerator,
    REVIEW_ITEM_TYPES.SECTION_CHANGE: SectionMonitorReviewFormGenerator,
    REVIEW_ITEM_TYPES.MULTISECTION_ITEM: MultisectionAddReviewFormGenerator,
    REVIEW_ITEM_TYPES.VERIFICATION: VerificationReviewFormGenerator
}


def create_review_forms(review_model):
    # for each review "item" we create the form class to collect data for it
    # the resulting set of forms is sent to a wizard
    l = []

    for review_item in review_model.items.all().order_by("position"):
        generator_class = GENERATOR_MAP[review_model.item_type]
        generator = generator_class(review_model)
        review_form_class = generator.create_form_class()
        l.append(review_form_class)
    return l


