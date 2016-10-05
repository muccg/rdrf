from django.conf.urls import patterns, url
from . import views

urlpatterns = patterns("",
                       url(r"^patient/", views.patient_report)
                       )
