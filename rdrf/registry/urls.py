from django.conf.urls import include, url

urlpatterns = [
    url(r'^patients/', include("registry.patients.urls")),
]
