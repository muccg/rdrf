from django.conf.urls import patterns, url
import views
import form_view

urlpatterns = patterns("",
    url(r"^patient/(\d+)$", views.patient_cdes),
    url(r"^forms/(?P<form_name>\w+)/(?P<patient_id>\d+)$", form_view.FormView.as_view()),
)
