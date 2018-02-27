import logging
from django.template import Origin
from django.template import TemplateDoesNotExist
from django.template.loaders.base import Loader as BaseLoader
from rdrf.helpers.utils import get_registry_definition_value

logger = logging.getLogger(__name__)


class Loader(BaseLoader):
    """
    A custom template loader which retrieves embedded html templates from the registry definition
    models.
    """
    PREFIX = "rdrf://"
    PRELUDE = "{% load i18n %}\n{% load static %}"

    def get_contents(self, origin):
        name = origin.name
        if not name.startswith(self.PREFIX):
            raise TemplateDoesNotExist("test")

        return self._get_template_html(name)

    def get_template_sources(self, template_name):
        yield Origin(
            name=template_name,
            template_name=template_name,
            loader=self,
        )

    def _get_template_html(self, template_name):
        try:
            _, field_path = template_name.split(self.PREFIX)
            html = get_registry_definition_value(field_path)
            return self.PRELUDE + "\n" + html
        except ValueError as verr:
            raise TemplateDoesNotExist("Bad template name %s: %s" % (template_name,
                                                                     verr.message))
