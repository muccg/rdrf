from registry.patients.models import Patient
from rdrf.models import RDRFContext
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q


class ContextBrowserError(Exception):
    pass


class ContextBrowser(object):
    def __init__(self, user, registry_model):
        self.user = user
        self.registry_model = registry_model
        self.query = {}
        self.grid_config = self._get_grid_config()

        self.columns = self._get_columns()

    def _get_grid_config(self):
        from django.conf import settings
        return setting.GRID_CONTEXT_LISTING

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

    def run_query(self, query):
        self.query = query
        patients = self._get_queryset(query)
        return self._get_rows(patients)

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

    def _get_queryset(self, query):
        patients = Patient.objects.filter(rdrf_registry__in=[self.registry_model])
        if not self.user.is_superuser:
            if self.user.is_curator:
                patients.filter(working_groups__in=self.user.working_groups.all())
            elif self.user.is_genetic_staff:
                patients = patients.filter(working_groups__in=self.user.working_groups.all())
            elif self.user.is_genetic_curator:
                patients = patients.filter(working_groups__in=self.user.working_groups.all())
            elif self.user.is_working_group_staff:
                patients = patients.filter(working_groups__in=self.user.working_groups.all())
            elif self.user.is_clinician and clinicians_have_patients:
                patients = patients.filter(clinician=self.user)
            elif self.user.is_clinician and not clinicians_have_patients:
                patients = patients.filter(working_groups__in=self.user.working_groups.all())
            elif request.user.is_patient:
                patients = patients.filter(user=self.user)
            else:
                patients = patients.none()

        return patients

    def _get_rows(self, patients):
        rows = []
        for patient in patients:
            context_models = patient.context_models
            if len(context_models) == 0:
                row.append(self._get_row(patient))
            else:
                for context_model in context_models:
                    row.append(self._get_row(patient, context_model))
        return rows

    def _get_row(self, patient_model, context_model=None):
        row = []
        for column in self.columns:
            field = column["data"]
            label = column["label"]
            model = column["model"]
            if model == "Patient":
                value = getattr(patient_model, field)

            elif model == "RDRFContext":
                if context_model is not None:
                    value = getattr(context_model, field)
                else:
                    value = None
            else:
                raise Exception("Unknown model: %s" % model)

            row.append((model, field, label, value))
        return row















