from django.urls import include, re_path

# app_name = 'rdrf'

urlpatterns = [
    re_path(r'^patients/', include("registry.patients.urls")),
]
