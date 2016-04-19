from django.shortcuts import redirect
from django.views.generic.base import View
from django.core.urlresolvers import reverse


# todo update ophg registries to use new demographics and patients listing
# forms: we need to fix this properly
def in_fkrp(user):
    user_reg_codes = [r.code for r in user.registry.all()]
    return "fkrp" in user_reg_codes

_ADMIN_PATIENT_LISTING = "admin:patients_patient_changelist"
_HOME_PAGE = "admin:index"
_CONTEXTS_LISTING = "contextslisting"


class RouterView(View):

    def get(self, request):
        user = request.user

        redirect_url = None

        if user.is_authenticated():
            if user.is_superuser:
                redirect_url = reverse(_CONTEXTS_LISTING)
            elif user.is_clinician:
                redirect_url = reverse(_CONTEXTS_LISTING)
            elif user.is_genetic_staff:
                redirect_url = reverse(_CONTEXTS_LISTING)
            elif user.is_working_group_staff:
                redirect_url = reverse(_CONTEXTS_LISTING)
            elif user.is_genetic_curator:
                redirect_url = reverse(_CONTEXTS_LISTING)
            elif user.is_curator:
                redirect_url = reverse(_CONTEXTS_LISTING)
            elif user.is_parent or user.is_patient:
                if user.num_registries == 1:
                    registry_code = user.get_registries()[0].code
                    redirect_url = reverse(
                        "parent_page" if user.is_parent else "patient_page",
                        args=[registry_code])
            else:
                redirect_url = reverse(_CONTEXTS_LISTING)

        else:
            redirect_url = "%s?next=%s" % (reverse("login"), reverse("login_router"))

        return redirect(redirect_url)
