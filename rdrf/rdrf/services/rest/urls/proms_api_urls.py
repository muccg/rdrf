from django.conf.urls import url
from rdrf.services.rest.views import proms_api

urlpatterns = [
    url(r'surveys/(?P<survey_id>\d+)$', proms_api.SurveyEndpoint.as_view(), name='survey_endpoint'),
]
