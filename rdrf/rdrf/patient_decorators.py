from functools import wraps
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib.auth.models import Group

import logging

logger = logging.getLogger("registry_log")


def patient_has_access(function):

    @wraps(function)
    def _wrapped_view(*args, **kwargs):
        user = args[0].user
        access = False
        
        if not user.is_authenticated():
            return HttpResponseRedirect(reverse("patient_page", args={ kwargs['registry_code'] }))
        
        try:
            patient_group = Group.objects.get(name__icontains = "patients")
            if not patient_group in user.groups.all():
                return HttpResponseRedirect(reverse("patient_page", args={ kwargs['registry_code'] }))
        except Group.DoesNotExist:
            logger.error("Group Patient not found")
         
        return function(*args, **kwargs)
    
    return _wrapped_view
    