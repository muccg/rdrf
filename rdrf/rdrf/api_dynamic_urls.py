from django.conf.urls import url
from . import api_views
from .models import Registry
from .utils import camel_to_snake, camel_to_dash_separated


def create_url(form, section):
    # TODO hardcoded
    name = section.code[3:] if section.code.startswith('MTM') else section.code
    url_name = camel_to_dash_separated(name + 'Detail')
    view = api_views.create_section_detail(name, form, section).as_view()

    return url(r'registries/(?P<registry_code>\w+)/%s/(?P<pk>\d+)/$' % camel_to_snake(name),
               view, name=url_name)


def clinical_urls():
    return [create_url(f, sec)
            for reg in Registry.objects.all() for f in reg.forms for sec in f.section_models]


urlpatterns = clinical_urls()
