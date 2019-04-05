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
        self.patient_review = None
        self.patient_model = None
        self.context_model = None

        self._populate_models()  # validates token and creates target models
        self._validate_models()
        

    def update_patient_data(self):
        from django.db import transaction
        try:
            with transaction.atomic():
                self._process_review()
        except ReviewDataError:
            pass

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

        self.patient_model = patient_review.patient
        self.context_model = patient_review.context

    def _validate_models(self):
        if not self.patient_model.in_registry(self.registry_model):
            raise ValidationError("Patient not in registry")


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
            logger.debug("token = %s" % token)
            
            return HttpResponseRedirect("TODO")

        class_dict = {
            "form_list": form_list,
            "template_name": template_name,
            "done": done_method,
        }

        wizard_class = type(class_name, (self.base_class,), class_dict)

        return wizard_class
