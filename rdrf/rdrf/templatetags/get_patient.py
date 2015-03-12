from django import template
from registry.patients.models import Patient
from rdrf.hooking import run_hooks


register = template.Library()


@register.assignment_tag
def get_patient(patient_id):
    try:
        if not patient_id:
            return None
        patient = Patient.objects.get(pk=patient_id)
        return patient
    except Patient.DoesNotExist:
        return None
