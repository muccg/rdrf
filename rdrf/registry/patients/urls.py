from django.conf.urls import url

from .views import ConsentFileView

urlpatterns = [
    url("^download/(?P<consent_id>\d+)/(?P<filename>.*)$",
        ConsentFileView.as_view(),
        name="consent-form-download"),
]
