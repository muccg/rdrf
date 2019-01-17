from django.conf.urls import url
from django.urls import path
from django.urls import re_path

from .views import ConsentFileView

urlpatterns = [
    re_path("^download/(?P<consent_id>\d+)/(?P<filename>.*)$",
        ConsentFileView.as_view(),
        name="consent-form-download"),
]
