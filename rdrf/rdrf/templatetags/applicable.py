from django import template

register = template.Library()

# run func on argument


@register.filter()
def applicable(form_model, patient_model):
    return form_model.applicable_to(patient_model)
