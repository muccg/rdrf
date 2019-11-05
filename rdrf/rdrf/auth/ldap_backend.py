from django.conf import settings
from django_auth_ldap.backend import LDAPBackend
import logging

logger = logging.getLogger(__name__)


class RDRFLDAPBackend(LDAPBackend):
    default_settings = {
        "LOGIN_COUNTER_KEY": "CUSTOM_LDAP_LOGIN_ATTEMPT_COUNT",
        "LOGIN_ATTEMPT_LIMIT": 3,
        "RESET_TIME": 30 * 60,
        "USERNAME_REGEX": r"^.*$",
    }

    def get_or_build_user(self, username, ldap_user):
        user, built = super().get_or_build_user(username, ldap_user)

        # We need to update the user information whatever it existed or not in RDRF database.

        from rdrf.models.definition.models import Registry
        from registry.groups.models import WorkingGroup
        registry_model = Registry.objects.get(code=settings.RDRF_AUTH_LDAP_REGISTRY_CODE)
        wg = WorkingGroup.objects.get(registry=registry_model,
                                      name=settings.RDRF_AUTH_LDAP_WORKING_GROUP)

        # User must be staff
        user.is_staff = True
        user.is_active = True

        # Check if 2fa is mandatory
        if settings.RDRF_AUTH_LDAP_REQUIRE_2FA:
            user.require_2_fact_auth = True

        # Save the user a first time.
        # It is required to be able to set working_group and registry in the next lines.
        user.save()

        # Update working group and registry
        user.working_groups.set([wg])
        user.registry.set([registry_model])
        logger.debug(f"RDRF_AUTH_LDAP_AUTH_GROUP: {settings.RDRF_AUTH_LDAP_AUTH_GROUP}")
        user.add_group(settings.RDRF_AUTH_LDAP_AUTH_GROUP)
        user.save()

        logger.debug(f"LDAP USER: {user.__dict__}")

        return user, built
