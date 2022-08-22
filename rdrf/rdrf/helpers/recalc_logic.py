from registry.patients.models import Patient
from rdrf.models.definition.models import Registry
from rdrf.models.definition.models import RegistryForm
from rdrf.models.definition.models import CommonDataElement
from rdrf.views.form_view import SectionInfo
from rdrf.services.tasks import recalculate_cde
from rdrf.helpers.utils import get_location
from rdrf.helpers.utils import is_calculated_cde_in_registry as in_registry
from rdrf.forms.fields import calculated_functions as cf
import logging

logger = logging.getLogger(__name__)


def get_calcs_reverse_map(registry: Registry) -> dict:
    """
    Discover relevant calculations and work out
    input-output relationships. Return a reverse
    map so we can quickly workout which calculated
    fields (outputs) need to be recalculated.
    """
    reverse_map = {}
    for name, thing in cf.__dict__.items():
        if callable(thing) and name.endswith("_inputs"):
            output_cde_code = name.replace("_inputs", "")
            try:
                output_cde_model = CommonDataElement.objects.get(code=output_cde_code)
            except CommonDataElement.DoesNotExist:
                continue
            except CommonDataElement.MultipleObjectsReturned:
                continue
            if output_cde_model.datatype != "calculated":
                continue
            if not in_registry(output_cde_model, registry):
                continue

            inputs_func = thing
            input_cde_codes = inputs_func()
            for input_cde_code in input_cde_codes:
                if input_cde_code in reverse_map:
                    reverse_map[input_cde_code].append(output_cde_code)
                else:
                    reverse_map[input_cde_code] = [output_cde_code]
    return reverse_map


class Recalculator:
    def __init__(self, registry: Registry, patient: Patient):
        self.registry = registry
        self.patient = patient
        self.inputs_map: dict = get_calcs_reverse_map(self.registry)

    def check_recalc(self, section_info: SectionInfo):
        section_form: RegistryForm = section_info.patient_wrapper.current_form_model
        recalc_needed = set([])
        for cde_model in section_info.cde_models:
            if cde_model.code in self.inputs_map:
                for output_cde_code in self.inputs_map[cde_model.code]:
                    if self._on_different_form(output_cde_code, section_form):
                        recalc_needed.add(output_cde_code)

        for output_cde_code in recalc_needed:
            self._recalc(output_cde_code, section_info)

    def _on_different_form(self, cde_code, section_form: RegistryForm):
        for section_model in section_form.section_models:
            for cde_model in section_model.cde_models:
                if cde_model.code == cde_code:
                    return False
        return True

    def _recalc(self, output_cde_code, section_info: SectionInfo):
        calc_cde: CommonDataElement = CommonDataElement.objects.get(code=output_cde_code)
        form_model, section_model = get_location(self.registry, calc_cde)
        context_id = section_info.patient_wrapper.rdrf_context_id
        section_index = 0

        # originally I thought this would be in a task
        # but will call synchronously as it doesn't seem
        # slow

        #func = recalculate_cde.delay
        func = recalculate_cde
        func(self.patient.id,
             self.registry.code,
             context_id,
             form_model.name,
             section_model.code,
             section_index,
             calc_cde.code)
