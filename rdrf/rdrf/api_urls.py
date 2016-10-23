from django.conf import settings
from django.conf.urls import url, include
from . import api_views
from .custom_rest_router import DefaultRouterWithSimpleViews


import logging
logger = logging.getLogger(__name__)


router = DefaultRouterWithSimpleViews()
router.register(r'registries', api_views.RegistryList, base_name='registry')
router.register(r'users', api_views.CustomUserViewSet)
router.register(r'doctors', api_views.DoctorViewSet)
router.register(r'nextofkinrelationship', api_views.NextOfKinRelationshipViewSet)
router.register(r'permitted_value_groups', api_views.PermittedValueGroupViewSet)
router.register(r'common_data_elements', api_views.CommonDataElementViewSet)
router.register(r'workinggroups', api_views.WorkingGroupViewSet)
router.register(r'countries', api_views.CountryViewSet, base_name='country')
router.register(r'genes', api_views.LookupGenes, base_name='gene')
router.register(r'laboratories', api_views.LookupLaboratories, base_name='laboratory')
router.register(r'registries/(?P<registry_code>\w+)/indices', api_views.LookupIndex, base_name='index')
router.register(r'registries/(?P<registry_code>\w+)/clinicians', api_views.ListClinicians, base_name='clinician')


# Dynamic urls
# TODO make sure we avoid clashing urls
clinical_data_urlpatterns = []
if getattr(settings, 'API_CLINICAL_DATA_ENABLED', False):
    clinical_data_urlpatterns = [
        url(r'registries/(?P<registry_code>\w+)/patients/(?P<pk>\d+)/clinical_data/$',
            api_views.ClinicalDataDetail.as_view(), name='clinical-data-detail'),
        url(r'^clinical_data/', include('rdrf.api_dynamic_urls', namespace='clinical')),
    ]

urlpatterns = clinical_data_urlpatterns + [
    url(r'registries/(?P<code>\w+)/$', api_views.RegistryDetail.as_view(), name='registry-detail'),
    url(r'registries/(?P<registry_code>\w+)/patients/$',
        api_views.PatientList.as_view(), name='patient-list'),
    url(r'registries/(?P<registry_code>\w+)/patients/(?P<pk>\d+)/$',
        api_views.PatientDetail.as_view(), name='patient-detail'),
    url(r'registries/(?P<registry_code>\w+)/forms/$',
        api_views.RegistryFormList.as_view(), name='registry-form-list'),
    url(r'registries/(?P<registry_code>\w+)/forms/(?P<name>\w+)/$',
        api_views.RegistryFormDetail.as_view(), name='registry-form-detail'),
    url(r'permitted_value_groups/(?P<pvg_code>\w+)/permitted_values/$',
        api_views.PermittedValueList.as_view(), name='permitted-value-list'),
    url(r'permitted_value_groups/(?P<pvg_code>\w+)/permitted_values/(?P<code>\w+)/$',
        api_views.PermittedValueDetail.as_view(), name='permitted-value-detail'),
    url(r'^countries/(?P<country_code>[A-Z]{2})/states/$',
        api_views.ListStates.as_view(), name="state_lookup"),
]


urlpatterns += router.urls
