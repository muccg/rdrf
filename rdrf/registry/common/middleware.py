import logging
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin
from ccg_django_utils.conf import EnvConfig

logger = logging.getLogger(__name__)


class EnforceTwoFactorAuthMiddleware(MiddlewareMixin):
    """
    This must be installed after
    :class:`~django.contrib.auth.middleware.AuthenticationMiddleware` and
    :class:`~django_otp.middleware.OTPMiddleware`.
    Users who are required to have two-factor authentication but aren't verified
    will always be redirected to the two-factor setup page.
    """

    def process_request(self, request):
        whitelisted_views = (
            'two_factor:login',
            'two_factor:setup',
            'two_factor:qr',
            'logout',
            'javascript-catalog')
        if any([reverse(v) in request.path_info for v in whitelisted_views]):
            return None

        user = getattr(request, 'user', None)
        if user is None or user.is_anonymous:
            return None

        site_requires_2fa = EnvConfig().get("require_2fa", False) == 1

        if not user.is_verified() and (site_requires_2fa or user.require_2_fact_auth):
            return HttpResponseRedirect(reverse('two_factor:setup'))

        return None
