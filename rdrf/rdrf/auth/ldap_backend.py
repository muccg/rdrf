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
        logger.debug("in get_or_build_user")
        user, built = super().get_or_build_user(username, ldap_user)
        if built:
            logger.debug("in built clause")
            from rdrf.models.definition import Registry
            from registry.patients.models import WorkingGroup
            registry_model = Registry.objects.get(code="ICHOMCRC")
            wg = WorkingGroup.objects.get(registry=registry_model,
                                          name="RPH")
            user.is_active = True
            logger.debug("set is_active")
            user.is_staff = True
            logger.debug("set is_staff")
            user.rdrf_registry.set([registry_model])
            logger.debug("set registry")

            user.working_groups.set([wg])
            logger.debug("set working_group")
            user.save()
            return user, built
        else:
            return user, built
