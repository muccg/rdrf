from django.conf.urls import patterns, url
from django.conf.urls import patterns, include
from django.contrib import admin
from django.shortcuts import render_to_response
import registry.urls as common_urls
from registry.common import views
import views
import form_view
import registry_view
import landing_view
import import_registry_view
import rest_interface
import hgvs_view
from django.shortcuts import render_to_response
from ajax_select import urls as ajax_select_urls

admin.autodiscover() # very important so that registry admins (genetic, patient, etc) are discovered.

def handler404(request):
    return render_to_response("error/404.html")

def handler500(request):
    return render_to_response("error/500.html")

def handlerApplicationError(request):
    return render_to_response("rdrf_cdes/application_error.html",{"application_error": "Example config Error"})

urlpatterns = patterns("",
    url(r'^test404',handler404),
    url(r'^test500',handler500),
    url(r'^testAppError',handlerApplicationError),
    (r'^admin/', include(admin.site.urls)),
    (r'', include('django.contrib.auth.urls')),
    (r'', include(common_urls, namespace="registry")),
    url(r"^patient/(\d+)$", views.patient_cdes),
    url(r"^(?P<registry_code>\w+)/forms/(?P<form_id>\w+)/(?P<patient_id>\d+)$", form_view.FormView.as_view(), name='registry_form'),
    url(r"^registry/(?P<registry_code>\w+)/?$", registry_view.RegistryView.as_view(), name='registry'),
    url(r'^/?$',landing_view.LandingView.as_view(), name='landing'),
    url(r'^import/?', import_registry_view.ImportRegistryView.as_view(), name='import_registry' ),
    url(r'^login/?$', 'django.contrib.auth.views.login', {'template_name': 'admin/login.html'}, name='login'),
    url(r'^(?P<registry_code>\w+)/questionnaire/?$',form_view.QuestionnaireView.as_view(), name='questionnaire'),
    url(r'^(?P<registry_code>\w+)/approval/(?P<questionnaire_response_id>\d+)/?$',form_view.QuestionnaireResponseView.as_view(),
        name='questionnaire_response'),
    url(r'^(?P<registry_code>\w+)/uploads/(?P<gridfs_file_id>\w+)$',form_view.FileUploadView.as_view(), name='file_upload'),
    url(r'^(?P<registry_code>\w+)/patients/(?P<patient_id>\d+)?/(?P<form_name>.+?)/(?P<section_code>.+?)/(?P<cde_code>.+?)/?$', rest_interface.RDRFEndpointView.as_view(), name='rest_cde_interface'),
    url(r'^(?P<registry_code>\w+)/patients/(?P<patient_id>\d+)?/(?P<form_name>.+?)/(?P<section_code>.+?)/?$', rest_interface.RDRFEndpointView.as_view(), name='rest_section_interface'),
    url(r'^(?P<registry_code>\w+)/patients/(?P<patient_id>\d+)?/(?P<form_name>.+?)/?$', rest_interface.RDRFEndpointView.as_view(), name='rest_form_interface'),
    url(r'^(?P<registry_code>\w+)/patients/(?P<patient_id>\d+)?/?$', rest_interface.RDRFEndpointView.as_view(), name='rest_interface'),
    (r'^admin/lookups/', include(ajax_select_urls)),
    
    url(r'^hgvs/(?P<hgvs_code>.+)/?$', hgvs_view.HGVSView.as_view(), name='hgvs_validator'),
)