
from registration.backends.default.views import RegistrationView


class RdrfRegistrationView(RegistrationView):

    registry_code = None

    def get(self, request, *args, **kwargs):
        self.registry_code = kwargs['registry_code']
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        return self.render_to_response(self.get_context_data(form=form))

    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super(RdrfRegistrationView, self).get_context_data(**kwargs)
        context['registry_code'] = self.registry_code
        context["preferred_languages"] = self._get_preferred_languages()
        return context

    def _get_preferred_languages(self):
        # Registration allows choice of preferred language
        # But we allow different sites to expose different values
        # over time without code change via env --> settings
        from django.conf import settings

        # The default list is english only which we don't bother to show
        if len(settings.LANGUAGES) == 1:
            if settings.LANGUAGES[0][0].lower() == "en":
                return []
            
        l = [] 

        class LanguageWrapper:
            def __init__(self, code, name):
                self.code = code
                self.name = name

        for code, name in settings.LANGUAGES:
            l.append(LanguageWrapper(code, name))

        return l
            
