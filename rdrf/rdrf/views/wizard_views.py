from formtools.wizard.views import SessionWizardView
from django.http import HttpResponseRedirect

from rdrf.forms.dynamic.review_forms import create_review_forms


class ReviewWizardGenerator:
    def __init__(self, review_model):
        self.review_model = review_model
        self.base_class = SessionWizardView

    def create_wizard_class(self):
        form_list = create_review_forms(self.review_model)
        class_name = "ReviewWizard"

        def done_method(myself, form_list, form_dict, **kwargs):
            # when all valid data processed ,
            # fan the data back out
            return HttpResponseRedirect("TODO")

        class_dict = {
            "form_list": form_list,
            "done": done_method,
        }

        wizard_class = type(class_name, (self.base_class,), class_dict)

        return wizard_class
