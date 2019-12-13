from django.http import HttpResponse, FileResponse
from rdrf.models.definition.models import Registry
from rdrf.models.definition.models import Section
from rdrf.models.definition.models import CommonDataElement

from rdrf.helpers.utils import format_date
from datetime import datetime
from datetime import date

import logging
logger = logging.getLogger(__name__)


class ParseException(Exception):
    pass


class FieldSpec:
    PATH_DELIMITER = "/"


class TemplateSetup:
    LOAD_STATEMENTS = "{% load report_filters %}"


class Markdown:
    LINE_BREAK = '\n'
    TABLETOP = "|\n" + "--|--\n"


def cleanup(s):
    return s.replace("&lt;", "<").replace("&gt;", ">")


def get_country(country_code):
    import pycountry
    for country in pycountry.countries:
        if country.alpha_2 == country_code:
            return country.name
    return ""


def convert_american_date(american_date_string):
    if not american_date_string:
        return ""
    year, month, day = american_date_string.split("-")
    return "%s-%s-%s" % (day, month, year)


DEMOGRAPHICS_VARIABLES = ['id', 'consent', 'consent_clinical_trials', 'consent_sent_information',
                          'consent_provided_by_parent_guardian', 'family_name', 'given_names',
                          'maiden_name', 'umrn', 'date_of_birth', 'date_of_death', 'place_of_birth',
                          'date_of_migration', 'country_of_birth',
                          'ethnic_origin', 'sex', 'home_phone', 'mobile_phone', 'work_phone', 'email',
                          'next_of_kin_family_name', 'next_of_kin_given_names', 'next_of_kin_relationship',
                          'next_of_kin_address', 'next_of_kin_suburb', 'next_of_kin_state', 'next_of_kin_postcode',
                          'next_of_kin_home_phone', 'next_of_kin_mobile_phone', 'next_of_kin_work_phone',
                          'next_of_kin_email', 'next_of_kin_parent_place_of_birth',
                          'next_of_kin_country', 'active', 'inactive_reason',
                          'clinician', 'living_status', 'patient_type']


def nice(func):
    def safe(*args, **kwargs):
        try:
            value = func(*args, **kwargs)
        except KeyError:
            # no data entered in form
            return "[Not Entered]"

        if value is None:
            return ""
        else:
            return value
    return safe


def make_table(cde_model, range_dict, raw_values):
    result = {}
    names = []
    newline = "\n"
    for d in range_dict["values"]:
        name = d["value"]
        names.append(name)
        if d["code"] in raw_values:
            result[name] = "Yes"
        else:
            result[name] = "No"

    header1 = "|" + cde_model.name + "|Answer|"
    header2 = ":----|----:|"
    table_content = newline.join("|%s|%s|" % (name, result[name]) for name in names)
    table = header1 + newline + header2 + newline + table_content + newline
    logger.debug(table)
    return table


def human_value(cde_model, raw_value, is_list=False):
    if cde_model.pv_group:
        range_dict = cde_model.pv_group.as_dict()
        if is_list:
            logger.debug("making a table for %s" % cde_model.code)
            return make_table(cde_model, range_dict, raw_value)

        for value_dict in range_dict["values"]:
            if raw_value == value_dict["code"]:
                return cleanup(value_dict["value"])
    else:
        if cde_model.datatype == "date":
            if raw_value:
                return convert_american_date(raw_value)

    return raw_value


