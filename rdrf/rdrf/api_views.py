import pycountry

from django.db.models import Q
from rest_framework import generics
from rest_framework import mixins
from rest_framework import viewsets
from rest_framework import serializers
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView

from registry.genetic.models import Gene, Laboratory
from registry.patients.models import Patient, Registry, Doctor, NextOfKinRelationship
from registry.groups.models import CustomUser, WorkingGroup
from serializers import PatientSerializer, RegistrySerializer, WorkingGroupSerializer, CustomUserSerializer, DoctorSerializer, NextOfKinRelationshipSerializer


import logging
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


class DoctorDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer


class DoctorViewSet(viewsets.ModelViewSet):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer


class NextOfKinRelationshipDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = NextOfKinRelationship.objects.all()
    serializer_class = NextOfKinRelationshipSerializer


class NextOfKinRelationshipViewSet(viewsets.ModelViewSet):
    queryset = NextOfKinRelationship.objects.all()
    serializer_class = NextOfKinRelationshipSerializer


class PatientDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer

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


class WorkingGroupViewSet(viewsets.ModelViewSet):
    queryset = WorkingGroup.objects.all()
    serializer_class = WorkingGroupSerializer


class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer


class ListCountries(APIView):
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def get(self, request, format=None):
        countries = sorted(pycountry.countries, key=lambda c: c.name)

        def to_dict(country):
            # WANTED_FIELDS = ('name', 'alpha2', 'alpha3', 'numeric', 'official_name')
            WANTED_FIELDS = ('name', 'numeric', 'official_name')
            ALIASES = {
                'alpha2': 'country_code',
                'alpha3': 'country_code3',
            }

            d = dict([(k, getattr(country, k, None)) for k in WANTED_FIELDS])
            for attr, alias in ALIASES.items():
                d[alias] = getattr(country, attr)
            d['states'] = reverse('state_lookup', args=[country.alpha2], request=request)

            return d

        return Response(map(to_dict, countries))


class ListStates(APIView):
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def get(self, request, country_code, format=None):
        try:
            states = sorted(pycountry.subdivisions.get(
                country_code=country_code.upper()), key=lambda x: x.name)
        except KeyError:
            # For now returning empty list because the old api view was doing the same
            # raise BadRequestError("Invalid country code '%s'" % country_code)
            states = []

        WANTED_FIELDS = ('name', 'code', 'type', 'country_code')
        to_dict = lambda x: dict([(k, getattr(x, k)) for k in WANTED_FIELDS])

        return Response(map(to_dict, states))


class ListClinicians(APIView):
    queryset = CustomUser.objects.none()
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def get(self, request, registry_code, format=None):
        users = CustomUser.objects.filter(registry__code=registry_code, is_superuser=False)
        clinicians = filter(lambda u: u.is_clinician, users)

        def to_dict(c, wg):
            return {
                'id': "%d_%d" % (c.id, wg.id),
                'full_name': "%s %s (%s)" % (c.first_name, c.last_name, wg.name),
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
        return Response(map(to_dict, genes))


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
        return Response(map(to_dict, labs))


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

        return Response(map(to_dict, filter(lambda p: p.is_index, Patient.objects.filter(query))))
