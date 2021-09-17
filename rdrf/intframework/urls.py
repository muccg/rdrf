from django.urls import re_path
from .. views import DataRequestView

urlpatterns = [
    re_path(r'^datarequests/umrn/(?P<umrn>\w+)/?$', DataRequestView.as_view())
]
