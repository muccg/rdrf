from django.views.generic.base import View
from django.http import HttpResponse
import logging
import dynamic_data
from registry.patients.models import Patient
from rdrf.models import *
import json
import yaml
from django.core.servers.basehttp import FileWrapper
import cStringIO as StringIO
from django.http import Http404
from functools import wraps
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


logger = logging.getLogger("registry_log")

class ResourceFormat:
    JSON = "JSON"
    YAML = "YAML"

    @staticmethod
    def get(format, data):
        if format == ResourceFormat.YAML:
            return ResourceFormat.as_yaml(data)
        elif format == ResourceFormat.JSON:
            return ResourceFormat.as_json(data)
        else:
            raise RESTInterfaceError("Unknown format: %s" % format)

    @staticmethod
    def as_yaml(data):
        import yaml
        return yaml.dumps(data)

    @staticmethod
    def as_json(data):
        import json
        return json.dumps(data)

    @staticmethod
    def mime_type(format):
        if format == ResourceFormat.YAML:
            return "text/yaml"
        elif format == ResourceFormat.JSON:
            return "text/json"
        else:
            raise RESTInterfaceError("Unknown format: %s" % format)



class RESTInterfaceError(Exception):
    pass

class CDECodeNotDefined(RESTInterfaceError):
    pass

