from registry.patients.models import Patient
from registry.groups.models import WorkingGroup
from rdrf.models import Registry, RegistryForm
from rdrf.utils import de_camelcase
from rdrf.form_progress import FormProgress

from django.conf.urls import url
from django.core.paginator import Paginator, InvalidPage
from django.http import Http404
from django.core.urlresolvers import reverse
from django.templatetags.static import static

from tastypie.serializers import Serializer
from tastypie.authorization import DjangoAuthorization
from tastypie.utils import trailing_slash
from tastypie.resources import ModelResource
from tastypie import fields

import urlparse
import time
import logging

logger = logging.getLogger("registry_log")


class UrlEncodeSerializer(Serializer):
    formats = ['json', 'jsonp', 'xml', 'yaml', 'html', 'plist', 'urlencode']
    content_types = {
        'json': 'application/json',
        'jsonp': 'text/javascript',
        'xml': 'application/xml',
        'yaml': 'text/yaml',
        'html': 'text/html',
        'plist': 'application/x-plist',
        'urlencode': 'application/x-www-form-urlencoded',
    }

    def from_urlencode(self, data, options=None):
        """ handles basic formencoded url posts """
        qs = dict((k, v if len(v) > 1 else v[0])
                  for k, v in urlparse.parse_qs(data).iteritems())
        return qs

    def to_urlencode(self, content):
        pass


class WorkingGroupResource(ModelResource):
    name = fields.CharField(attribute='name')

    class Meta:
        queryset = WorkingGroup.objects.all()


class PatientResource(ModelResource):
    working_groups = fields.ToManyField(WorkingGroupResource, 'working_groups')

    class Meta:
        queryset = Patient.objects.all()
        serializer = UrlEncodeSerializer()
        authorization = DjangoAuthorization()

