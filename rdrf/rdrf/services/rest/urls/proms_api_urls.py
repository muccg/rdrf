from django.conf.urls import url
from rdrf.services.rest.views import proms_api

urlpatterns = [
    url(r'surveys/?$', proms_api.SurveyEndpoint.as_view(), name='survey_endpoint'),
    url(r'surveyassignments/?$', proms_api.SurveyAssignments.as_view(), name='survey_assignments'),
    url(r'promsdownload/?$', proms_api.PromsDownload.as_view(), name='proms_download'),
]
