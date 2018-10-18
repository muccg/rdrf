from django.contrib.auth.models import User
from rest_framework import authentication
from rest_framework import exceptions
from registry.groups.models import CustomUser


import logging
logger = logging.getLogger(__name__)


class PromsAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        logger.info("authenticating proms")
        from django.conf import settings
        secret_token = request.META.get('HTTP_PROMS_SECRET_TOKEN')
        logger.info("token from request: %s" % secret_token)
        PROMS_SECRET_TOKEN = settings.PROMS_SECRET_TOKEN
        logger.info("settings proms token: %s" % PROMS_SECRET_TOKEN)
        PROMS_USERNAME = settings.PROMS_USERNAME
        logger.info("settings proms user: %s" % PROMS_USERNAME)

        if secret_token != PROMS_SECRET_TOKEN:
            logger.info("tokens don't match - failed to auth")
            return None

        try:
            user = CustomUser.objects.get(username=PROMS_USERNAME)
        except CustomUser.DoesNotExist:
            logger.info("proms user doesn't exist")
            raise exceptions.AuthenticationFailed('No such user')

        logger.info("authenticated as %s" % PROMS_USERNAME)

        return (user, None)
