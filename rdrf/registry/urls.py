from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
    url(r'^groups/', include("registry.groups.urls")),
    url(r'^patients/', include("registry.patients.urls")),
    url(r'^reports/', include("registry.common.report_urls")),
)
