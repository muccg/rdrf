import logging
import pycountry

from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework import viewsets
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView

from registry.genetic.models import Gene, Laboratory
from registry.patients.models import Patient, Registry, Doctor, NextOfKinRelationship
from registry.groups.models import CustomUser, WorkingGroup
from .models import CommonDataElement, CDEPermittedValueGroup, CDEPermittedValue, RegistryForm, Section
from .dynamic_data import DynamicDataWrapper
from .serializers import (create_adapter,
                          create_section_serializer,
                          ClinicalDataSerializer,
                          CommonDataElementSerializer,
                          CountryAdapter,
                          CountrySerializer,
                          CustomUserSerializer,
                          DoctorSerializer,
                          PatientSerializer,
                          PermittedValueGroupSerializer,
                          PermittedValueSerializer,
                          RegistrySerializer,
                          RegistryFormSerializer,
                          SectionSerializer,
                          WorkingGroupSerializer,
                          NextOfKinRelationshipSerializer)


logger = logging.getLogger(__name__)


class BadRequestError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST


class RegistryDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Registry.objects.all()
    serializer_class = RegistrySerializer
    lookup_field = 'code'


class RegistryList(generics.ListCreateAPIView):
    queryset = Registry.objects.all()
    serializer_class = RegistrySerializer


class DoctorViewSet(viewsets.ModelViewSet):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer


class SectionViewSet(viewsets.ModelViewSet):
    queryset = Section.objects.all()
    serializer_class = SectionSerializer
    lookup_field = 'code'


class RegistryFormList(generics.ListCreateAPIView):
    serializer_class = RegistryFormSerializer

    def _get_registry_by_code(self, registry_code):
        try:
            return Registry.objects.get(code=registry_code)
        except Registry.DoesNotExist:
            raise BadRequestError("Invalid registry code '%s'" % registry_code)

    def get_queryset(self):
        registry_code = self.kwargs.get('registry_code')
        registry = self._get_registry_by_code(registry_code)
        return registry.registry_forms

    def post(self, request, *args, **kwargs):
        registry_code = kwargs.get('registry_code')
        if len(request.data) > 0:
            # For empty posts don't set the registry as it fails because request.data
            # is immutable for empty posts. Post request will fail on validation anyways.
            request.data['registry'] = self._get_registry_by_code(registry_code)
        if not (request.user.is_superuser or request.data['registry'] in request.user.registry.all()):
            self.permission_denied(request, message='Not allowed to create Form in this Registry')
        return super(RegistryFormList, self).post(request, *args, **kwargs)


class RegistryFormDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = RegistryForm.objects.all()
    serializer_class = RegistryFormSerializer
    permission_classes = (IsAuthenticated,)
    lookup_field = 'name'


class NextOfKinRelationshipViewSet(viewsets.ModelViewSet):
    queryset = NextOfKinRelationship.objects.all()
    serializer_class = NextOfKinRelationshipSerializer


class PatientDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes = (IsAuthenticated,)

    def _get_registry_by_code(self, registry_code):
        try:
            return Registry.objects.get(code=registry_code)
        except Registry.DoesNotExist:
            raise BadRequestError("Invalid registry code '%s'" % registry_code)

    def check_object_permissions(self, request, patient):
        """We're always filtering the patients by the registry code form the url and the user's working groups"""
        super(PatientDetail, self).check_object_permissions(request, patient)
        registry_code = self.kwargs.get('registry_code')
        registry = self._get_registry_by_code(registry_code)
        if registry not in patient.rdrf_registry.all():
            self.permission_denied(request, message='Patient not available in requested registry')
        if request.user.is_superuser:
            return
        if registry not in request.user.registry.all():
            self.permission_denied(request, message='Not allowed to get Patients from this Registry')

        if not patient.working_groups.filter(pk__in=request.user.working_groups.all()).exists():
            self.permission_denied(request, message='Patient not in your working group')


