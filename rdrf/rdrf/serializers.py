from rest_framework import serializers
from rest_framework.reverse import reverse
from registry.patients.models import Patient, Registry, Doctor, NextOfKinRelationship
from registry.groups.models import CustomUser, WorkingGroup


class DoctorHyperlinkId(serializers.HyperlinkedRelatedField):
    view_name = "doctor-detail"


class DoctorSerializer(serializers.HyperlinkedModelSerializer):
    url = DoctorHyperlinkId(read_only=True, source='*')

    class Meta:
        model = Doctor


class NextOfKinRelationshipHyperlinkId(serializers.HyperlinkedRelatedField):
    view_name = "nextofkinrelationship-detail"


class NextOfKinRelationshipSerializer(serializers.HyperlinkedModelSerializer):
    url = NextOfKinRelationshipHyperlinkId(read_only=True, source='*')

    class Meta:
        model = NextOfKinRelationship


# Needed so we can display the URL to the patient that also has the registry code in it
class PatientHyperlinkId(serializers.HyperlinkedRelatedField):
    view_name = 'patient-detail'

    def get_url(self, obj, view_name, request, format):
        url_kwargs = {
            'pk': obj.pk,
            'registry_code': request.resolver_match.kwargs['registry_code'],
        }
        return reverse(view_name, kwargs=url_kwargs, request=request, format=format)


class CustomUserSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = CustomUser
        # TODO add groups and user_permissions as well?
        exclude = ('groups', 'user_permissions', 'password')
        extra_kwargs = {
            'registry': {'lookup_field': 'code'},
        }


class PatientSerializer(serializers.HyperlinkedModelSerializer):
    age = serializers.IntegerField(read_only=True)
    url = PatientHyperlinkId(read_only=True, source='*')
    user = CustomUserSerializer()

    class Meta:
        model = Patient
        extra_kwargs = {
            'rdrf_registry': {'required': False, 'lookup_field': 'code'},
            'consent': {'required': True},
        }

    def create(self, validated_data):
        new_patient = super(PatientSerializer, self).create(validated_data)
        new_patient.rdrf_registry.clear()
        new_patient.rdrf_registry.add(self.initial_data.get('registry'))
        new_patient.save()
        return new_patient

    def update(self, instance, validated_data):
        user = instance.user

        user.working_groups.clear()
        for wg in validated_data.get('working_groups'):
            user.working_groups.add(wg)
        user.save()

        instance.clinician = validated_data.get('clinician')
        instance.working_groups = validated_data.get('working_groups')
        instance.save()

        return instance


class RegistryHyperlink(serializers.HyperlinkedRelatedField):

    def get_url(self, obj, view_name, request, format):
        url_kwargs = {
            'registry_code': obj.code,
        }
        return reverse(self.view_name, kwargs=url_kwargs, request=request, format=format)


class CliniciansHyperlink(RegistryHyperlink):
    view_name = 'clinician-list'


class PatientsHyperlink(RegistryHyperlink):
    view_name = 'patient-list'


class RegistrySerializer(serializers.HyperlinkedModelSerializer):
    # Add some more urls for better browsability
    patients_url = PatientsHyperlink(read_only=True, source='*')
    clinicians_url = CliniciansHyperlink(read_only=True, source='*')

    class Meta:
        model = Registry
        fields = ('pk', 'name', 'code', 'desc', 'version', 'url', 'patients_url', 'clinicians_url')
        extra_kwargs = {
            'url': {'lookup_field': 'code'},
        }


class WorkingGroupSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = WorkingGroup
        extra_kwargs = {
            'registry': {'lookup_field': 'code'},
        }
