from django import template
from rdrf.models.definition.models import ConsentSection
import logging

logger = logging.getLogger(__name__)

register = template.Library()


@register.filter()
def get_info_text_expression(fields):
    #  ['customconsent_15_13_21', 'customconsent_15_13_22']
    if len(fields) > 0:
        consent_field = fields[0]
        if not consent_field.startswith("customconsent_"):
            return

        consent_section_model_pk = consent_field.split("_")[2]
        try:
            consent_section_model = ConsentSection.objects.get(pk=consent_section_model_pk)
            if consent_section_model.information_text:
                try:
                    field_path = "rdrf://model/ConsentSection/%s/information_text" % consent_section_model.pk
                    return field_path

                except Exception as ex:
                    logger.error(
                        "Error getting custom consent information text for pk %s: %s" %
                        (consent_section_model.pk, ex))
                    return
        except BaseException:
            return
