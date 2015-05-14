from django.shortcuts import render_to_response, RequestContext
from django.shortcuts import redirect
from django.views.generic.base import View
from django.core.urlresolvers import reverse
from django.contrib.auth.models import Group


# todo update ophg registries to use new demographics and patients listing forms: we need to fix this properly
def in_fkrp(user):
    user_reg_codes = [ r.code for r in user.registry.all()]
    return "fkrp" in user_reg_codes

_ADMIN_PATIENT_LISTING = "admin:patients_patient_changelist"
_NEW_PATIENT_LISTING = "patientslisting"

class RouterView(View):

    def get(self, request):
        user = request.user
        
        redirect_url = None

        if user.is_authenticated():
            if user.is_superuser:
                redirect_url = reverse(_ADMIN_PATIENT_LISTING)
            elif user.is_clinician:
                if in_fkrp(user):
                    redirect_url = reverse(_NEW_PATIENT_LISTING)
                else:
                    redirect_url = reverse(_ADMIN_PATIENT_LISTING)
            elif user.is_genetic_staff:
                redirect_url = reverse(_ADMIN_PATIENT_LISTING)
            elif user.is_working_group_staff:
                redirect_url = reverse(_ADMIN_PATIENT_LISTING)
            elif user.is_genetic_curator:
                redirect_url = reverse(_ADMIN_PATIENT_LISTING)
            elif user.is_curator:
                if in_fkrp(user):
                    redirect_url = reverse(_NEW_PATIENT_LISTING)
                else:
                    redirect_url = reverse(_ADMIN_PATIENT_LISTING)
            elif user.is_patient:
                regs = user.get_registries()
                if regs:
                    if len(regs) == 1:
                        redirect_url = reverse("patient_page", args=[regs[0].code])
            else:
                redirect_url = reverse("admin:index")
        else:
            redirect_url = "%s?next=%s" % (reverse("login"), reverse("login_router"))

        return redirect(redirect_url)
