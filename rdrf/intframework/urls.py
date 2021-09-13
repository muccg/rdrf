from django.urls import re_path, include, path, reverse_lazy
from .. views import DataRequestView

urlpatterns = [
    re_path(r'^datarequests/umrn/(?P<umrn>\w+)/?$', DataRequestView.as_view())
]
