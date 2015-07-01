from django import template

register = template.Library()


@register.filter(name='is_patient_relative_widget')
def is_patient_relative_widget(field):
    if field.field.widget.__class__.__name__ == "PatientRelativeLinkWidget":
        return True
    return False
