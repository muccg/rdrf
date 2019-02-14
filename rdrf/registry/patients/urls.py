from django.urls import re_path

from .views import ConsentFileView

urlpatterns = [
    re_path(r"^download/(?P<consent_id>\d+)/(?P<filename>.*)$",
            ConsentFileView.as_view(),
            name="consent-form-download"),
]
