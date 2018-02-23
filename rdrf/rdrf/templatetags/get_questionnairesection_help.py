from django import template
from rdrf.models.definition.models import Section

register = template.Library()


@register.filter()
def get_questionnairesection_help(section_name):
    section_model = Section.objects.get(code=section_name)
    if section_model.questionnaire_help:
        return section_model.questionnaire_help
