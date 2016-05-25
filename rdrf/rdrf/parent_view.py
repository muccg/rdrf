import logging

from django.views.generic.base import View
from django.shortcuts import render_to_response, RequestContext, redirect
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model

from registry.patients.models import ParentGuardian, Patient, PatientAddress, AddressType, ConsentValue
from models import Registry, RegistryForm, ConsentSection, ConsentQuestion
from registry.patients.admin_forms import ParentGuardianForm
from utils import consent_status_for_patient


from utils import consent_status_for_patient

from rdrf.contexts_api import RDRFContextManager, RDRFContextError

from registry.groups.models import WorkingGroup
from django.utils.translation import ugettext as _
import logging


logger = logging.getLogger("registry_log")


class LoginRequiredMixin(object):

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(LoginRequiredMixin, self).dispatch(
            request, *args, **kwargs)


class RDRFContextSwitchError(Exception):
    pass


class BaseParentView(LoginRequiredMixin, View):
    
    def __init__(self,):
        self.registry = None
        self.rdrf_context = None
        self.rdrf_context_manager = None

    _OTHER_CLINICIAN = "clinician-other"
    _UNALLOCATED_GROUP = "Unallocated"

    _ADDRESS_TYPE = "Postal"
    _GENDER_CODE = {
        "M": 1,
        "F": 2
    }

    def get_clinician_centre(self, request, registry):

        working_group = None

        try:
            clinician_id, working_group_id = request.POST['clinician'].split("_")
            clinician = get_user_model().objects.get(id=clinician_id)
            working_group = WorkingGroup.objects.get(id=working_group_id)
        except ValueError:
            clinician = None
            working_group, status = WorkingGroup.objects.get_or_create(
                name=self._UNALLOCATED_GROUP, registry=registry)





    def set_rdrf_context(self, patient_model, context_id):
        # Ensure we always have a context , otherwise bail
        self.rdrf_context = None
        try:
            if context_id is None:
                if self.registry.has_feature("contexts"):
                    raise RDRFContextError("Registry %s supports contexts but no context id  passed in url" %
                                           self.registry)
                else:
                    self.rdrf_context = self.rdrf_context_manager.get_or_create_default_context(patient_model)
            else:
                    self.rdrf_context = self.rdrf_context_manager.get_context(context_id, patient_model)

            if self.rdrf_context is None:
                raise RDRFContextSwitchError
            else:
                logger.debug("switched context for patient %s to context %s" % (patient_model,
                                                                                self.rdrf_context.id))

        except RDRFContextError, ex:
            logger.error("Error setting rdrf context id %s for patient %s in %s: %s" % (context_id,
                                                                                        patient_model,
                                                                                        self.registry,
                                                                                        ex))

            raise RDRFContextSwitchError

class ParentView(BaseParentView):

    def get(self, request, registry_code, context_id=None):
        context = {}
        if request.user.is_authenticated():
            parent = ParentGuardian.objects.get(user=request.user)
            registry = Registry.objects.get(code=registry_code)

            self.registry = registry
            self.rdrf_context_manager = RDRFContextManager(self.registry)

            forms_objects = RegistryForm.objects.filter(registry=registry).order_by('position')
            forms = []
            for form in forms_objects:
                forms.append({
                    "form": form,
                    "readonly": request.user.has_perm("rdrf.form_%s_is_readonly" % form.id)
                })

            patients_objects = parent.patient.all()
            patients = []
            for patient in patients_objects:
                self.set_rdrf_context(patient, context_id)
                patients.append({
                    "patient": patient,
                    "consent": consent_status_for_patient(registry_code, patient)
                    "context_id": self.rdrf_context.pk
                })

            context['parent'] = parent
            context['patients'] = patients
            context['registry_code'] = registry_code
            context['registry_forms'] = forms
            
            self.set_rdrf_context(parent, context_id)
            context['context_id'] = self.rdrf_context.pk

        return render_to_response(
            'rdrf_cdes/parent.html',
            context,
            context_instance=RequestContext(request))

    def post(self, request, registry_code, context_id=None):
        parent = ParentGuardian.objects.get(user=request.user)
        registry = Registry.objects.get(code=registry_code)

        patient = Patient.objects.create(
            consent=True,
            family_name=request.POST["surname"],
            given_names=request.POST["first_name"],
            date_of_birth=request.POST["date_of_birth"],
            sex=self._GENDER_CODE[request.POST["gender"]],
        )
        patient.rdrf_registry.add(registry)

        clinician, centre = self.get_clinician_centre(request, registry)
        patient.clinician = clinician
        patient.save()

        use_parent_address = "use_parent_address" in request.POST

        PatientAddress.objects.create(
            patient=patient,
            address_type=AddressType.objects.get(description__icontains=self._ADDRESS_TYPE),
            address=parent.address if use_parent_address else request.POST["address"],
            suburb=parent.suburb if use_parent_address else request.POST["suburb"],
            state=parent.state if use_parent_address else request.POST["state"],
            postcode=parent.postcode if use_parent_address else request.POST["postcode"],
            country=parent.country if use_parent_address else request.POST["country"]
        )

        parent.patient.add(patient)
        parent.save()
        messages.add_message(request, messages.SUCCESS, 'Patient added successfully')
        return redirect(reverse("parent_page", args={registry_code: registry_code}))


class ParentEditView(BaseParentView):

    def get(self, request, registry_code, parent_id, context_id=None):
        context = {}
        parent = ParentGuardian.objects.get(user=request.user)

        context['parent'] = parent
        context['registry_code'] = registry_code
        context['parent_form'] = ParentGuardianForm(instance=parent)

        return render_to_response(
            "rdrf_cdes/parent_edit.html",
            context,
            context_instance=RequestContext(request))

    def post(self, request, registry_code, parent_id, context_id=None):
        context = {}
        parent = ParentGuardian.objects.get(id=parent_id)

        parent_form = ParentGuardianForm(request.POST, instance=parent)
        if parent_form.is_valid():
            parent_form.save()
            messages.add_message(request, messages.SUCCESS, "Details saved")
        else:
            messages.add_message(request, messages.ERROR, "Please correct the errors bellow")

        if "self_patient_flag" in request.POST:
            registry = Registry.objects.get(code=registry_code)
            patient = Patient.objects.create(
                consent=True,
                family_name=request.POST["last_name"],
                given_names=request.POST["first_name"],
                date_of_birth=request.POST["date_of_birth"],
                sex=self._GENDER_CODE[request.POST["gender"]],
            )

            PatientAddress.objects.create(
                patient=patient,
                address_type=AddressType.objects.get(description__icontains=self._ADDRESS_TYPE),
                address=parent.address,
                suburb=parent.suburb,
                state=parent.state,
                postcode=parent.postcode,
                country=parent.country
            )

            patient.rdrf_registry.add(registry)
            clinician, centre = self.get_clinician_centre(request, registry)
            patient.clinician = clinician
            patient.save()

            parent.patient.add(patient)
            parent.self_patient = patient
            parent.save()

        context['parent'] = parent
        context['registry_code'] = registry_code
        context['parent_form'] = parent_form

        return render_to_response(
            "rdrf_cdes/parent_edit.html",
            context,
            context_instance=RequestContext(request))
