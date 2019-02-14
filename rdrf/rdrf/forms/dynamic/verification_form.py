from django.forms import BaseForm
from collections import OrderedDict
from rdrf.forms.dynamic.field_lookup import FieldFactory


def make_verification_form(verifications):
    # This allows us to present the clinician's form identically to any clinical form
    # as far as cde widgets etc go.
    form_class_name = "VerificationForm"
    base_fields = OrderedDict()
    data = {}
    # create fields for the clinician to override the patient's responses if necessary
    for verification in verifications:

        cde_field = FieldFactory(verification.registry_model,
                                 verification.form_model,
                                 verification.section_model,
                                 verification.cde_model).create_field()
        field_name = "%s____%s____%s" % (verification.form_model.name,
                                         verification.section_model.code,
                                         verification.cde_model.code)

        if verification.status == "corrected":
            data[field_name] = verification.clinician_data

        base_fields[field_name] = cde_field

    form_class_dict = {"base_fields": base_fields}

    form_class = type(form_class_name, (BaseForm,), form_class_dict)

    if data:
        form = form_class(data)
    else:
        form = form_class()

    return form
