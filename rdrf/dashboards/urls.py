from rdrf.views.dash_view import PatientsDashboardView

urlpatterns = [
    re_path("dash/", include("django_plotly_dash.urls")),
    re_path(
        r"^patientsdashboard/?$",
        PatientsDashboardView.as_view(),
        name="patientsdashboard",
    ),
]
