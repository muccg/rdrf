from django.conf.urls import include, url

urlpatterns = [
    url(r'^patients/', include("registry.patients.urls")),
    url(r'^reports/', include("registry.common.report_urls")),
]
