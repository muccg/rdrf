from django.conf import settings


def can_user_self_unlock(user):
    def user_is_nonprivileged(user):
        return user.is_patient or user.is_parent or user.is_carrier

    return (getattr(settings, 'ACCOUNT_SELF_UNLOCK_ENABLED', False) and
            user_is_nonprivileged(user) and
            not user.prevent_self_unlock)
