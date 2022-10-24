from dash import dcc, html
import dash
from django_plotly_dash import DjangoDash


def get_patients_dashboard_app(registry_model):
    app = DjangoDash("patients-dashboard")
