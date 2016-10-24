from operator import itemgetter
from itertools import chain
import json
from django.views.generic.base import View
from django.template.context_processors import csrf
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.shortcuts import redirect, get_object_or_404
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.db.models import Q
from django.core.paginator import Paginator, InvalidPage
from rdrf.models import Registry
from rdrf.form_progress import FormProgress
from rdrf.contexts_api import RDRFContextManager
from rdrf.components import FormsButton
from registry.patients.models import Patient

import logging
logger = logging.getLogger(__name__)


class PatientsListingView(View):

    def __init__(self, *args, **kwargs):
        super(PatientsListingView, self).__init__(*args, **kwargs)
        self.registry_model = None
        self.user = None
        self.registries = []
        self.patient_id = None

        # grid params
        self.custom_ordering = None
        self.start = None
        self.length = None
        self.page_number = None
        self.sort_field = None
        self.sort_direction = None
        self.columns = None
        self.queryset = None
        self.records_total = None
        self.filtered_total = None
        self.context = {}

    def get(self, request):
        # get just displays the empty table and writes the page
        # which initiates an ajax/post request on registry select
        # the protocol is the jquery DataTable
        # see http://datatables.net/manual/server-side

        self.user = request.user
        if self.user and self.user.is_anonymous():
            login_url = "%s?next=/router/" % reverse("login")
            return redirect(login_url)

        self.do_security_checks()
        self.set_csrf(request)
        self.set_registry(request)
        self.set_registries()  # for drop down
        self.patient_id = request.GET.get("patient_id", None)

        template_context = self.build_context()
        template = self.get_template()

        return render(request, template, template_context)

    def get_template(self):
        template = 'rdrf_cdes/patients_listing_no_registries.html' if len(
            self.registries) == 0 else 'rdrf_cdes/patients_listing.html'
        return template

    def build_context(self):
        return {
            "registries": self.registries,
            "location": "Patient Listing",
            "patient_id": self.patient_id,
            "registry_code": self.registry_model.code if self.registry_model else None,
            "columns": [col.to_dict(i) for (i, col) in enumerate(self.get_configure_columns())]
        }

    def get_columns(self):
        return [
            ColumnFullName("Patient", "patients.can_see_full_name"),
            ColumnDateOfBirth("Date of Birth", "patients.can_see_dob"),
            ColumnWorkingGroups("Working Groups", "patients.can_see_working_groups"),
            ColumnDiagnosisProgress("Diagnosis Entry Progress", "patients.can_see_diagnosis_progress"),
            ColumnDiagnosisCurrency("Updated < 365 days", "patients.can_see_diagnosis_currency"),
            ColumnGeneticDataMap("Genetic Data", "patients.can_see_genetic_data_map"),
            ColumnContextMenu("Modules", "patients.can_see_data_modules"),
        ]

    def get_configure_columns(self):
        columns = self.get_columns()
        for i, col in enumerate(columns):
            col.configure(self.registry_model, self.user, i)
        return [col for col in columns if col.user_can_see]

    def do_security_checks(self):
        if self.user.is_patient:
            raise PermissionDenied()

    def set_csrf(self, request):
        self.context.update(csrf(request))

    def set_registry(self, request):
        registry_code = request.GET.get("registry_code", None)
        if registry_code is not None:
            try:
                self.registry_model = Registry.objects.get(code=registry_code)
            except Registry.DoesNotExist:
                return HttpResponseRedirect("/")

    def set_registries(self):
        if self.registry_model is None:
            if self.user.is_superuser:
                self.registries = [
                    registry_model for registry_model in Registry.objects.all()]
            else:
                self.registries = [
                    registry_model for registry_model in self.user.registry.all()]
        else:
            self.registries = [self.registry_model]

    def json(self, data):
        json_data = json.dumps(data)
        return HttpResponse(json_data, content_type="application/json")

    ########################   POST #################################
    def post(self, request):
        # see http://datatables.net/manual/server-side
        logger.debug("********* RECEIVED POST *********")
        self.set_parameters(request)
        self.set_csrf(request)
        rows = self.get_results(request)
        results_dict = self.get_results_dict(self.draw,
                                             self.page_number,
                                             self.record_total,
                                             self.filtered_total,
                                             rows)
        return self.json(results_dict)

    def set_parameters(self, request):
        self.user = request.user
        self.registry_code = request.GET.get("registry_code")
        self.registry_model = get_object_or_404(Registry, code=self.registry_code)

        self.clinicians_have_patients = self.registry_model.has_feature("clinicians_have_patients")
        self.form_progress = FormProgress(self.registry_model)
        self.supports_contexts = self.registry_model.has_feature("contexts")
        self.rdrf_context_manager = RDRFContextManager(self.registry_model)

        def getint(param):
            try:
                return int(request.POST.get(param) or 0)
            except ValueError:
                return 0

        self.search_term = request.POST.get("search[value]") or ""
        self.draw = getint("draw")  # unknown
        self.start = getint("start")  # offset
        self.length = getint("length")  # page size
        self.page_number = ((self.start / self.length) if self.length else 0) + 1

        self.sort_field, self.sort_direction = self.get_ordering(request)

        self.columns = self.get_configure_columns()

    def get_results(self, request):
        if self.registry_model is None:
            logger.debug("registry model is None - returning empty results")
            return []
        if not self.check_security():
            logger.debug("security check failed - returning empty results")
            return []

        patients = self.run_query()
        logger.debug("got column data for each row in page OK")
        return patients

    def check_security(self):
        self.do_security_checks()
        if not self.user.is_superuser:
            if self.registry_model.code not in [r.code for r in self.user.registry.all()]:
                logger.info(
                    "User %s tried to browse patients in registry %s of which they are not a member" %
                    (self.user, self.registry_model.code))
                return False
        return True

    def get_ordering(self, request):
        # columns[0][data]:full_name
        #...
        # order[0][column]:1
        # order[0][dir]:asc
        sort_column_index = None
        sort_direction = None
        for key in request.POST:
            if key.startswith("order"):
                if "[column]" in key:
                    sort_column_index = request.POST[key]
                elif "[dir]" in key:
                    sort_direction = request.POST[key]

        column_name = "columns[%s][data]" % sort_column_index
        sort_field = request.POST.get(column_name, None)

        return sort_field, sort_direction

    def run_query(self):
        self.get_initial_queryset()
        self.filter_by_user_group()
        self.apply_ordering()
        self.record_total = self.patients.count()
        self.apply_search_filter()
        self.filtered_total = self.patients.count()
        return self.get_rows_in_page()

    def _get_main_or_default_context(self, patient_model):
        # for registries which do not have multiple contexts this will be the single context model
        # assigned to the patient
        # for registries which allow multiple form groups, it will be the
        # (only) context with cfg marked as default
        context_model = patient_model.default_context(self.registry_model)
        assert context_model is not None, "Expected context model to exist always"
        if context_model.context_form_group:
            assert context_model.context_form_group.is_default, "Expected to always get a context of the default form group"

        logger.debug("retrieved the default context for %s: it is %s" %
                     (patient_model, context_model))
        return context_model

    def apply_custom_ordering(self, qs):
        key_func = [col.sort_key(self.supports_contexts, self.form_progress, self.rdrf_context_manager)
                    for col in self.columns
                    if col.field == self.sort_field and col.sort_key and not col.sort_fields]

        if key_func:
            # we have to retrieve all rows - otehrwise , queryset has already been
            # ordered on base model
            return sorted(qs, key=key_func[0], reverse=(self.sort_direction == "desc"))
        else:
            logger.debug("key_func is none - not sorting")
            return qs

    def get_rows_in_page(self):
        results = self.apply_custom_ordering(self.patients)

        rows = []
        paginator = Paginator(results, self.length)
        try:
            page = paginator.page(self.page_number)
        except InvalidPage:
            logger.error("invalid page number: %s" % self.page_number)
            return []

        self.append_rows(page, rows)
        return rows

    def append_rows(self, page_object, row_list_to_update):
        for obj in page_object.object_list:
            row_list_to_update.append(self._get_row_dict(obj))

    def _get_row_dict(self, instance):
        # we need to do this so that the progress data for this instance
        # loaded!
        self.form_progress.reset()
        return {col.field: col.fmt(col.cell(instance, self.supports_contexts, self.form_progress, self.rdrf_context_manager))
                for col in self.columns}

    def get_initial_queryset(self):
        self.registry_queryset = Registry.objects.filter(
            code=self.registry_model.code)
        self.patients = Patient.objects.all()

    def apply_search_filter(self):
        if self.search_term:
            self.patients = self.patients.filter(Q(given_names__icontains=self.search_term) |
                                                 Q(family_name__icontains=self.search_term))

            count_after_search = self.patients.count()
            logger.debug(
                "search term provided - count after search = %s" % count_after_search)

    def filter_by_user_group(self):
        if not self.user.is_superuser:
            if self.user.is_curator:
                query_patients = Q(rdrf_registry__in=self.registry_queryset) & Q(
                    working_groups__in=self.user.working_groups.all())
                self.patients = self.patients.filter(query_patients)
                logger.debug(
                    "user is curator - returning patients in their working groups")
            elif self.user.is_genetic_staff:
                self.patients = self.patients.filter(
                    working_groups__in=self.user.working_groups.all())
                logger.debug(
                    "user is genetic staff - returning patients in their working groups")
            elif self.user.is_genetic_curator:
                self.patients = self.patients.filter(
                    working_groups__in=self.user.working_groups.all())
                logger.debug(
                    "user is genetic curator - returning patients in their working groups")
            elif self.user.is_working_group_staff:
                self.patients = self.patients.filter(
                    working_groups__in=self.user.working_groups.all())
                logger.debug(
                    "user is working group staff - returning patients in their working groups")
            elif self.user.is_clinician and self.clinicians_have_patients:
                self.patients = self.patients.filter(clinician=self.user)
                logger.debug(
                    "user is a clinician and clinicians have patients - returning their patients")
            elif self.user.is_clinician and not self.clinicians_have_patients:
                query_patients = Q(rdrf_registry__in=self.registry_queryset) & Q(
                    working_groups__in=self.user.working_groups.all())
                self.patients = self.patients.filter(query_patients)
                logger.debug(
                    "user is a clinician and clinicians don't have patients - returning patients in their working groups")
            elif self.user.is_patient:
                self.patients = self.patients.filter(user=self.user)
                logger.debug(
                    "user is a patient - returning the patient of which I am the user")
            else:
                logger.debug(
                    "user not in any recognised group - returning empty quesryset")
                self.patients = self.patients.none()
        else:
            logger.debug(
                "user is superuser - returning all patients in registry %s" % self.registry_model.code)
            self.patients = self.patients.filter(
                rdrf_registry__in=self.registry_queryset)

    def apply_ordering(self):
        if self.sort_field and self.sort_direction:
            dir = lambda field: "-" + field if self.sort_direction == "desc" else field
            sort_fields = chain(*[map(dir, col.sort_fields)
                                  for col in self.columns
                                  if col.field == self.sort_field])
            self.patients = self.patients.order_by(*sort_fields)

    def get_results_dict(self, draw, page, total_records, total_filtered_records, rows):
        return {
            "draw": draw,
            "recordsTotal": total_records,
            "recordsFiltered": total_filtered_records,
            "rows": rows
        }

