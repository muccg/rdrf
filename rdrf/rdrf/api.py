from tastypie.resources import ModelResource
from registry.patients.models import Patient


class PatientResource(ModelResource):

    class Meta:
        queryset = Patient.objects.all()
