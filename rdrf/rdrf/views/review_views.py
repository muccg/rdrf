from django.views.generic.base import View
from django.http import Http404
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from rdrf.helpers.utils import is_authorised

import logging

logger = logging.getLogger(__name__)


class ReviewWizardLandingView(View):
    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        token = self._get_token(request)
        return self._get_wizard_view(request,
                                     token,
                                     args,
                                     kwargs,
                                     initialise=True)

    def _get_token(self, request):
        token = request.GET.get("t", None)
        if token is None:
            raise Http404
        return token

    def _get_wizard_view(self, request, token, args, kwargs, initialise=False):
        from rdrf.models.definition.review_models import PatientReview
        patient_review_model = get_object_or_404(PatientReview, token=token)

        if not is_authorised(request.user,
                             patient_review_model.patient):
            raise PermissionDenied

        wizard_view = patient_review_model.create_wizard_view(initialise)
        return wizard_view(request, *args, **kwargs)

    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        token = self._get_token(request)
        return self._get_wizard_view(request, token, args, kwargs)
