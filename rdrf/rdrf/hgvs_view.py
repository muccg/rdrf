from django.http import HttpResponse
from django.views.generic.base import View

import hgvs.parser
import json

from ometa.runtime import ParseError


class HGVSView(View):

    _hgvsparser = None

    def __init__(self):
        self._hgvsparser = self.get_instance()

    def get(self, request):
        hgvs_code = request.GET.get('code', None)

        try:
            self._hgvsparser.parse_hgvs_variant(hgvs_code)
            parse_result = True
        except ParseError:
            parse_result = False

        return HttpResponse(json.dumps({'parse_result': parse_result}), mimetype='application/json')

    def post(self, request, hgvs_code):
        pass

    @classmethod
    def get_instance(cls):
        if cls._hgvsparser is None:
            cls._hgvsparser = hgvs.parser.Parser()
        return cls._hgvsparser