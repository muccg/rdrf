from django.conf.urls import url
from rdrf.services.rest.views import proms_api

urlpatterns = [
    url(r'surveys/?$', proms_api.SurveyEndpoint.as_view(), name='survey_endpoint'),
]