class Column(object):
    field = "id"
    sort_fields = ["id"]

    def __init__(self, label, perm):
        self.label = label
        self.perm = perm

    def configure(self, registry, user, order):
        self.registry = registry
        self.user = user
        self.order = order
        self.user_can_see = user.has_perm(self.perm)

    def sort_key(self, supports_contexts=False,
                 form_progress=None, context_manager=None):
        return lambda patient: self.cell(patient, supports_contexts, form_progress, context_manager)

    def cell(self, patient, supports_contexts=False,
             form_progress=None, context_manager=None):
        return getattr(patient, self.field)

    def fmt(self, val):
        return str(val)

    def to_dict(self, i):
        "Structure used by jquery datatables"
        return {
            "data": self.field,
            "label": self.label,
            "order": i,
        }

class ColumnFullName(Column):
    field = "full_name"
    sort_fields = ["family_name", "given_names"]

    def configure(self, registry, user, order):
        super(ColumnFullName, self).configure(registry, user, order)
        if not registry:
            return "<span>%d %s</span>"

        # cache reversed url because urlroute searches are slow
        base_url = reverse("patient_edit", kwargs={ "registry_code": registry.code,
                                                    "patient_id": 0})
        self.link_template = '<a href="%s">%%s</a>' % (base_url.replace("/0", "/%d"))

    def cell(self, patient, supports_contexts=False, form_progress=None, context_manager=None):
        return self.link_template % (patient.id, patient.display_name)

