from rest_framework import authentication
from rest_framework import exceptions
from registry.groups.models import CustomUser


import logging
logger = logging.getLogger(__name__)


class PromsAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        from django.conf import settings
        secret_token = request.POST.get("proms_secret_token", "")

        proms_secret_token = settings.PROMS_SECRET_TOKEN
        proms_username = settings.PROMS_USERNAME

        if secret_token != proms_secret_token:
            logger.warning("tokens don't match - failed to auth")
            return False

        try:
            user = CustomUser.objects.get(username=proms_username)
        except CustomUser.DoesNotExist:
            logger.warning("proms user doesn't exist")
            raise exceptions.AuthenticationFailed('No such user')

        return (user, None)
