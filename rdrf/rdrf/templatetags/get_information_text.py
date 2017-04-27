from django import template
from rdrf.models import ConsentSection
from rdrf.utils import process_embedded_html
import logging

logger = logging.getLogger(__name__)

register = template.Library()


@register.filter()
def get_information_text(fields):
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
                    translated_html = process_embedded_html(consent_section_model.information_text, translate=True)
                except Exception as ex:
                    return "Error returting translation: %s" % ex
                
                return translated_html
        except:
            return None
