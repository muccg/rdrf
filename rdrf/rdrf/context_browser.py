from registry.patients.models import Patient
from rdrf.models import RDRFContext
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from operator import itemgetter
from django.core.paginator import Paginator
from django.core.urlresolvers import reverse
from rdrf.context_menu import PatientContextMenu
from . import context_defnitions as definitions


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
        return definitions.GRID_CONTEXT_LISTING

    def _get_columns(self):
        columns = []

        sorted_by_order = sorted(self.grid_config, key=itemgetter('order'), reverse=False)

        for definition in sorted_by_order:

            # I am now ignoring the default attribute ( was or definition["access"]["default"] or ..)
            if self.user.is_superuser or self.user.has_perm(definition["access"]["permission"]):
                columns.append(
                    {
                        "data": definition["data"],
                        "label": definition["label"],
                        "model": definition["model"]
                    }
                )

        return columns

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
