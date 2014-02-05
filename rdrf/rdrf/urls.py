from django.conf.urls import patterns, url
from django.conf.urls import patterns, include
from django.contrib import admin
from django.shortcuts import render_to_response
import registry.urls as common_urls
from registry.common import views
import views
import form_view
import registry_view
import dashboard_view
import landing_view
from django.shortcuts import render_to_response

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
    url(r"^(?P<registry_code>\w+)/forms/(?P<form_id>\w+)/(?P<patient_id>\d+)$", form_view.FormView.as_view()),
    url(r"^registry/(?P<registry_code>\w+)/?$", registry_view.RegistryView.as_view()),
    url(r'^/?$',landing_view.LandingView.as_view()),
    url(r'^dashboard/?$', dashboard_view.DashboardView.as_view(), name='dashboard' ),
    url(r'^login/?$', 'django.contrib.auth.views.login', {'template_name': 'admin/login.html'}),
    url(r'^(?P<registry_code>\w+)/questionnaire/?$',form_view.QuestionnaireView.as_view() ),
    url(r'^(?P<registry_code>\w+)/approval/(?P<questionnaire_response_id>\d+)/?$',form_view.QuestionnaireResponseView.as_view() ),
    url(r'^(?P<registry_code>\w+)/uploads/(?P<gridfs_file_id>\w+)$',form_view.FileUploadView.as_view()),
)


