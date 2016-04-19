from django.conf.urls import patterns, url, include
from rest_framework.routers import DefaultRouter
from rdrf import api_views
from rdrf.custom_rest_router import DefaultRouterWithSimpleViews

router = DefaultRouterWithSimpleViews()
# router.register(r'patients', api_views.PatientViewSet)
router.register(r'registries', api_views.RegistryViewSet, base_name='registry')
router.register(r'users', api_views.CustomUserViewSet)
router.register(r'workinggroups', api_views.WorkingGroupViewSet)
router.register(r'countries', api_views.country, base_name='country')
# router.register(r'countries/(?P<country_code>[A-Z]{2})/states', api_views.state_lookup, base_name='state')
router.register(r'genes', api_views.genes, base_name='gene')
router.register(r'laboratories', api_views.laboratories, base_name='laboratory')
# router.register(r'registries/(?P<registry_code>\w+)/clinitians', api_views.clinitian_lookup, base_name='clinitian')
router.register(r'registries/(?P<registry_code>\w+)/clinitians', api_views.clinitian_lookup, base_name='clinitian')

urlpatterns = patterns('rdrf.api_views',
    url(r'registries/(?P<registry_code>\w+)/patients/?$', api_views.PatientList.as_view(), name='patient-list'),
    url(r'registries/(?P<registry_code>\w+)/patients/(?P<pk>\d+)/?$', api_views.PatientDetail.as_view(), name='patient-detail'),

#    url(r'^countries/?$', api_views.country, name="countries"),
    url(r'^countries/(?P<country_code>[A-Z]{2})/states/?$', api_views.state_lookup, name="state_lookup"),
    (r'', include(router.urls)))

