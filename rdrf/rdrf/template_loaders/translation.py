from django.template import Template
from django.template import Origin
from django.template import TemplateDoesNotExist
from django.template.loaders.base import Loader as BaseLoader
from rdrf.models import Registry
from rdrf.models import RegistryForm
from rdrf.models import Section
from rdrf.models import CommonDataElement

class TemplateNameParseError(Exception):
    pass


class Loader(BaseLoader):
    """
    A custom templater which retrieves embedded templates from the registry definition
    models.
    """
    PREFIX = "rdrf://"
    
    def get_contents(self, origin):
        name = origin.name
        if not name.startswith(self.PREFIX):
            raise TemplateDoesNotExist()
        
        return self._get_template_html(name)


    def get_template_sources(self, template_name):
        yield Origin(
                name=template_name,
                template_name=template_name,
                loader=self,
            )

    def _get_template_html(self, template_name):
        try:
            protocol, field_path = template_name.split(self.PREFIX)
            registry_code, form_name, section_code, cde_code, cde_field = field_path.split("/")
        except ValueError:
            raise TemplateDoesNotExist("malformed template name: %s" % template_name)
        
        try:
            registry_model = Registry.objects.get(code=registry_code)
        except Registry.DoesNotExist:
            raise TemplateNameParseError("Unknown registry code: %s" % registry_code)

        try:
            form_model = RegistryForm.objects.get(name=form_name, registry=registry_model)
        except RegistryForm.DoesNotExist:
            raise TemplateNameParseError("Form not found: %s" % form_name)

        try:
            section_model = [s for s in form_model.section_models if s.code == section_code][0]
        except IndexError:
            raise TemplateNameParseError("Section not found: %s" % section_code)

        try:
            cde_model = [ c for c in section_model.cde_models if c.code == cde_code ][0]
        except IndexError:
            raise TemplateNameParseError("CDE not found: %s" % cde_code)


        if not hasattr(cde_model, cde_field):
            raise TemplateNameParseError("field  not on cde: %s" % cde_field)

        value = getattr(cde_model, cde_field)

        # type check?

        return value
