from django.conf.urls import patterns, url
import views

urlpatterns = patterns("",
    url(r"^patient/", views.patient_report)
)
