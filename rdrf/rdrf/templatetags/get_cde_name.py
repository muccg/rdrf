from django import template
from rdrf.models.definition.models import CommonDataElement

register = template.Library()


@register.filter()
def get_cde_name(cde_code):
    try:
        cde_model = CommonDataElement.objects.get(code=cde_code)
        return cde_model.name
    except CommonDataElement.DoesNotExist:
        return "%s does not exist?" % cde_code