class REST(object):
    def __init__(self, verb, request, args, initial_data_dict):
        self.format = ResourceFormat.JSON
        self.error_message = None
        self.verb = verb
        self.request = request
        self.args = args
        self.data = None
        self.patient_id = initial_data_dict.get("patient_id",None)
        self.registry_code = initial_data_dict.get("registry_code", None)
        self.form_name = initial_data_dict.get("form_name", None)
        self.section_code = initial_data_dict.get("section_code", None)
        self.cde_code = initial_data_dict.get("cde_code", None)

        if self.registry_code:
            try:
                self.registry = Registry.objects.get(code=self.registry_code)
            except Registry.DoesNotExist:
                raise RESTInterfaceError("Registry %s does not exist" % self.registry_code)
        else:
            self.registry = None

        if self.form_name:
            try:
                self.registry_form = RegistryForm.objects.get(registry=self.registry, name = self.form_name)
            except RegistryForm.DoesNotExist:
                raise RESTInterfaceError("Registry Form %s does not in exist in registry %s" % (self.form_name, self.registry_code))
        else:
            self.registry = None

        if self.section_code:
            if self.section_code in self.registry_form.get_sections():
                try:
                    self.section = Section.objects.get(code=self.section_code)
                except Section.DoesNotExist:
                    raise RESTInterfaceError("Section %s does not exist" % self.section_code)


            else:
                raise RESTInterfaceError("Section %s does not appear in Registry form %s in Registry %s" %  (self.section_code, self.form_name, self.registry_code))

        else:
            self.section = None

        if self.cde_code:
            try:
                self.cde = CommonDataElement.objects.get(code=self.cde_code)
                if not appears_in(self.cde, self.registry, self.registry_form, self.section ):
                    raise RESTInterfaceError("Data Element with code %s does not appear in Registry %s Form %s Section %s" % (self.cde_code, self.registry_code, self.form_name, self.section_code))
            except CommonDataElement.DoesNotExist:
                raise RESTInterfaceError("Data Elemement with code %s doesn't exist" % self.cde_code)

        if self.patient_id is None:
            self.error_message = 'No patient id supplied'
        else:
            try:
                patient = Patient.objects.get(pk=self.patient_id)
                self._validate()
                self.dyn_data_wrapper = dynamic_data.DynamicDataWrapper(patient)
            except Patient.DoesNotExist:
                self.error_message = "Patient with id %s does not exist" % self.patient_id
                self.dyn_data_wrapper = None

    def _validate(self):
        #TODO check supplied reg code , etc against definition
        pass

    def __unicode__(self):
        return "Registry %s Patient %s Form %s Section %s CDE %s" % (self.registry_code, self.patient_id, self.form_name, self.section_code, self.cde_code)


    @property
    def valid(self):
       return self.error_message is None

    @property
    def html(self):
        return """
            Registry CODE [%s]<br>
            Patient ID [%s]<br>
            Form [%s]<br>
            Section [%s]<br>
            CDE [%s]<br>
            """ % (self.registry_code, self.patient_id, self.form_name, self.section_code, self.cde_code)

    @property
    def response(self):
        method = getattr(self, "do_%s" % self.verb)
        try:
            return method()
        except CDECodeNotDefined, cdeerr:
            return HttpResponse(cdeerr, status=400)

        except RESTInterfaceError, rierr:
            return HttpResponse(rierr, status=400)


    def do_GET(self):
        if self.patient_id is None:
            return HttpResponse("No patient id supplied", status=400)

        if self.dyn_data_wrapper is None:
            raise Http404("No Patient with %s exists" % self.patient_id)

        existing_patient_data  = self.dyn_data_wrapper.load_dynamic_data(registry=self.registry_code, collection_name="cdes")

        if self.cde_code:
            retrieved_data = self._retrieve("cde",existing_patient_data)
        elif self.section_code:
            retrieved_data = self._retrieve("section", existing_patient_data)
        elif self.form_name:
            retrieved_data = self._retrieve("form", existing_patient_data)
        elif self.registry_code:
            retrieved_data = self._retrieve("registry", existing_patient_data)
        else:
            retrieved_data = None

        return self._response_data(retrieved_data)


    def do_POST(self):
        # PUT didn't work so uating with POST
        #existing_patient_data  = self.dyn_data_wrapper.load_dynamic_data(registry=self.registry_code, collection_name="cdes")

        if self.cde_code:
            # update the value of cde code and save back
            key = self._create_delimited_key()
            new_value = self._get_value()
            logger.debug("Updating %s to %s" % (key, new_value))
            updated_data = { key : new_value }
            self.dyn_data_wrapper.save_dynamic_data(self.registry.code, "cdes", updated_data)
            return HttpResponse('OK', status=200)


        elif self.section_code:
            # update entire section
            #todo - REST interface update section
            pass

        elif self.form_name:
            #update entire form
            #todo - REST interface update form
            pass
        elif self.registry_code:
            #update all form data
            #todo - REST interface update forms
            pass

    def _get_value(self):
        if self.cde_code:
            is_file = self.request.META["CONTENT_TYPE"].startswith("multipart")
            if is_file:
                logger.debug("file received")
                return self.request.FILES["value"]

            else:
                source = self.request.body
                request_format = self._get_request_format()

            if request_format == ResourceFormat.JSON:
                import json
                data = json.loads(source)

            elif request_format == ResourceFormat.YAML:
                import yaml
                data = yaml.loads(source)
            else:
                raise RESTInterfaceError("Unknown request format")


            logger.debug("decoded request data = %s" % data)
            return data
        else:
            raise NotImplementedError()

    def _get_request_format(self):
        # application/json etc
        accept_header = self.request.META["HTTP_ACCEPT"].lower()
        if "json" in accept_header:
            return ResourceFormat.JSON
        elif "yaml" in accept_header:
            return ResourceFormat.YAML
        else:
            raise RESTInterfaceError("Unknown HTTP_ACCEPT Header: %s" % self.request.META["HTTP_ACCEPT"] )

    def _create_delimited_key(self):
        from django.conf import settings
        return settings.FORM_SECTION_DELIMITER.join([self.form_name, self.section_code, self.cde_code])


    def _retrieve(self, level, data):
        from operator import add
        logger.debug("dynamic data = %s" % data)

        if level == 'cde':
            delimited_key = self._create_delimited_key()
            logger.debug("delimited key = %s" % delimited_key)
            if delimited_key in data:
                retrieved_data = data[delimited_key]
                logger.debug("%s=%s" % (self.cde_code, retrieved_data))
                return retrieved_data
            else:
                return None
        elif level == 'section':
            section_cde_map = {}
            for delimited_key in data:
                logger.debug("checking key %s" % delimited_key)
                try:
                    form_name, section_code, cde_code = delimited_key.split(settings.FORM_SECTION_DELIMITER)
                except ValueError,ex:
                    # this means there's bad data in there - saved with diff delimiter
                    continue

                if section_code == self.section_code:
                    section_model = Section.objects.get(code=self.section_code)
                    defined_cde_codes  = section_model.get_elements()
                    if cde_code in defined_cde_codes:
                        section_cde_map[cde_code] = data[delimited_key]
                    else:
                        raise CDECodeNotDefined(cde_code)
            return section_cde_map

        elif level == 'form':
            form_map = {}
            defined_section_codes  = self.registry_form.get_sections()
            for defined_section_code in defined_section_codes:
                defined_section = Section.objects.get(code=defined_section_code)
                section_map = {}
                for delimited_key in data:
                    try:
                        form_name, section_code, cde_code = delimited_key.split(settings.FORM_SECTION_DELIMITER)
                    except ValueError,ex:
                    # this means there's bad data in there - saved with diff delimiter
                        continue
                    if self.registry_form.name == form_name and  defined_section_code == section_code:
                        section_map[cde_code] = data[delimited_key]

                form_map[defined_section_code] = section_map
            return form_map

        elif level == 'registry':
            registry_map = {}
            for delimited_key in data:
                try:
                    form_name, section_code, cde_code = delimited_key.split(settings.FORM_SECTION_DELIMITER)
                except ValueError, verr:
                    continue

                if not form_name in registry_map:
                    registry_map[form_name] = {}
                if not section_code in registry_map[form_name]:
                    registry_map[form_name][section_code] = {}

                if not cde_code in registry_map[form_name][section_code]:
                    registry_map[form_name][section_code][cde_code] = data[delimited_key]

            return registry_map

        else:
            raise RESTInterfaceError("Unknown level: %s" % level)

    def _response_data(self, data):
        formatted_data = ResourceFormat.get(self.format, data)
        return HttpResponse(formatted_data, content_type=ResourceFormat.mime_type(self.format))


def rest_call(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except RESTInterfaceError, rierr:
            return HttpResponse(str(rierr), status=400)
    return wrapper


class RDRFEndpointView(View):

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(RDRFEndpointView, self).dispatch(*args, **kwargs)

    @rest_call
    def get(self, request, *args, **kwargs):
        resource_request = REST("GET",request,args,kwargs)
        return resource_request.response

    @rest_call
    def post(self, request, *args, **kwargs):
        resource_request = REST("POST",request,args,kwargs)
        return resource_request.response

    @rest_call
    def put(self, request, *args, **kwargs):
        resource_request = REST("PUT",request,args,kwargs)
        return resource_request.response

    @rest_call
    def delete(self, request, *args, **kwargs):
        resource_request = REST("DELETE",request,args,kwargs)
        return resource_request.response

    # @rest_call
    # @csrf_exempt
    # def patch(self, request, *args, **kwargs):
    #     resource_request = REST("PATCH",request,args,kwargs)
    #     return resource_request.response