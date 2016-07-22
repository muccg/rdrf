from django.views.generic.base import View
from django.template.context_processors import csrf
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect

from rdrf.models import Registry

import logging
logger = logging.getLogger(__name__)

PATIENT_CONTENT_TYPE = ContentType.objects.get(model='patient')

# new improved patient listing - incomplete and not hooked up yet

class PatientListing(View):

    def __init__(self, *args, **kwargs):
        super(PatientListing, self).__init__(*args, **kwargs)
        self.registry_model = None
        self.user = None
        self.registries = [] 

        # grid params
        self.start = None
        self.length = None
        self.page_number = None
        self.sort_field = None
        self.sort_direction = None
        self.columns = None
        self.queryset = None
        self.records_total = None
        self.context = {}
        

    # PUBLIC

    def get(self, request):
        # get just displays the empty table and writes the page
        # which initiates an ajax/post request on registry select
        # the protocol is the jquery DataTable
        # see http://datatables.net/manual/server-side

        self.user = request.user

        self._do_security_checks()
        self._set_csrf(request)
        self._set_registry(request)

        self._set_registries()


        patient_id = request.GET.get("patient_id", None)

        if patient_id is not None:
            if not self._allowed(request.user, registry_model, patient_id):
                return HttpResponseRedirect("/")

        context_form_group_id = request.GET.get("context_form_group_id", None)

        context["registries"] = registries
        context["location"] = "Context List"
        context["patient_id"] = patient_id
        context["context_form_group_id"] = context_form_group_id
        context["registry_code"] = registry_code

        columns = []

        sorted_by_order = sorted(
            settings.GRID_CONTEXT_LISTING, key=itemgetter('order'), reverse=False)

        for definition in sorted_by_order:
            if request.user.is_superuser or definition["access"]["default"] or \
                    request.user.has_perm(definition["access"]["permission"]):
                columns.append(
                    {
                        "data": definition["data"],
                        "label": definition["label"]
                    }
                )

        context["columns"] = columns

        template = 'rdrf_cdes/contexts_no_registries.html' if len(
            registries) == 0 else 'rdrf_cdes/contexts.html'

        return render_to_response(
            template,
            context,
            context_instance=RequestContext(request))

    def _allowed(self, user, registry_model, patient_id):
        return True  # todo restrict

    def get_columns(self, user):
        columns = []
        sorted_by_order = sorted(self.get_grid_definitions(
        ), key=itemgetter('order'), reverse=False)

        for definition in sorted_by_order:
            if user.is_superuser or definition["access"]["default"] or user.has_perm(definition["access"]["permission"]):
                columns.append(
                    {
                        "data": definition["data"],
                        "label": definition["label"]
                    }
                )

        return columns

    def get_grid_definitions(self):
        return settings.GRID_PATIENT_LISTING

    @login_required
    def post(self, request):
        # see http://datatables.net/manual/server-side
        results = self._get_results(request)
        json_packet = self._json(results)
        return json_packet

    # PRIVATE

    def _do_security_checks(self):
        if self.user.is_patient:
            raise PermissionDenied()

    def _set_csrf(self, request):
        self.context.update(csrf(request))

    def _set_registry(self, request):
        registry_code = request.GET.get("registry_code", None)
        if registry_code is not None:
            try:
                self.registry_model = Registry.objects.get(code=registry_code)
            except Registry.DoesNotExist:
                return HttpResponseRedirect("/")


    def _set_registries(self):
        if self.registry_model is None:
            if self.user.is_superuser:
                self.registries = [
                    registry_model for registry_model in Registry.objects.all()]
            else:
                self.registries = [
                    registry_model for registry_model in self.user.registry.all()]
        else:
            self.registries = [registry_model]


    def _json(self, data):
        json_data = json.dumps(data)
        return HttpResponse(json_data, content_type="application/json")

    def _get_results(self, request):
        patients = self._run_query()
        return self._get_rows(patients)

    def _run_query(self):
        pass