class ColumnDateOfBirth(Column):
    field = "date_of_birth"
    sort_fields = ["date_of_birth"]

    def fmt(self, val):
        return val.strftime("%d-%m-%Y") if val is not None else ""

class ColumnNonContexts(Column):
    sort_fields = []

    def cell(self, patient, supports_contexts=False, form_progress=None, context_manager=None):
        if supports_contexts:
            # if registry supports contexts, should use the context browser
            return None
        return self.cell_non_contexts(patient, form_progress, context_manager)

    def fmt(self, val):
        return "N/A" if val is None else self.fmt_non_contexts(val)

    def sort_key(self, supports_contexts=False,
                 form_progress=None, context_manager=None):
        return lambda patient: self.cell(patient, supports_contexts, form_progress, context_manager)

    def cell_non_contexts(self, patient, form_progress=None, context_manager=None):
        pass

    def fmt_non_contexts(self, val):
        return val

    def icon(self, tick):
        icon = "ok" if tick else "remove"
        color = "green" if tick else "red"
        # fixme: replace inline style with css class
        return "<span class='glyphicon glyphicon-%s' style='color:%s'></span>" % (icon, color)

class ColumnWorkingGroups(Column):
    field = "working_groups_display"

class ColumnDiagnosisProgress(ColumnNonContexts):
    field = "diagnosis_progress"

    def cell_non_contexts(self, patient, form_progress=None, context_manager=None):
        return form_progress.get_group_progress("diagnosis", patient)

    def fmt_non_contexts(self, progress_number):
        template = "<div class='progress'><div class='progress-bar progress-bar-custom' role='progressbar'" \
                   " aria-valuenow='%s' aria-valuemin='0' aria-valuemax='100' style='width: %s%%'>" \
                   "<span class='progress-label'>%s%%</span></div></div>"
        return template % (progress_number, progress_number, progress_number)

