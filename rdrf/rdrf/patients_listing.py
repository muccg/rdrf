from operator import itemgetter
import json
from django.views.generic.base import View
from django.template.context_processors import csrf
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.utils.html import escape
from django.conf import settings
from django.shortcuts import render_to_response, RequestContext, get_object_or_404
from django.db.models import Q
from django.core.paginator import Paginator, InvalidPage
from rdrf.models import Registry
from rdrf.models import RDRFContext
from rdrf.form_progress import FormProgress
from rdrf.contexts_api import RDRFContextManager
from rdrf.context_menu import PatientContextMenu
from rdrf.components import FormsButton
from registry.patients.models import Patient

import logging
logger = logging.getLogger(__name__)

PATIENT_CONTENT_TYPE = ContentType.objects.get(model='patient')


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
        self.do_security_checks()
        self.set_csrf(request)
        self.set_registry(request)
        self.set_registries()  # for drop down
        self.patient_id = request.GET.get("patient_id", None)

        template_context = self.build_context()
        template = self.get_template()

        return render_to_response(
            template,
            template_context,
            context_instance=RequestContext(request))

    def get_template(self):
        template = 'rdrf_cdes/patients_listing_no_registries.html' if len(
            self.registries) == 0 else 'rdrf_cdes/patients_listing.html'
        return template

    def build_context(self):
        context = {}
        context["registries"] = self.registries
        context["location"] = "Patient Listing"
        context["patient_id"] = self.patient_id
        context[
            "registry_code"] = self.registry_model.code if self.registry_model else None
        context["columns"] = self.get_columns()
        return context

    def get_columns(self):
        columns = []
        sorted_by_order = sorted(self.get_grid_definitions(
        ), key=itemgetter('order'), reverse=False)

        for definition in sorted_by_order:
            if self.user.is_superuser or definition["access"]["default"] or self.user.has_perm(definition["access"]["permission"]):
                columns.append(
                    {
                        "data": definition["data"],
                        "label": definition["label"]
                    }
                )

        return columns

    def get_grid_definitions(self):
        return settings.GRID_PATIENT_LISTING

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
        json_packet = self.json(results_dict)
        return json_packet

    def set_parameters(self, request):
        self.user = request.user
        logger.debug("user = %s" % self.user)
        self.registry_code = request.GET.get("registry_code", None)
        try:
            self.registry_model = Registry.objects.get(code=self.registry_code)
            logger.debug("registry_model = %s" % self.registry_model)
            self.clinicians_have_patients = self.registry_model.has_feature(
                "clinicians_have_patients")
            self.form_progress = FormProgress(self.registry_model)
            self.supports_contexts = self.registry_model.has_feature(
                "contexts")
            self.rdrf_context_manager = RDRFContextManager(self.registry_model)
            self.search_term = request.POST.get("search[value]", "")
            logger.debug("search term = %s" % self.search_term)

            self.draw = int(request.POST.get("draw", None))
            logger.debug("draw = %s" % self.draw)

            self.start = int(request.POST.get("start", None))
            logger.debug("start = %s" % self.start)

            # length = records per page
            self.length = int(request.POST.get("length", None))
            logger.debug("length = %s" % self.length)

            self.page_number = (self.start / self.length) + 1
            logger.debug("page = %s" % self.page_number)

            self.sort_field, self.sort_direction = self.get_ordering(request)

            self.columns = self.get_columns()
            self.func_map = self.get_func_map()

        except Registry.DoesNotExist:
            logger.debug("selected registry does not exist")
            pass

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
            if not self.registry_model.code in [r.code for r in self.user.registry.all()]:
                logger.info("User %s tried to browse patients in registry %s of which they are not a member" % (self.user,
                                                                                                                self.registry_model.code))
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
        if sort_field == "full_name":
            sort_field = "family_name"

        return sort_field, sort_direction

    def run_query(self):
        self.get_initial_queryset()
        logger.debug("created initial queryset OK")
        self.filter_by_user_group()
        logger.debug("filtered by user group OK")
        self.apply_ordering()
        self.record_total = self.patients.count()
        self.apply_search_filter()
        self.filtered_total = self.patients.count()

        logger.debug("filtered by search term OK")
        rows = self.get_rows_in_page()
        logger.debug("got rows in page OK")
        return rows

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

    def apply_custom_ordering(self, rows):
        key_func = None
        if self.custom_ordering.startswith("-"):
            ordering = self.custom_ordering[1:]
            direction = "desc"
        else:
            ordering = self.custom_ordering
            direction = "asc"

        if ordering == "patient_link":
            def get_name(patient_model):
                return patient_model.display_name

            key_func = get_name
            logger.debug("key_func is by patient_link")

        elif ordering == "date_of_birth":
            def get_dob(patient_model):
                return patient_model.date_of_birth
            key_func = get_dob

        elif ordering == "working_groups_display":
            def get_wg(patient_model):
                try:
                    wg = patient_model.working_groups.get()
                    return wg.name
                except Exception, ex:
                    logger.debug("error wg %s" % ex)
                    return ""
            key_func = get_wg

        elif ordering == "diagnosis_progress":
            # only makes sense to show progress with the fixed or main context
            self.form_progress.reset()

            def get_dp(patient_model):
                try:
                    context_model = self._get_main_or_default_context(
                        patient_model)
                    return self.form_progress.get_group_progress("diagnosis", patient_model, context_model)
                except:
                    return 0

            key_func = get_dp

        elif ordering == "diagnosis_currency":
            # only makes sense to show progress with the fixed or main context
            self.form_progress.reset()

            def get_dc(patient_model):
                try:
                    context_model = self._get_main_or_default_context(
                        patient_model)
                    return self.form_progress.get_group_currency("diagnosis", patient_model, context_model)
                except:
                    return False

            key_func = get_dc

        elif ordering == "genetic_data_map":
            self.form_progress.reset()

            def get_gendatamap(patient_model):
                try:
                    context_model = self._get_main_or_default_context(
                        patient_model)
                    return self.form_progress.get_group_has_data("genetic", patient_model, context_model)
                except:
                    return False

            key_func = get_gendatamap

        if key_func is None:
            logger.debug("key_func is none - not sorting")
            return rows

        d = direction == "desc"

        return sorted(rows, key=key_func, reverse=d)

    def get_rows_in_page(self):
        query_set = self.patients

        if self.custom_ordering:
            # we have to retrieve all rows - otehrwise , queryset has already been
            # ordered on base model
            query_set = [p for p in query_set]
            query_set = self.apply_custom_ordering(query_set)

        rows = []
        paginator = Paginator(query_set, self.length)
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
        row_dict = {}
        for field in self.func_map:
            try:
                value = self.func_map[field](instance)
            except KeyError:
                value = "UNKNOWN COLUMN"
            row_dict[field] = value

        logger.debug("got row_dict for %s = %s" % (instance, row_dict))
        return row_dict

    def get_func_map(self):
        logger.debug("generating func map")
        func_map = {}
        patient_field_names = [
            field_object.name for field_object in Patient._meta.fields]
        logger.debug("patient fields = %s" % patient_field_names)

        def patient_func(field):
            def f(patient):
                try:
                    return str(getattr(patient, field))
                except Exception, ex:
                    msg = "Error retrieving grid field %s for patient %s: %s" % (
                        field, patient, ex)
                    logger.error(msg)
                    return "GRID ERROR: %s" % msg

            return f

        def grid_func(obj, field):
            method = getattr(obj, field)

            def f(patient):
                try:
                    return method(patient)
                except Exception, ex:
                    msg = "Error retrieving grid field %s for patient %s: %s" % (
                        field, patient, ex)
                    logger.error(msg)
                    return "GRID ERROR: %s" % msg

            return f

        def k(msg):
            # constant combinator
            def f(patient):
                return msg
            return f

        for column in self.columns:
            field = column["data"]
            logger.debug("checking field %s" % field)
            func_name = "_get_grid_field_%s" % field
            logger.debug("checking %s" % func_name)
            if hasattr(self, func_name):
                func_map[field] = grid_func(self, func_name)
                logger.debug("field %s is a serverside api func" % field)
            elif field in patient_field_names:
                logger.debug("field is a patient field")
                func_map[field] = patient_func(field)
                logger.debug("field %s is a patient function" % field)
            else:
                logger.debug("field %s is unknown" % field)
                func_map[field] = k("UNKNOWN COLUMN!")

        return func_map

    def _get_grid_field_diagnosis_progress(self, patient_model):
        if not self.supports_contexts:
            progress_number = self.form_progress.get_group_progress(
                "diagnosis", patient_model)
            template = "<div class='progress'><div class='progress-bar progress-bar-custom' role='progressbar'" + \
                       " aria-valuenow='%s' aria-valuemin='0' aria-valuemax='100' style='width: %s%%'>" + \
                       "<span class='progress-label'>%s%%</span></div></div>"
            return template % (progress_number, progress_number, progress_number)
        else:
            # if registry supports contexts, should use the context browser
            return "N/A"

    def _get_grid_field_data_modules(self, patient_model):
        if not self.supports_contexts:
            default_context_model = self.rdrf_context_manager.get_or_create_default_context(
                patient_model)
            return self.form_progress.get_data_modules(self.user, patient_model, default_context_model)
        else:
            return "N/A"

    def _get_grid_field_genetic_data_map(self, patient_model):
        if not self.supports_contexts:
            has_genetic_data = self.form_progress.get_group_has_data(
                "genetic", patient_model)
            icon = "ok" if has_genetic_data else "remove"
            color = "green" if has_genetic_data else "red"
            return "<span class='glyphicon glyphicon-%s' style='color:%s'></span>" % (icon, color)
        else:
            return "N/A"

    def _get_grid_field_diagnosis_currency(self, patient_model):
        if not self.supports_contexts:
            diagnosis_currency = self.form_progress.get_group_currency(
                "diagnosis", patient_model)
            icon = "ok" if diagnosis_currency else "remove"
            color = "green" if diagnosis_currency else "red"
            return "<span class='glyphicon glyphicon-%s' style='color:%s'></span>" % (icon, color)
        else:
            return "N/A"

    def _get_grid_field_full_name(self, patient_model):

        return "<a href='%s'>%s</a>" % (reverse("patient_edit", kwargs={"registry_code": self.registry_code,
                                                                        "patient_id": patient_model.id}),
                                        patient_model.display_name)

    def _get_grid_field_working_groups_display(self, patient_model):
        return patient_model.working_groups_display

    def _get_grid_field_context_menu(self, patient_model):
        buttons = [
            forms_button for forms_button in self._get_forms_buttons(patient_model)]
        return "".join(buttons)

    def _get_forms_buttons(self, patient_model):
        buttons = []
        free_forms = self.registry_model.free_forms
        if free_forms:
            # if there are no context groups -normal registry
            free_forms_button = self._get_forms_button(
                patient_model, None, free_forms)
            buttons.append(free_forms_button)
            return buttons

        logger.debug("no free forms ...")

        # fixed context groups

        for fixed_form_group in self.registry_model.fixed_form_groups:
            fixed_form_group_button = self._get_forms_button(patient_model,
                                                             fixed_form_group,
                                                             fixed_form_group.forms)
            buttons.append(fixed_form_group_button)

        for multiple_form_group in self.registry_model.multiple_form_groups:
            multiple_form_group_button = self._get_forms_button(patient_model,
                                                                multiple_form_group,
                                                                multiple_form_group.forms)

            buttons.append(multiple_form_group_button)

        return buttons

    def _get_forms_button(self, patient_model, context_form_group, forms):
        forms_button_component = FormsButton(self.registry_model,
                                             patient_model,
                                             context_form_group,
                                             forms)

        button_html = """<button type="button" class="contextmenu btn btn-primary btn-xs" data-toggle="popover" data-html="true" data-content="%s"
                      id="forms_button_%s" data-original-title="" title="">%s</button>""" % (escape(forms_button_component.html),
                                                                                             forms_button_component.id,
                                                                                             forms_button_component.button_caption)
        return button_html

        return forms_button_component

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
        if all([self.sort_field, self.sort_direction]):
            logger.debug("*** ordering %s %s" %
                         (self.sort_field, self.sort_direction))

            if self.sort_direction == "desc":
                self.sort_field = "-" + self.sort_field

            self.patients = self.patients.order_by(self.sort_field)
            logger.debug("sort field = %s" % self.sort_field)

    def no_results(self, draw):
        return {
            "draw": draw,
            "recordsTotal": 0,
            "recordsFiltered": 0,
            "rows": []
        }

    def get_results_dict(self, draw, page, total_records, total_filtered_records, rows):

        #       {
        # "draw": 2,  <-- must be returned , is a counter used by DataTable
        # "recordsTotal": 57,
        # "recordsFiltered": 57,
        # "rows": [
        #   {
        #     "first_name": "Charde",
        #     "last_name": "Marshall",
        #     "position": "Regional Director",
        #     "office": "San Francisco",
        #     "start_date": "16th Oct 08",
        #     "salary": "$470,600"
        #   },..]

        results = {
            "draw": draw,
            "recordsTotal": total_records,
            "recordsFiltered": total_filtered_records,
            "rows": [row for row in rows]
        }

        return results
