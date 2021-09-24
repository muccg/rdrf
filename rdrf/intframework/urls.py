from django.urls import re_path
from intframework.views import IntegrationHubRequestView

urlpatterns = [
    re_path(r"^(?P<registry_code>\w+)/patient/data/request/data/(?P<umrn>\w+)?$",
            IntegrationHubRequestView.as_view(), name='hub'),
]
