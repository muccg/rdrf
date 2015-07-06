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

        if "use_parent_address" in request.POST:
            PatientAddress.objects.create(
                patient=patient,
                address_type=AddressType.objects.get(description__icontains=self._ADDRESS_TYPE),
                address=parent.address,
                suburb=parent.suburb,
                state=parent.state,
                postcode=parent.postcode,
                country=parent.country
            )
        else:
            PatientAddress.objects.create(
                patient=patient,
                address_type=AddressType.objects.get(description__icontains=self._ADDRESS_TYPE),
                address=request.POST["address"],
                suburb=request.POST["suburb"],
                state=request.POST["state"],
                postcode=request.POST["postcode"],
                country=request.POST["country"]
            )

        parent.patient.add(patient)
        parent.save()
        messages.add_message(request, messages.SUCCESS, 'Patient added successfully')
        return redirect(reverse("parent_page", args={registry_code: registry_code}))


class ParentEditView(View):

    def get(self, request, registry_code, parent_id):
        context = {}
        if request.user.is_authenticated():
            parent = ParentGuardian.objects.get(user=request.user)

            context['parent'] = parent
            context['registry_code'] = registry_code
            context['parent_form'] = ParentGuardianForm(instance=parent)

        return render_to_response("rdrf_cdes/parent_edit.html", context, context_instance=RequestContext(request))
