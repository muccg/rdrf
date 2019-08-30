from rest_framework import serializers
from rest_framework.reverse import reverse
from registry.patients.models import Patient, Registry, Doctor, NextOfKinRelationship
from registry.groups.models import CustomUser, WorkingGroup
from rdrf.models.proms.models import SurveyAssignment


class DoctorHyperlinkId(serializers.HyperlinkedRelatedField):
    view_name = "doctor-detail"


class DoctorSerializer(serializers.HyperlinkedModelSerializer):
    url = DoctorHyperlinkId(read_only=True, source='*')

    class Meta:
        model = Doctor
        fields = '__all__'


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
        fields = '__all__'

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
        fields = (
            'pk',
            'name',
            'code',
            'desc',
            'version',
            'url',
            'patients_url',
            'clinicians_url')
        extra_kwargs = {
            'url': {'lookup_field': 'code'},
        }


class WorkingGroupSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = WorkingGroup
        extra_kwargs = {
            'registry': {'lookup_field': 'code'},
        }
        fields = '__all__'


class RegistryCodeField(serializers.CharField):
    def get_attribute(self, survey_assignment):
        return survey_assignment.registry.code


class SurveyAssignmentSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    registry_code = RegistryCodeField(max_length=10)
    survey_name = serializers.CharField(max_length=80)
    patient_token = serializers.CharField(max_length=80)
    state = serializers.CharField(max_length=20)
    response = serializers.CharField()

    def create(self, validated_data):
        registry_code = validated_data["registry_code"]
        registry_model = Registry.objects.get(code=registry_code)
        survey_name = validated_data["survey_name"]
        state = "requested"
        patient_token = validated_data["patient_token"]
        sa = SurveyAssignment(registry=registry_model,
                              survey_name=survey_name,
                              patient_token=patient_token,
                              response="",
                              state=state)

        sa.save()
        return sa

    def validate(self, data):
        return data
