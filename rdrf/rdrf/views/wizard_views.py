from django.http import HttpResponseRedirect
from django.core.exceptions import ValidationError
from formtools.wizard.views import SessionWizardView
from django.utils.translation import ugettext as _

from rdrf.forms.dynamic.review_forms import create_review_forms
from rdrf.models.definition.review_models import ReviewStates
from rdrf.models.definition.review_models import PatientReview
from rdrf.models.definition.review_models import ReviewItem
from rdrf.models.definition.review_models import ReviewItemTypes
from registry.patients.models import ParentGuardian

import logging

logger = logging.getLogger(__name__)

THANKYOU_PAGE = "/"  # TODO


class TokenError(Exception):
    pass


class ReviewDataError(Exception):
    pass


class ReviewDataHandler:
    def __init__(self, review_model, token, form_list, form_dict, user):
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
        self.user = user
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
        self.patient_review.state = ReviewStates.DATA_COLLECTED
        self.patient_review.save()
        user = self.patient_review.user
        for patient_review_item in self.patient_review.items.all():
            code = patient_review_item.review_item.code
            if code in self.form_map:
                form = self.form_map[code]
                patient_review_item.update_data(form.cleaned_data,
                                                user)

    def complete(self):
        self.patient_review.state = ReviewStates.FINISHED
        self.patient_review.save()

    def _populate_models(self):
        try:
            patient_review = PatientReview.objects.get(token=self.token,
                                                       review=self.review_model,
                                                       state=ReviewStates.CREATED)
        except PatientReview.DoesNotExist:
            raise TokenError()
        except PatientReview.MultipleObjectsReturned:
            raise TokenError()

        self.patient_review = patient_review
        self.patient_review.user = self.user
        self.patient_model = patient_review.patient
        self.context_model = patient_review.context

    def _validate_models(self):
        if not self.patient_model.in_registry(self.registry_model.code):
            raise ValidationError("Patient not in registry")

    def _get_item_data(self, review_item):
        return self.form_map.get(review_item.code, None)


class PreviousResponse:
    def __init__(self, field, value):
        self.field = field
        self.field_value = value

    @property
    def label(self):
        return _(self.field)

    @property
    def answer(self):
        return self.field_value


class ReviewItemPageData:
    """
    This class gathers together all the relevant information
    for the review template
    """

    def __init__(self, token, review_model, review_form, review_user):
        self.token = token
        self.review_model = review_model
        self.review_form = review_form
        self.review_item_model = ReviewItem.objects.get(review=self.review_model,
                                                        code=self.review_form.review_item_code)
        self.patient_review = self._get_patient_review(self.token)
        self.user = review_user
        self.state = self.patient_review.state
        self.patient_model = self.patient_review.patient
        self.parent_model = self._get_parent(self.patient_model)
        self.is_parent = self.parent_model is not None
        self.clinician_user = None
        # this depends on the type of review item:
        self.previous_data = self.review_item_model.get_data(self.patient_model,
                                                             self.patient_review.context)

    def _trans(self, s):
        if s:
            return _(s)
        else:
            return ""

    def _get_patient_review(self, token):
        return PatientReview.objects.get(token=token)

    def _get_parent(self, patient_model):
        parents = ParentGuardian.objects.filter(patient__in=[patient_model])
        num_parents = len(parents)
        if num_parents == 1:
            return parents[0]
        elif num_parents == 0:
            return None
        else:
            # if more than one parent ( possible?)
            # try to locate based on the logged in user
            for parent in parents:
                if parent.user.id == self.user.id:
                    return parent
                # choose first
            return parents[0]

    @property
    def summary(self):
        return self._trans(self.review_item_model.summary)

    @property
    def is_clinician_review(self):
        return self.review_item_model.item_type == ReviewItemTypes.VERIFICATION

    @property
    def category(self):
        if self.review_item_model.category:
            return self._trans(self.review_item_model.category)

    @property
    def name(self):
        return self._trans(self.review_item_model.name)

    @property
    def title(self):
        return self._trans(self.review_model.name)

    @property
    def valid(self):
        return self.state == ReviewStates.CREATED

    @property
    def is_parent_review(self):
        return self.parent_model and self.patient_model

    @property
    def responses(self):
        return [PreviousResponse(pair[0], pair[1]) for pair in self.previous_data]


class ReviewTemplates:
    CAREGIVER_REVIEW = "rdrf_cdes/review_form.html"
    CLINICIAN_VERIFICATION = "rdrf_cdes/clinician_review_form.html"


class ReviewWizardGenerator:
    def __init__(self, patient_review_model, review_user):
        self.patient_review = patient_review_model
        self.review_model = patient_review_model.review
        self.review_user = review_user  # the user filling out the review
        self.base_class = SessionWizardView

    def create_wizard_class(self):

        if self.review_model.review_type == "R":
            template_name = ReviewTemplates.CAREGIVER_REVIEW
        elif self.review_model.review_type == "V":
            template_name = ReviewTemplates.CLINICIAN_VERIFICATION

        form_list = create_review_forms(self.patient_review)
        class_name = "ReviewWizard"

        def get_form_initial_method(myself, step):
            data = myself.initial_dict.get(step, {})
            return data

        def done_method(myself, form_list, form_dict, **kwargs):
            # when all valid data processed ,
            # fan the data back out
            token = myself.request.GET.get('t')
            user = myself.request.user
            rdh = ReviewDataHandler(self.review_model,
                                    token,
                                    form_list,
                                    form_dict,
                                    user)

            rdh.update_patient_data()
            rdh.complete()

            return HttpResponseRedirect(THANKYOU_PAGE)

        def get_context_data_method(myself, form, **kwargs):
            token = myself.request.GET.get("t")
            page = ReviewItemPageData(token, self.review_model, form, self.review_user)

            context = super(myself.__class__, myself).get_context_data(form=form,
                                                                       **kwargs)

            context.update({"review_title": page.title,
                            "summary": page.summary,
                            "category": page.category,
                            "name": page.name,
                            "responses": page.responses,
                            "valid": page.valid,
                            "parent": page.parent_model,
                            "patient": page.patient_model,
                            "is_clinician_review": page.is_clinician_review,
                            "is_parent_review": page.is_parent_review,
                            "clinician": page.clinician_user})
            return context

        class_dict = {
            "initial_dict": {},
            "form_list": form_list,
            "template_name": template_name,
            "get_context_data": get_context_data_method,
            "done": done_method,
            "get_form_initial": get_form_initial_method,
        }

        wizard_class = type(class_name, (self.base_class,), class_dict)

        return wizard_class
