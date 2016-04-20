from django.conf.urls import patterns, url, include
from rest_framework.routers import DefaultRouter
from rdrf import api_views
from rdrf.custom_rest_router import DefaultRouterWithSimpleViews

router = DefaultRouterWithSimpleViews()
router.register(r'registries', api_views.RegistryList, base_name='registry')
router.register(r'users', api_views.CustomUserViewSet)
router.register(r'workinggroups', api_views.WorkingGroupViewSet)
router.register(r'countries', api_views.ListCountries, base_name='country')
router.register(r'genes', api_views.LookupGenes, base_name='gene')
router.register(r'laboratories', api_views.LookupLaboratories, base_name='laboratory')
router.register(r'registries/(?P<registry_code>\w+)/indexes', api_views.LookupIndex, base_name='index')
router.register(r'registries/(?P<registry_code>\w+)/clinitians', api_views.ListClinitians, base_name='clinitian')

urlpatterns = patterns('rdrf.api_views',
    url(r'registries/(?P<code>\w+)/$', api_views.RegistryDetail.as_view(), name='registry-detail'),
    url(r'registries/(?P<registry_code>\w+)/patients/$', api_views.PatientList.as_view(), name='patient-list'),
    url(r'registries/(?P<registry_code>\w+)/patients/(?P<pk>\d+)/$', api_views.PatientDetail.as_view(), name='patient-detail'),

    url(r'^countries/(?P<country_code>[A-Z]{2})/states/$', api_views.ListStates.as_view(), name="state_lookup"),
    (r'', include(router.urls)))

