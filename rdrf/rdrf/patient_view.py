from django.shortcuts import render_to_response, RequestContext, redirect
from django.views.generic.base import View
from django.core.urlresolvers import reverse
from django.forms.formsets import formset_factory
from django.utils.datastructures import SortedDict

from rdrf.models import RegistryForm
from rdrf.models import Registry

from registry.patients.models import Patient, PatientAddress, PatientDoctor
from registry.patients.admin_forms import PatientForm, PatientAddressForm, PatientDoctorForm

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
                    context['patient_id'] = patient.id
                except Patient.DoesNotExist:
                    logger.error("Paient record not found for user %s" % request.user.username)

        return render_to_response('rdrf_cdes/patient.html', context, context_instance=RequestContext(request))


class PatientEditView(View):

    def get(self, request, patient_id):
        if not request.user.is_authenticated():
            patient_edit_url = reverse('patient_edit', args=[patient_id,])
            login_url = reverse('login')
            return redirect("%s?next=%s" % (login_url, patient_edit_url))
    
        patient, form_sections = self._get_forms(patient_id)
        
        context = {
            "forms": form_sections,
            "patient": patient
        }
    
        return render_to_response('rdrf_cdes/patient_edit.html', context, context_instance=RequestContext(request))

    def post(self, request, patient_id):
        patient_form = PatientForm(request.POST)

        patient_form.save()
        
#        PatientDoctorFormSet = formset_factory(PatientDoctorForm)
#        patient_doctor_form_set = PatientDoctorFormSet(request.POST, prefix="patient_doctor")

#        for form in patient_doctor_form_set:
#            form.save()
        
#        PatientAddressFormSet = formset_factory(PatientAddressForm)
#        patient_address_form_set = PatientAddressFormSet(request.POST, prefix="patient_address")

#        for form in patient_address_form_set:
#            form.save()
        
        patient, form_sections = self._get_forms(patient_id)
        
        context = {
            "forms": form_sections,
            "patient": patient
        }
    
        return render_to_response('rdrf_cdes/patient_edit.html', context_instance=RequestContext(request))

    def _get_forms(self, patient_id):
        patient = Patient.objects.get(id=patient_id)
        patient_form = PatientForm(instance=patient)
        
        patient_address = PatientAddress.objects.filter(patient = patient).values()
        patient_doctor = PatientDoctor.objects.filter(patient = patient).values()
        
        patient_address_formset = formset_factory(PatientAddressForm, extra=0, can_delete=True)
        patient_address_form = patient_address_formset(initial=patient_address, prefix="patient_address")
        
        patient_doctor_formset = formset_factory(PatientDoctorForm, extra=0, can_delete=True)
        patient_doctor_form = patient_doctor_formset(initial=patient_doctor, prefix="patient_doctor")
        
        personal_details_fields = ('Personal Details', [
            #"working_groups",
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
        
        next_of_kin = ("Next of Kin", [
            "next_of_kin_family_name",
             "next_of_kin_given_names",
             "next_of_kin_relationship",
             "next_of_kin_address",
             "next_of_kin_suburb",
             "next_of_kin_state",
             "next_of_kin_postcode",
             "next_of_kin_home_phone",
             "next_of_kin_mobile_phone",
             "next_of_kin_work_phone",
             "next_of_kin_email",
             "next_of_kin_parent_place_of_birth"
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
        
        patient_address_section = ("Patient Address", None)
        
        patient_doctor_section = ("Patient Doctor", None)
        
        form_sections = [
            (
                patient_form,
                ( consent, personal_details_fields, next_of_kin )
#            ),(
#                patient_address_form, 
#                ( patient_address_section, )
#            ),(
#                patient_doctor_form,
#                ( patient_doctor_section, )
            )
        ]
        
        return patient, form_sections
        

    def _add_registry_specific_fields(self, form_class, registry_specific_fields_dict):
        additional_fields = SortedDict()
        for reg_code in registry_specific_fields_dict:
            field_pairs = registry_specific_fields_dict[reg_code]
            for cde, field_object in field_pairs:
                logger.debug("xxxx %s" % cde.code)
                additional_fields[cde.code] = field_object

        new_form_class = type(form_class.__name__, (form_class,), additional_fields)
        return new_form_class

    def _get_registry_specific_patient_fields(self, user):
        result_dict = SortedDict()
        for registry in user.registry.all():
            patient_cde_field_pairs = registry.patient_fields
            if patient_cde_field_pairs:
                result_dict[registry.code] = patient_cde_field_pairs

        return result_dict

    def _get_registry_specific_fieldsets(self, user):
        reg_spec_field_defs = self._get_registry_specific_patient_fields(user)
        fieldsets = []
        for reg_code in reg_spec_field_defs:
            cde_field_pairs = reg_spec_field_defs[reg_code]
            fieldset_title = "%s Specific Fields" % reg_code.upper()
            field_dict = [pair[0].code for pair in cde_field_pairs]  # pair up cde name and field object generated from that cde
            fieldsets.append((fieldset_title, field_dict))
        return fieldsets
