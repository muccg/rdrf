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
admin.autodiscover() # very important so that registry admins (genetic, patient, etc) are discovered.

urlpatterns = patterns("",
    (r'^admin/', include(admin.site.urls)),
    (r'', include(common_urls, namespace="registry")),
    url(r"^patient/(\d+)$", views.patient_cdes),
    url(r"^(?P<registry_code>\w+)/forms/(?P<form_id>\w+)/(?P<patient_id>\d+)$", form_view.FormView.as_view()),
    url(r"^registry/(?P<registry_code>\w+)/?$", registry_view.RegistryView.as_view()),
    url(r'^dashboard/?$', dashboard_view.DashboardView.as_view()),
    url(r'^login/?$', 'django.contrib.auth.views.login', {'template_name': 'admin/login.html'})
)


def handler404(request):
    return render_to_response("error/404.html")

def handler500(request):
    return render_to_response("error/500.html")
