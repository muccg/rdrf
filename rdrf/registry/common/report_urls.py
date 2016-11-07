from django.conf.urls import url
from . import views

urlpatterns = [
    url(r"^patient/", views.patient_report)
]
