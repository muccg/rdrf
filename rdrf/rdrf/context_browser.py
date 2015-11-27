from registry.patients.models import Patient
from rdrf.models import RDRFContext
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from operator import itemgetter
from django.core.paginator import Paginator
from django.core.urlresolvers import reverse
from rdrf.context_menu import PatientContextMenu


class ContextBrowserError(Exception):
    pass


class ContextBrowser(object):
    def __init__(self, user, registry_model):
        self.user = user
        self.registry_model = registry_model
        self.grid_config = self._get_grid_config()
        self.columns = self._get_columns()
        self.search_phrase = None
        self.current = None
        self.row_count = 0
        self.objects = []
        self.total = 0

    def _create_results(self, objects, total):
        results = {
            "current": self.current,
            "rowCount": self.row_count,
            "searchPhrase": self.search_phrase,
            "rows": objects,
            "total": total,
            "show_add_patient": not self.registry_model.has_feature("no_add_patient_button")
        }
        return results

    def _get_grid_config(self):
        from django.conf import settings
        return settings.GRID_CONTEXT_LISTING

    def _get_columns(self):
        columns = []

        sorted_by_order = sorted(self.grid_config, key=itemgetter('order'), reverse=False)

        for definition in sorted_by_order:
            if self.user.is_superuser or definition["access"]["default"] or \
                    self.user.has_perm(definition["access"]["permission"]):
                columns.append(
                    {
                        "data": definition["data"],
                        "label": definition["label"],
                        "model": definition["model"]
                    }
                )

        return columns

    def do_search(self, search_phrase, row_count, current):
        self.search_phrase = search_phrase
        self.row_count = row_count
        self.current = current
        patient_query_set = self._get_patient_queryset()

        total = patient_query_set.count()

        if total == 0:
            return self._create_results([], 0)

        if self.row_count == -1:
            # all rows
            self.row_count = total

        rows = self._get_rows(patient_query_set)

        return self._create_results(rows, len(rows))


    def foo(self):
        # TODO fix up this - just moved it from the ContextResource
        if sort_field and sort_direction:
            if sort_direction == "desc":
                sort_field = "-" + sort_field
            query_set = query_set.order_by(sort_field)
            logger.debug("sort field = %s" % sort_field)

        if search_phrase:
            from django.db.models import Q
            query_set = query_set.filter(
                Q(given_names__icontains=search_phrase) | Q(family_name__icontains=search_phrase))

        total = query_set.count()

        if total == 0:
            # No patients found
            results = {
                "current": 1,
                "rowCount": 0,
                "searchPhrase": search_phrase,
                "rows": [],
                "total": total,
                "show_add_patient": not chosen_registry.has_feature("no_add_patient_button"),
            }
            self.log_throttled_access(request)
            return self.create_response(request, results)

        if row_count == -1:
            # All
            row_count = total

        paginator = Paginator(query_set, row_count)

        try:
            page = paginator.page(current)
        except InvalidPage:
            raise Http404("Sorry, no results on that page.")

        objects = []

        logger.debug("reg code = %s" % registry_code)
        logger.debug("user = %s" % request.user)

        bulk_progress_data = self._bulk_compute_progress(
            page, request.user, registry_code)

        for result in page.object_list:
            bundle = self.build_bundle(obj=result, request=request)
            setattr(bundle, 'progress_data', bulk_progress_data)  # crap I know
            bundle = self.full_dehydrate(bundle)
            objects.append(bundle)

        # Adapt the results to fit what jquery bootgrid expects

        results = {
            "current": current,
            "rowCount": row_count,
            "searchPhrase": search_phrase,
            "rows": objects,
            "total": total,
            "show_add_patient": not chosen_registry.has_feature("no_add_patient_button"),
        }

    def _get_patient_queryset(self):
        patients_queryset = Patient.objects.filter(rdrf_registry__in=[self.registry_model])
        if not self.user.is_superuser:
            if self.user.is_curator:
                patients_queryset.filter(working_groups__in=self.user.working_groups.all())
            elif self.user.is_genetic_staff:
                patients_queryset = patients_queryset.filter(working_groups__in=self.user.working_groups.all())
            elif self.user.is_genetic_curator:
                patients_queryset = patients_queryset.filter(working_groups__in=self.user.working_groups.all())
            elif self.user.is_working_group_staff:
                patients_queryset = patients_queryset.filter(working_groups__in=self.user.working_groups.all())
            elif self.user.is_clinician and clinicians_have_patients:
                patients_queryset = patients_queryset.filter(clinician=self.user)
            elif self.user.is_clinician and not clinicians_have_patients:
                patients_queryset = patients_queryset.filter(working_groups__in=self.user.working_groups.all())
            elif request.user.is_patient:
                patients_queryset = patients_queryset.filter(user=self.user)
            else:
                patients_queryset = patients_queryset.none()

        if self.search_phrase:
            patients_queryset = patients_queryset.filter(Q(given_names__icontains=self.search_phrase) |
                                        Q(family_name__icontains=self.search_phrase))

        return patients_queryset

    def _get_rows(self, patients):
        rows = []

        for patient in patients:
            context_models = patient.context_models
            if len(context_models) == 0:
                rows.append(self._get_row(patient))
            else:
                for context_model in context_models:
                    rows.append(self._get_row(patient, context_model))
        return rows

    def _get_row(self, patient_model, context_model=None):
        row = {}
        for column in self.columns:
            field = column["data"]
            label = column["label"]
            model = column["model"]
            if model == "Patient":
                if hasattr(patient_model, field):
                    value = str(getattr(patient_model, field))
                else:
                    value = None

            elif model == "RDRFContext":
                if context_model is not None:
                    value = str(getattr(context_model, field))
                else:
                    value = None
            elif model == "func":
                func_name = "get_%s" % field
                if hasattr(self, func_name):
                    func = getattr(self, func_name)
                    value = func(patient_model, context_model)

            row[field] = value
        return row

    def get_context_menu(self, patient_model, context_model):
        registry_code = self.registry_model.code
        context_menu = PatientContextMenu(self.user, self.registry_model, patient_model, context_model)
        return context_menu.html















