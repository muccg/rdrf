from __future__ import absolute_import
from registration.backends.default.views import ActivationView
from registration.backends.default.views import RegistrationView


class RdrfRegistrationView(RegistrationView):

    def get_success_url(self, request, user):
        """
        Return the name of the URL to redirect to after successful
        user registration.
        """
        assert False
        return ('registration_complete', (), {})
        

class RdrfActivationView(ActivationView):

    def activate(self, request, regsitry_code, activation_key):
        activated_user = RegistrationProfile.objects.activate_user(activation_key)
        if activated_user:
            signals.user_activated.send(sender=self.__class__,
                                        user=activated_user,
                                        request=request)
        return activated_user