class ColumnDiagnosisCurrency(ColumnNonContexts):
    field = "diagnosis_currency"

    def cell_non_contexts(self, patient, form_progress=None, context_manager=None):
        return form_progress.get_group_currency("diagnosis", patient)

    def fmt_non_contexts(self, diagnosis_currency):
        return self.icon(diagnosis_currency)

class ColumnGeneticDataMap(ColumnNonContexts):
    field = "genetic_data_map"

    def cell_non_contexts(self, patient, form_progress=None, context_manager=None):
        return form_progress.get_group_has_data("genetic", patient)

    def fmt_non_contexts(self, has_genetic_data):
        return self.icon(has_genetic_data)

class ColumnContextMenu(Column):
    field = "context_menu"

    def configure(self, registry, user, order):
        super(ColumnContextMenu, self).configure(registry, user, order)
        self.registry_has_context_form_groups = registry.has_groups if registry else False
        
        if registry:
            # fixme: slow, do intersection instead
            self.free_forms = list(filter(user.can_view, registry.free_forms))

    def cell(self, patient, supports_contexts=False, form_progress=None, context_manager=None):
        return "".join(self._get_forms_buttons(patient))

    def _get_forms_buttons(self, patient, form_progress=None, context_manager=None):
        if not self.registry_has_context_form_groups:
            # if there are no context groups -normal registry
            return [self._get_forms_button(patient, None, self.free_forms)]
        else:
            # display one button per form group
            buttons = []
            for fixed_form_group in self.registry.fixed_form_groups:
                buttons.append(self._get_forms_button(patient,
                                                      fixed_form_group,
                                                      fixed_form_group.forms))

            for multiple_form_group in self.registry.multiple_form_groups:
                buttons.append(self._get_forms_button(patient,
                                                      multiple_form_group,
                                                      multiple_form_group.forms))


            return buttons

    def _get_forms_button(self, patient_model, context_form_group, forms):
        button = FormsButton(self.registry, self.user, patient_model,
                             context_form_group, forms)

        return """
            <div class="dropdown">
                <button class="btn btn-primary btn-sm dropdown-toggle" type="button" id="forms_button_%s" data-toggle="dropdown" aria-haspopup="true" aria-expanded="true">
                    %s <span class="caret"></span>
                </button>
                <ul class="dropdown-menu" aria-labelledby="forms_button_%s">%s</ul>
            </div>
        """ % (button.id, button.button_caption, button.id, button.html)

    def sort_key(self, *args, **kwargs):
        return None
