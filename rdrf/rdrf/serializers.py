from rest_framework import serializers
from rest_framework.reverse import reverse
from registry.patients.models import Patient, Registry
from registry.groups.models import CustomUser, WorkingGroup


class PatientSerializer(serializers.HyperlinkedModelSerializer):
    age = serializers.IntegerField(read_only=True)

    class Meta:
        model = Patient
        # TODO including url currently breaks things
        exclude = ('url',)
        extra_kwargs = {
            'rdrf_registry': {'required': False},
            'consent': {'required': True},
        }

    def create(self, validated_data):
        new_patient = super(PatientSerializer, self).create(validated_data)
        new_patient.rdrf_registry.clear()
        new_patient.rdrf_registry.add(self.initial_data.get('registry'))
        new_patient.save()
        return new_patient


class RegistryHyperlink(serializers.HyperlinkedRelatedField):

    def get_url(self, obj, view_name, request, format):
        url_kwargs = {
            'registry_code': obj.code,
        }
        return reverse(self.view_name, kwargs=url_kwargs, request=request, format=format)


class RegistryUrlHyperlinkIdentity(serializers.HyperlinkedRelatedField):
    view_name = 'registry-detail'

    def get_url(self, obj, view_name, request, format):
        url_kwargs = {
            'pk': obj.code,
        }
        return reverse(self.view_name, kwargs=url_kwargs, request=request, format=format)


class ClinitiansHyperlink(RegistryHyperlink):
    view_name = 'clinitian-list'


class PatientsHyperlink(RegistryHyperlink):
    view_name = 'patient-list'


class RegistrySerializer(serializers.HyperlinkedModelSerializer):
    # Make the Registry detail url be based on the registry code instead of the pk
    url = RegistryUrlHyperlinkIdentity(read_only=True, source='*')
    # Add some more url for better browsability
    patients_url = PatientsHyperlink(read_only=True, source='*')
    clinitians_url = ClinitiansHyperlink(read_only=True, source='*')

    class Meta:
        model = Registry
        lookup_field = 'code'
        fields = ('id', 'name', 'code', 'desc', 'version', 'patients_url', 'clinitians_url', 'url')


class WorkingGroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = WorkingGroup
        fields = ('id', 'name')


class CustomUserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = CustomUser
        # TODO add groups and user_permissions as well?
        exclude = ('groups', 'user_permissions', 'password')

