from functools import wraps
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib.auth.models import Group

import logging

from models import Registry

logger = logging.getLogger("registry_log")


def patient_has_access(function):

    @wraps(function)
    def _wrapped_view(*args, **kwargs):
        user = args[0].user
        registry_code = kwargs['registry_code']
        registry = Registry.objects.get(code=registry_code)
        
        if not registry.questionnaire:
            return function(*args, **kwargs)
        
        if not registry.questionnaire.login_required:
            return function(*args, **kwargs)

        if not user.is_authenticated():
            return HttpResponseRedirect(reverse("patient_page", args={registry_code}))

        try:
            patient_group = Group.objects.get(name__icontains="patients")
            if patient_group not in user.groups.all():
                return HttpResponseRedirect(reverse("patient_page", args={registry_code}))
        except Group.DoesNotExist:
            logger.error("Group Patient not found")

        return function(*args, **kwargs)

    return _wrapped_view
