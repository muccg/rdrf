from django.shortcuts import render_to_response, RequestContext
from django.views.generic.base import View

from rdrf.models import RegistryForm
from rdrf.models import Registry

from registry.patients.models import Patient
from registry.patients.admin_forms import PatientForm

import logging

logger = logging.getLogger("registry_log")


class PatientView(View):

    def get(self, request, registry_code):
        context = {
            'registry_code': registry_code,
            'access': False
        }
        
        try:
            registry = Registry.objects.get(code=registry_code)
            context['splash_screen'] = registry.patient_splash_screen
        except Registry.DoesNotExist:
            context['error_msg'] = "Registry does not exist"
            logger.error("Registry %s does not exist" % registry_code)
            return render_to_response('rdrf_cdes/patient.html', context, context_instance=RequestContext(request))

        if request.user.is_authenticated():
            try:
                registry = Registry.objects.get(code=registry_code)
                if registry in request.user.registry.all():
                    context['access'] = True
                    context['splash_screen'] = registry.patient_splash_screen
            except Registry.DoesNotExist:
                context['error_msg'] = "Registry does not exist"
                logger.error("Registry %s does not exist" % registry_code)

            try:
                forms = RegistryForm.objects.filter(registry__code=registry_code).filter(is_questionnaire=True)
                context['forms'] = forms
            except RegistryForm.DoesNotExist:
                logger.error("No questionnaire for %s reistry" % registry_code)

            if request.user.is_patient:
                try:
                    patient = Patient.objects.get(user__id=request.user.id)
                    context['patient_record'] = patient
                    context['patient_form'] = PatientForm(instance=patient)
                except Patient.DoesNotExist:
                    logger.error("Paient record not found for user %s" % request.user.username)

        return render_to_response('rdrf_cdes/patient.html', context, context_instance=RequestContext(request))
