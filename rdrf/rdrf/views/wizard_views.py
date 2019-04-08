from django.http import HttpResponseRedirect
from django.core.exceptions import ValidationError
from formtools.wizard.views import SessionWizardView

from rdrf.forms.dynamic.review_forms import create_review_forms

import logging

logger = logging.getLogger(__name__)


class TokenError(Exception):
    pass


class ReviewDataError(Exception):
    pass


class ReviewDataHandler:
    def __init__(self, review_model, token, form_list, form_dict):
        self.review_model = review_model
        self.registry_model = review_model.registry
        self.token = token
        self.form_list = form_list
        self.form_dict = form_dict
        self.form_map = None
        self.patient_review = None
        self.patient_model = None
        self.parent_model = None
        self.context_model = None
        self._build_data_map()

        self._populate_models()  # validates token and creates target models
        self._validate_models()

    def _build_data_map(self):
        # the step info isn't relevant - we need the review item code 
        d = {}
        for step, form in self.form_dict.items():
            d[form.review_item_code] = form
        self.form_map = d
            

    def update_patient_data(self):
        from django.db import transaction

        self._update_patient_review()
        
        try:
            with transaction.atomic():
                self._process_review()
        except ReviewDataError:
            pass

    def _update_patient_review(self):
        from rdrf.models.definition.review_models import ReviewStates
        self.patient_review.state = ReviewStates.DATA_COLLECTED
        self.patient_review.save()
        for patient_review_item in self.patient_review.items.all():
            code = patient_review_item.review_item.code
            if code in self.form_map:
                form = self.form_map[code]
                patient_review_item.update_data(form.cleaned_data)

    def _populate_models(self):
        from rdrf.models.definition.review_models import PatientReview
        from rdrf.models.definition.review_models import ReviewStates

        try:
            patient_review = PatientReview.objects.get(token=self.token,
                                                       review=self.review_model,
                                                       state=ReviewStates.CREATED)
        except PatientReview.DoesNotExist:
            raise TokenError()
        except PatientReview.MultipleObjectsReturned:
            raise TokenError()

        self.patient_review = patient_review
        self.patient_model = patient_review.patient
        self.context_model = patient_review.context

    def _validate_models(self):
        if not self.patient_model.in_registry(self.registry_model.code):
            raise ValidationError("Patient not in registry")

    def _process_review(self):
        for review_item in self.review_model.items.all():
            self._process_review_item(review_item)

    def _process_review_item(self, review_item):
        form = self._get_item_data(review_item)
        item_data = form.cleaned_data
        if item_data is not None:
            logger.debug("updating review item %s with data %s ..." % (review_item.code,
                                                                       item_data))
            review_item.update_data(self.patient_model,
                                    self.parent_model,
                                    self.context_model,
                                    item_data)

    def _get_item_data(self, review_item):
        return self.form_map.get(review_item.code, None)


class ReviewWizardGenerator:
    def __init__(self, review_model):
        self.review_model = review_model
        self.base_class = SessionWizardView

    def create_wizard_class(self):
        template_name = "rdrf_cdes/review_form.html"
        form_list = create_review_forms(self.review_model)
        class_name = "ReviewWizard"

        def done_method(myself, form_list, form_dict, **kwargs):
            # when all valid data processed ,
            # fan the data back out
            token = myself.request.GET.get('token')
            rdh = ReviewDataHandler(self.review_model,
                                    token,
                                    form_list,
                                    form_dict)

            rdh.update_patient_data()
                                    
            return HttpResponseRedirect("/")

        class_dict = {
            "form_list": form_list,
            "template_name": template_name,
            "done": done_method,
        }

        wizard_class = type(class_name, (self.base_class,), class_dict)

        return wizard_class
