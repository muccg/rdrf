from django.urls import re_path
from .views import PatientsDashboardView


urlpatterns = [
    re_path(
        r"^patients/?$",
        PatientsDashboardView.as_view(),
        name="overall",
    ),
]
