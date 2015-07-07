from django.views.generic.base import View
from django.shortcuts import render_to_response, RequestContext, redirect
from django.core.urlresolvers import reverse
from django.contrib import messages

from registry.patients.models import ParentGuardian, Patient, PatientAddress, AddressType
from models import Registry, RegistryForm
from registry.patients.admin_forms import ParentGuardianForm


class ParentView(View):

    _ADDRESS_TYPE = "Postal"

    def get(self, request, registry_code):
        context = {}
        if request.user.is_authenticated():
            parent = ParentGuardian.objects.get(user=request.user)
            registry = Registry.objects.get(code=registry_code)
            forms = RegistryForm.objects.filter(registry=registry)

            context['parent'] = parent
            context['patients'] = parent.patient.all()
            context['registry_code'] = registry_code
            context['registry_forms'] = forms

        return render_to_response('rdrf_cdes/parent.html', context, context_instance=RequestContext(request))

    def post(self, request, registry_code):
        parent = ParentGuardian.objects.get(user=request.user)
        registry = Registry.objects.get(code=registry_code)

        patient = Patient.objects.create(
            consent=True,
            family_name=request.POST["surname"],
            given_names=request.POST["first_name"],
            date_of_birth=request.POST["date_of_birth"],
            sex=request.POST["gender"],
        )
        patient.rdrf_registry.add(registry)
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


class ParentEditView(View):
    _ADDRESS_TYPE = "Postal"

    def get(self, request, registry_code, parent_id):
        context = {}
        parent = ParentGuardian.objects.get(user=request.user)

        context['parent'] = parent
        context['registry_code'] = registry_code
        context['parent_form'] = ParentGuardianForm(instance=parent)

        return render_to_response("rdrf_cdes/parent_edit.html", context, context_instance=RequestContext(request))

    def post(self, request, registry_code, parent_id):
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
                sex=request.POST["gender"],
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
            patient.save()

            parent.patient.add(patient)
            parent.self_patient = patient
            parent.save()

        context['parent'] = parent
        context['registry_code'] = registry_code
        context['parent_form'] = parent_form

        return render_to_response("rdrf_cdes/parent_edit.html", context, context_instance=RequestContext(request))
