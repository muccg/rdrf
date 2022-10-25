from django_plotly_dash import DjangoDash


def get_patients_dashboard_app(registry_model):
    return DjangoDash("patients-dashboard")
