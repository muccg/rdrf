from django.urls import re_path, path
from rdrf.services.rest.views import api_views
from rdrf.routing.custom_rest_router import DefaultRouterWithSimpleViews


router = DefaultRouterWithSimpleViews()
router.register(r'registries', api_views.RegistryList, base_name='registry')
router.register(r'users', api_views.CustomUserViewSet)
router.register(r'doctors', api_views.DoctorViewSet)
router.register(r'nextofkinrelationship', api_views.NextOfKinRelationshipViewSet)
router.register(r'workinggroups', api_views.WorkingGroupViewSet)
router.register(r'countries', api_views.ListCountries, base_name='country')
router.register(r'genes', api_views.LookupGenes, base_name='gene')
router.register(r'laboratories', api_views.LookupLaboratories, base_name='laboratory')
router.register(r'registries/(?P<registry_code>\w+)/indices',
                api_views.LookupIndex, base_name='index')
router.register(r'registries/(?P<registry_code>\w+)/clinicians',
                api_views.ListClinicians, base_name='clinician')
router.register(r'calculatedcdes', api_views.CalculatedCdeValue, base_name='calculatedcde')

urlpatterns = [
    re_path(r'registries/(?P<code>\w+)/$', api_views.RegistryDetail.as_view(), name='registry-detail'),
    re_path(r'registries/(?P<registry_code>\w+)/patients/$',
            api_views.PatientList.as_view(), name='patient-list'),
    re_path(r'registries/(?P<registry_code>\w+)/patients/(?P<pk>\d+)/$',
            api_views.PatientDetail.as_view(), name='patient-detail'),
    re_path(r'^countries/(?P<country_code>[A-Z]{2})/states/$',
            api_views.ListStates.as_view(), name="state_lookup"),
] + router.urls
