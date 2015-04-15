from tastypie.resources import ModelResource
from registry.patients.models import Patient
from django.conf.urls import url
from django.core.paginator import Paginator, InvalidPage
from django.http import Http404
#from haystack.query import SearchQuerySet
from tastypie.utils import trailing_slash

import urlparse
from tastypie.serializers import Serializer
from tastypie.authorization import DjangoAuthorization

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

    def from_urlencode(self, data,options=None):
        """ handles basic formencoded url posts """
        qs = dict((k, v if len(v)>1 else v[0] )
            for k, v in urlparse.parse_qs(data).iteritems())
        return qs

    def to_urlencode(self,content):
        pass


class PatientResource(ModelResource):

    class Meta:
        queryset = Patient.objects.all()
        serializer = UrlEncodeSerializer()
        authorization = DjangoAuthorization()


    # https://django-tastypie.readthedocs.org/en/latest/cookbook.html#adding-search-functionality
    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/search%s$" % (self._meta.resource_name, trailing_slash()), self.wrap_view('get_search'), name="api_get_search"),
        ]

    def get_search(self, request, **kwargs):
        logger.debug("get_search request.GET = %s" % request.GET)
        patients = Patient.objects.all()

        if not request.user.is_superuser:
            if request.user.is_curator:
                patients = patients.filter(working_groups__in=request.user.working_groups.all())
            elif request.user.is_genetic:
                patients = patients.filter(working_groups__in=request.user.working_groups.all())  #unclear what to do here
            elif request.user.is_clinician:
                patients = patients.filter(clinician=request.user)
            elif request.user.is_patient:
                patients = patients.filter(user=request.user)
            else:
                patients = patients.objects.none()



        # ] request.GET = <QueryDict: {u'current': [u'1'], u'rowCount': [u'10'], u'searchPhrase': [u'ffff']}>


        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)

        row_count = int(request.GET.get('rowCount', 20))
        search_phrase = request.GET.get("searchPhrase", None)
        current = int(request.GET.get("current", 1))
        sort_field, sort_direction = self._get_sorting(request)

        # Do the query.

        query_set = patients

        if sort_field and sort_direction:
            if sort_direction == "desc":
                sort_field = "-" + sort_field
            query_set = query_set.order_by(sort_field)
            logger.debug("sort field = %s" % sort_field)

        if search_phrase:
            from django.db.models import Q
            query_set = query_set.filter(Q(given_names__icontains=search_phrase) | Q(family_name__icontains=search_phrase))

        total = query_set.count()
        if row_count == -1:
            # All
            row_count = total

        paginator = Paginator(query_set, row_count)



        try:
            page = paginator.page(current)
        except InvalidPage:
            raise Http404("Sorry, no results on that page.")

        objects = []

        for result in page.object_list:
            bundle = self.build_bundle(obj=result, request=request)
            bundle = self.full_dehydrate(bundle)
            objects.append(bundle)


        # jquery bootgrid expects:
        #         {
        #   "current": 1,
        #   "rowCount": 10,
        #   "rows": [
        #     {
        #       "id": 19,
        #       "sender": "123@test.de",
        #       "received": "2014-05-30T22:15:00"
        #     },
        #     {
        #       "id": 14,
        #       "sender": "123@test.de",
        #       "received": "2014-05-30T20:15:00"
        #     },
        #     ...
        #   ],
        #   "total": 1123
        # }


        results = {
            "current" : current,
            "rowCount": row_count,
            "searchPhrase": search_phrase,
            "rows"  : objects,
            "total" : total
        }

        self.log_throttled_access(request)
        return self.create_response(request, results)

    def _get_sorting(self, request):
        # boot grid uses this convention
        #sort[given_names]': [u'desc']
        for k in request.GET:
            if k.startswith("sort["):
                import re
                pattern = re.compile(r'^sort\[(.*?)\]$')
                m = pattern.match(k)
                if m:
                    sort_field = m.groups(1)[0]
                    sort_direction = request.GET.get(k)
                    return sort_field, sort_direction

        return None, None
