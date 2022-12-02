from django.urls import re_path
from .views import PatientsDashboardView
from .views import PatientDashboardView


urlpatterns = [
    re_path(
        r"^patients/?$",
        PatientsDashboardView.as_view(),
        name="overall",
    ),
    re_path(
        r"^patient/(?P<patient_id>\d+)$",
        PatientDashboardView.as_view(),
        name="single",
    ),
]
