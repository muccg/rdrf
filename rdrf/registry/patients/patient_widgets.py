from django.forms import widgets
import logging
from django.urls import reverse

logger = logging.getLogger(__name__)


class PatientRelativeLinkWidget(widgets.Widget):

    """
    This provides a link to the patient created from the relative
    Before the patient is created , it provides a checkbox
    ( Similar to the delete checkbox provided against other inlines )
    - checking it signals  that a patient should be created from the patient relative data supplied.
    There is also javascript to hide the green plus symbol to avoid the popup
    """

    def render(self, name, value, attrs=None, renderer=None):
        if value is None:
            return """<input type="checkbox" id="%s" name="%s">""" % (attrs['id'], name)
        elif value == 'on':
            return """<input type="checkbox" value="on" id="%s" name="%s">""" % (
                attrs['id'], name)
        else:
            # value is patient id
            registry_model = self._get_family_linkage_registry(value)

            hidden_field = """<input type=hidden id="%s" name="%s" value="%s">""" % (
                attrs['id'], name, value)  # ensure that the link to patient not lost on submission!

            if registry_model:
                patient_url = reverse("patient_edit", args=[registry_model.code, value])
            else:
                raise Exception("Patient not in a registry with family linkage")

            html = """<a  href='%s'>Patient in registry</a>%s""" % (patient_url, hidden_field)
            return html

    def _get_default_context(self, reg_code, patient_id):
        from rdrf.models.definition.models import Registry
        from registry.patients.models import Patient
        patient_model = Patient.objects.get(pk=int(patient_id))
        registry_model = Registry.objects.get(code=reg_code)
        return patient_model.default_context(registry_model)

    def _get_family_linkage_registry(self, patient_id):
        from registry.patients.models import Patient
        patient_model = Patient.objects.get(pk=patient_id)
        family_linkage_regs = [
            r for r in patient_model.rdrf_registry.all() if r.has_feature("family_linkage")]
        if len(family_linkage_regs) == 1:
            return family_linkage_regs[0]
