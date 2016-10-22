from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers
from rest_framework.reverse import reverse
from . import models as m
from .utils import camel_to_snake, camel_to_dash_separated, mongo_key
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


class ClinicalDataHyperlinkId(PatientHyperlinkId):
    view_name = 'clinical-data-detail'


class PatientSerializer(serializers.HyperlinkedModelSerializer):
    age = serializers.IntegerField(read_only=True)
    url = PatientHyperlinkId(read_only=True, source='*')
    user = CustomUserSerializer()
    clinical_data = ClinicalDataHyperlinkId(read_only=True, source='*')

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


# Used for url to a PermittedValue
class PermittedValueHyperlinkId(serializers.HyperlinkedRelatedField):
    view_name = 'permitted-value-detail'

    def get_url(self, obj, view_name, request, format):
        if obj is None:
            return None
        url_kwargs = {
            'pvg_code': obj.pv_group.code,
            'code': obj.code,
        }
        return reverse(view_name, kwargs=url_kwargs, request=request, format=format)


class PermittedValueGroupSerializer(serializers.HyperlinkedModelSerializer):
    permitted_values = PermittedValueHyperlinkId(many=True, read_only=True)

    class Meta:
        model = m.CDEPermittedValueGroup
        fields = ('url', 'code', 'permitted_values')
        extra_kwargs = {
            'url': {'lookup_field': 'code'},
        }


class PermittedValueSerializer(serializers.HyperlinkedModelSerializer):
    url = PermittedValueHyperlinkId(read_only=True, source='*')

    class Meta:
        model = m.CDEPermittedValue
        fields = ('url', 'code', 'value', 'desc', 'pv_group')
        extra_kwargs = {
            'url': {'lookup_field': 'code'},
            'pv_group': {'lookup_field': 'code'},
        }


# Used for url links from sections to PermittedValues
class PermittedValueFieldHyperlink(PermittedValueHyperlinkId):
    def get_url(self, obj, *args, **kwargs):
        attr = getattr(obj, self.attr_name)
        return super(PermittedValueFieldHyperlink, self).get_url(attr, *args, **kwargs)


# Used for url links from sections to multiples of PermittedValues
# TODO this currently displays the first value instead of nested links
class PermittedValueMultipleFieldHyperlink(PermittedValueHyperlinkId):
    def get_url(self, obj, *args, **kwargs):
        attr = getattr(obj, self.attr_name)
        if not attr:
            return None
        try:
            first = m.CDEPermittedValue.objects.get(code=attr[0])
            return super(PermittedValueMultipleFieldHyperlink, self).get_url(first, *args, **kwargs)
        except m.CDEPermittedValue.DoesNotExist:
            return None


def cde_code_to_field_name(code):
    # TODO hardcoded
    if code.startswith('MTM'):
        code = code[3:]
    return camel_to_snake(code)


class SectionAdapter(object):
    '''Makes the Mongo doc look like a python object representing data in a Section.

    For field names drop 'MTM' prefix and convert camelCase to snake_case.
    If a value is a permitted value's name it returns the permitted value.
    '''
    def __init__(self, doc):
        self._doc = doc
        self.ALIASES = {}
        try:
            section = m.Section.objects.get(code=self.SECTION_CODE)
            self.ALIASES = {
                cde_code_to_field_name(cde.code): mongo_key(self.FORM_CODE, self.SECTION_CODE, cde.code)
                for cde in section.cde_models}
        except m.Section.DoesNotExist:
            pass

    def __getattr__(self, attr):
        if attr in self.ALIASES:
            attr = self.ALIASES[attr]
        val = self._doc.get(attr)
        pv = self._get_pv(attr, val)
        if pv is not None:
            return pv
        return val

    def _get_pv(self, name, val):
        try:
            cde_name = name.split(settings.FORM_SECTION_DELIMITER)[-1]
            cde = m.CommonDataElement.objects.get(code=cde_name)
            if cde.pv_group is not None:
                pv = cde.pv_group.permitted_value_set.get(code=val)
                return pv
        except ObjectDoesNotExist:
            pass


def create_adapter(form_code, section_code):
    '''Create a SectionAdapter subclass for the given section.'''
    # TODO hardcoded
    name = section_code[3:] if section_code.startswith('MTM') else section_code
    return type(name + 'Adapter', (SectionAdapter, ),
                {'FORM_CODE': form_code, 'SECTION_CODE': section_code})


def create_link_to_pv(field_name):
    '''Creates a field that is a URL link to the given PermittedValue'''
    return type('PermittedValueFieldHyperlink' + field_name,
                (PermittedValueFieldHyperlink,),
                {'attr_name': field_name})


def create_link_to_multiple_pv(field_name):
    '''Creates a field that is a URL link to the a list of PermittedValues'''
    return type('PermittedValueMultipleFieldHyperlink' + field_name,
                (PermittedValueMultipleFieldHyperlink,),
                {'attr_name': field_name})


def cde_field(cde):
    '''Creates a SerializerField for a given cde'''
    if cde.pv_group is not None:
        # TODO handle multiple choices
        field_name = cde_code_to_field_name(cde.code)
        if cde.allow_multiple:
            cls = create_link_to_multiple_pv(field_name)
        else:
            cls = create_link_to_pv(cde_code_to_field_name(cde.code))
        return cls(read_only=True, source='*')
    elif cde.datatype == 'date':
        return serializers.DateTimeField()
    elif cde.datatype == 'file':
        # TODO deal with files, currently they're all None
        return serializers.FileField()
    return serializers.CharField()


def create_section_serializer(form_code, section_code):
    '''Dynamically creates a Serializer for a Section with fields representing each CDE'''
    # TODO hardcoded
    name = section_code[3:] if section_code.startswith('MTM') else section_code

    fields = {}
    try:
        section = m.Section.objects.get(code=section_code)
        fields = dict([
            (cde_code_to_field_name(cde.code), cde_field(cde))
            for cde in section.cde_models])

    except m.Section.DoesNotExist:
        pass

    return type(name + 'Serializer', (serializers.Serializer,), fields)


def create_patient_hyperlink_id(name, view_name):
    if not name.endswith('HyperlinkId'):
        name += 'HyperlinkId'
    return type(name, (PatientHyperlinkId,), {'view_name': view_name})


def create_link_to_section_field(form_name, section_code):
    # TODO hardcoded
    # and similar logic as in api_urls.create_url
    # Make class that is initialised once with section and can create url
    # detail view and this field
    name = section_code[3:] if section_code.startswith('MTM') else section_code
    field_name = camel_to_snake(name)
    view_name = 'clinical:' + camel_to_dash_separated(name + 'Detail')
    link_field = create_patient_hyperlink_id(name, view_name)(read_only=True, source='*')

    return (field_name, link_field)


def create_clinical_data_serialzer():
    fields = dict([create_link_to_section_field(form.name, section.code)
                   for registry in Registry.objects.all()
                   for form in registry.forms
                   for section in form.section_models])

    return type('ClinicalDataSerializer', (serializers.Serializer,), fields)


ClinicalDataSerializer = create_clinical_data_serialzer()
