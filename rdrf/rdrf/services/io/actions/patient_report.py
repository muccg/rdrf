from django.http import HttpResponse, FileResponse
import logging
logger = logging.getLogger(__name__)

DEMOGRAPHICS_VARIABLES = ["given_names"]


class Report:
    def __init__(self, content, content_type):
        self.content = content
        self.content_type = content_type


class ReportParser:
    def __init__(self, registry_model, report_name, report_spec, user, patient_model):
        self.registry_model = registry_model
        self.report_name = report_name
        self.report_spec = report_spec
        self.user = user
        self.patient_model = patient_model
        self.data = {}

    def generate_report(self):
        content_type = "text/plain"
        content = self.get_content()
        report = Report(content, content_type)
        return report

    def _get_variable_value(self, variable):
        if variable in DEMOGRAPHICS_VARIABLES:
            return getattr(self.patient_model, variable)

        return "TODO"

    def get_content(self):
        from django.template import Context, Template
        markdown_template = Template(self.report_spec)
        variables = self._get_variable_names(markdown_template)
        context = {}
        for variable in variables:
            value = self._get_variable_value(variable)
            context[variable] = value
        template_context = Context(context)
        markdown = markdown_template.render(template_context)
        return markdown

    def _get_variable_names(self, template_object):
        return [node.filter_expression.token for node in template_object.nodelist
                if node.__class__.__name__ == 'VariableNode']


def execute(registry_model, report_name, report_spec, user, patient_model):
    logger.debug("creating patient report %s" % report_name)
    parser = ReportParser(registry_model, report_name, report_spec, user, patient_model)
    report = parser.generate_report()
    if report:
        response = FileResponse(report.content, content_type=report.content_type)
    else:
        response = HttpResponse()

    return response