@nice
def retrieve(registry_model, field, patient_model, clinical_data):
    if FieldSpec.PATH_DELIMITER not in field:
        # e.g. {{ CDECODE }}
        for form_model in registry_model.forms:
            for section_model in form_model.section_models:
                if not section_model.allow_multiple:
                    for cde_model in section_model.cde_models:
                        if cde_model.code == field:
                            form_value = patient_model.get_form_value(registry_model.code,
                                                                      form_model.name,
                                                                      section_model.code,
                                                                      cde_model.code,
                                                                      clinical_data=clinical_data)
                            logger.debug("form_value = %s" % form_value)
                            if cde_model.allow_multiple and type(form_value) is list:
                                return human_value(cde_model, form_value, is_list=True)
                            return human_value(cde_model, form_value)
        return "ERROR"

    form, section, cde = field.split(FieldSpec.PATH_DELIMITER)
    form_model = RegistryModel.objects.get(registry=registry_model,
                                           name=form)
    section_model = Section.objects.get(code=section)
    cde_model = CommonDataElement.objects.get(code=cde)

    form_value = patient_model.get_form_value(registry_model.code,
                                              form_model.name,
                                              section_model.code,
                                              cde_model.code)
    return human_value(cde_model, form_value)


class Report:
    def __init__(self, content, content_type):
        self.content = content
        self.content_type = content_type


class ReportParser:
    def __init__(self, registry_model, report_name, report_spec, user, patient_model):
        self.registry_model = registry_model
        self.report_name = report_name
        self.report_spec = report_spec  # a django template that will create the markdown
        self.user = user
        self.patient_model = patient_model
        self.data = {}
        self.clinical_data = self._load()

    @property
    def filename(self):
        return "%s-%s-%s.pdf" % (self.registry_model.code,
                                 self.report_name,
                                 self.patient_model.pk)

    def _load(self):
        if not self.registry_model.has_feature("contexts"):
            logger.debug("no contexts")
            return self.patient_model.get_dynamic_data(self.registry_model)
        else:
            for context_model in self.patient_model.context_models:
                if context_model.context_form_group:
                    if context_model.context_form_group.is_default:
                        logger.debug("found default context")
                        return self.patient_model.get_dynamic_data(self.registry_model,
                                                                   context_id=context_model.id,
                                                                   flattened=True)
        raise Exception("can't load clinical data")

    def generate_report(self):
        import markdown
        from xhtml2pdf import pisa
        content_type = "application/pdf"
        markdown_content = self.get_markdown()
        html_content = markdown.markdown(markdown_content, extensions=['tables'])
        response = HttpResponse(content_type="application/pdf")
        response['Content-Disposition'] = 'attachment; filename="%s"' % self.filename
        pisa_status = pisa.CreatePDF(html_content, dest=response)
        return response

    def _get_variable_value(self, variable):
        value = "TODO"
        if variable in DEMOGRAPHICS_VARIABLES:
            logger.debug("%s is a demographic field" % variable)
            value = getattr(self.patient_model, variable)
            if isinstance(value, datetime) or isinstance(value, date):
                value = format_date(value)
                logger.debug("updated value = %s" % value)
            if variable == "country_of_birth":
                value = get_country(value)
        else:
            value = retrieve(self.registry_model,
                             variable,
                             self.patient_model,
                             self.clinical_data)
        logger.debug("%s = %s" % (variable, value))
        return value

    def get_markdown(self):
        from django.template import Context, Template
        #template_text = TemplateSetup.LOAD_STATEMENTS + "\n" + self.report_spec
        template_text = self.report_spec
        markdown_template = Template(template_text)
        variables = self._get_variable_names(markdown_template)
        context = {}
        for variable in variables:
            value = self._get_variable_value(variable)
            context[variable] = value
        template_context = Context(context)
        markdown = markdown_template.render(template_context)
        return markdown

    def _get_variable_names(self, template_object):
        vars = [node.filter_expression.token for node in template_object.nodelist
                if node.__class__.__name__ == 'VariableNode']
        logger.debug("variables in template = %s" % vars)
        return vars


def execute(registry_model, report_name, report_spec, user, patient_model):
    logger.debug("creating patient report %s" % report_name)
    parser = ReportParser(registry_model, report_name, report_spec, user, patient_model)
    report = parser.generate_report()
    if report:
        return report
        response = FileResponse(report.content, content_type=report.content_type)
    else:
        response = HttpResponse()

    return response