class PatientList(generics.ListCreateAPIView):
    serializer_class = PatientSerializer

    def _get_registry_by_code(self, registry_code):
        try:
            return Registry.objects.get(code=registry_code)
        except Registry.DoesNotExist:
            raise BadRequestError("Invalid registry code '%s'" % registry_code)

    def get_queryset(self):
        """We're always filtering the patients by the registry code form the url and the user's working groups"""
        registry_code = self.kwargs.get('registry_code')
        registry = self._get_registry_by_code(registry_code)
        if self.request.user.is_superuser:
            return Patient.objects.get_by_registry(registry.pk)
        return Patient.objects.get_by_registry_and_working_group(registry, self.request.user)

    def post(self, request, *args, **kwargs):
        registry_code = kwargs.get('registry_code')
        if len(request.data) > 0:
            # For empty posts don't set the registry as it fails because request.data
            # is immutable for empty posts. Post request will fail on validation anyways.

            request.data['registry'] = self._get_registry_by_code(registry_code)
        if not (request.user.is_superuser or request.data['registry'] in request.user.registry.all()):
            self.permission_denied(request, message='Not allowed to create Patient in this Registry')
        return super(PatientList, self).post(request, *args, **kwargs)


class RegistryViewSet(viewsets.ModelViewSet):
    queryset = Registry.objects.all()
    serializer_class = RegistrySerializer
    lookup_field = 'code'

    # Overriding get_object to make registry lookup be based on the registry code
    # instead of the pk
    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        obj = generics.get_object_or_404(queryset, code=self.kwargs['pk'])
        self.check_object_permissions(self.request, obj)

        return obj


# TODO add resources for PermittedValueGroups, and CDEs
# review permissions etc.

class PermittedValueGroupViewSet(viewsets.ModelViewSet):
    queryset = CDEPermittedValueGroup.objects.all()
    serializer_class = PermittedValueGroupSerializer
    lookup_field = 'code'


class CommonDataElementViewSet(viewsets.ModelViewSet):
    queryset = CommonDataElement.objects.all()
    serializer_class = CommonDataElementSerializer
    lookup_field = 'code'


class PermittedValueDetail(APIView):
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def get(self, request, pvg_code, code, format=None):
        pv = self.get_pv(pvg_code, code)
        serializer = PermittedValueSerializer(pv, context={'request': request})
        return Response(serializer.data)

    def get_pv(self, pvg_code, code):
        return get_object_or_404(CDEPermittedValue, pv_group__code=pvg_code, code=code)


class PermittedValueList(generics.ListCreateAPIView):
    serializer_class = PermittedValueSerializer

    def _get_pvg_by_code(self, pvg_code):
        try:
            return CDEPermittedValueGroup.objects.get(code=pvg_code)
        except CDEPermittedValueGroup.DoesNotExist:
            raise BadRequestError("Invalid permittable value group code '%s'" % pvg_code)

    def get_queryset(self):
        pvg_code = self.kwargs.get('pvg_code')
        pvg = self._get_pvg_by_code(pvg_code)
        return CDEPermittedValue.objects.filter(pv_group=pvg)


class WorkingGroupViewSet(viewsets.ModelViewSet):
    queryset = WorkingGroup.objects.all()
    serializer_class = WorkingGroupSerializer


class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer


class CountryViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def list(self, request, format=None):
        countries = sorted([CountryAdapter(c) for c in pycountry.countries], key=lambda c: c.name)
        serializer = CountrySerializer(countries, many=True, context={'request': request})
        return Response(serializer.data)

    def retrieve(self, request, pk, format=None):
        country = self.get_object(pk)
        serializer = CountrySerializer(CountryAdapter(country), context={'request': request})
        return Response(serializer.data)

    def get_object(self, code):
        try:
            return pycountry.countries.get(alpha2=code)
        except KeyError:
            raise Http404


class ListStates(APIView):
    permission_classes = (IsAuthenticatedOrReadOnly,)
    WANTED_FIELDS = ('name', 'code', 'type', 'country_code')

    def get(self, request, country_code, format=None):
        try:
            states = sorted(pycountry.subdivisions.get(
                country_code=country_code.upper()), key=lambda x: x.name)
        except KeyError:
            # For now returning empty list because the old api view was doing the same
            # raise BadRequestError("Invalid country code '%s'" % country_code)
            states = []

        def to_dict(x):
            return {k: getattr(x, k) for k in self.WANTED_FIELDS}

        return Response([to_dict(s) for s in states])


