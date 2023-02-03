import logging
from django.urls import re_path
from .views import PatientsDashboardView
from .views import PatientDashboardView

# register the DjangoDashApps once on load
from .dash_apps import single_app, all_app


logger = logging.getLogger(__name__)
logger.debug(f"loaded {single_app}")
logger.debug(f"loaded {all_app}")

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
