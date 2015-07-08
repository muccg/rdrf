from __future__ import absolute_import

from django.views.generic.base import TemplateView
from registration.backends.default.views import ActivationView
from registration.backends.default.views import RegistrationView


class RdrfRegistrationView(RegistrationView):
    pass