class ListClinicians(APIView):
    queryset = CustomUser.objects.none()
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def get(self, request, registry_code, format=None):
        users = CustomUser.objects.filter(registry__code=registry_code, is_superuser=False)
        clinicians = [u for u in users if u.is_clinician]

        def to_dict(c, wg):
            return {
                'id': "%s_%s" % (reverse(
                    'v1:customuser-detail',
                    args=[
                        c.id,
                    ]),
                    reverse(
                    'v1:workinggroup-detail',
                    args=[
                        wg.id,
                    ])),
                'full_name': "%s %s (%s)" % (c.first_name,
                                             c.last_name,
                                             wg.name),
            }

        return Response([to_dict(c, wg) for c in clinicians for wg in c.working_groups.all()])


class LookupGenes(APIView):
    queryset = Gene.objects.none()

    def get(self, request, format=None):
        query = None
        try:
            query = request.GET['term']
        except KeyError:
            pass
            # raise BadRequestError("Required query parameter 'term' not received")

        def to_dict(gene):
            return {
                'value': gene.symbol,
                'label': gene.name,
            }

        genes = None
        if query is None:
            genes = Gene.objects.all()
        else:
            genes = Gene.objects.filter(symbol__icontains=query)
        return Response(list(map(to_dict, genes)))


class LookupLaboratories(APIView):
    queryset = Laboratory.objects.none()

    def get(self, request, format=None):
        query = None
        try:
            query = request.GET['term']
        except KeyError:
            pass
            # raise BadRequestError("Required query parameter 'term' not received")

        def to_dict(lab):
            return {
                'value': lab.pk,
                'label': lab.name,
            }

        labs = None
        if query is None:
            labs = Laboratory.objects.all()
        else:
            labs = Laboratory.objects.filter(name__icontains=query)
        return Response(list(map(to_dict, labs)))


class LookupIndex(APIView):
    queryset = Patient.objects.none()

    def get(self, request, registry_code, format=None):
        term = ""
        try:
            term = request.GET['term']
        except KeyError:
            pass
            # raise BadRequestError("Required query parameter 'term' not received")
        registry = Registry.objects.get(code=registry_code)

        if not registry.has_feature('family_linkage'):
            return Response([])

        query = (Q(given_names__icontains=term) | Q(family_name__icontains=term)) & \
            Q(working_groups__in=request.user.working_groups.all(), active=True)

        def to_dict(patient):
            return {
                'pk': patient.pk,
                "class": "Patient",
                'value': patient.pk,
                'label': "%s" % patient,
            }

        return Response(list(map(to_dict, [p for p in Patient.objects.filter(query) if p.is_index])))


class ClinicalDataDetail(APIView):
    '''Clinical Data entry point'''
    permission_classes = (IsAuthenticated,)

    def get(self, request, registry_code, pk, format=None):
        patient = get_object_or_404(Patient, pk=pk)
        serializer = ClinicalDataSerializer(patient, context={'request': request})
        return Response(serializer.data)


class SectionDetail(APIView):
    permission_classes = (IsAuthenticated,)
    adapter = None
    serializer = None

    def get(self, request, registry_code, pk, format=None):
        doc = self.get_doc(registry_code, pk)
        serializer = self.serializer(self.adapter(doc), context={'request': request})
        return Response(serializer.data)

    def get_doc(self, registry_code, pk):
        patient = get_object_or_404(Patient, pk=pk)
        wrapper = DynamicDataWrapper(patient)
        doc = wrapper.load_dynamic_data(registry_code, 'cdes')
        if doc is None:
            raise Http404
        return doc


def create_section_detail(name, form, section):
    if not name.endswith('Detail'):
        name += 'Detail'
    doc = 'Section of Form "%s"' % form.nice_name
    return type(name, (SectionDetail,),
                {'__doc__': doc,
                 'adapter': create_adapter(form.name, section.code),
                 'serializer': create_section_serializer(form.name, section.code)})
