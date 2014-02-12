from django.views.generic.base import View
from django.http import HttpResponse
import logging
import dynamic_data

logger = logging.getLogger("registry_log")

class REST(object):
    def __init__(self, verb, request, args, initial_data_dict):
        self.verb = verb
        self.request = request
        self.args = args

        self.patient_id = initial_data_dict.get("patient_id",None)
        self.registry_code = initial_data_dict.get("registry_code", None)
        self.form_name = initial_data_dict.get("form_name", None)
        self.section_name = initial_data_dict.get("section_name", None)
        self.cde_code = initial_data_dict.get("cde_code", None)

    def __unicode__(self):
        return "Registry %s Patient %s Form %s Section %s CDE %s" % (self.registry_code, self.patient_id, self.form_name, self.section_name, self.cde_code)

    @property
    def html(self):
        return """
            Registry CODE [%s]<br>
            Patient ID [%s]<br>
            Form [%s]<br>
            Section [%s]<br>
            CDE [%s]<br>
            """ % (self.registry_code, self.patient_id, self.form_name, self.section_name, self.cde_code)




    @property
    def response(self):
        method = getattr(self, "do_%s" % self.verb)
        return method()

    def do_GET(self):
        return HttpResponse(self.html)

class RDRFEndpointView(View):

    def get(self, request, *args, **kwargs):
        resource_request = REST("GET",request,args,kwargs)
        return resource_request.response

    def post(self, request, *args, **kwargs):
        resource_request = REST("POST",request,args,kwargs)
        return resource_request.response

    def put(self, request, *args, **kwargs):
        resource_request = REST("PUT",request,args,kwargs)
        return resource_request.response

    def delete(self, request, *args, **kwargs):
        resource_request = REST("DELETE",request,args,kwargs)
        return resource_request.response

    def patch(self, request, *args, **kwargs):
        resource_request = REST("PATCH",request,args,kwargs)
        return resource_request.response