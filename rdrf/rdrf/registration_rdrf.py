from __future__ import absolute_import
from registration.backends.default.views import RegistrationView
import datetime
import dateutil


class RdrfRegistrationView(RegistrationView):

    registry_code = None

    def get_context_data(self, **kwargs):
        context = super(RdrfRegistrationView, self).get_context_data(**kwargs)
        context['registry_code'] = self.registry_code
        return context
