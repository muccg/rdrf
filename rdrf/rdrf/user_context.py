from django.contrib.auth.models import Group


def is_admin(request):
    user = request.user
    
    return {
        'is_admin': user.is_superuser
    }

def is_patient(request):
    user = request.user
    is_patient = False
    group = _get_group("patients")

    if group in user.groups.all():
        is_patient = True

    return {
        'is_patient': is_patient
    }

def is_clinician(request):
    return {
        'is_clinician': False
    }

def _get_group(group_name):
    try:
        group = Group.objects.get(name__icontains = group_name)
        return group
    except Group.DoesNotExist:
        return None
