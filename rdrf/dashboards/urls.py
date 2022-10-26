from django.urls import re_path, include
from .views import PatientsDashboardView


urlpatterns = [
    re_path(
        r"^patients/?$",
        PatientsDashboardView.as_view(),
        name="patients",
    ),
]
