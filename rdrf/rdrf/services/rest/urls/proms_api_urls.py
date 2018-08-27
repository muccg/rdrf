from django.conf.urls import url
from rdrf.services.rest.views import proms_api

urlpatterns = [
    url(r'questions/(?P<code>\w+)/$', proms_api_views.QuestionEndpoint.as_view(), name='question-endpoint'),
]
