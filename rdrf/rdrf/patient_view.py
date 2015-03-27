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


class PatientEditView(View):

    def get(self, request, patient_id):
        patient = Patient.objects.get(id=patient_id)
        patient_form = PatientForm(instance=patient)
        
        personal_details_fields = ('Personal Details', [
            "working_groups",
            "family_name",
            "given_names",
            "maiden_name",
            "umrn",
            "date_of_birth",
            "place_of_birth",
            "country_of_birth",
            "ethnic_origin",
            "sex",
            "home_phone",
            "mobile_phone",
            "work_phone",
            "email"
        ])
        
        consent = ("Consent", [
            "consent",
            "consent_clinical_trials",
            "consent_sent_information",
        ])
        
        rdrf_registry = ("Registry", [
            "rdrf_registry",
            "clinician"
        ])
        
        sections = [consent, rdrf_registry, personal_details_fields]
        #sections.extend(self._get_registry_specific_fieldsets(request.user))

        registry_specific_fields = self._get_registry_specific_patient_fields(request.user)
        #patient_form = self._add_registry_specific_fields(PatientForm, registry_specific_fields)

        context = {
            "patient_form": patient_form,
            "patient": patient,
            "sections": sections
        }
    
        return render_to_response('rdrf_cdes/patient_edit.html', context, context_instance=RequestContext(request))

    def _add_registry_specific_fields(self, form_class, registry_specific_fields_dict):
        additional_fields = {}
        for reg_code in registry_specific_fields_dict:
            field_pairs = registry_specific_fields_dict[reg_code]
            for cde, field_object in field_pairs:
                additional_fields[cde.code] = field_object
                
        new_form_class = type(form_class.__name__, (form_class,), additional_fields)
        return new_form_class

    def _get_registry_specific_patient_fields(self, user):
        result_dict = {}
        for registry in user.registry.all():
            patient_cde_field_pairs = registry.patient_fields
            if patient_cde_field_pairs:
                result_dict[registry.code] = patient_cde_field_pairs

        return result_dict

    def _get_registry_specific_fieldsets(self, user):
        reg_spec_field_defs = self._get_registry_specific_patient_fields(user)
        fieldsets = []
        for reg_code in reg_spec_field_defs:
            cde_field_pairs = reversed(reg_spec_field_defs[reg_code])
            fieldset_title = "%s Specific Fields" % reg_code.upper()
            field_dict = [pair[0].code for pair in cde_field_pairs]  # pair up cde name and field object generated from that cde
            fieldsets.append((fieldset_title, field_dict))
        return fieldsets
