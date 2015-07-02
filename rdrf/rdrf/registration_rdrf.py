from __future__ import absolute_import
from registration.backends.default.views import RegistrationView


class RdrfRegistrationView(RegistrationView):

    registry_code = None

    def get(self, request, *args, **kwargs):
        self.registry_code = kwargs['registry_code']
        form_class = self.get_form_class(request)
        form = self.get_form(form_class)
        return self.render_to_response(self.get_context_data(form=form))

    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class(request)
        form = self.get_form(form_class)

        if form.is_valid():
            return self.form_valid(request, form)
        else:
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super(RdrfRegistrationView, self).get_context_data(**kwargs)
        context['registry_code'] = self.registry_code
        return context
