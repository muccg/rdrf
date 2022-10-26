from django.urls import re_path, include
from .views import PatientsDashboardView


urlpatterns = [
    re_path("^dash/", include("django_plotly_dash.urls")),
    re_path(
        r"^patients/?$",
        PatientsDashboardView.as_view(),
        name="patients",
    ),
]
