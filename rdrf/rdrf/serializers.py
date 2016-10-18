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
        exclude = ('next_of_kin_family_name',
                   'next_of_kin_given_names',
                   'next_of_kin_relationship',
                   'next_of_kin_address',
                   'next_of_kin_suburb',
                   'next_of_kin_state',
                   'next_of_kin_postcode',
                   'next_of_kin_home_phone',
                   'next_of_kin_mobile_phone',
                   'next_of_kin_work_phone',
                   'next_of_kin_email',
                   'next_of_kin_parent_place_of_birth',
                   'next_of_kin_country')
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


class CountryAdapter(object):
    '''Adapter from pycountry's Country object.

    Adds aliases and return None for unset attrs.'''

    ALIASES = {
        'country_code': 'alpha2',
        'pk': 'alpha2',
        'country_code3': 'alpha3',
    }

    def __init__(self, country):
        self._country = country

    def __getattr__(self, attr):
        if attr in self.ALIASES:
            attr = self.ALIASES[attr]
        return getattr(self._country, attr, None)


class CountrySerializer(serializers.Serializer):
    url = serializers.HyperlinkedIdentityField(view_name='country-detail')
    numeric = serializers.IntegerField()
    country_code = serializers.CharField(min_length=2, max_length=2)
    country_code3 = serializers.CharField(min_length=3, max_length=3)
    name = serializers.CharField()
    official_name = serializers.CharField()
